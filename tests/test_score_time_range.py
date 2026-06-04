from __future__ import annotations

from pathlib import Path

import pytest

from clipper.artifacts import ArtifactError
from clipper.cli import build_parser, parse_time
from clipper.scoring import filter_scoring_context_by_time


def test_parse_time_accepts_seconds_minutes_and_hours() -> None:
    assert parse_time("12.5") == 12.5
    assert parse_time("01:02") == 62.0
    assert parse_time("01:02:03.5") == 3723.5
    assert parse_time(None) is None


def test_parse_time_rejects_bad_values() -> None:
    with pytest.raises(ArtifactError):
        parse_time("1:2:3:4")
    with pytest.raises(ArtifactError):
        parse_time("-1")


def test_filter_scoring_context_by_time_keeps_overlapping_segments() -> None:
    context = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "duration": 100.0,
        "segments": [
            {"start": 0.0, "end": 9.0, "text": "before"},
            {"start": 10.0, "end": 20.0, "text": "overlaps start"},
            {"start": 30.0, "end": 40.0, "text": "inside"},
            {"start": 50.0, "end": 60.0, "text": "after"},
        ],
    }

    filtered = filter_scoring_context_by_time(context, start=15.0, end=45.0)

    assert [segment["text"] for segment in filtered["segments"]] == ["overlaps start", "inside"]
    assert filtered["duration"] == 45.0


def test_filter_scoring_context_by_time_rejects_empty_or_invalid_ranges() -> None:
    context = {"schema_version": 1, "source_file": "source/source.mp4", "duration": 100.0, "segments": [{"start": 1.0, "end": 2.0, "text": "x"}]}
    with pytest.raises(ArtifactError, match="--end must be greater"):
        filter_scoring_context_by_time(context, start=10.0, end=5.0)
    with pytest.raises(ArtifactError, match="no scoring evidence"):
        filter_scoring_context_by_time(context, start=10.0, end=20.0)


def test_score_help_exposes_time_range_flags() -> None:
    parser = build_parser()
    subparser = parser._subparsers._group_actions[0].choices["score"]  # type: ignore[attr-defined]
    help_text = subparser.format_help()
    assert "--start" in help_text
    assert "--end" in help_text
