from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


class FakeWord:
    def __init__(self, word: str, start: float, end: float) -> None:
        self.word = word
        self.start = start
        self.end = end


class FakeSegment:
    def __init__(self, start: float, end: float, text: str, words: list[FakeWord]) -> None:
        self.start = start
        self.end = end
        self.text = text
        self.words = words


class FakeInfo:
    language = "en"
    duration = 3.0


class FakeCompletions:
    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps({"description": "A speaker at a desk.", "objects": ["desk"]})}}]}


class FakeClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions()})()


def make_source(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "sources" / "episode"
    root.mkdir(parents=True)
    (root / "source.mp4").write_bytes(b"fake")
    metadata = {
        "schema_version": 1,
        "input_ref": "input.mp4",
        "input_type": "local",
        "canonical_input_ref": "/abs/input.mp4",
        "source_path": "source.mp4",
        "title": "Episode",
        "duration": 10.0,
        "created_at": "2026-06-04T00:00:00Z",
    }
    (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return store, root


def install_fake_whisper(monkeypatch, seen: dict[str, object]) -> None:  # type: ignore[no-untyped-def]
    class FakeWhisperModel:
        def __init__(self, model: str, *, device: str, compute_type: str) -> None:
            pass

        def transcribe(self, path: str, *, language: str | None = None, word_timestamps: bool = False):
            seen["path"] = path
            seen["word_timestamps"] = word_timestamps
            return [FakeSegment(0.0, 3.0, "hello world.", [FakeWord("hello", 0.0, 1.0), FakeWord("world.", 1.0, 3.0)])], FakeInfo()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))


def test_transcribe_source_writes_flattened_artifacts(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    store, root = make_source(tmp_path)
    seen: dict[str, object] = {}
    install_fake_whisper(monkeypatch, seen)

    assert main(["transcribe", "episode", "--store", str(store), "--json"]) == EXIT_SUCCESS

    assert seen == {"path": str(root / "source.mp4"), "word_timestamps": True}
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["video"] == "episode"
    transcript = json.loads((root / "transcript.json").read_text())
    sentences = json.loads((root / "sentences.json").read_text())
    assert transcript["source_file"] == "source.mp4"
    assert sentences["source_transcript_path"] == "transcript.json"
    assert not (root / "work" / "transcript.json").exists()


def test_transcribe_source_reuse_requires_complete_output_set(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    store, root = make_source(tmp_path)
    install_fake_whisper(monkeypatch, {})
    assert main(["transcribe", "episode", "--store", str(store), "--json"]) == EXIT_SUCCESS
    (root / "sentences.json").unlink()

    assert main(["transcribe", "episode", "--store", str(store), "--reuse", "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["ok"] is False
    assert "complete output set" in payload["error"]["message"]


def test_shots_source_writes_frames_and_contact_sheet(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    store, root = make_source(tmp_path)
    monkeypatch.setattr("clipper.shots.detect_shot_ranges", lambda *_, **__: [(0.0, 4.0)])
    monkeypatch.setattr("clipper.shots.choose_representative_frame", lambda *_, **__: (2.0, {"score": 1.0}))
    monkeypatch.setattr("clipper.shots.extract_frame_jpeg", lambda source, output, timestamp: output.write_bytes(b"jpg"))
    monkeypatch.setattr("clipper.shots._write_contact_sheet", lambda frames, output: output.write_bytes(b"sheet"))

    assert main(["shots", "episode", "--store", str(store), "--contact-sheet", "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    manifest = json.loads((root / "shots.json").read_text())
    assert manifest["source_file"] == "source.mp4"
    assert manifest["shots"][0]["representative_frame_path"] == "frames/shot-0001.jpg"
    assert manifest["contact_sheet_path"] == "shot-contact-sheet.jpg"
    assert (root / "frames" / "shot-0001.jpg").exists()
    assert (root / "shot-contact-sheet.jpg").exists()


def test_visual_source_reads_frames_and_writes_flattened_index(monkeypatch, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    store, root = make_source(tmp_path)
    (root / "frames").mkdir()
    (root / "frames" / "shot-0001.jpg").write_bytes(b"jpg")
    shots = {
        "schema_version": 1,
        "source_file": "source.mp4",
        "shots": [
            {
                "id": "shot-0001",
                "start": 0.0,
                "end": 3.0,
                "duration": 3.0,
                "representative_frame_path": "frames/shot-0001.jpg",
                "representative_time": 1.5,
                "quality": {"score": 1.0},
            }
        ],
        "detection": {"tool": "test"},
    }
    (root / "shots.json").write_text(json.dumps(shots), encoding="utf-8")
    monkeypatch.setenv("LLM_BASE_URL", "http://vision.test/v1")
    monkeypatch.setenv("LLM_MODEL", "vision-model")
    monkeypatch.setattr("clipper.visual.make_openai_client", lambda options: FakeClient())

    assert main(["visual", "episode", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    index = json.loads((root / "visual-index.json").read_text())
    assert index["source_file"] == "source.mp4"
    assert index["shots_path"] == "shots.json"
    assert index["observations"][0]["frame_path"] == "frames/shot-0001.jpg"
