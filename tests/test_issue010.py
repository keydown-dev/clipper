from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from clipper.artifacts import ArtifactLayout, write_json
from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.pipeline import run_pipeline
from clipper.schemas import validate_pipeline
from tests.helpers.generated_media import generate_test_video


def install_mocked_transcription_and_scoring(monkeypatch: pytest.MonkeyPatch, *, passing_score: float = 8.0) -> None:
    def fake_transcribe_video(*, store: Path, video: str | None, **_: Any):
        assert video is not None
        layout = ArtifactLayout.for_video(store, video)
        transcript = {
            "schema_version": 1,
            "source_file": "source/source.mp4",
            "language": "en",
            "duration": 4.0,
            "segments": [{"id": 0, "start": 0.0, "end": 2.0, "text": "hosts laugh"}],
        }
        write_json(layout.transcript, transcript)
        return video, layout.transcript, transcript, False

    def fake_score_video(*, store: Path, video: str | None, directive: str, **_: Any):
        assert video is not None
        layout = ArtifactLayout.for_video(store, video)
        scores = {
            "schema_version": 1,
            "source_file": "source/source.mp4",
            "directive": directive,
            "segments": [{"start": 0.0, "end": 2.0, "score": passing_score, "reason": "hosts laugh"}],
        }
        write_json(layout.scores, scores)
        return video, layout.scores, scores, False

    monkeypatch.setattr("clipper.pipeline.transcribe_video", fake_transcribe_video)
    monkeypatch.setattr("clipper.pipeline.score_video", fake_score_video)


def test_pipeline_runs_generated_local_video_with_mocked_transcription_and_scoring(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = generate_test_video(tmp_path / "src", duration=4.0)
    store = tmp_path / ".clipper"
    install_mocked_transcription_and_scoring(monkeypatch)

    result = run_pipeline(source.as_posix(), name="video", store=store, directive="Find laughter", min_score=6, max_duration=2)

    layout = ArtifactLayout.for_video(store, "video")
    persisted = json.loads(layout.pipeline.read_text())
    assert validate_pipeline(persisted) == persisted
    assert result["clip_count"] == 1
    assert result["source_path"] == "source/source.mp4"
    assert result["metadata_path"] == "work/metadata.json"
    assert result["transcript_path"] == "work/transcript.json"
    assert result["scores_path"] == "work/scores.json"
    assert result["clips_path"] == "work/clips.json"
    assert result["montage_path"] == "output/montage.mp4"
    assert (layout.root / result["montage_path"]).exists()


def test_pipeline_fail_reuse_and_force_behavior(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = generate_test_video(tmp_path / "src", duration=4.0)
    store = tmp_path / ".clipper"
    install_mocked_transcription_and_scoring(monkeypatch)

    first = run_pipeline(str(source), name="video", store=store, directive="Find laughter")
    with pytest.raises(ValueError, match="output already exists"):
        run_pipeline(str(source), name="video", store=store, directive="Find laughter")
    reused = run_pipeline(str(source), name="video", store=store, directive="Find laughter", reuse=True)
    assert reused == first
    forced = run_pipeline(str(source), name="video", store=store, directive="Find laughter", force=True)
    assert forced["runtime_seconds"] >= 0
    assert forced["video"] == "video"


def test_pipeline_no_clips_preserves_upstream_and_does_not_write_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = generate_test_video(tmp_path / "src", duration=4.0)
    store = tmp_path / ".clipper"
    install_mocked_transcription_and_scoring(monkeypatch, passing_score=2.0)

    assert main(["pipeline", str(source), "--name", "video", "--store", str(store), "--min-score", "6", "--json"]) == EXIT_FAILURE
    layout = ArtifactLayout.for_video(store, "video")
    assert layout.metadata.exists()
    assert layout.transcript.exists()
    assert layout.scores.exists()
    assert not layout.clips_manifest.exists()
    assert not layout.montage_json.exists()
    assert not layout.pipeline.exists()


def test_pipeline_cli_supports_human_and_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = generate_test_video(tmp_path / "src", duration=4.0)
    store = tmp_path / ".clipper"
    install_mocked_transcription_and_scoring(monkeypatch)

    assert main(["pipeline", str(source), "--name", "video", "--store", str(store)]) == EXIT_SUCCESS
    human = capsys.readouterr().out
    assert "Ran pipeline for video video" in human
    assert "Pipeline:" in human

    assert main(["pipeline", str(source), "--name", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["video"] == "video"
    assert payload["result"]["clip_count"] == 1
