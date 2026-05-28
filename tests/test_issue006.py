from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

import pytest

from clipper.cli import EXIT_SUCCESS, main
from clipper.config import ClipperConfig
from clipper.schemas import SchemaError, validate_scores
from clipper.scoring import (
    BASELINE_SYSTEM_PROMPT,
    ScoringOptions,
    TranscriptWindow,
    build_messages,
    chunk_transcript,
    merge_overlapping_segments,
    parse_segments_response,
    score_transcript,
    validate_normalize_segments,
)


class Message:
    def __init__(self, content: str) -> None:
        self.content = content


class Choice:
    def __init__(self, content: str) -> None:
        self.message = Message(content)


class Response:
    def __init__(self, content: str) -> None:
        self.choices = [Choice(content)]


class FakeCompletions:
    def __init__(self, responses: list[str], seen: list[dict[str, object]]) -> None:
        self.responses = responses
        self.seen = seen

    def create(self, **kwargs: object) -> Response:
        self.seen.append(kwargs)
        return Response(self.responses.pop(0))


class FakeClient:
    def __init__(self, responses: list[str], seen: list[dict[str, object]] | None = None) -> None:
        self.seen = seen if seen is not None else []
        self.chat = types.SimpleNamespace(completions=FakeCompletions(responses, self.seen))


def make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "clips").mkdir()
    (root / "output").mkdir()
    (root / "source" / "source.mp4").write_bytes(b"fake")
    transcript = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": "en",
        "duration": 20.0,
        "segments": [
            {"id": 0, "start": 0.0, "end": 5.0, "text": "calm intro"},
            {"id": 1, "start": 5.0, "end": 12.0, "text": "hosts laugh loudly"},
            {"id": 2, "start": 12.0, "end": 20.0, "text": "wrap up"},
        ],
    }
    (root / "work" / "transcript.json").write_text(json.dumps(transcript), encoding="utf-8")
    return store, root


def test_prompt_construction_includes_baseline_directive_and_timestamps() -> None:
    window = TranscriptWindow(0.0, 12.0, [{"start": 1.0, "end": 4.5, "text": "big laugh"}])

    messages = build_messages(directive="Find laughter", window=window)

    assert messages[0]["content"] == BASELINE_SYSTEM_PROMPT
    assert "Directive: Find laughter" in messages[1]["content"]
    assert "[1.00-4.50] big laugh" in messages[1]["content"]
    assert "Prefer 5-15 second segments" in messages[1]["content"]


def test_chunk_transcript_uses_ten_minute_windows_with_overlap() -> None:
    transcript = {
        "duration": 1300.0,
        "segments": [
            {"id": i, "start": float(i * 100), "end": float(i * 100 + 10), "text": str(i)}
            for i in range(13)
        ],
    }

    windows = chunk_transcript(transcript)

    assert [(w.start, w.end) for w in windows] == [(0.0, 600.0), (570.0, 1170.0), (1140.0, 1300.0)]
    assert any(seg["id"] == 6 for seg in windows[0].segments)
    assert any(seg["id"] == 6 for seg in windows[1].segments)


def test_parse_response_extracts_array_from_markdown_wrappers() -> None:
    response = "Here you go:\n```json\n[{\"start\":1,\"end\":8,\"score\":7,\"reason\":\"laugh\"}]\n```"

    assert parse_segments_response(response) == [{"start": 1, "end": 8, "score": 7, "reason": "laugh"}]


def test_invalid_json_retries_with_stricter_instruction() -> None:
    client = FakeClient(["not json", '[{"start":5,"end":14,"score":8,"reason":"hosts laugh"}]'])
    transcript = {"duration": 20.0, "segments": [{"id": 0, "start": 0.0, "end": 20.0, "text": "hosts laugh"}]}

    segments, warnings = score_transcript(transcript, client=client, options=ScoringOptions(directive="Find laughs", model="model"))

    assert segments == [{"start": 5.0, "end": 14.0, "score": 8.0, "reason": "hosts laugh"}]
    assert "Your previous response was not valid" in client.seen[1]["messages"][0]["content"]
    assert any("retried invalid JSON" in warning for warning in warnings)


def test_validation_clamps_drops_bad_scores_and_warns() -> None:
    valid, warnings = validate_normalize_segments(
        [
            {"start": -1, "end": 6, "score": 7, "reason": "near beginning"},
            {"start": 7, "end": 9, "score": 11, "reason": "too high"},
            {"start": 15, "end": 12, "score": 5, "reason": "bad times"},
        ],
        lower_bound=0.0,
        upper_bound=20.0,
    )

    assert valid == [{"start": 0.0, "end": 6.0, "score": 7.0, "reason": "near beginning"}]
    assert any("clamped segment 0" in warning for warning in warnings)
    assert any("score 11 outside 0-10" in warning for warning in warnings)
    assert any("end <= start" in warning for warning in warnings)


def test_overlap_handling_prefers_stronger_score() -> None:
    merged = merge_overlapping_segments(
        [
            {"start": 10.0, "end": 20.0, "score": 6.0, "reason": "ok"},
            {"start": 15.0, "end": 25.0, "score": 9.0, "reason": "better"},
            {"start": 30.0, "end": 35.0, "score": 7.0, "reason": "separate"},
        ]
    )

    assert merged == [
        {"start": 10.0, "end": 25.0, "score": 9.0, "reason": "better"},
        {"start": 30.0, "end": 35.0, "score": 7.0, "reason": "separate"},
    ]


def test_score_cli_writes_scores_without_real_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    store, root = make_workspace(tmp_path)
    seen: list[dict[str, object]] = []

    class FakeOpenAI:
        def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
            assert base_url == "https://ollama.com/v1"
            assert api_key == "not-needed"
            assert timeout == 60.0
            self.chat = FakeClient(['[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]'], seen).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--directive", "Find laughter", "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["result"]["segments"] == 1
    assert seen[0]["model"] == "deepseek-v4-flash"
    assert seen[0]["temperature"] == 0.0
    assert seen[0]["timeout"] == 60.0
    scores = json.loads((root / "work" / "scores.json").read_text())
    assert scores["directive"] == "Find laughter"
    assert scores["segments"] == [{"start": 5.0, "end": 15.0, "score": 8.0, "reason": "hosts laugh"}]
    assert validate_scores(scores) == scores


def test_score_cli_empty_valid_segments_writes_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(['[{"start":5,"end":15,"score":12,"reason":"bad"}]']).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--json"]) == EXIT_SUCCESS

    assert json.loads(capsys.readouterr().out)["result"]["segments"] == 0
    scores = json.loads((root / "work" / "scores.json").read_text())
    assert scores["segments"] == []
    assert any("no valid candidate segments" in warning for warning in scores["warnings"])


def test_scores_schema_rejects_bad_segment_shape() -> None:
    with pytest.raises(SchemaError, match="segment.start"):
        validate_scores({"schema_version": 1, "source_file": "source/source.mp4", "directive": "x", "segments": [{"start": "bad", "end": 1, "score": 5, "reason": "x"}]})


@pytest.mark.skipif(os.environ.get("CLIPPER_RUN_LLM_TESTS") != "1", reason="real LLM test gated by CLIPPER_RUN_LLM_TESTS=1")
def test_real_llm_smoke_only_when_enabled() -> None:
    from clipper.scoring import make_openai_client

    config = ClipperConfig()
    client = make_openai_client(config)
    transcript = {"duration": 20.0, "segments": [{"id": 0, "start": 0.0, "end": 20.0, "text": "The hosts laugh loudly at a surprising reveal."}]}
    segments, _ = score_transcript(transcript, client=client, options=ScoringOptions(directive="Find laughter", model=config.llm_model))
    assert isinstance(segments, list)
