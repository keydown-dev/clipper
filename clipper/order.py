"""Project-level editorial clip ordering helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import ArtifactError, ProjectArtifactLayout, read_validated_json, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clip_order_path(store: Path, project: str) -> Path:
    return ProjectArtifactLayout.for_project(store, project).root / "clip-order.json"


def _clips_by_id(layout: ProjectArtifactLayout) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not layout.clips_manifest.exists():
        raise ArtifactError(f"clips manifest not found: {layout.clips_manifest}")
    manifest = read_validated_json(layout.clips_manifest, "clips")
    clips = manifest["clips"]
    by_id: dict[str, dict[str, Any]] = {}
    for clip in clips:
        clip_id = clip.get("id")
        if not isinstance(clip_id, str):
            raise ArtifactError(f"schema-invalid JSON in {layout.clips_manifest}: clip.id must be a string")
        by_id[clip_id] = clip
    return by_id, clips, manifest


def _order_entry(clip: dict[str, Any]) -> dict[str, Any]:
    return {"id": clip["id"], "path": clip["path"], "duration": float(clip["duration"])}


def build_clip_order(store: Path, project: str, clip_ids: list[str] | None = None) -> tuple[Path, dict[str, Any]]:
    """Build a canonical clip order document from clips.json."""

    layout = ProjectArtifactLayout.for_project(store, project)
    by_id, clips, manifest = _clips_by_id(layout)
    ordered_ids = [clip["id"] for clip in clips] if clip_ids is None else clip_ids
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    for clip_id in ordered_ids:
        if clip_id in seen and clip_id not in duplicates:
            duplicates.append(clip_id)
        seen.add(clip_id)
        if clip_id not in by_id and clip_id not in missing:
            missing.append(clip_id)
    if duplicates:
        raise ArtifactError(f"duplicate clip id(s) in order: {', '.join(duplicates)}")
    if missing:
        raise ArtifactError(f"ordered clip id(s) not found in clips.json: {', '.join(missing)}")

    path = clip_order_path(store, project)
    now = utc_now()
    existing_created = None
    if path.exists():
        try:
            existing_created = read_validated_json(path, "clip_order").get("created_at")
        except ArtifactError:
            existing_created = None
    order = {
        "schema_version": 1,
        "source_file": "clips.json",
        "created_at": existing_created or now,
        "updated_at": now,
        "order": [_order_entry(by_id[clip_id]) for clip_id in ordered_ids],
    }
    return path, order


def write_clip_order(store: Path, project: str, clip_ids: list[str] | None = None) -> tuple[Path, dict[str, Any]]:
    path, order = build_clip_order(store, project, clip_ids)
    write_json(path, order)
    return path, order


def _write_existing_order(path: Path, order: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    order["updated_at"] = utc_now()
    write_json(path, order)
    return path, order


def read_clip_order(store: Path, project: str) -> tuple[Path, dict[str, Any]]:
    layout = ProjectArtifactLayout.for_project(store, project)
    _clips_by_id(layout)
    path = clip_order_path(store, project)
    if not path.exists():
        path, order = build_clip_order(store, project)
        return path, order
    order = read_validated_json(path, "clip_order")
    by_id, _, _ = _clips_by_id(layout)
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    for entry in order["order"]:
        clip_id = entry["id"]
        if clip_id in seen and clip_id not in duplicates:
            duplicates.append(clip_id)
        seen.add(clip_id)
        if clip_id not in by_id and clip_id not in missing:
            missing.append(clip_id)
    if duplicates:
        raise ArtifactError(f"duplicate clip id(s) in clip-order.json: {', '.join(duplicates)}")
    if missing:
        raise ArtifactError(f"ordered clip id(s) not found in clips.json: {', '.join(missing)}")
    return path, order


def move_clip_order(store: Path, project: str, clip_id: str, position: int) -> tuple[Path, dict[str, Any]]:
    """Move a clip to a 1-based position in the project clip order."""

    path, order = read_clip_order(store, project)
    entries = order["order"]
    if position < 1 or position > len(entries):
        raise ArtifactError(f"--to position must be between 1 and {len(entries)}")
    index = next((idx for idx, entry in enumerate(entries) if entry["id"] == clip_id), None)
    if index is None:
        raise ArtifactError(f"clip id not found in clip-order.json: {clip_id}")
    entry = entries.pop(index)
    entries.insert(position - 1, entry)
    return _write_existing_order(path, order)


def swap_clip_order(store: Path, project: str, clip_a: str, clip_b: str) -> tuple[Path, dict[str, Any]]:
    """Swap two clips in the project clip order."""

    path, order = read_clip_order(store, project)
    entries = order["order"]
    indexes = {entry["id"]: idx for idx, entry in enumerate(entries)}
    missing = [clip_id for clip_id in (clip_a, clip_b) if clip_id not in indexes]
    if missing:
        raise ArtifactError(f"clip id(s) not found in clip-order.json: {', '.join(missing)}")
    index_a = indexes[clip_a]
    index_b = indexes[clip_b]
    entries[index_a], entries[index_b] = entries[index_b], entries[index_a]
    return _write_existing_order(path, order)


def total_duration(order: dict[str, Any]) -> float:
    return float(sum(float(entry["duration"]) for entry in order["order"]))
