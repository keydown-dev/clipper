from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.schemas import validate_sentence_transcript
from clipper.transcription import build_sentence_transcript
from tests.test_issue005 import FakeInfo, FakeSegment, FakeWord, make_workspace


def test_sentence_grouping_within_one_segment_uses_word_timings_and_traceability() -> None:
    transcript = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": "en",
        "duration": 10.0,
        "segments": [
            {
                "id": 7,
                "start": 0.0,
                "end": 10.0,
                "text": "Hello world. Next idea",
                "words": [
                    {"word": "Hello", "start": 1.0, "end": 1.2},
                    {"word": "world.", "start": 1.3, "end": 1.8},
                    {"word": "Next", "start": 4.0, "end": 4.3},
                    {"word": "idea", "start": 4.4, "end": 4.9},
                ],
            }
        ],
    }

    sentences = build_sentence_transcript(transcript=transcript, source_transcript_path="work/transcript.json")

    assert sentences["sentences"] == [
        {
            "id": 0,
            "start": 1.0,
            "end": 1.8,
            "text": "Hello world.",
            "source_segments": [7],
            "word_ranges": [{"segment_id": 7, "start_word_index": 0, "end_word_index": 1}],
        },
        {
            "id": 1,
            "start": 4.0,
            "end": 4.9,
            "text": "Next idea",
            "source_segments": [7],
            "word_ranges": [{"segment_id": 7, "start_word_index": 2, "end_word_index": 3}],
        },
    ]
    assert validate_sentence_transcript(sentences) == sentences


def test_sentence_grouping_across_multiple_segments_preserves_word_ranges() -> None:
    transcript = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": None,
        "duration": 4.0,
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "This crosses", "words": [{"word": "This", "start": 0.1, "end": 0.2}, {"word": "crosses", "start": 0.3, "end": 0.7}]},
            {"id": 1, "start": 1.0, "end": 2.0, "text": "segments.", "words": [{"word": "segments.", "start": 1.2, "end": 1.6}]},
        ],
    }

    sentences = build_sentence_transcript(transcript=transcript, source_transcript_path="work/transcript.json")

    assert sentences["sentences"] == [
        {
            "id": 0,
            "start": 0.1,
            "end": 1.6,
            "text": "This crosses segments.",
            "source_segments": [0, 1],
            "word_ranges": [
                {"segment_id": 0, "start_word_index": 0, "end_word_index": 1},
                {"segment_id": 1, "start_word_index": 0, "end_word_index": 0},
            ],
        }
    ]


def test_transcribe_writes_sentence_transcript_and_reports_counts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)

    class FakeWhisperModel:
        def __init__(self, model: str, *, device: str, compute_type: str) -> None:
            pass

        def transcribe(self, path: str, *, language: str | None = None, word_timestamps: bool = False):
            assert word_timestamps is True
            return [FakeSegment(0.0, 2.0, "Hello world.", [FakeWord("Hello", 0.2, 0.5), FakeWord("world.", 0.8, 1.1)])], FakeInfo()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    assert main(["transcribe", "video", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["sentence_transcript_path"] == str(root / "work" / "sentences.json")
    assert payload["result"]["sentences"] == 1
    sentence_transcript = json.loads((root / "work" / "sentences.json").read_text())
    assert sentence_transcript["source_transcript_path"] == "work/transcript.json"
    assert sentence_transcript["sentences"][0]["start"] == 0.2
    assert sentence_transcript["sentences"][0]["end"] == 1.1


def test_reuse_requires_complete_transcript_output_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, root = make_workspace(tmp_path)
    (root / "work" / "transcript.json").write_text(
        json.dumps({"schema_version": 1, "source_file": "source/source.mp4", "language": None, "duration": 1.0, "segments": []}),
        encoding="utf-8",
    )

    assert main(["transcribe", "video", "--store", str(store), "--reuse", "--json"]) == EXIT_FAILURE
    payload = json.loads(capsys.readouterr().out)
    assert "missing" in payload["error"]["message"]
    assert "sentences.json" in payload["error"]["message"]


def test_sentence_grouping_missing_word_timestamps_is_actionable() -> None:
    transcript = {"schema_version": 1, "source_file": "source/source.mp4", "language": None, "duration": 1.0, "segments": [{"id": 0, "start": 0, "end": 1, "text": "old"}]}
    with pytest.raises(ValueError, match="clipper transcribe --force"):
        build_sentence_transcript(transcript=transcript, source_transcript_path="work/transcript.json")
