from __future__ import annotations

import json
from pathlib import Path

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.schemas import validate_shots
from clipper.shots import ShotOptions, _read_ppm, candidate_times, score_frame_quality, shots_video


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
        "input_ref": "source.mp4",
        "input_type": "local",
        "canonical_input_ref": "/abs/source.mp4",
        "source_path": "source/source.mp4",
        "title": "source",
        "duration": 10.0,
        "created_at": "2026-05-29T00:00:00Z",
    }
    (root / "work" / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return store, root


def test_shots_persists_manifest_and_representative_frames(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    monkeypatch.setattr("clipper.shots.detect_shot_ranges", lambda *_, **__: [(0.0, 4.0), (4.0, 10.0)])
    selected: list[tuple[float, float, int]] = []

    def fake_choose(source: Path, *, start: float, end: float, samples: int) -> tuple[float, dict[str, float]]:
        selected.append((start, end, samples))
        return ((start + end) / 2.0, {"score": 0.9, "sharpness": 1.0, "contrast": 0.8, "exposure": 0.7, "mean_luma": 128.0, "black_ratio": 0.0, "white_ratio": 0.0})

    monkeypatch.setattr("clipper.shots.choose_representative_frame", fake_choose)
    monkeypatch.setattr("clipper.shots.extract_frame_jpeg", lambda source, output, timestamp: output.write_bytes(b"jpg"))

    _, manifest_path, manifest, reused = shots_video(store=store, video="video", options=ShotOptions(threshold=30.0, min_duration=1.0, samples_per_shot=3))

    assert reused is False
    assert manifest_path == root / "work" / "shots.json"
    assert selected == [(0.0, 4.0, 3), (4.0, 10.0, 3)]
    assert [shot["representative_frame_path"] for shot in manifest["shots"]] == ["work/frames/shot-0001.jpg", "work/frames/shot-0002.jpg"]
    assert manifest["shots"][0]["representative_time"] == 2.0
    assert (root / "work" / "frames" / "shot-0001.jpg").exists()
    assert json.loads(manifest_path.read_text()) == manifest
    assert validate_shots(manifest) == manifest


def test_read_ppm_preserves_whitespace_pixel_bytes_after_header() -> None:
    # PPM headers are separated from binary pixels by one whitespace byte. Pixel
    # data itself may also start with bytes such as spaces/newlines, so the
    # parser must not skip all whitespace after the max-value field.
    pixels = bytes([32, 10, 13, 255, 0, 128])

    width, height, parsed = _read_ppm(b"P6\n2 1\n255\n" + pixels)

    assert (width, height) == (2, 1)
    assert parsed == pixels


def test_frame_quality_prefers_clear_exposed_contrast_over_flat_black() -> None:
    # A 4x4 checkerboard has strong local gradients, balanced exposure, and contrast.
    clear_pixels = bytearray()
    for index in range(16):
        value = 32 if index % 2 else 224
        clear_pixels.extend([value, value, value])
    black_pixels = bytes([0, 0, 0] * 16)

    assert score_frame_quality(4, 4, bytes(clear_pixels))["score"] > score_frame_quality(4, 4, black_pixels)["score"]


def test_output_policy_for_shots_requires_complete_frame_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    monkeypatch.setattr("clipper.shots.detect_shot_ranges", lambda *_, **__: [(0.0, 4.0)])
    monkeypatch.setattr("clipper.shots.choose_representative_frame", lambda *_, **__: (2.0, {"score": 1.0}))
    monkeypatch.setattr("clipper.shots.extract_frame_jpeg", lambda source, output, timestamp: output.write_bytes(b"jpg"))

    assert main(["shots", "video", "--store", str(store), "--json"]) == EXIT_SUCCESS
    assert main(["shots", "video", "--store", str(store), "--json"]) == EXIT_FAILURE
    (root / "work" / "frames" / "shot-0001.jpg").unlink()
    assert main(["shots", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_FAILURE
    assert main(["shots", "video", "--store", str(store), "--force", "--json"]) == EXIT_SUCCESS


def test_shots_help_is_routed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["shots", "--help"])

    assert exc.value.code == 0
    assert "--samples-per-shot" in capsys.readouterr().out


def test_candidate_times_avoid_exact_edges() -> None:
    assert candidate_times(10.0, 20.0, 3) == [10.25, 15.0, 19.75]
