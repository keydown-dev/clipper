from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.artifacts import ArtifactError
from clipper.cli import main
from clipper.montage import MontageOptions, montage_project


def make_project(tmp_path: Path, *, durations: list[float] | None = None) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    project = store / "projects" / "story-a"
    clips_dir = project / "clips"
    clips_dir.mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"schema_version": 1, "name": "story-a", "sources": []}), encoding="utf-8")
    durations = durations or [2.0]
    clips = []
    start = 0.0
    for index, duration in enumerate(durations, start=1):
        clip_id = f"clip-{index:04d}"
        (clips_dir / f"{clip_id}.mp4").write_bytes(b"clip")
        clips.append(
            {
                "id": clip_id,
                "path": f"clips/{clip_id}.mp4",
                "start": start,
                "end": start + duration,
                "duration": duration,
                "score": 8.0,
                "reason": "story beat",
                "source": "source-a",
            }
        )
        start += duration
    (project / "clips.json").write_text(json.dumps({"schema_version": 1, "source_file": "source-a/source.mp4", "clips": clips}), encoding="utf-8")
    return store, project


def test_project_montage_reads_project_clips_and_writes_project_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"montage")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    owner, montage_path, manifest, reused = montage_project(store=store, project="story-a", options=MontageOptions(max_duration=2))

    assert owner == "story-a"
    assert reused is False
    assert montage_path == project / "montage.json"
    assert manifest["montage_path"] == "montage.mp4"
    assert manifest["clips"] == ["clips/clip-0001.mp4"]
    assert (project / "montage.mp4").exists()


def test_project_montage_max_duration_trims_last_clip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path, durations=[2.0, 3.0])
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        commands.append(command)
        Path(command[-1]).write_bytes(b"video")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    _, _, manifest, _ = montage_project(store=store, project="story-a", options=MontageOptions(max_duration=3.0))

    assert manifest["duration"] == 3.0
    assert manifest["clips"] == ["clips/clip-0001.mp4", "clips/clip-0002.mp4"]
    assert commands[0][:4] == ["ffmpeg", "-y", "-i", str(project / "clips" / "clip-0002.mp4")]
    assert commands[0][4:6] == ["-t", "1"]


def test_project_montage_reuse_validates_complete_outputs(tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    (project / "montage.mp4").write_bytes(b"montage")
    manifest = {"schema_version": 1, "montage_path": "montage.mp4", "clips": ["clips/clip-0001.mp4"], "duration": 2.0, "width": 1920, "height": 1080, "silent": False}
    (project / "montage.json").write_text(json.dumps(manifest), encoding="utf-8")

    _, montage_path, reused_manifest, reused = montage_project(store=store, project="story-a", reuse=True)

    assert reused is True
    assert montage_path == project / "montage.json"
    assert reused_manifest == manifest


def test_project_montage_failure_cleans_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"partial")
        return SimpleNamespace(returncode=1, stdout="", stderr="nope")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    with pytest.raises(ArtifactError, match="ffmpeg montage failed"):
        montage_project(store=store, project="story-a")

    assert not (project / "montage.mp4").exists()
    assert not (project / "montage.json").exists()


def test_cli_montage_positional_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"montage")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    assert main(["montage", "story-a", "--store", str(store), "--json"]) == 0
    assert (project / "montage.mp4").exists()
    assert json.loads((project / "montage.json").read_text(encoding="utf-8"))["montage_path"] == "montage.mp4"
