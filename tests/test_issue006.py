from __future__ import annotations

import io
import json
import os
import sys
import types
from pathlib import Path

import pytest

from clipper.cli import EXIT_SUCCESS, main
from clipper.config import ClipperConfig
from clipper.progress import CliProgress
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
    def __init__(self, content: str, usage: dict[str, int] | None = None) -> None:
        self.choices = [Choice(content)]
        if usage is not None:
            self.usage = usage


class FakeCompletions:
    def __init__(self, responses: list[str | tuple[str, dict[str, int]]], seen: list[dict[str, object]]) -> None:
        self.responses = responses
        self.seen = seen

    def create(self, **kwargs: object) -> Response:
        self.seen.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, tuple):
            return Response(response[0], response[1])
        return Response(response)


class FakeClient:
    def __init__(self, responses: list[str | tuple[str, dict[str, int]]], seen: list[dict[str, object]] | None = None) -> None:
        self.seen = seen if seen is not None else []
        self.chat = types.SimpleNamespace(completions=FakeCompletions(responses, self.seen))


def configure_default_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://ollama.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_TEMPERATURE", "0")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")


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
    sentence_transcript = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": "en",
        "duration": 20.0,
        "source_transcript_path": "work/transcript.json",
        "sentences": [
            {"id": 0, "start": 0.0, "end": 5.0, "text": "calm intro", "source_segments": [0], "word_ranges": []},
            {"id": 1, "start": 5.0, "end": 12.0, "text": "hosts laugh loudly", "source_segments": [1], "word_ranges": []},
            {"id": 2, "start": 12.0, "end": 20.0, "text": "wrap up", "source_segments": [2], "word_ranges": []},
        ],
    }
    (root / "work" / "sentences.json").write_text(json.dumps(sentence_transcript), encoding="utf-8")
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
    configure_default_llm(monkeypatch)
    store, root = make_workspace(tmp_path)
    seen: list[dict[str, object]] = []

    class FakeOpenAI:
        def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
            assert base_url == "https://ollama.com/v1"
            assert api_key == "not-needed"
            assert timeout == 60.0
            self.chat = FakeClient(['[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]'], seen).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--directive", "Find laughter", "--with-transcript", "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["result"]["segments"] == 1
    assert seen[0]["model"] == "deepseek-v4-flash"
    assert seen[0]["temperature"] == 0.0
    assert seen[0]["timeout"] == 60.0
    scores = json.loads((root / "work" / "scores.json").read_text())
    assert scores["directive"] == "Find laughter"
    assert scores["segments"][0]["start"] == 5.0
    assert scores["segments"][0]["end"] == 15.0
    assert scores["segments"][0]["score"] == 8.0
    assert scores["segments"][0]["reason"] == "hosts laugh"
    assert scores["segments"][0]["dialogue"] == "calm intro hosts laugh loudly wrap up"
    assert validate_scores(scores) == scores


def test_score_cli_empty_valid_segments_writes_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(['[{"start":5,"end":15,"score":12,"reason":"bad"}]']).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--json"]) == EXIT_SUCCESS

    assert json.loads(capsys.readouterr().out)["result"]["segments"] == 0
    scores = json.loads((root / "work" / "scores.json").read_text())
    assert scores["segments"] == []
    assert any("no valid candidate segments" in warning for warning in scores["warnings"])


def test_scores_schema_rejects_bad_segment_shape() -> None:
    with pytest.raises(SchemaError, match="segment.start"):
        validate_scores({"schema_version": 1, "source_file": "source/source.mp4", "directive": "x", "segments": [{"start": "bad", "end": 1, "score": 5, "reason": "x"}]})


def test_non_verbose_scoring_stderr_remains_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_default_llm(monkeypatch)
    store, _ = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(['[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]']).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--directive", "Find laughter", "--with-transcript", "--json"]) == EXIT_SUCCESS

    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is True
    assert captured.err == ""


def test_score_cli_verbose_logs_to_stderr_and_json_stdout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_default_llm(monkeypatch)
    store, _ = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient([('[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]', {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14})]).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--directive", "Find laughter", "--with-transcript", "--json", "--verbose"]) == EXIT_SUCCESS

    captured = capsys.readouterr()
    assert json.loads(captured.out)["result"]["segments"] == 1
    assert "video video: transcript=" in captured.err
    assert "scoring directive: Find laughter" in captured.err
    assert "model=deepseek-v4-flash" in captured.err
    assert "temperature=0.0" in captured.err
    assert "timeout=60.0" in captured.err
    assert "transcript duration=20.0 segments=3" in captured.err
    assert "scoring windows=1" in captured.err
    assert "scoring progress: window 1/1 (100%)" in captured.err
    assert "token usage: prompt=10 completion=4 total=14" in captured.err
    assert "scores output=" in captured.err


def test_score_progress_reaches_100_for_transcript_windows() -> None:
    transcript = {
        "duration": 1300.0,
        "segments": [{"id": i, "start": float(i * 100), "end": float(i * 100 + 10), "text": str(i)} for i in range(13)],
    }
    stream = io.StringIO()
    client = FakeClient([
        '[{"start":1,"end":8,"score":7,"reason":"one"}]',
        '[{"start":610,"end":618,"score":8,"reason":"two"}]',
        '[{"start":1201,"end":1208,"score":9,"reason":"three"}]',
    ])

    score_transcript(
        transcript,
        client=client,
        options=ScoringOptions(directive="Find moments", model="model"),
        progress=CliProgress(enabled=True, stream=stream),
    )

    err = stream.getvalue()
    assert "scoring progress: window 1/3 (33%)" in err
    assert "scoring progress: window 2/3 (66%)" in err
    assert "scoring progress: window 3/3 (100%)" in err
    assert "\r" not in err


def test_verbose_reports_unavailable_token_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_default_llm(monkeypatch)
    store, _ = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(['[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]']).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--json", "--verbose"]) == EXIT_SUCCESS

    assert "token usage unavailable: API did not provide usage metadata" in capsys.readouterr().err


def test_retry_usage_is_included_in_verbose_totals(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_default_llm(monkeypatch)
    store, _ = make_workspace(tmp_path)

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient([
                ("not json", {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9}),
                ('[{"start":5,"end":15,"score":8,"reason":"hosts laugh"}]', {"prompt_tokens": 11, "completion_tokens": 5, "total_tokens": 16}),
            ]).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--json", "--verbose"]) == EXIT_SUCCESS

    err = capsys.readouterr().err
    assert "retrying invalid JSON" in err
    assert "token usage: prompt=18 completion=7 total=25" in err


def test_reuse_verbose_does_not_call_llm_or_show_progress(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    configure_default_llm(monkeypatch)
    store, root = make_workspace(tmp_path)
    (root / "work" / "scores.json").write_text(
        json.dumps({"schema_version": 1, "source_file": "source/source.mp4", "directive": "old", "segments": []}),
        encoding="utf-8",
    )

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            raise AssertionError("LLM should not be instantiated when reusing scores")

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    assert main(["score", "video", "--store", str(store), "--with-transcript", "--reuse", "--json", "--verbose"]) == EXIT_SUCCESS

    captured = capsys.readouterr()
    assert json.loads(captured.out)["result"]["reused"] is True
    assert "reusing existing scores" in captured.err
    assert "scoring progress" not in captured.err


@pytest.mark.skipif(os.environ.get("CLIPPER_RUN_LLM_TESTS") != "1", reason="real LLM test gated by CLIPPER_RUN_LLM_TESTS=1")
def test_real_llm_smoke_only_when_enabled() -> None:
    from clipper.scoring import make_openai_client

    config = ClipperConfig()
    client = make_openai_client(config)
    transcript = {"duration": 20.0, "segments": [{"id": 0, "start": 0.0, "end": 20.0, "text": "The hosts laugh loudly at a surprising reveal."}]}
    segments, _ = score_transcript(transcript, client=client, options=ScoringOptions(directive="Find laughter", model=config.llm_model))
    assert isinstance(segments, list)
