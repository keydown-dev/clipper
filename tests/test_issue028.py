from pathlib import Path

import pytest

from clipper.artifacts import ArtifactError, ArtifactLayout, ProjectArtifactLayout, SourceArtifactLayout


def test_source_layout_uses_flattened_source_namespace(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    layout = SourceArtifactLayout.for_source(store, "source_a")

    assert layout.root == store / "sources" / "source_a"
    assert layout.source_media("webm") == layout.root / "source.webm"
    assert layout.metadata == layout.root / "metadata.json"
    assert layout.transcript == layout.root / "transcript.json"
    assert layout.sentence_transcript == layout.root / "sentences.json"
    assert layout.shots_manifest == layout.root / "shots.json"
    assert layout.visual_index == layout.root / "visual-index.json"
    assert layout.shot_contact_sheet == layout.root / "shot-contact-sheet.jpg"
    assert layout.shot_frames_dir == layout.root / "frames"
    assert layout.fixed_paths("webm") == {
        "source": "source.webm",
        "metadata": "metadata.json",
        "transcript": "transcript.json",
        "sentence_transcript": "sentences.json",
        "shots": "shots.json",
        "visual_index": "visual-index.json",
        "shot_contact_sheet": "shot-contact-sheet.jpg",
        "frames": "frames/",
    }

    layout.create_dirs()
    assert layout.root.is_dir()
    assert layout.shot_frames_dir.is_dir()


def test_project_layout_uses_project_namespace_and_editorial_outputs(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    layout = ProjectArtifactLayout.for_project(store, "story-a")

    assert layout.root == store / "projects" / "story-a"
    assert layout.project_json == layout.root / "project.json"
    assert layout.scores == layout.root / "scores.json"
    assert layout.clips_manifest == layout.root / "clips.json"
    assert layout.montage_video == layout.root / "montage.mp4"
    assert layout.montage_json == layout.root / "montage.json"
    assert layout.clips_dir == layout.root / "clips"
    assert layout.fixed_paths() == {
        "project": "project.json",
        "scores": "scores.json",
        "clips": "clips.json",
        "montage_video": "montage.mp4",
        "montage_json": "montage.json",
        "clips_dir": "clips/",
    }

    layout.create_dirs()
    assert layout.root.is_dir()
    assert layout.clips_dir.is_dir()


def test_source_and_project_layouts_validate_names_and_can_share_slug(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"

    with pytest.raises(ArtifactError):
        SourceArtifactLayout.for_source(store, "Bad Name")
    with pytest.raises(ArtifactError):
        ProjectArtifactLayout.for_project(store, "Bad Name")

    source = SourceArtifactLayout.for_source(store, "same")
    project = ProjectArtifactLayout.for_project(store, "same")

    assert source.root == store / "sources" / "same"
    assert project.root == store / "projects" / "same"
    assert source.root != project.root


def test_existing_video_layout_remains_available(tmp_path: Path) -> None:
    layout = ArtifactLayout.for_video(tmp_path / ".clipper", "video")

    assert layout.root == tmp_path / ".clipper" / "video"
    assert layout.metadata == layout.root / "work" / "metadata.json"
    assert layout.fixed_paths("mov")["source"] == "source/source.mov"
