from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.montage import MontageOptions, ffmpeg_montage_command, montage_video, select_clips_for_montage
from tests.helpers.generated_media import assert_duration_close, generate_test_video, has_audio_stream, probe_duration, video_dimensions


def make_workspace(tmp_path: Path, clips: list[dict[str, object]], *, clip_bytes: bytes = b"fake") -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "clips").mkdir()
    (root / "output").mkdir()
    for clip in clips:
        path = root / str(clip["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(clip_bytes)
    manifest = {"schema_version": 1, "source_file": "source/source.mp4", "clips": clips}
    (root / "work" / "clips.json").write_text(json.dumps(manifest), encoding="utf-8")
    return store, root


def clip(id_: str, path: str, start: float, end: float, *, score: float = 1.0) -> dict[str, object]:
    return {"id": id_, "path": path, "start": start, "end": end, "duration": end - start, "score": score, "reason": id_}


def test_select_preserves_input_order_without_score_refiltering_and_trims_final_clip() -> None:
    selected, total = select_clips_for_montage(
        [
            clip("late", "clips/late.mp4", 8, 12, score=0),
            clip("early", "clips/early.mp4", 1, 4, score=0),
            clip("middle", "clips/middle.mp4", 5, 7, score=0),
        ],
        min_duration=None,
        max_duration=6.0,
    )

    assert [item["id"] for item in selected] == ["late", "early"]
    assert [item["selected_duration"] for item in selected] == [4.0, 2.0]
    assert total == 6.0


def test_select_chronological_flag_sorts_by_time() -> None:
    selected, total = select_clips_for_montage(
        [
            clip("late", "clips/late.mp4", 8, 12, score=0),
            clip("early", "clips/early.mp4", 1, 4, score=0),
            clip("middle", "clips/middle.mp4", 5, 7, score=0),
        ],
        min_duration=None,
        max_duration=6.0,
        chronological=True,
    )

    assert [item["id"] for item in selected] == ["early", "middle", "late"]
    assert [item["selected_duration"] for item in selected] == [3.0, 2.0, 1.0]
    assert total == 6.0


def test_min_duration_failure_does_not_create_outputs(tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path, [clip("one", "clips/clip-0001.mp4", 0, 1)])

    assert main(["montage", "video", "--store", str(store), "--min-duration", "2", "--json"]) == EXIT_FAILURE

    assert not (root / "output" / "montage.mp4").exists()
    assert not (root / "output" / "montage.json").exists()


def test_montage_invokes_concat_demuxer_and_writes_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path, [clip("two", "clips/two.mp4", 5, 7), clip("one", "clips/one.mp4", 0, 3)])
    seen: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        seen.append(command)
        Path(command[-1]).write_bytes(b"montage")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    _, montage_path, manifest, reused = montage_video(store=store, video="video", options=MontageOptions(max_duration=4.0))

    assert reused is False
    assert montage_path == root / "output" / "montage.json"
    assert manifest["clips"] == ["clips/two.mp4", "clips/one.mp4"]
    assert manifest["duration"] == 4.0
    assert manifest["order_source"] == "clips.json"
    assert manifest["width"] == 1920
    assert manifest["height"] == 1080
    assert seen[0][:4] == ["ffmpeg", "-y", "-i", str(root / "clips" / "one.mp4")]
    assert seen[1][0:6] == ["ffmpeg", "-y", "-f", "concat", "-safe", "0"]
    assert "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" in seen[1]
    assert json.loads((root / "output" / "montage.json").read_text()) == manifest


def test_silent_montage_command_strips_audio() -> None:
    command = ffmpeg_montage_command(filelist=Path("filelist.txt"), output=Path("montage.mp4"), width=1920, height=1080, silent=True)

    assert "-an" in command
    assert "-c:a" not in command


def test_partial_outputs_are_cleaned_up_on_ffmpeg_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path, [clip("one", "clips/one.mp4", 0, 2)])

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"partial")
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    with pytest.raises(ValueError, match="ffmpeg montage failed"):
        montage_video(store=store, video="video", options=MontageOptions())

    assert not (root / "output" / "montage.mp4").exists()
    assert not (root / "output" / "montage.json").exists()


def test_generated_clips_assemble_with_duration_dimensions_and_audio_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "work").mkdir(parents=True)
    (root / "clips").mkdir()
    (root / "output").mkdir()
    generate_test_video(root / "clips", filename="clip-0001.mp4", duration=2.0, width=320, height=180, audio=True)
    generate_test_video(root / "clips", filename="clip-0002.mp4", duration=2.0, width=320, height=180, audio=True)
    manifest = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "clips": [
            clip("clip-0001", "clips/clip-0001.mp4", 0, 2),
            clip("clip-0002", "clips/clip-0002.mp4", 2, 4),
        ],
    }
    (root / "work" / "clips.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("DEFAULT_WIDTH", "640")
    monkeypatch.setenv("DEFAULT_HEIGHT", "360")

    assert main(["montage", "video", "--store", str(store), "--max-duration", "3", "--json"]) == EXIT_SUCCESS
    montage = root / "output" / "montage.mp4"
    assert_duration_close(probe_duration(montage), 3.0)
    assert video_dimensions(montage) == (640, 360)
    assert has_audio_stream(montage)

    assert main(["montage", "video", "--store", str(store), "--force", "--silent", "--json"]) == EXIT_SUCCESS
    assert not has_audio_stream(montage)
