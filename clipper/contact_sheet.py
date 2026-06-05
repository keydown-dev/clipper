"""Render project clip contact sheets with FFmpeg."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactError, ProjectArtifactLayout, read_validated_json


@dataclass(frozen=True)
class ContactSheetOptions:
    chronological: bool = False
    columns: int = 4
    thumb_width: int = 320
    thumb_height: int = 180
    output: Path | None = None
    force: bool = False


@dataclass(frozen=True)
class ContactSheetResult:
    project: str
    path: Path
    clip_count: int
    order_source: str
    columns: int
    thumb_width: int
    thumb_height: int
    width: int
    height: int


def _validate_options(options: ContactSheetOptions) -> None:
    if options.columns <= 0:
        raise ArtifactError("--columns must be greater than zero")
    if options.thumb_width <= 0:
        raise ArtifactError("--thumb-width must be greater than zero")
    if options.thumb_height <= 0:
        raise ArtifactError("--thumb-height must be greater than zero")


def _ordered_project_clips(layout: ProjectArtifactLayout, *, chronological: bool) -> tuple[list[dict[str, Any]], str]:
    manifest = read_validated_json(layout.clips_manifest, "clips")
    clips = list(manifest["clips"])
    if chronological:
        clips.sort(key=lambda item: (str(item.get("source") or item.get("source_file") or ""), float(item["start"]), float(item["end"])))
        return clips, "chronological"
    if not layout.clip_order.exists():
        return clips, "clips.json"

    order = read_validated_json(layout.clip_order, "clip_order")
    clips_by_id = {clip["id"]: clip for clip in clips}
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    for entry in order["order"]:
        clip_id = entry["id"]
        if clip_id in seen and clip_id not in duplicates:
            duplicates.append(clip_id)
        seen.add(clip_id)
        clip = clips_by_id.get(clip_id)
        if clip is None:
            missing.append(clip_id)
            continue
        ordered.append(clip)
    if duplicates:
        raise ArtifactError(f"duplicate clip id(s) in clip-order.json: {', '.join(duplicates)}")
    if missing:
        raise ArtifactError(f"ordered clip id(s) not found in clips.json: {', '.join(missing)}")
    return ordered, "clip-order.json"


def _preview_time(clip: dict[str, Any]) -> float:
    duration = max(0.0, float(clip["duration"]))
    return min(0.5, duration / 2.0)


def ffmpeg_preview_command(*, source: Path, output: Path, offset: float, width: int, height: int) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{offset:g}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        str(output),
    ]


def ffmpeg_tile_command(*, input_pattern: Path, output: Path, columns: int, rows: int) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-framerate",
        "1",
        "-i",
        str(input_pattern),
        "-frames:v",
        "1",
        "-vf",
        f"tile={columns}x{rows}:padding=0:margin=0",
        str(output),
    ]


def _run(command: list[str], *, error: str) -> None:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise ArtifactError(f"{error}: {result.stderr.strip() or result.stdout.strip()}")


def render_project_contact_sheet(*, store: Path, project: str, options: ContactSheetOptions | None = None) -> ContactSheetResult:
    """Render a project contact sheet and reusable per-clip previews."""

    options = options or ContactSheetOptions()
    _validate_options(options)
    layout = ProjectArtifactLayout.for_project(store, project)
    output = options.output or (layout.root / "contact-sheet.jpg")
    if output.exists() and not options.force:
        raise ArtifactError(f"output already exists: {output}")

    clips, order_source = _ordered_project_clips(layout, chronological=options.chronological)
    if not clips:
        raise ArtifactError("no clips are available for contact sheet; no contact sheet was created")

    previews_dir = layout.root / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    preview_paths: list[Path] = []
    for clip in clips:
        source = layout.root / clip["path"]
        if not source.exists():
            raise ArtifactError(f"clip file not found: {clip['path']}")
        preview = previews_dir / f"{clip['id']}.jpg"
        if options.force or not preview.exists():
            command = ffmpeg_preview_command(source=source, output=preview, offset=_preview_time(clip), width=options.thumb_width, height=options.thumb_height)
            _run(command, error=f"ffmpeg preview extraction failed for {clip['id']}")
        preview_paths.append(preview)

    rows = int(math.ceil(len(preview_paths) / options.columns))
    with tempfile.TemporaryDirectory(prefix="clipper-contact-sheet-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for index, preview in enumerate(preview_paths, start=1):
            ordered = temp_dir / f"thumb-{index:04d}.jpg"
            try:
                ordered.symlink_to(preview.resolve())
            except OSError:
                shutil.copy2(preview, ordered)
        command = ffmpeg_tile_command(input_pattern=temp_dir / "thumb-%04d.jpg", output=output, columns=options.columns, rows=rows)
        _run(command, error="ffmpeg contact sheet render failed")

    return ContactSheetResult(
        project=layout.project,
        path=output,
        clip_count=len(clips),
        order_source=order_source,
        columns=options.columns,
        thumb_width=options.thumb_width,
        thumb_height=options.thumb_height,
        width=options.columns * options.thumb_width,
        height=rows * options.thumb_height,
    )
