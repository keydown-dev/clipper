"""Typed artifact contracts and lightweight schema validation."""

from __future__ import annotations

import re
from typing import Any, Literal, NotRequired, TypedDict

SCHEMA_VERSION = 1
UTC_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class Metadata(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    input_ref: str
    input_type: Literal["remote", "local"]
    canonical_input_ref: str
    source_path: str
    title: str
    duration: float
    created_at: str


class TranscriptWord(TypedDict, total=False):
    word: str
    start: float
    end: float


class TranscriptSegment(TypedDict, total=False):
    id: int
    start: float
    end: float
    text: str
    words: NotRequired[list[TranscriptWord]]


class Transcript(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    language: str | None
    duration: float
    segments: list[TranscriptSegment]


class SentenceWordRange(TypedDict, total=False):
    segment_id: int
    start_word_index: int
    end_word_index: int


class SentenceTranscriptSentence(TypedDict, total=False):
    id: int
    start: float
    end: float
    text: str
    source_segments: list[int]
    word_ranges: list[SentenceWordRange]


class SentenceTranscript(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    language: str | None
    duration: float
    source_transcript_path: str
    sentences: list[SentenceTranscriptSentence]


class ScoreSegment(TypedDict, total=False):
    start: float
    end: float
    score: float
    reason: str
    sentences: NotRequired[list[SentenceTranscriptSentence]]
    dialogue: NotRequired[str]


class Scores(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    directive: str
    segments: list[ScoreSegment]


class ClipEntry(TypedDict, total=False):
    id: str
    path: str
    start: float
    end: float
    duration: float
    score: float
    reason: str


class ClipManifest(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    clips: list[ClipEntry]


class MontageResult(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    montage_path: str
    clips: list[str]
    duration: float
    width: int
    height: int
    silent: bool


class ShotEntry(TypedDict, total=False):
    id: str
    start: float
    end: float
    duration: float
    representative_frame_path: str
    representative_time: float
    quality: dict[str, float]


class ShotManifest(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    shots: list[ShotEntry]
    detection: dict[str, Any]
    contact_sheet_path: NotRequired[str]


class PipelineResult(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    metadata_path: str
    transcript_path: str
    scores_path: str
    clips_path: str
    montage_path: str
    clip_count: int
    runtime_seconds: float


class SchemaError(ValueError):
    """Raised when an artifact fails schema validation."""


def _require_mapping(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SchemaError("artifact must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError("schema_version must be 1")
    if "warnings" in data and not isinstance(data["warnings"], list):
        raise SchemaError("warnings must be a list when present")
    return data


def _require(data: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise SchemaError(f"missing required field(s): {', '.join(missing)}")


def _number(value: Any, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SchemaError(f"{name} must be numeric")


def _relative_path(value: Any, name: str) -> None:
    if not isinstance(value, str) or value.startswith("/") or ".." in value.split("/"):
        raise SchemaError(f"{name} must be a video-relative path")


def validate_metadata(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["input_ref", "input_type", "canonical_input_ref", "source_path", "title", "duration", "created_at"])
    if data["input_type"] not in {"remote", "local"}:
        raise SchemaError("input_type must be remote or local")
    _relative_path(data["source_path"], "source_path")
    _number(data["duration"], "duration")
    if not isinstance(data["created_at"], str) or not UTC_Z_RE.match(data["created_at"]):
        raise SchemaError("created_at must be a UTC ISO-8601 string ending in Z")
    return data


def validate_transcript(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "language", "duration", "segments"])
    _relative_path(data["source_file"], "source_file")
    _number(data["duration"], "duration")
    if data["language"] is not None and not isinstance(data["language"], str):
        raise SchemaError("language must be a string or null")
    if not isinstance(data["segments"], list):
        raise SchemaError("segments must be a list")
    for seg in data["segments"]:
        if not isinstance(seg, dict):
            raise SchemaError("segment must be an object")
        _require(seg, ["id", "start", "end", "text"])
        if not isinstance(seg["id"], int) or isinstance(seg["id"], bool):
            raise SchemaError("segment.id must be an integer")
        _number(seg["start"], "segment.start")
        _number(seg["end"], "segment.end")
        if not isinstance(seg["text"], str):
            raise SchemaError("segment.text must be a string")
        if "words" in seg:
            if not isinstance(seg["words"], list):
                raise SchemaError("segment.words must be a list when present")
            for word in seg["words"]:
                if not isinstance(word, dict):
                    raise SchemaError("segment.words[] must be an object")
                _require(word, ["word", "start", "end"])
                if not isinstance(word["word"], str):
                    raise SchemaError("segment.words[].word must be a string")
                _number(word["start"], "segment.words[].start")
                _number(word["end"], "segment.words[].end")
    return data


def _integer(value: Any, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SchemaError(f"{name} must be an integer")


def validate_sentence_transcript(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "language", "duration", "source_transcript_path", "sentences"])
    _relative_path(data["source_file"], "source_file")
    _relative_path(data["source_transcript_path"], "source_transcript_path")
    _number(data["duration"], "duration")
    if data["language"] is not None and not isinstance(data["language"], str):
        raise SchemaError("language must be a string or null")
    if not isinstance(data["sentences"], list):
        raise SchemaError("sentences must be a list")
    for sentence in data["sentences"]:
        if not isinstance(sentence, dict):
            raise SchemaError("sentence must be an object")
        _require(sentence, ["id", "start", "end", "text", "source_segments", "word_ranges"])
        _integer(sentence["id"], "sentence.id")
        _number(sentence["start"], "sentence.start")
        _number(sentence["end"], "sentence.end")
        if not isinstance(sentence["text"], str):
            raise SchemaError("sentence.text must be a string")
        if not isinstance(sentence["source_segments"], list):
            raise SchemaError("sentence.source_segments must be a list")
        for segment_id in sentence["source_segments"]:
            _integer(segment_id, "sentence.source_segments[]")
        if not isinstance(sentence["word_ranges"], list):
            raise SchemaError("sentence.word_ranges must be a list")
        for word_range in sentence["word_ranges"]:
            if not isinstance(word_range, dict):
                raise SchemaError("sentence.word_ranges[] must be an object")
            _require(word_range, ["segment_id", "start_word_index", "end_word_index"])
            _integer(word_range["segment_id"], "sentence.word_ranges[].segment_id")
            _integer(word_range["start_word_index"], "sentence.word_ranges[].start_word_index")
            _integer(word_range["end_word_index"], "sentence.word_ranges[].end_word_index")
    return data


def _validate_score_sentence(sentence: Any) -> None:
    if not isinstance(sentence, dict):
        raise SchemaError("segment.sentences[] must be an object")
    _require(sentence, ["id", "start", "end", "text", "source_segments", "word_ranges"])
    _integer(sentence["id"], "segment.sentences[].id")
    _number(sentence["start"], "segment.sentences[].start")
    _number(sentence["end"], "segment.sentences[].end")
    if not isinstance(sentence["text"], str):
        raise SchemaError("segment.sentences[].text must be a string")
    if not isinstance(sentence["source_segments"], list):
        raise SchemaError("segment.sentences[].source_segments must be a list")
    for segment_id in sentence["source_segments"]:
        _integer(segment_id, "segment.sentences[].source_segments[]")
    if not isinstance(sentence["word_ranges"], list):
        raise SchemaError("segment.sentences[].word_ranges must be a list")
    for word_range in sentence["word_ranges"]:
        if not isinstance(word_range, dict):
            raise SchemaError("segment.sentences[].word_ranges[] must be an object")
        _require(word_range, ["segment_id", "start_word_index", "end_word_index"])
        _integer(word_range["segment_id"], "segment.sentences[].word_ranges[].segment_id")
        _integer(word_range["start_word_index"], "segment.sentences[].word_ranges[].start_word_index")
        _integer(word_range["end_word_index"], "segment.sentences[].word_ranges[].end_word_index")


def validate_scores(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "directive", "segments"])
    _relative_path(data["source_file"], "source_file")
    if not isinstance(data["directive"], str):
        raise SchemaError("directive must be a string")
    if not isinstance(data["segments"], list):
        raise SchemaError("segments must be a list")
    for seg in data["segments"]:
        if not isinstance(seg, dict):
            raise SchemaError("segment must be an object")
        _require(seg, ["start", "end", "score", "reason"])
        _number(seg["start"], "segment.start")
        _number(seg["end"], "segment.end")
        _number(seg["score"], "segment.score")
        if not isinstance(seg["reason"], str):
            raise SchemaError("segment.reason must be a string")
        if "dialogue" in seg and not isinstance(seg["dialogue"], str):
            raise SchemaError("segment.dialogue must be a string")
        if "sentences" in seg:
            if not isinstance(seg["sentences"], list):
                raise SchemaError("segment.sentences must be a list")
            for sentence in seg["sentences"]:
                _validate_score_sentence(sentence)
    return data


def validate_clips(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "clips"])
    _relative_path(data["source_file"], "source_file")
    for clip in data["clips"]:
        _require(clip, ["id", "path", "start", "end", "duration", "score", "reason"])
        _relative_path(clip["path"], "clip.path")
    return data


def validate_montage(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["montage_path", "clips", "duration", "width", "height", "silent"])
    _relative_path(data["montage_path"], "montage_path")
    for path in data["clips"]:
        _relative_path(path, "clips[]")
    _number(data["duration"], "duration")
    return data


def validate_shots(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "shots", "detection"])
    _relative_path(data["source_file"], "source_file")
    if not isinstance(data["shots"], list):
        raise SchemaError("shots must be a list")
    if not isinstance(data["detection"], dict):
        raise SchemaError("detection must be an object")
    if "contact_sheet_path" in data:
        _relative_path(data["contact_sheet_path"], "contact_sheet_path")
    for shot in data["shots"]:
        if not isinstance(shot, dict):
            raise SchemaError("shot must be an object")
        _require(shot, ["id", "start", "end", "duration", "representative_frame_path", "representative_time", "quality"])
        if not isinstance(shot["id"], str):
            raise SchemaError("shot.id must be a string")
        _number(shot["start"], "shot.start")
        _number(shot["end"], "shot.end")
        _number(shot["duration"], "shot.duration")
        _relative_path(shot["representative_frame_path"], "shot.representative_frame_path")
        _number(shot["representative_time"], "shot.representative_time")
        if not isinstance(shot["quality"], dict):
            raise SchemaError("shot.quality must be an object")
        for key, value in shot["quality"].items():
            _number(value, f"shot.quality.{key}")
    return data


def validate_pipeline(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["metadata_path", "transcript_path", "scores_path", "clips_path", "montage_path", "clip_count", "runtime_seconds"])
    for field in ["metadata_path", "transcript_path", "scores_path", "clips_path", "montage_path"]:
        _relative_path(data[field], field)
    _number(data["runtime_seconds"], "runtime_seconds")
    return data


VALIDATORS = {
    "metadata": validate_metadata,
    "transcript": validate_transcript,
    "sentence_transcript": validate_sentence_transcript,
    "scores": validate_scores,
    "clips": validate_clips,
    "montage": validate_montage,
    "shots": validate_shots,
    "pipeline": validate_pipeline,
}
