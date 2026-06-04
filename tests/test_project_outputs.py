from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from clipper.cli import build_parser
from clipper.cutting import CutOptions, cut_video
from clipper.montage import MontageOptions, montage_video


def make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work" / "projects" / "story-a").mkdir(parents=True)
    (root / "clips").mkdir()
    (root / "output").mkdir()
    (root / "source" / "source.mp4").write_bytes(b"fake")
    scores = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "directive": "Find story A",
        "segments": [{"start": 1.0, "end": 3.0, "score": 8.0, "reason": "story beat"}],
    }
    (root / "work" / "projects" / "story-a" / "scores.json").write_text(json.dumps(scores), encoding="utf-8")
    return store, root


def test_project_cut_uses_project_scores_and_writes_project_clips(monkeypatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"clip")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.cutting.subprocess.run", fake_run)

    _, clips_path, manifest, reused = cut_video(store=store, video="video", options=CutOptions(min_score=6), project="story-a")

    assert reused is False
    assert clips_path == root / "work" / "projects" / "story-a" / "clips.json"
    assert manifest["clips"][0]["path"] == "clips/projects/story-a/clip-0001.mp4"
    assert (root / "clips" / "projects" / "story-a" / "clip-0001.mp4").exists()
    assert not (root / "work" / "clips.json").exists()


def test_project_montage_uses_project_clips_and_writes_project_output(monkeypatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    project_clip = root / "clips" / "projects" / "story-a" / "clip-0001.mp4"
    project_clip.parent.mkdir(parents=True)
    project_clip.write_bytes(b"clip")
    clips = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "clips": [
            {
                "id": "clip-0001",
                "path": "clips/projects/story-a/clip-0001.mp4",
                "start": 1.0,
                "end": 3.0,
                "duration": 2.0,
                "score": 8.0,
                "reason": "story beat",
            }
        ],
    }
    (root / "work" / "projects" / "story-a" / "clips.json").write_text(json.dumps(clips), encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"montage")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)

    _, montage_path, manifest, reused = montage_video(store=store, video="video", options=MontageOptions(max_duration=2), project="story-a")

    assert reused is False
    assert montage_path == root / "output" / "projects" / "story-a" / "montage.json"
    assert manifest["montage_path"] == "output/projects/story-a/montage.mp4"
    assert (root / "output" / "projects" / "story-a" / "montage.mp4").exists()
    assert not (root / "output" / "montage.json").exists()


def test_project_flag_is_exposed_on_downstream_commands() -> None:
    help_text = build_parser().format_help()
    assert "project" not in help_text.lower()
    for command in ["score", "cut", "montage", "pipeline"]:
        parser = build_parser()
        subparser = parser._subparsers._group_actions[0].choices[command]  # type: ignore[attr-defined]
        assert "--project" in subparser.format_help()
