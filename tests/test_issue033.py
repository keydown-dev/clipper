from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from tests.test_issue006 import FakeClient, configure_default_llm


def _write_source_artifacts(store: Path, name: str, *, sentence_text: str, visual_text: str) -> None:
    root = store / "sources" / name
    (root / "frames").mkdir(parents=True)
    (root / "source.mp4").write_bytes(b"media")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "input_ref": f"{name}.mp4",
                "input_type": "local",
                "canonical_input_ref": f"/abs/{name}.mp4",
                "source_path": "source.mp4",
                "title": name,
                "duration": 30.0,
                "created_at": "2026-06-04T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (root / "transcript.json").write_text(
        json.dumps({"schema_version": 1, "source_file": "source.mp4", "language": "en", "duration": 30.0, "segments": []}),
        encoding="utf-8",
    )
    (root / "sentences.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_file": "source.mp4",
                "language": "en",
                "duration": 30.0,
                "source_transcript_path": "transcript.json",
                "sentences": [
                    {"id": 0, "start": 0.0, "end": 4.0, "text": "outside range", "source_segments": [], "word_ranges": []},
                    {"id": 1, "start": 10.0, "end": 14.0, "text": sentence_text, "source_segments": [], "word_ranges": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "shots.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_file": "source.mp4",
                "detection": {"tool": "test"},
                "shots": [
                    {
                        "id": "shot-0001",
                        "start": 10.0,
                        "end": 14.0,
                        "duration": 4.0,
                        "representative_frame_path": "frames/shot-0001.jpg",
                        "representative_time": 12.0,
                        "quality": {"score": 1.0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "visual-index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_file": "source.mp4",
                "shots_path": "shots.json",
                "provider": {"base_url": "http://vision.test/v1", "model": "vision"},
                "observations": [
                    {
                        "shot_id": "shot-0001",
                        "start": 10.0,
                        "end": 14.0,
                        "representative_time": 12.0,
                        "frame_path": "frames/shot-0001.jpg",
                        "description": visual_text,
                        "visible_people": [],
                        "actions": [],
                        "objects": [],
                        "mood": "",
                        "setting": "",
                        "visible_text": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _install_fake_openai(monkeypatch, responses: list[str], seen: list[dict[str, object]]) -> None:  # type: ignore[no-untyped-def]
    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.chat = FakeClient(responses, seen).chat

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))


def test_project_score_single_source_respects_range_and_writes_project_scores(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    configure_default_llm(monkeypatch)
    store = tmp_path / ".clipper"
    assert main(["create", "story", "--store", str(store)]) == EXIT_SUCCESS
    _write_source_artifacts(store, "source-a", sentence_text="in range laugh", visual_text="in range smile")
    assert main(["include", "story", "source-a", "--start", "9", "--end", "15", "--store", str(store)]) == EXIT_SUCCESS
    seen: list[dict[str, object]] = []
    _install_fake_openai(monkeypatch, ['[{"start":10,"end":14,"score":9,"reason":"laugh"}]'], seen)

    assert main(["score", "story", "--store", str(store), "--with-transcript", "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["artifact_path"] == str(store / "projects" / "story" / "scores.json")
    prompt = seen[0]["messages"][1]["content"]  # type: ignore[index]
    assert "Source source-a transcript: in range laugh" in prompt
    assert "outside range" not in prompt
    scores = json.loads((store / "projects" / "story" / "scores.json").read_text())
    assert scores["segments"][0]["source"] == "source-a"
    assert scores["segments"][0]["dialogue"] == "in range laugh"


def test_project_score_multi_source_keeps_source_tags(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    configure_default_llm(monkeypatch)
    store = tmp_path / ".clipper"
    assert main(["create", "story", "--store", str(store)]) == EXIT_SUCCESS
    _write_source_artifacts(store, "source-a", sentence_text="alpha line", visual_text="alpha visual")
    _write_source_artifacts(store, "source-b", sentence_text="beta line", visual_text="beta visual")
    assert main(["include", "story", "source-a", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["include", "story", "source-b", "--store", str(store)]) == EXIT_SUCCESS
    seen: list[dict[str, object]] = []
    _install_fake_openai(
        monkeypatch,
        ['[{"source":"source-a","start":10,"end":14,"score":8,"reason":"alpha"},{"source":"source-b","start":10,"end":14,"score":9,"reason":"beta"}]'],
        seen,
    )

    assert main(["score", "story", "--store", str(store), "--with-transcript", "--with-visuals", "--json"]) == EXIT_SUCCESS

    prompt = seen[0]["messages"][1]["content"]  # type: ignore[index]
    assert "Source source-a transcript: alpha line" in prompt
    assert "Source source-b transcript: beta line" in prompt
    assert "Source source-a visual" in prompt
    assert "Source source-b visual" in prompt
    scores = json.loads((store / "projects" / "story" / "scores.json").read_text())
    assert [segment["source"] for segment in scores["segments"]] == ["source-a", "source-b"]


def test_project_score_fails_with_no_included_sources(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    configure_default_llm(monkeypatch)
    store = tmp_path / ".clipper"
    assert main(["create", "empty", "--store", str(store)]) == EXIT_SUCCESS

    assert main(["score", "empty", "--store", str(store), "--with-transcript", "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert "no included sources" in payload["error"]["message"]
