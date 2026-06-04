"""Analyze representative shot frames with a multimodal chat model."""

from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .artifacts import ArtifactError, ArtifactLayout, SourceArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .config import ClipperConfig
from .progress import CliProgress
from .schemas import SCHEMA_VERSION

VISUAL_SYSTEM_PROMPT = """You analyze video representative frames for clip selection.
Return ONLY one raw JSON object with these fields:
- description: concise visual description
- visible_people: array of visible people or roles
- actions: array of visible actions
- objects: array of notable objects
- mood: concise mood
- setting: concise setting
- visible_text: array of readable visible text strings
No markdown, prose, or code fences."""


@dataclass(frozen=True)
class VisualOptions:
    base_url: str
    api_key: str | None
    model: str
    temperature: float = 0.0
    timeout_seconds: float = 60.0


def options_from_config(config: ClipperConfig) -> VisualOptions:
    """Build visual analysis options, defaulting to LLM settings with VISION_* overrides."""

    return VisualOptions(
        base_url=config.vision_base_url or config.llm_base_url,
        api_key=config.vision_api_key if config.vision_api_key is not None else config.llm_api_key,
        model=config.vision_model or config.llm_model,
        temperature=config.vision_temperature if config.vision_temperature is not None else config.llm_temperature,
        timeout_seconds=config.vision_timeout_seconds if config.vision_timeout_seconds is not None else config.llm_timeout_seconds,
    )


def make_openai_client(options: VisualOptions) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - doctor catches this in normal installs.
        raise ArtifactError("openai is not installed; install project dependencies with `uv sync`") from exc
    return OpenAI(base_url=options.base_url, api_key=options.api_key or "not-needed", timeout=options.timeout_seconds)


def _base_url_origin(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return base_url


def _video_relative(layout: ArtifactLayout | SourceArtifactLayout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _resolve_analysis_layout(store: Path, target: str | None, *, json_output: bool = False) -> ArtifactLayout | SourceArtifactLayout:
    """Resolve source-level analysis target, preferring .clipper/sources/{name}."""

    if target:
        path = Path(target).expanduser()
        if path.exists() and path.is_dir():
            if path.parent.name == "sources":
                return SourceArtifactLayout.for_source(path.parent.parent, path.name)
            return ArtifactLayout.for_video(path.parent, path.name)
        source = store / "sources" / target
        if source.exists() and source.is_dir():
            return SourceArtifactLayout.for_source(store, target)
    root = resolve_video(store, target, json_output=json_output)
    return ArtifactLayout.for_video(root.parent, root.name)


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_messages(*, shot: dict[str, Any], frame_path: Path) -> list[dict[str, Any]]:
    user_text = (
        f"Analyze this representative frame for shot {shot['id']} "
        f"({float(shot['start']):.2f}-{float(shot['end']):.2f}s, representative_time={float(shot['representative_time']):.2f}s)."
    )
    return [
        {"role": "system", "content": VISUAL_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": _data_url(frame_path)}},
            ],
        },
    ]


def _find_first_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
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
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("unterminated JSON object")


def parse_visual_response(text: str) -> dict[str, Any]:
    payload = json.loads(_find_first_json_object(text))
    if not isinstance(payload, dict):
        raise ValueError("visual response must be a JSON object")
    return payload


def _message_content(response: Any) -> str:
    if isinstance(response, dict):
        try:
            return str(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ArtifactError("vision response did not include choices[0].message.content") from exc
    try:
        return str(response.choices[0].message.content)
    except (AttributeError, IndexError, TypeError) as exc:
        raise ArtifactError("vision response did not include choices[0].message.content") from exc


def _list_of_strings(value: Any, field: str, warnings: list[str], shot_id: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        warnings.append(f"repaired {shot_id}.{field}: coerced string to one-item list")
        return [value]
    if not isinstance(value, list):
        warnings.append(f"repaired {shot_id}.{field}: replaced non-list with empty list")
        return []
    repaired = [str(item).strip() for item in value if str(item).strip()]
    if len(repaired) != len(value):
        warnings.append(f"repaired {shot_id}.{field}: dropped empty list item(s)")
    return repaired


def normalize_observation(raw: dict[str, Any], *, shot: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    shot_id = str(shot["id"])
    description = str(raw.get("description", "")).strip()
    if not description:
        raise ArtifactError(f"visual analysis for {shot_id} missing required description")
    return {
        "shot_id": shot_id,
        "start": float(shot["start"]),
        "end": float(shot["end"]),
        "representative_time": float(shot["representative_time"]),
        "frame_path": str(shot["representative_frame_path"]),
        "description": description,
        "visible_people": _list_of_strings(raw.get("visible_people"), "visible_people", warnings, shot_id),
        "actions": _list_of_strings(raw.get("actions"), "actions", warnings, shot_id),
        "objects": _list_of_strings(raw.get("objects"), "objects", warnings, shot_id),
        "mood": str(raw.get("mood", "")).strip(),
        "setting": str(raw.get("setting", "")).strip(),
        "visible_text": _list_of_strings(raw.get("visible_text"), "visible_text", warnings, shot_id),
    }


def analyze_frames(
    shots: dict[str, Any],
    *,
    layout: ArtifactLayout | SourceArtifactLayout,
    client: Any,
    options: VisualOptions,
    progress: CliProgress | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    warnings: list[str] = []
    shot_list = list(shots.get("shots", []))
    for index, shot in enumerate(shot_list, start=1):
        frame_path = layout.root / shot["representative_frame_path"]
        if not frame_path.exists():
            raise ArtifactError(f"missing representative frame for {shot['id']}: {shot['representative_frame_path']}")
        if progress:
            progress.log(f"visual analysis {index}/{len(shot_list)}: {shot['id']} frame={shot['representative_frame_path']}")
        try:
            response = client.chat.completions.create(
                model=options.model,
                messages=build_messages(shot=shot, frame_path=frame_path),
                temperature=options.temperature,
                timeout=options.timeout_seconds,
            )
            raw = parse_visual_response(_message_content(response))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ArtifactError(f"invalid visual JSON for {shot['id']}: {exc}") from exc
        observations.append(normalize_observation(raw, shot=shot, warnings=warnings))
    return observations, warnings


def visual_video(
    *,
    store: Path,
    video: str | None,
    config: ClipperConfig,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    client: Any | None = None,
    progress: CliProgress | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Analyze shot frames and write work/visual-index.json."""

    layout = _resolve_analysis_layout(store, video, json_output=json_output)
    target_name = layout.source if isinstance(layout, SourceArtifactLayout) else layout.video
    if not layout.shots_manifest.exists():
        raise ArtifactError(f"missing shot manifest; run `clipper shots {target_name}` first: {layout.shots_manifest}")
    shots = read_validated_json(layout.shots_manifest, "shots")
    policy = output_policy([layout.visual_index], reuse=reuse, force=force, schema="visual_index")
    if policy == "reuse":
        return target_name, layout.visual_index, read_validated_json(layout.visual_index, "visual_index"), True

    missing = [shot["representative_frame_path"] for shot in shots.get("shots", []) if not (layout.root / shot["representative_frame_path"]).exists()]
    if missing:
        raise ArtifactError(f"missing representative frame artifact(s): {', '.join(missing)}")
    if force:
        layout.visual_index.unlink(missing_ok=True)

    options = options_from_config(config)
    if not options.base_url or not options.model:
        raise ArtifactError("Set VISION_BASE_URL/VISION_MODEL or LLM_BASE_URL/LLM_MODEL before visual analysis.")
    if progress:
        progress.log(f"vision base_url={_base_url_origin(options.base_url)} model={options.model} temperature={options.temperature} timeout={options.timeout_seconds}")
        progress.log(f"visual index output={layout.visual_index}")
    client = client or make_openai_client(options)
    observations, warnings = analyze_frames(shots, layout=layout, client=client, options=options, progress=progress)
    index: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_file": shots["source_file"],
        "shots_path": _video_relative(layout, layout.shots_manifest),
        "provider": {
            "base_url": options.base_url,
            "model": options.model,
            "temperature": float(options.temperature),
            "timeout_seconds": float(options.timeout_seconds),
        },
        "observations": observations,
    }
    if warnings:
        index["warnings"] = warnings
    write_json(layout.visual_index, index)
    return target_name, layout.visual_index, index, False
