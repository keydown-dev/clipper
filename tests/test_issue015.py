from __future__ import annotations

from clipper.schemas import validate_scores
from clipper.scoring import ScoringOptions, enrich_segments_with_dialogue, score_transcript
from tests.test_issue006 import FakeClient


def make_sentence_transcript() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "language": "en",
        "duration": 20.0,
        "source_transcript_path": "work/transcript.json",
        "sentences": [
            {
                "id": 0,
                "start": 0.5,
                "end": 3.0,
                "text": "Calm intro.",
                "source_segments": [0],
                "word_ranges": [{"segment_id": 0, "start_word_index": 0, "end_word_index": 1}],
            },
            {
                "id": 1,
                "start": 5.0,
                "end": 9.0,
                "text": "Hosts laugh loudly.",
                "source_segments": [1],
                "word_ranges": [{"segment_id": 1, "start_word_index": 0, "end_word_index": 2}],
            },
            {
                "id": 2,
                "start": 9.5,
                "end": 12.0,
                "text": "A guest points at the chart.",
                "source_segments": [1, 2],
                "word_ranges": [
                    {"segment_id": 1, "start_word_index": 3, "end_word_index": 4},
                    {"segment_id": 2, "start_word_index": 0, "end_word_index": 2},
                ],
            },
        ],
    }


def test_score_transcript_prompts_from_sentence_transcript_when_available() -> None:
    transcript = {
        "duration": 20.0,
        "segments": [
            {"id": 0, "start": 0.0, "end": 12.0, "text": "raw faster whisper text should not be used"},
        ],
    }
    client = FakeClient(['[{"start":5,"end":11,"score":9,"reason":"visual moment"}]'])

    score_transcript(
        transcript,
        client=client,
        options=ScoringOptions(directive="Find visual moments", model="model"),
        sentence_transcript=make_sentence_transcript(),
    )

    prompt = client.seen[0]["messages"][1]["content"]
    assert "[5.00-9.00] Hosts laugh loudly." in prompt
    assert "[9.50-12.00] A guest points at the chart." in prompt
    assert "raw faster whisper text should not be used" not in prompt


def test_score_output_includes_overlapping_sentence_objects_and_joined_dialogue() -> None:
    transcript = {"duration": 20.0, "segments": [{"id": 0, "start": 0.0, "end": 20.0, "text": "raw"}]}
    client = FakeClient(['[{"start":5,"end":11,"score":9,"reason":"visual moment"}]'])

    segments, warnings = score_transcript(
        transcript,
        client=client,
        options=ScoringOptions(directive="Find visual moments", model="model"),
        sentence_transcript=make_sentence_transcript(),
    )

    assert warnings == []
    assert segments[0]["dialogue"] == "Hosts laugh loudly. A guest points at the chart."
    assert [sentence["id"] for sentence in segments[0]["sentences"]] == [1, 2]
    assert segments[0]["sentences"][1]["word_ranges"] == [
        {"segment_id": 1, "start_word_index": 3, "end_word_index": 4},
        {"segment_id": 2, "start_word_index": 0, "end_word_index": 2},
    ]
    scores = {"schema_version": 1, "source_file": "source/source.mp4", "directive": "x", "segments": segments}
    assert validate_scores(scores) == scores


def test_dialogue_enrichment_is_derived_from_sentences_not_model_prose() -> None:
    transcript = {"duration": 20.0, "segments": [{"id": 0, "start": 0.0, "end": 20.0, "text": "raw"}]}
    client = FakeClient(['[{"start":5,"end":9,"score":8,"reason":"Model says: rewritten dialogue"}]'])

    segments, _ = score_transcript(
        transcript,
        client=client,
        options=ScoringOptions(directive="Find laughs", model="model"),
        sentence_transcript=make_sentence_transcript(),
    )

    assert segments[0]["reason"] == "Model says: rewritten dialogue"
    assert segments[0]["dialogue"] == "Hosts laugh loudly."


def test_dialogue_enrichment_handles_segments_with_no_overlapping_sentences() -> None:
    segments = enrich_segments_with_dialogue(
        [{"start": 15.0, "end": 18.0, "score": 6.0, "reason": "quiet visual"}],
        make_sentence_transcript(),
    )

    assert segments == [{"start": 15.0, "end": 18.0, "score": 6.0, "reason": "quiet visual", "sentences": []}]
