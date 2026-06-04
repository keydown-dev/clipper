from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def test_source_ingests_local_file_to_flattened_source_layout(monkeypatch, capsys, tmp_path: Path) -> None:
    media = tmp_path / "input.mov"
    media.write_bytes(b"fake media")
    store = tmp_path / ".clipper"
    monkeypatch.setattr("clipper.cli._probe_duration", lambda path: 12.5)

    assert main(["source", str(media), "--name", "my-source", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    root = store / "sources" / "my-source"
    assert payload["ok"] is True
    assert payload["result"]["source"] == "my-source"
    assert payload["result"]["source_path"] == "source.mov"
    assert payload["artifact_path"] == str(root / "metadata.json")
    assert (root / "source.mov").read_bytes() == b"fake media"
    metadata = json.loads((root / "metadata.json").read_text())
    assert metadata["input_type"] == "local"
    assert metadata["source_path"] == "source.mov"
    assert metadata["duration"] == 12.5


def test_source_reuse_and_force_follow_output_policy(monkeypatch, capsys, tmp_path: Path) -> None:
    media = tmp_path / "input.mp4"
    media.write_bytes(b"v1")
    store = tmp_path / ".clipper"
    monkeypatch.setattr("clipper.cli._probe_duration", lambda path: 1.0)

    assert main(["source", str(media), "--name", "same", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["source", str(media), "--name", "same", "--store", str(store), "--json"]) == EXIT_FAILURE
    assert "output already exists" in json.loads(capsys.readouterr().out.splitlines()[-1])["error"]["message"]

    assert main(["source", str(media), "--name", "same", "--store", str(store), "--reuse", "--json"]) == EXIT_SUCCESS
    assert json.loads(capsys.readouterr().out)["result"]["reused"] is True

    media.write_bytes(b"v2")
    assert main(["source", str(media), "--name", "same", "--store", str(store), "--force"]) == EXIT_SUCCESS
    assert (store / "sources" / "same" / "source.mp4").read_bytes() == b"v2"


def test_source_remote_uses_ytdlp_proxy_and_flattened_json(monkeypatch, capsys, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            seen["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, input_ref: str, *, download: bool):
            seen["input_ref"] = input_ref
            seen["download"] = download
            outtmpl = Path(seen["options"]["outtmpl"])
            target = outtmpl.parent / "source.webm"
            target.write_bytes(b"remote media")
            return {"duration": 9, "title": "Remote Title", "webpage_url": input_ref, "extractor": "fake"}

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    store = tmp_path / ".clipper"

    assert main(["source", "https://example.com/watch?v=1", "--name", "remote", "--proxy", "http://proxy", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    root = store / "sources" / "remote"
    assert seen["input_ref"] == "https://example.com/watch?v=1"
    assert seen["download"] is True
    assert seen["options"]["proxy"] == "http://proxy"
    assert payload["result"]["source"] == "remote"
    assert payload["result"]["source_path"] == "source.webm"
    metadata = json.loads((root / "metadata.json").read_text())
    assert metadata["input_type"] == "remote"
    assert metadata["source_path"] == "source.webm"
    assert metadata["source_url"] == "https://example.com/watch?v=1"


def test_start_is_deprecated_alias_for_source_ingestion(monkeypatch, capsys, tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    store = tmp_path / ".clipper"
    monkeypatch.setattr("clipper.cli._probe_duration", lambda path: 2.0)

    assert main(["start", str(media), "--name", "alias", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["deprecated_alias"] == "start"
    assert payload["result"]["source"] == "alias"
    assert (store / "sources" / "alias" / "source.mp4").exists()
    assert (store / "sources" / "alias" / "metadata.json").exists()
