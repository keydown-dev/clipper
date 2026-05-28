from __future__ import annotations

from pathlib import Path

from tests.helpers.generated_media import (
    assert_duration_close,
    generate_test_video,
    has_audio_stream,
    probe_duration,
    video_dimensions,
)


def test_generated_video_fixture_defaults_to_ten_second_low_resolution_media(tmp_path: Path) -> None:
    video = generate_test_video(tmp_path)

    assert video.exists()
    assert_duration_close(probe_duration(video), 10.0)
    assert video_dimensions(video) == (320, 180)
    assert has_audio_stream(video) is True


def test_generated_video_fixture_supports_duration_size_and_silent_overrides(tmp_path: Path) -> None:
    video = generate_test_video(tmp_path, filename="short.mp4", duration=2.0, width=160, height=90, audio=False)

    assert_duration_close(probe_duration(video), 2.0)
    assert video_dimensions(video) == (160, 90)
    assert has_audio_stream(video) is False
