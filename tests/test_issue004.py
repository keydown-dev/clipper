from __future__ import annotations

import json
from pathlib import Path

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def test_start_local_file_copies_source_and_writes_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "Input Video.mov"
    src.write_bytes(b"fake-video")
    monkeypatch.setattr("clipper.cli._probe_duration", lambda path: 12.5)

    assert main(["start", str(src), "--name", "my_video", "--store", str(tmp_path / ".clipper"), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["video"] == "my_video"
    result = payload["result"]
    assert result["path"] == str(tmp_path / ".clipper" / "my_video")
    source = tmp_path / ".clipper" / "my_video" / "source" / "source.mov"
    assert source.read_bytes() == b"fake-video"
    metadata = json.loads((tmp_path / ".clipper" / "my_video" / "work" / "metadata.json").read_text())
    assert metadata["schema_version"] == 1
    assert metadata["input_ref"] == str(src)
    assert metadata["input_type"] == "local"
    assert metadata["canonical_input_ref"] == str(src.resolve())
    assert metadata["source_path"] == "source/source.mov"
    assert metadata["title"] == "Input Video"
    assert metadata["duration"] == 12.5
    assert metadata["created_at"].endswith("Z")


def test_start_output_policy_fail_reuse_and_force(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "video.mp4"
    src.write_bytes(b"v1")
    monkeypatch.setattr("clipper.cli._probe_duration", lambda path: 1.0)
    store = tmp_path / ".clipper"

    assert main(["start", str(src), "--name", "same", "--store", str(store)]) == EXIT_SUCCESS
    capsys.readouterr()
    assert main(["start", str(src), "--name", "same", "--store", str(store), "--json"]) == EXIT_FAILURE
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "artifact_error"

    assert main(["start", str(src), "--name", "same", "--store", str(store), "--reuse", "--json"]) == EXIT_SUCCESS
    assert json.loads(capsys.readouterr().out)["result"]["reused"] is True

    src.write_bytes(b"v2")
    assert main(["start", str(src), "--name", "same", "--store", str(store), "--force"]) == EXIT_SUCCESS
    assert (store / "same" / "source" / "source.mp4").read_bytes() == b"v2"


def test_start_remote_download_is_mockable_forwards_proxy_and_records_extras(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    seen: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            seen["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download):
            seen["url"] = url
            seen["download"] = download
            outtmpl = Path(seen["options"]["outtmpl"])
            target = outtmpl.with_name("source.mp4")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"download")
            return {"title": "Remote Title", "duration": 9, "id": "abc", "webpage_url": url, "thumbnail": "https://t", "extractor": "fake"}

    monkeypatch.setattr("clipper.cli.YoutubeDL", FakeYoutubeDL, raising=False)
    import types
    import sys

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=FakeYoutubeDL))

    url = "https://Example.com/watch?v=2"
    assert main(["start", url, "--name", "remote", "--store", str(tmp_path / ".clipper"), "--proxy", "http://proxy", "--json"]) == EXIT_SUCCESS
    assert seen["url"] == url
    assert seen["download"] is True
    assert seen["options"]["format"] == "bestvideo[height<=720]+bestaudio/best[height<=720]"
    assert seen["options"]["proxy"] == "http://proxy"
    metadata = json.loads((tmp_path / ".clipper" / "remote" / "work" / "metadata.json").read_text())
    assert metadata["input_type"] == "remote"
    assert metadata["canonical_input_ref"] == "https://example.com/watch?v=2"
    assert metadata["source_path"] == "source/source.mp4"
    assert metadata["title"] == "Remote Title"
    assert metadata["duration"] == 9.0
    assert metadata["video_id"] == "abc"
    assert metadata["thumbnail_url"] == "https://t"
    assert metadata["extractor"] == "fake"
    assert json.loads(capsys.readouterr().out)["result"]["source_path"] == "source/source.mp4"


def test_start_remote_download_failure_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download):
            raise RuntimeError("boom")

    import types
    import sys

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    assert main(["start", "https://example.com/v", "--name", "bad", "--store", str(tmp_path / ".clipper"), "--json"]) == EXIT_FAILURE
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "download failed" in payload["error"]["message"]
    assert "proxy" in payload["error"]["message"]
