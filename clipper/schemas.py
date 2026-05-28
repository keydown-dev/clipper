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


class TranscriptSegment(TypedDict, total=False):
    id: int
    start: float
    end: float
    text: str


class Transcript(TypedDict, total=False):
    schema_version: Literal[1]
    warnings: NotRequired[list[str]]
    source_file: str
    language: str | None
    duration: float
    segments: list[TranscriptSegment]


class ScoreSegment(TypedDict, total=False):
    start: float
    end: float
    score: float
    reason: str


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
    return data


def validate_scores(data: Any) -> dict[str, Any]:
    data = _require_mapping(data)
    _require(data, ["source_file", "directive", "segments"])
    _relative_path(data["source_file"], "source_file")
    for seg in data["segments"]:
        _require(seg, ["start", "end", "score", "reason"])
        _number(seg["score"], "segment.score")
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
    "scores": validate_scores,
    "clips": validate_clips,
    "montage": validate_montage,
    "pipeline": validate_pipeline,
}
