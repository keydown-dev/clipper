"""LLM transcript scoring for candidate clips."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .artifacts import ArtifactError, ArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .config import ClipperConfig
from .progress import CliProgress
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


@dataclass
class TokenUsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    responses_with_usage: int = 0
    responses_without_usage: int = 0

    def add(self, usage: Any) -> None:
        prompt = _usage_value(usage, "prompt_tokens")
        completion = _usage_value(usage, "completion_tokens")
        total = _usage_value(usage, "total_tokens")
        if prompt is None and completion is None and total is None:
            self.responses_without_usage += 1
            return
        self.prompt_tokens += int(prompt or 0)
        self.completion_tokens += int(completion or 0)
        self.total_tokens += int(total if total is not None else int(prompt or 0) + int(completion or 0))
        self.responses_with_usage += 1


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


def sentence_transcript_as_context(transcript: dict[str, Any], sentence_transcript: dict[str, Any] | None) -> dict[str, Any]:
    """Return a transcript-shaped scoring context, preferring sentence artifacts when available."""

    if sentence_transcript is None:
        return transcript
    context = dict(transcript)
    context["duration"] = sentence_transcript.get("duration", transcript.get("duration", 0.0))
    context["segments"] = list(sentence_transcript.get("sentences", []))
    return context


def format_timestamped_transcript(segments: Iterable[dict[str, Any]]) -> str:
    return "\n".join(f"[{float(seg['start']):.2f}-{float(seg['end']):.2f}] {str(seg.get('text', '')).strip()}" for seg in segments)


def build_messages(*, directive: str, window: TranscriptWindow, retry: bool = False, context_label: str = "Transcript") -> list[dict[str, str]]:
    system = BASELINE_SYSTEM_PROMPT + (STRICT_RETRY_SUFFIX if retry else "")
    user = (
        f"Directive: {directive}\n\n"
        f"{context_label} window: {window.start:.2f}-{window.end:.2f} seconds\n"
        "Choose candidate clips that best match the directive. Prefer 5-15 second segments where possible.\n\n"
        f"{context_label}:\n{format_timestamped_transcript(window.segments)}"
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


def _sentence_overlaps_segment(sentence: dict[str, Any], segment: dict[str, Any]) -> bool:
    return float(sentence["end"]) >= float(segment["start"]) and float(sentence["start"]) <= float(segment["end"])


def enrich_segments_with_dialogue(segments: Iterable[dict[str, Any]], sentence_transcript: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Attach overlapping sentence artifacts and joined dialogue to scored segments."""

    if sentence_transcript is None:
        return [dict(segment) for segment in segments]
    sentences = list(sentence_transcript.get("sentences", []))
    enriched: list[dict[str, Any]] = []
    for segment in segments:
        current = dict(segment)
        overlapping = [dict(sentence) for sentence in sentences if _sentence_overlaps_segment(sentence, current)]
        current["sentences"] = overlapping
        dialogue = " ".join(str(sentence.get("text", "")).strip() for sentence in overlapping if str(sentence.get("text", "")).strip())
        if dialogue:
            current["dialogue"] = dialogue
        enriched.append(current)
    return enriched


def _message_content(response: Any) -> str:
    try:
        return str(response.choices[0].message.content)
    except (AttributeError, IndexError, TypeError) as exc:
        raise ArtifactError("LLM response did not include choices[0].message.content") from exc


def _usage_value(usage: Any, key: str) -> int | None:
    if usage is None:
        return None
    value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _response_usage(response: Any) -> Any:
    if isinstance(response, dict):
        return response.get("usage")
    return getattr(response, "usage", None)


def _call_llm(client: Any, *, options: ScoringOptions, messages: list[dict[str, str]]) -> tuple[str, Any]:
    try:
        response = client.chat.completions.create(model=options.model, messages=messages, temperature=options.temperature, timeout=options.timeout_seconds)
    except Exception as exc:
        raise ArtifactError(f"LLM scoring request failed: {exc}") from exc
    return _message_content(response), _response_usage(response)


def _log_window_progress(progress: CliProgress | None, *, index: int, total: int, window: TranscriptWindow) -> None:
    if not progress:
        return
    percent = int((index / total) * 100) if total else 100
    progress.log(f"scoring progress: window {index}/{total} ({percent}%) range={window.start:.2f}-{window.end:.2f}s")


def _summarize_warnings(warnings: list[str]) -> str:
    dropped = sum(1 for warning in warnings if "dropped" in warning)
    clamped = sum(1 for warning in warnings if "clamped" in warning)
    retried = sum(1 for warning in warnings if "retried" in warning)
    return f"warnings={len(warnings)} dropped={dropped} clamped={clamped} retries={retried}"


def score_transcript(
    transcript: dict[str, Any],
    *,
    client: Any,
    options: ScoringOptions,
    progress: CliProgress | None = None,
    token_usage: TokenUsageTotals | None = None,
    sentence_transcript: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    scoring_context = sentence_transcript_as_context(transcript, sentence_transcript)
    return score_context(
        scoring_context,
        client=client,
        options=options,
        progress=progress,
        token_usage=token_usage,
        sentence_transcript=sentence_transcript,
        context_label="Transcript",
    )


def score_context(
    context: dict[str, Any],
    *,
    client: Any,
    options: ScoringOptions,
    progress: CliProgress | None = None,
    token_usage: TokenUsageTotals | None = None,
    sentence_transcript: dict[str, Any] | None = None,
    context_label: str = "Context",
) -> tuple[list[dict[str, Any]], list[str]]:
    lower, upper = transcript_bounds(context)
    all_segments: list[dict[str, Any]] = []
    warnings: list[str] = []
    windows = chunk_transcript(context)
    total_windows = len(windows)
    for index, window in enumerate(windows, start=1):
        if progress:
            progress.log(f"scoring window {index}/{total_windows}: range={window.start:.2f}-{window.end:.2f}s segments={len(window.segments)}")
        try:
            content, usage = _call_llm(client, options=options, messages=build_messages(directive=options.directive, window=window, context_label=context_label))
            if token_usage:
                token_usage.add(usage)
            raw = parse_segments_response(content)
        except (ValueError, json.JSONDecodeError):
            if progress:
                progress.log(f"retrying invalid JSON for window {window.start:.2f}-{window.end:.2f}s")
            try:
                content, usage = _call_llm(client, options=options, messages=build_messages(directive=options.directive, window=window, retry=True, context_label=context_label))
                if token_usage:
                    token_usage.add(usage)
                raw = parse_segments_response(content)
                warnings.append(f"retried invalid JSON for window {window.start:.2f}-{window.end:.2f}")
            except (ValueError, json.JSONDecodeError) as exc:
                warnings.append(f"dropped window {window.start:.2f}-{window.end:.2f}: invalid JSON after retry ({exc})")
                _log_window_progress(progress, index=index, total=total_windows, window=window)
                continue
        valid, segment_warnings = validate_normalize_segments(raw, lower_bound=lower, upper_bound=upper)
        all_segments.extend(valid)
        warnings.extend(segment_warnings)
        _log_window_progress(progress, index=index, total=total_windows, window=window)
    merged = enrich_segments_with_dialogue(merge_overlapping_segments(all_segments), sentence_transcript)
    if not merged:
        warnings.append("no valid candidate segments remained after validation")
    if progress and warnings:
        progress.log(_summarize_warnings(warnings))
    return merged, warnings


def _require_artifact(path: Path, context_flag: str, artifact_name: str, hint: str) -> None:
    if not path.exists():
        raise ArtifactError(f"{context_flag} requires {artifact_name} artifact: {path}; {hint}")


def _join_values(values: Iterable[Any]) -> str:
    return ", ".join(str(value) for value in values if str(value).strip())


def _visual_observation_text(observation: dict[str, Any], shot: dict[str, Any] | None) -> str:
    parts = [f"Visual shot {observation['shot_id']}"]
    if shot is not None:
        parts.append(f"shot duration {float(shot['duration']):.2f}s")
        parts.append(f"frame {shot['representative_frame_path']}")
    parts.append(str(observation.get("description", "")).strip())
    for label, field in [("people", "visible_people"), ("actions", "actions"), ("objects", "objects"), ("text", "visible_text")]:
        joined = _join_values(observation.get(field, []))
        if joined:
            parts.append(f"{label}: {joined}")
    for label, field in [("mood", "mood"), ("setting", "setting")]:
        value = str(observation.get(field, "")).strip()
        if value:
            parts.append(f"{label}: {value}")
    return "; ".join(parts)


def filter_scoring_context_by_time(context: dict[str, Any], *, start: float | None = None, end: float | None = None) -> dict[str, Any]:
    """Return scoring context limited to segments overlapping a time range."""

    if start is None and end is None:
        return context
    lower = 0.0 if start is None else float(start)
    upper = float(context.get("duration") or 0.0) if end is None else float(end)
    if lower < 0:
        raise ArtifactError("--start must be non-negative")
    if upper <= lower:
        raise ArtifactError("--end must be greater than --start")
    filtered = [seg for seg in context.get("segments", []) if float(seg["end"]) >= lower and float(seg["start"]) <= upper]
    if not filtered:
        raise ArtifactError(f"no scoring evidence overlaps requested range {lower:g}-{upper:g}s")
    result = dict(context)
    result["duration"] = upper
    result["segments"] = filtered
    return result


def build_explicit_scoring_context(
    *,
    sentence_transcript: dict[str, Any] | None = None,
    shots_manifest: dict[str, Any] | None = None,
    visual_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    source_file = "source/source.mp4"
    duration = 0.0
    if sentence_transcript is not None:
        source_file = str(sentence_transcript["source_file"])
        duration = max(duration, float(sentence_transcript.get("duration") or 0.0))
        for sentence in sentence_transcript.get("sentences", []):
            segments.append({"start": sentence["start"], "end": sentence["end"], "text": f"Transcript: {sentence['text']}"})
    if visual_index is not None:
        source_file = str(visual_index["source_file"])
        shots_by_id = {shot["id"]: shot for shot in (shots_manifest or {}).get("shots", [])}
        for observation in visual_index.get("observations", []):
            segments.append(
                {
                    "start": observation["start"],
                    "end": observation["end"],
                    "text": _visual_observation_text(observation, shots_by_id.get(observation["shot_id"])),
                }
            )
            duration = max(duration, float(observation.get("end") or 0.0))
    segments.sort(key=lambda segment: (float(segment["start"]), float(segment["end"]), str(segment.get("text", ""))))
    return {"schema_version": SCHEMA_VERSION, "source_file": source_file, "duration": duration, "segments": segments}


def make_openai_client(config: ClipperConfig) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - doctor catches this in normal installs
        raise ArtifactError("openai is not installed; install project dependencies with `uv sync`") from exc
    return OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key or "not-needed", timeout=config.llm_timeout_seconds)


def _base_url_origin(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return base_url


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
    progress: CliProgress | None = None,
    with_transcript: bool = False,
    with_visuals: bool = False,
    project: str | None = None,
    start: float | None = None,
    end: float | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name).for_project(project)
    if not with_transcript and not with_visuals:
        raise ArtifactError("clipper score requires at least one scoring context: add --with-transcript, --with-visuals, or both")
    policy = output_policy([layout.scores], reuse=reuse, force=force, schema="scores")
    if policy == "reuse":
        if progress:
            progress.log(f"reusing existing scores for video {layout.video}: {layout.scores}")
        return layout.video, layout.scores, read_validated_json(layout.scores, "scores"), True
    sentence_transcript = None
    shots_manifest = None
    visual_index = None
    if with_transcript:
        _require_artifact(layout.sentence_transcript, "--with-transcript", "sentence transcript", "run `clipper transcribe` first")
        sentence_transcript = read_validated_json(layout.sentence_transcript, "sentence_transcript")
    if with_visuals:
        _require_artifact(layout.shots_manifest, "--with-visuals", "shot manifest", "run `clipper shots` first")
        _require_artifact(layout.visual_index, "--with-visuals", "visual index", "run `clipper visual` first")
        shots_manifest = read_validated_json(layout.shots_manifest, "shots")
        visual_index = read_validated_json(layout.visual_index, "visual_index")
    scoring_context = filter_scoring_context_by_time(
        build_explicit_scoring_context(sentence_transcript=sentence_transcript, shots_manifest=shots_manifest, visual_index=visual_index),
        start=start,
        end=end,
    )
    options = ScoringOptions(directive=directive, model=config.llm_model, temperature=config.llm_temperature, timeout_seconds=config.llm_timeout_seconds)
    windows = chunk_transcript(scoring_context)
    if progress:
        selected = ",".join(name for name, enabled in [("transcript", with_transcript), ("visuals", with_visuals)] if enabled)
        project_text = f" project={project}" if project else ""
        progress.log(f"video {layout.video}{project_text}: scoring_context={selected}")
        progress.log(f"scoring directive: {directive}")
        progress.log(
            "LLM "
            f"base_url={_base_url_origin(config.llm_base_url)} model={options.model} "
            f"temperature={options.temperature} timeout={options.timeout_seconds}"
        )
        if sentence_transcript is not None:
            progress.log(f"video {layout.video}: transcript={layout.sentence_transcript}")
            progress.log(f"transcript duration={float(sentence_transcript.get('duration') or 0.0)} segments={len(sentence_transcript.get('sentences', []))}")
            progress.log(f"sentence transcript={layout.sentence_transcript} sentences={len(sentence_transcript.get('sentences', []))}")
        if visual_index is not None:
            progress.log(
                f"visual index={layout.visual_index} observations={len(visual_index.get('observations', []))} "
                f"shots={len((shots_manifest or {}).get('shots', []))}"
            )
        if start is not None or end is not None:
            progress.log(f"scoring range={start if start is not None else 0:g}-{end if end is not None else float(scoring_context.get('duration') or 0.0):g}s")
        progress.log(f"scoring evidence items={len(scoring_context.get('segments', []))}")
        progress.log(f"scoring windows={len(windows)}")
        progress.log(f"scores output={layout.scores}")
    client = client or make_openai_client(config)
    token_usage = TokenUsageTotals()
    context_label = "Transcript and visual context" if with_transcript and with_visuals else "Transcript" if with_transcript else "Visual context"
    segments, warnings = score_context(
        scoring_context,
        client=client,
        options=options,
        progress=progress,
        token_usage=token_usage,
        sentence_transcript=sentence_transcript,
        context_label=context_label,
    )
    scores: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_file": scoring_context["source_file"],
        "directive": directive,
        "segments": segments,
    }
    if warnings:
        scores["warnings"] = warnings
    write_json(layout.scores, scores)
    if progress:
        if token_usage.responses_with_usage:
            progress.log(
                "token usage: "
                f"prompt={token_usage.prompt_tokens} completion={token_usage.completion_tokens} "
                f"total={token_usage.total_tokens} responses_with_usage={token_usage.responses_with_usage}"
            )
            if token_usage.responses_without_usage:
                progress.log(f"token usage unavailable for {token_usage.responses_without_usage} response(s)")
        else:
            progress.log("token usage unavailable: API did not provide usage metadata")
        progress.log(f"completed scoring: segments={len(segments)} scores={layout.scores}")
    return layout.video, layout.scores, scores, False
