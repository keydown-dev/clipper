from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

DEFAULT_DURATION_SECONDS = 10.0
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 180
DURATION_TOLERANCE_SECONDS = 0.5


def ffmpeg_available() -> bool:
    """Return True when both FFmpeg and ffprobe are available for media fixture tests."""

    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    """Skip the current pytest test when generated media tools are unavailable."""

    if not ffmpeg_available():
        pytest.skip("FFmpeg and ffprobe are required for generated video fixture tests")


def generate_test_video(
    directory: Path,
    *,
    filename: str = "source.mp4",
    duration: float = DEFAULT_DURATION_SECONDS,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    audio: bool = True,
) -> Path:
    """Generate a deterministic low-resolution MP4 fixture and return its path.

    The default fixture is a 10-second 320x180 test pattern. Tests can override
    duration and dimensions, and can disable audio when exercising silent media.
    The helper skips via pytest when FFmpeg/ffprobe are not installed.
    """

    require_ffmpeg()
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / filename
    size = f"{width}x{height}"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size={size}:rate=30:duration={duration}",
    ]
    if audio:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:sample_rate=44100:duration={duration}",
                "-shortest",
                "-c:a",
                "aac",
            ]
        )
    else:
        command.append("-an")
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return output


def ffprobe_json(path: Path) -> dict[str, Any]:
    """Return ffprobe JSON for a generated media file, skipping if unavailable."""

    require_ffmpeg()
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def probe_duration(path: Path) -> float:
    """Return media duration in seconds using ffprobe."""

    return float(ffprobe_json(path)["format"]["duration"])


def assert_duration_close(actual: float, expected: float, *, tolerance: float = DURATION_TOLERANCE_SECONDS) -> None:
    """Assert FFmpeg/ffprobe duration values with the project tolerance."""

    assert abs(actual - expected) <= tolerance


def has_audio_stream(path: Path) -> bool:
    """Return whether a generated media file contains an audio stream."""

    return any(stream.get("codec_type") == "audio" for stream in ffprobe_json(path).get("streams", []))


def video_dimensions(path: Path) -> tuple[int, int]:
    """Return the first video stream dimensions."""

    for stream in ffprobe_json(path).get("streams", []):
        if stream.get("codec_type") == "video":
            return int(stream["width"]), int(stream["height"])
    raise AssertionError(f"no video stream found in {path}")
