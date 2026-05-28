from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.schemas import SchemaError, validate_transcript


class FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


class FakeInfo:
    language = "en"
    duration = 3.5


def make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "clips").mkdir()
    (root / "output").mkdir()
    (root / "source" / "source.mp4").write_bytes(b"fake")
    metadata = {
        "schema_version": 1,
        "input_ref": "input.mp4",
        "input_type": "local",
        "canonical_input_ref": "/abs/input.mp4",
        "source_path": "source/source.mp4",
        "title": "Video",
        "duration": 10.0,
        "created_at": "2026-05-28T00:00:00Z",
    }
    (root / "work" / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return store, root


def install_fake_whisper(monkeypatch: pytest.MonkeyPatch, seen: dict[str, object], *, fail_load: bool = False) -> None:
    class FakeWhisperModel:
        def __init__(self, model: str, *, device: str, compute_type: str) -> None:
            seen["model"] = model
            seen["device"] = device
            seen["compute_type"] = compute_type
            if fail_load:
                raise RuntimeError("bad model")

        def transcribe(self, path: str, *, language: str | None = None):
            seen["path"] = path
            seen["language"] = language
            return [FakeSegment(0.0, 1.25, " hello "), FakeSegment(1.25, 3.5, "world")], FakeInfo()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))


def test_transcribe_writes_schema_with_mocked_whisper(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)
    seen: dict[str, object] = {}
    install_fake_whisper(monkeypatch, seen)

    assert main(["transcribe", "video", "--store", str(store), "--model", "tiny", "--device", "cpu", "--compute-type", "int8", "--language", "en", "--json"]) == EXIT_SUCCESS

    assert seen == {"model": "tiny", "device": "cpu", "compute_type": "int8", "path": str(root / "source" / "source.mp4"), "language": "en"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["video"] == "video"
    assert payload["result"]["segments"] == 2
    transcript = json.loads((root / "work" / "transcript.json").read_text())
    assert transcript == {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": "en",
        "duration": 3.5,
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.25, "text": "hello"},
            {"id": 1, "start": 1.25, "end": 3.5, "text": "world"},
        ],
    }
    assert validate_transcript(transcript) == transcript


def test_transcript_schema_rejects_missing_segment_fields() -> None:
    with pytest.raises(SchemaError, match="missing required field"):
        validate_transcript({"schema_version": 1, "source_file": "source/source.mp4", "language": None, "duration": 1, "segments": [{"id": 0, "start": 0, "end": 1}]})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("id", "0", "segment.id"), ("start", "0", "segment.start"), ("end", "1", "segment.end"), ("text", 1, "segment.text")],
)
def test_transcript_schema_checks_segment_id_start_end_and_text(field: str, value: object, message: str) -> None:
    segment = {"id": 0, "start": 0.0, "end": 1.0, "text": "hi"}
    segment[field] = value
    with pytest.raises(SchemaError, match=message):
        validate_transcript({"schema_version": 1, "source_file": "source/source.mp4", "language": None, "duration": 1, "segments": [segment]})


def test_transcribe_output_policy_reuse_and_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)
    seen: dict[str, object] = {}
    install_fake_whisper(monkeypatch, seen)

    assert main(["transcribe", "video", "--store", str(store)]) == EXIT_SUCCESS
    capsys.readouterr()
    assert main(["transcribe", "video", "--store", str(store), "--json"]) == EXIT_FAILURE
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "artifact_error"

    assert main(["transcribe", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_SUCCESS
    assert json.loads(capsys.readouterr().out)["result"]["reused"] is True

    assert main(["transcribe", "video", "--store", str(store), "--force", "--json"]) == EXIT_SUCCESS
    assert json.loads(capsys.readouterr().out)["result"]["reused"] is False


def test_whisper_model_load_failure_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, _ = make_workspace(tmp_path)
    install_fake_whisper(monkeypatch, {}, fail_load=True)

    assert main(["transcribe", "video", "--store", str(store), "--model", "missing", "--json"]) == EXIT_FAILURE
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    message = payload["error"]["message"]
    assert "could not load Whisper model" in message
    assert "missing" in message
    assert "Check the model name" in message


def test_transcribe_help_routes_to_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["transcribe", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "usage: clipper transcribe" in output
    assert "--language" in output
    assert "--model" in output
    assert "--compute-type" in output


@pytest.mark.skipif(os.environ.get("CLIPPER_RUN_WHISPER_TESTS") != "1", reason="set CLIPPER_RUN_WHISPER_TESTS=1 to run real faster-whisper integration")
def test_real_whisper_integration_is_env_gated(tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    wav = root / "source" / "source.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(wav)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (root / "source" / "source.mp4").unlink()
    metadata_path = root / "work" / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["source_path"] = "source/source.wav"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert main(["transcribe", "video", "--store", str(store), "--model", "tiny"]) == EXIT_SUCCESS
    assert (root / "work" / "transcript.json").exists()
