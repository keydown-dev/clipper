"""LLM transcript scoring for candidate clips."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .config import ClipperConfig
from .schemas import SCHEMA_VERSION

BASELINE_SYSTEM_PROMPT = """You are a video clip scorer. Given a transcript with timestamps, identify the most visually interesting segments based on the user's directive.

For each segment, provide:
- start: start time in seconds (float)
- end: end time in seconds (float) — segments should be 5-15 seconds long
- score: 0-10 rating of how well this matches the directive
- reason: one-sentence explanation of why this segment scores highly

Return ONLY a JSON array of objects. No markdown, no explanation, no code fences. Example:
[{"start": 12.5, "end": 22.0, "score": 8, "reason": "Hosts laugh and gesture expressively"}]"""

STRICT_RETRY_SUFFIX = "\n\nYour previous response was not valid. Return ONLY a raw JSON array, with no markdown, no prose, and no code fences."
WINDOW_SECONDS = 10 * 60
OVERLAP_SECONDS = 30


@dataclass(frozen=True)
class ScoringOptions:
    directive: str
    model: str
    temperature: float = 0.0
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class TranscriptWindow:
    start: float
    end: float
    segments: list[dict[str, Any]]


def transcript_bounds(transcript: dict[str, Any]) -> tuple[float, float]:
    duration = float(transcript.get("duration") or 0.0)
    starts = [float(seg["start"]) for seg in transcript.get("segments", [])]
    ends = [float(seg["end"]) for seg in transcript.get("segments", [])]
    lower = min(starts, default=0.0)
    upper = max([duration, *ends], default=duration)
    return lower, upper


def chunk_transcript(transcript: dict[str, Any], *, window_seconds: float = WINDOW_SECONDS, overlap_seconds: float = OVERLAP_SECONDS) -> list[TranscriptWindow]:
    """Split transcript into overlapping timestamp windows."""

    segments = list(transcript.get("segments", []))
    if not segments:
        return [TranscriptWindow(0.0, float(transcript.get("duration") or 0.0), [])]
    _, upper = transcript_bounds(transcript)
    if upper <= window_seconds:
        return [TranscriptWindow(0.0, upper, segments)]
    windows: list[TranscriptWindow] = []
    start = 0.0
    step = window_seconds - overlap_seconds
    while start < upper:
        end = min(start + window_seconds, upper)
        window_segments = [seg for seg in segments if float(seg["end"]) >= start and float(seg["start"]) <= end]
        if window_segments:
            windows.append(TranscriptWindow(start, end, window_segments))
        if end >= upper:
            break
        start += step
    return windows


def format_timestamped_transcript(segments: Iterable[dict[str, Any]]) -> str:
    return "\n".join(f"[{float(seg['start']):.2f}-{float(seg['end']):.2f}] {str(seg.get('text', '')).strip()}" for seg in segments)


def build_messages(*, directive: str, window: TranscriptWindow, retry: bool = False) -> list[dict[str, str]]:
    system = BASELINE_SYSTEM_PROMPT + (STRICT_RETRY_SUFFIX if retry else "")
    user = (
        f"Directive: {directive}\n\n"
        f"Transcript window: {window.start:.2f}-{window.end:.2f} seconds\n"
        "Choose candidate clips that best match the directive. Prefer 5-15 second segments where possible.\n\n"
        f"Transcript:\n{format_timestamped_transcript(window.segments)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _find_first_json_array(text: str) -> str:
    start = text.find("[")
    if start < 0:
        raise ValueError("no JSON array found")
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("unterminated JSON array")


def parse_segments_response(text: str) -> list[Any]:
    payload = json.loads(_find_first_json_array(text))
    if not isinstance(payload, list):
        raise ValueError("LLM response must be a JSON array")
    return payload


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    return float(value)


def validate_normalize_segments(raw_segments: Iterable[Any], *, lower_bound: float, upper_bound: float) -> tuple[list[dict[str, Any]], list[str]]:
    valid: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            warnings.append(f"dropped segment {index}: not an object")
            continue
        try:
            start = _coerce_float(raw.get("start"))
            end = _coerce_float(raw.get("end"))
            score = _coerce_float(raw.get("score"))
        except (TypeError, ValueError):
            warnings.append(f"dropped segment {index}: unusable start/end/score")
            continue
        reason = str(raw.get("reason", "")).strip()
        if not reason:
            warnings.append(f"dropped segment {index}: missing reason")
            continue
        if not 0 <= score <= 10:
            warnings.append(f"dropped segment {index}: score {score:g} outside 0-10")
            continue
        clamped_start = max(lower_bound, min(start, upper_bound))
        clamped_end = max(lower_bound, min(end, upper_bound))
        if (clamped_start, clamped_end) != (start, end):
            warnings.append(f"clamped segment {index} to transcript bounds")
        if clamped_end <= clamped_start:
            warnings.append(f"dropped segment {index}: end <= start")
            continue
        valid.append({"start": clamped_start, "end": clamped_end, "score": score, "reason": reason})
    return valid, warnings


def merge_overlapping_segments(segments: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(segments, key=lambda seg: (float(seg["start"]), -float(seg["score"])))
    merged: list[dict[str, Any]] = []
    for seg in ordered:
        current = dict(seg)
        if not merged or float(current["start"]) > float(merged[-1]["end"]):
            merged.append(current)
            continue
        previous = merged[-1]
        stronger = current if float(current["score"]) > float(previous["score"]) else previous
        previous["start"] = min(float(previous["start"]), float(current["start"]))
        previous["end"] = max(float(previous["end"]), float(current["end"]))
        previous["score"] = float(stronger["score"])
        previous["reason"] = str(stronger["reason"])
    return merged


def _message_content(response: Any) -> str:
    try:
        return str(response.choices[0].message.content)
    except (AttributeError, IndexError, TypeError) as exc:
        raise ArtifactError("LLM response did not include choices[0].message.content") from exc


def _call_llm(client: Any, *, options: ScoringOptions, messages: list[dict[str, str]]) -> str:
    try:
        response = client.chat.completions.create(model=options.model, messages=messages, temperature=options.temperature, timeout=options.timeout_seconds)
    except Exception as exc:
        raise ArtifactError(f"LLM scoring request failed: {exc}") from exc
    return _message_content(response)


def score_transcript(transcript: dict[str, Any], *, client: Any, options: ScoringOptions) -> tuple[list[dict[str, Any]], list[str]]:
    lower, upper = transcript_bounds(transcript)
    all_segments: list[dict[str, Any]] = []
    warnings: list[str] = []
    for window in chunk_transcript(transcript):
        try:
            raw = parse_segments_response(_call_llm(client, options=options, messages=build_messages(directive=options.directive, window=window)))
        except (ValueError, json.JSONDecodeError):
            try:
                raw = parse_segments_response(_call_llm(client, options=options, messages=build_messages(directive=options.directive, window=window, retry=True)))
                warnings.append(f"retried invalid JSON for window {window.start:.2f}-{window.end:.2f}")
            except (ValueError, json.JSONDecodeError) as exc:
                warnings.append(f"dropped window {window.start:.2f}-{window.end:.2f}: invalid JSON after retry ({exc})")
                continue
        valid, segment_warnings = validate_normalize_segments(raw, lower_bound=lower, upper_bound=upper)
        all_segments.extend(valid)
        warnings.extend(segment_warnings)
    merged = merge_overlapping_segments(all_segments)
    if not merged:
        warnings.append("no valid candidate segments remained after validation")
    return merged, warnings


def make_openai_client(config: ClipperConfig) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - doctor catches this in normal installs
        raise ArtifactError("openai is not installed; install project dependencies with `uv sync`") from exc
    return OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key or "not-needed", timeout=config.llm_timeout_seconds)


def score_video(
    *,
    store: Path,
    video: str | None,
    directive: str,
    config: ClipperConfig,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    client: Any | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name)
    transcript = read_validated_json(layout.transcript, "transcript")
    policy = output_policy([layout.scores], reuse=reuse, force=force, schema="scores")
    if policy == "reuse":
        return layout.video, layout.scores, read_validated_json(layout.scores, "scores"), True
    client = client or make_openai_client(config)
    options = ScoringOptions(directive=directive, model=config.llm_model, temperature=config.llm_temperature, timeout_seconds=config.llm_timeout_seconds)
    segments, warnings = score_transcript(transcript, client=client, options=options)
    scores: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_file": transcript["source_file"],
        "directive": directive,
        "segments": segments,
    }
    if warnings:
        scores["warnings"] = warnings
    write_json(layout.scores, scores)
    return layout.video, layout.scores, scores, False
