from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.cutting import CutOptions, cut_video, ffmpeg_cut_command, merge_overlapping_segments
from tests.helpers.generated_media import assert_duration_close, generate_test_video, has_audio_stream, probe_duration


def make_workspace(tmp_path: Path, segments: list[dict[str, object]], *, source_bytes: bytes = b"fake") -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "clips").mkdir()
    (root / "output").mkdir()
    (root / "source" / "source.mp4").write_bytes(source_bytes)
    scores = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "directive": "Find highlights",
        "segments": segments,
    }
    (root / "work" / "scores.json").write_text(json.dumps(scores), encoding="utf-8")
    return store, root


def test_cut_filters_merges_names_and_invokes_ffmpeg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(
        tmp_path,
        [
            {"start": 0.0, "end": 2.0, "score": 5.0, "reason": "too low"},
            {"start": 3.0, "end": 6.0, "score": 7.0, "reason": "first"},
            {"start": 5.0, "end": 8.0, "score": 9.0, "reason": "overlap"},
            {"start": 9.0, "end": 10.0, "score": 6.0, "reason": "separate"},
        ],
    )
    seen: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        seen.append(command)
        Path(command[-1]).write_bytes(b"clip")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.cutting.subprocess.run", fake_run)

    _, _, manifest, reused = cut_video(store=store, video="video", options=CutOptions(min_score=6.0))

    assert reused is False
    assert [clip["id"] for clip in manifest["clips"]] == ["clip-0001", "clip-0002"]
    assert manifest["clips"][0] == {
        "id": "clip-0001",
        "path": "clips/clip-0001.mp4",
        "start": 3.0,
        "end": 8.0,
        "duration": 5.0,
        "score": 9.0,
        "reason": "first; overlap",
    }
    assert seen[0] == ["ffmpeg", "-y", "-ss", "3", "-to", "8", "-i", str(root / "source" / "source.mp4"), "-c", "copy", str(root / "clips" / "clip-0001.mp4")]
    assert json.loads((root / "work" / "clips.json").read_text()) == manifest


def test_silent_ffmpeg_command_adds_audio_strip() -> None:
    command = ffmpeg_cut_command(source=Path("source.mp4"), output=Path("out.mp4"), start=1.5, end=3.0, silent=True)

    assert command == ["ffmpeg", "-y", "-ss", "1.5", "-to", "3", "-i", "source.mp4", "-c", "copy", "-an", "out.mp4"]


def test_no_passing_segments_fails_without_manifest_or_clips(tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path, [{"start": 0, "end": 1, "score": 5, "reason": "low"}])

    assert main(["cut", "video", "--store", str(store), "--min-score", "6", "--json"]) == EXIT_FAILURE

    assert not (root / "work" / "clips.json").exists()
    assert list((root / "clips").glob("*.mp4")) == []


def test_partial_outputs_are_cleaned_up_on_ffmpeg_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(
        tmp_path,
        [
            {"start": 0, "end": 1, "score": 8, "reason": "one"},
            {"start": 2, "end": 3, "score": 8, "reason": "two"},
        ],
    )
    calls = 0

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        Path(command[-1]).write_bytes(b"partial")
        if calls == 2:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.cutting.subprocess.run", fake_run)

    with pytest.raises(ValueError, match="ffmpeg cut failed"):
        cut_video(store=store, video="video", options=CutOptions())

    assert not (root / "work" / "clips.json").exists()
    assert list((root / "clips").glob("*.mp4")) == []


def test_reuse_requires_manifest_and_clip_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path, [{"start": 0, "end": 1, "score": 8, "reason": "one"}])
    monkeypatch.setattr("clipper.cutting.subprocess.run", lambda command, **_: (Path(command[-1]).write_bytes(b"clip"), SimpleNamespace(returncode=0, stdout="", stderr=""))[1])
    assert main(["cut", "video", "--store", str(store), "--json"]) == EXIT_SUCCESS
    (root / "clips" / "clip-0001.mp4").unlink()

    assert main(["cut", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_FAILURE


def test_generated_video_can_be_cut_with_audio_and_silent_modes(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "clips").mkdir()
    (root / "output").mkdir()
    generate_test_video(root / "source", duration=6.0, audio=True)
    scores = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "directive": "Find highlights",
        "segments": [{"start": 0.0, "end": 2.0, "score": 8.0, "reason": "opening"}],
    }
    (root / "work" / "scores.json").write_text(json.dumps(scores), encoding="utf-8")

    assert main(["cut", "video", "--store", str(store), "--json"]) == EXIT_SUCCESS
    clip = root / "clips" / "clip-0001.mp4"
    assert_duration_close(probe_duration(clip), 2.0)
    assert has_audio_stream(clip)

    assert main(["cut", "video", "--store", str(store), "--force", "--silent", "--json"]) == EXIT_SUCCESS
    assert not has_audio_stream(clip)


def test_human_and_json_output(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, _ = make_workspace(tmp_path, [{"start": 0, "end": 1, "score": 8, "reason": "one"}])
    monkeypatch.setattr("clipper.cutting.subprocess.run", lambda command, **_: (Path(command[-1]).write_bytes(b"clip"), SimpleNamespace(returncode=0, stdout="", stderr=""))[1])

    assert main(["cut", "video", "--store", str(store)]) == EXIT_SUCCESS
    assert "Cut video video" in capsys.readouterr().out
    assert main(["cut", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["result"]["clip_count"] == 1
    assert payload["result"]["reused"] is True


def test_merge_overlapping_segments_does_not_merge_touching_boundaries() -> None:
    assert merge_overlapping_segments([
        {"start": 0, "end": 1, "score": 8, "reason": "a"},
        {"start": 1, "end": 2, "score": 9, "reason": "b"},
    ]) == [
        {"start": 0.0, "end": 1.0, "score": 8.0, "reason": "a"},
        {"start": 1.0, "end": 2.0, "score": 9.0, "reason": "b"},
    ]
