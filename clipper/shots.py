"""Detect visual shots and extract representative frames."""

from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .schemas import SCHEMA_VERSION


@dataclass(frozen=True)
class ShotOptions:
    threshold: float = 27.0
    min_duration: float = 0.5
    samples_per_shot: int = 5
    contact_sheet: bool = False


def _video_relative(layout: ArtifactLayout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _probe_fps(path: Path) -> float:
    try:
        output = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "default=nw=1:nk=1", str(path)],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        numerator, denominator = output.split("/", 1) if "/" in output else (output, "1")
        fps = float(numerator) / float(denominator)
    except (OSError, subprocess.CalledProcessError, ValueError, ZeroDivisionError) as exc:
        raise ArtifactError(f"could not determine video frame rate with ffprobe for {path}: {exc}") from exc
    if fps <= 0:
        raise ArtifactError(f"could not determine positive video frame rate with ffprobe for {path}")
    return fps


def detect_shot_ranges(source: Path, *, duration: float, threshold: float, min_duration: float) -> list[tuple[float, float]]:
    """Detect shot boundaries with PySceneDetect and return sorted (start, end) ranges."""

    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except ImportError as exc:  # pragma: no cover - exercised when dependencies are missing in real use.
        raise ArtifactError("PySceneDetect is not installed; install project dependencies with `uv sync`") from exc

    fps = _probe_fps(source)
    min_scene_len = max(1, int(round(min_duration * fps)))
    try:
        video = open_video(str(source))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))
        manager.detect_scenes(video=video)
        scenes = manager.get_scene_list()
    except Exception as exc:
        raise ArtifactError(f"shot detection failed for {source}: {exc}") from exc

    ranges = [(max(0.0, float(start.get_seconds())), min(float(duration), float(end.get_seconds()))) for start, end in scenes]
    ranges = [(start, end) for start, end in ranges if end - start >= min_duration]
    if not ranges and duration > 0:
        ranges = [(0.0, float(duration))]
    return ranges


def candidate_times(start: float, end: float, samples: int) -> list[float]:
    """Return deterministic candidate times, avoiding exact shot edges where possible."""

    samples = max(1, int(samples))
    duration = max(0.0, end - start)
    if duration <= 0:
        return [start]
    edge = min(duration * 0.1, 0.25)
    inner_start = start + edge
    inner_end = end - edge
    if inner_end < inner_start:
        midpoint = start + duration / 2.0
        return [midpoint]
    if samples == 1:
        return [(inner_start + inner_end) / 2.0]
    step = (inner_end - inner_start) / (samples - 1)
    return [inner_start + index * step for index in range(samples)]


def _read_ppm(data: bytes) -> tuple[int, int, bytes]:
    parts: list[bytes] = []
    index = 0
    while len(parts) < 4:
        while index < len(data) and data[index:index + 1].isspace():
            index += 1
        if index < len(data) and data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in {b"\n", b"\r"}:
                index += 1
            continue
        start = index
        while index < len(data) and not data[index:index + 1].isspace():
            index += 1
        parts.append(data[start:index])
    if parts[0] != b"P6" or parts[3] != b"255":
        raise ArtifactError("ffmpeg produced an unsupported frame format")
    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    width, height = int(parts[1]), int(parts[2])
    pixels = data[index:]
    if len(pixels) < width * height * 3:
        raise ArtifactError("ffmpeg produced a truncated frame")
    return width, height, pixels[: width * height * 3]


def _extract_ppm(source: Path, timestamp: float) -> tuple[int, int, bytes]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.6f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "ppm",
        "-",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not result.stdout:
        raise ArtifactError(f"ffmpeg frame extraction failed at {timestamp:.3f}s: {result.stderr.decode(errors='replace').strip()}")
    return _read_ppm(result.stdout)


def score_frame_quality(width: int, height: int, pixels: bytes) -> dict[str, float]:
    """Score a PPM frame with deterministic sharpness, exposure, and contrast metrics."""

    luminance: list[float] = []
    for index in range(0, len(pixels), 3):
        r, g, b = pixels[index], pixels[index + 1], pixels[index + 2]
        luminance.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    if not luminance:
        raise ArtifactError("cannot score an empty frame")
    mean = sum(luminance) / len(luminance)
    variance = sum((value - mean) ** 2 for value in luminance) / len(luminance)
    contrast = math.sqrt(variance) / 128.0
    black_ratio = sum(1 for value in luminance if value < 12) / len(luminance)
    white_ratio = sum(1 for value in luminance if value > 243) / len(luminance)
    exposure = max(0.0, 1.0 - abs(mean - 128.0) / 128.0)

    # Mean absolute luminance differences between neighboring pixels. Blurry frames
    # have lower local gradients; hard cuts/black/overexposed frames are penalized separately.
    sharp_total = 0.0
    comparisons = 0
    for y in range(height):
        row = y * width
        for x in range(width):
            current = luminance[row + x]
            if x + 1 < width:
                sharp_total += abs(current - luminance[row + x + 1])
                comparisons += 1
            if y + 1 < height:
                sharp_total += abs(current - luminance[row + width + x])
                comparisons += 1
    sharpness = (sharp_total / max(1, comparisons)) / 64.0
    penalty = max(black_ratio, white_ratio) * 2.0
    score = max(0.0, sharpness * 0.45 + contrast * 0.35 + exposure * 0.20 - penalty)
    return {
        "score": float(score),
        "sharpness": float(sharpness),
        "contrast": float(contrast),
        "exposure": float(exposure),
        "mean_luma": float(mean),
        "black_ratio": float(black_ratio),
        "white_ratio": float(white_ratio),
    }


def choose_representative_frame(source: Path, *, start: float, end: float, samples: int) -> tuple[float, dict[str, float]]:
    """Pick the highest-quality candidate frame in a shot."""

    best_time: float | None = None
    best_metrics: dict[str, float] | None = None
    for timestamp in candidate_times(start, end, samples):
        width, height, pixels = _extract_ppm(source, timestamp)
        metrics = score_frame_quality(width, height, pixels)
        if best_metrics is None or (metrics["score"], -abs(timestamp - ((start + end) / 2.0))) > (best_metrics["score"], -abs((best_time or timestamp) - ((start + end) / 2.0))):
            best_time = timestamp
            best_metrics = metrics
    assert best_time is not None and best_metrics is not None
    return best_time, best_metrics


def extract_frame_jpeg(source: Path, output: Path, timestamp: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{timestamp:.6f}", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(output)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise ArtifactError(f"ffmpeg representative frame extraction failed at {timestamp:.3f}s: {result.stderr.strip()}")


def _write_contact_sheet(frame_paths: Iterable[Path], output: Path) -> None:
    frames = [path for path in frame_paths if path.exists()]
    if not frames:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    pattern_dir = output.parent / ".contact-sheet-inputs"
    shutil.rmtree(pattern_dir, ignore_errors=True)
    pattern_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, frame in enumerate(frames):
            shutil.copy2(frame, pattern_dir / f"frame-{index:04d}.jpg")
        columns = min(5, len(frames))
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-pattern_type",
            "glob",
            "-i",
            str(pattern_dir / "*.jpg"),
            "-vf",
            f"scale=160:-1,tile={columns}x{math.ceil(len(frames) / columns)}",
            "-frames:v",
            "1",
            str(output),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise ArtifactError(f"ffmpeg contact sheet generation failed: {result.stderr.strip()}")
    finally:
        shutil.rmtree(pattern_dir, ignore_errors=True)


def shots_video(
    *,
    store: Path,
    video: str | None,
    options: ShotOptions | None = None,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    progress: Any | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Detect shots for a video workspace and write work/shots.json plus frame images."""

    options = options or ShotOptions()
    if options.min_duration <= 0:
        raise ArtifactError("--min-duration must be positive")
    if options.samples_per_shot <= 0:
        raise ArtifactError("--samples-per-shot must be positive")

    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name)
    manifest_path = layout.shots_manifest
    frames_dir = layout.shot_frames_dir
    contact_sheet = layout.shot_contact_sheet

    if reuse:
        manifest = read_validated_json(manifest_path, "shots")
        missing = [shot["representative_frame_path"] for shot in manifest["shots"] if not (layout.root / shot["representative_frame_path"]).exists()]
        if options.contact_sheet and not contact_sheet.exists():
            missing.append(_video_relative(layout, contact_sheet))
        if missing:
            raise ArtifactError(f"--reuse requires existing shot artifacts; missing: {', '.join(missing)}")
        return layout.video, manifest_path, manifest, True

    metadata = read_validated_json(layout.metadata, "metadata")
    source = layout.root / metadata["source_path"]
    if not source.exists():
        raise ArtifactError(f"source video not found: {metadata['source_path']}")
    duration = float(metadata["duration"])
    ranges = detect_shot_ranges(source, duration=duration, threshold=options.threshold, min_duration=options.min_duration)
    if not ranges:
        raise ArtifactError("no shots detected")

    frame_paths = [frames_dir / f"shot-{index:04d}.jpg" for index in range(1, len(ranges) + 1)]
    output_paths = [manifest_path, *frame_paths]
    if options.contact_sheet:
        output_paths.append(contact_sheet)
    output_policy(output_paths, reuse=False, force=force, schema="shots")

    if force:
        shutil.rmtree(frames_dir, ignore_errors=True)
        contact_sheet.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
    layout.create_dirs()
    frames_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, Any]] = []
    created: list[Path] = []
    try:
        for index, (start, end) in enumerate(ranges, start=1):
            if progress:
                progress.log(f"selecting representative frame for shot {index}/{len(ranges)}")
            representative_time, metrics = choose_representative_frame(source, start=start, end=end, samples=options.samples_per_shot)
            frame_path = frames_dir / f"shot-{index:04d}.jpg"
            extract_frame_jpeg(source, frame_path, representative_time)
            created.append(frame_path)
            shots.append(
                {
                    "id": f"shot-{index:04d}",
                    "start": float(start),
                    "end": float(end),
                    "duration": float(end - start),
                    "representative_frame_path": _video_relative(layout, frame_path),
                    "representative_time": float(representative_time),
                    "quality": metrics,
                }
            )
        if options.contact_sheet:
            _write_contact_sheet(frame_paths, contact_sheet)
            created.append(contact_sheet)
        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "source_file": metadata["source_path"],
            "shots": shots,
            "detection": {
                "tool": "pyscenedetect",
                "threshold": float(options.threshold),
                "min_duration": float(options.min_duration),
                "samples_per_shot": int(options.samples_per_shot),
            },
        }
        if options.contact_sheet:
            manifest["contact_sheet_path"] = _video_relative(layout, contact_sheet)
        write_json(manifest_path, manifest)
    except Exception:
        for path in [*created, *frame_paths, contact_sheet, manifest_path]:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return layout.video, manifest_path, manifest, False
