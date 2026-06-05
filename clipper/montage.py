"""Assemble cut clips into a normalized montage with FFmpeg."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, ProjectArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .progress import CliProgress
from .schemas import SCHEMA_VERSION


@dataclass(frozen=True)
class MontageOptions:
    min_duration: float | None = None
    max_duration: float | None = None
    width: int = 1920
    height: int = 1080
    silent: bool = False
    chronological: bool = False


def _cleanup(paths: Iterable[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _scale_pad_filter(width: int, height: int) -> str:
    return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"


def select_clips_for_montage(clips: Iterable[dict[str, Any]], *, min_duration: float | None, max_duration: float | None, chronological: bool = False) -> tuple[list[dict[str, Any]], float]:
    """Return clip selections, trimming the last duration for max duration."""

    if min_duration is not None and min_duration < 0:
        raise ArtifactError("--min-duration must be non-negative")
    if max_duration is not None and max_duration <= 0:
        raise ArtifactError("--max-duration must be greater than zero")

    ordered_clips = [dict(clip) for clip in clips]
    if chronological:
        ordered_clips.sort(key=lambda item: (str(item.get("source") or item.get("source_file") or ""), float(item["start"]), float(item["end"])))

    selected: list[dict[str, Any]] = []
    remaining = max_duration
    for clip in ordered_clips:
        duration = float(clip["duration"])
        if duration <= 0:
            continue
        if remaining is None:
            selected.append({**clip, "selected_duration": duration})
            continue
        if remaining <= 0:
            break
        use_duration = min(duration, remaining)
        selected.append({**clip, "selected_duration": use_duration})
        remaining -= use_duration
        if remaining <= 0:
            break

    total = sum(float(clip["selected_duration"]) for clip in selected)
    if not selected:
        raise ArtifactError("no clips are available for montage; no montage was created")
    if min_duration is not None and total < min_duration:
        raise ArtifactError(f"selected clips total {total:g}s, below --min-duration {min_duration:g}s; no montage was created")
    return selected, total


def ffmpeg_trim_command(*, source: Path, output: Path, duration: float) -> list[str]:
    """Build a command to trim the final clip before concat demuxing."""

    return ["ffmpeg", "-y", "-i", str(source), "-t", f"{duration:g}", "-c", "copy", str(output)]


def ffmpeg_montage_command(*, filelist: Path, output: Path, width: int, height: int, silent: bool) -> list[str]:
    """Build the FFmpeg concat-demuxer command for a normalized montage."""

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(filelist),
        "-vf",
        _scale_pad_filter(width, height),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
    ]
    if silent:
        command.append("-an")
    else:
        command.extend(["-c:a", "aac"])
    command.append(str(output))
    return command


def _project_ordered_clips(layout: ProjectArtifactLayout, manifest: dict[str, Any], *, chronological: bool) -> tuple[list[dict[str, Any]], str]:
    if chronological:
        return list(manifest["clips"]), "chronological"
    if not layout.clip_order.exists():
        return list(manifest["clips"]), "clips.json"

    order = read_validated_json(layout.clip_order, "clip_order")
    clips_by_id = {clip["id"]: clip for clip in manifest["clips"]}
    ordered_clips: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    missing: list[str] = []
    for entry in order["order"]:
        clip_id = entry["id"]
        if clip_id in seen and clip_id not in duplicates:
            duplicates.append(clip_id)
        seen.add(clip_id)
        if clip_id not in clips_by_id:
            missing.append(clip_id)
            continue
        ordered_clips.append(clips_by_id[clip_id])
    if duplicates:
        raise ArtifactError(f"duplicate clip id(s) in clip-order.json: {', '.join(duplicates)}")
    if missing:
        raise ArtifactError(f"ordered clip id(s) not found in clips.json: {', '.join(missing)}")
    return ordered_clips, "clip-order.json"


def _clips_for_layout(layout: ArtifactLayout | ProjectArtifactLayout, manifest: dict[str, Any], *, chronological: bool) -> tuple[list[dict[str, Any]], str]:
    if isinstance(layout, ProjectArtifactLayout):
        return _project_ordered_clips(layout, manifest, chronological=chronological)
    return list(manifest["clips"]), "chronological" if chronological else "clips.json"


def _montage_from_layout(
    *,
    layout: ArtifactLayout | ProjectArtifactLayout,
    owner: str,
    options: MontageOptions,
    reuse: bool,
    force: bool,
    progress: CliProgress | None,
) -> tuple[str, Path, dict[str, Any], bool]:
    layout.montage_video.parent.mkdir(parents=True, exist_ok=True)
    layout.montage_json.parent.mkdir(parents=True, exist_ok=True)
    policy = output_policy([layout.montage_video, layout.montage_json], reuse=reuse, force=force, schema="montage")
    if policy == "reuse":
        return owner, layout.montage_json, read_validated_json(layout.montage_json, "montage"), True

    manifest = read_validated_json(layout.clips_manifest, "clips")
    ordered_clips, order_source = _clips_for_layout(layout, manifest, chronological=options.chronological)
    selected, selected_duration = select_clips_for_montage(ordered_clips, min_duration=options.min_duration, max_duration=options.max_duration, chronological=options.chronological)

    layout.create_dirs()
    for clip in selected:
        source = layout.root / clip["path"]
        if not source.exists():
            raise ArtifactError(f"clip file not found: {clip['path']}")

    temp_paths: list[Path] = []
    try:
        with tempfile.TemporaryDirectory(prefix="clipper-montage-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            concat_paths: list[Path] = []
            for index, clip in enumerate(selected, start=1):
                source = layout.root / clip["path"]
                selected_clip_duration = float(clip["selected_duration"])
                original_duration = float(clip["duration"])
                if selected_clip_duration < original_duration:
                    trimmed = temp_dir / f"clip-{index:04d}.mp4"
                    command = ffmpeg_trim_command(source=source, output=trimmed, duration=selected_clip_duration)
                    if progress:
                        progress.log("ffmpeg: " + " ".join(command))
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode != 0:
                        raise ArtifactError(f"ffmpeg montage trim failed for {clip['id']}: {result.stderr.strip() or result.stdout.strip()}")
                    temp_paths.append(trimmed)
                    concat_paths.append(trimmed)
                else:
                    concat_paths.append(source)

            filelist = temp_dir / "filelist.txt"
            filelist.write_text("".join(f"file '{_concat_escape(path.resolve())}'\n" for path in concat_paths), encoding="utf-8")
            command = ffmpeg_montage_command(filelist=filelist, output=layout.montage_video, width=options.width, height=options.height, silent=options.silent)
            if progress:
                progress.log("ffmpeg: " + " ".join(command))
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise ArtifactError(f"ffmpeg montage failed: {result.stderr.strip() or result.stdout.strip()}")

        montage: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "montage_path": layout.montage_video.relative_to(layout.root).as_posix(),
            "clips": [str(clip["path"]) for clip in selected],
            "duration": float(selected_duration),
            "width": int(options.width),
            "height": int(options.height),
            "silent": bool(options.silent),
            "order_source": order_source,
        }
        write_json(layout.montage_json, montage)
        return owner, layout.montage_json, montage, False
    except Exception:
        _cleanup([layout.montage_video, layout.montage_json, *temp_paths])
        raise


def montage_project(
    *,
    store: Path,
    project: str,
    options: MontageOptions | None = None,
    reuse: bool = False,
    force: bool = False,
    progress: CliProgress | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Assemble project clips.json into project montage.mp4 and montage.json."""

    options = options or MontageOptions()
    layout = ProjectArtifactLayout.for_project(store, project)
    return _montage_from_layout(layout=layout, owner=layout.project, options=options, reuse=reuse, force=force, progress=progress)


def montage_video(
    *,
    store: Path,
    video: str | None,
    options: MontageOptions | None = None,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    progress: CliProgress | None = None,
    project: str | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Assemble work/clips.json into output/montage.mp4 and output/montage.json."""

    options = options or MontageOptions()
    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name).for_project(project)
    layout.output_dir.mkdir(parents=True, exist_ok=True)
    return _montage_from_layout(layout=layout, owner=layout.video, options=options, reuse=reuse, force=force, progress=progress)
