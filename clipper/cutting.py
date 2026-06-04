"""Cut scored segments into individual media clips with FFmpeg."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .progress import CliProgress
from .schemas import SCHEMA_VERSION


@dataclass(frozen=True)
class CutOptions:
    min_score: float = 6.0
    silent: bool = False


def filter_segments_by_score(segments: Iterable[dict[str, Any]], *, min_score: float) -> list[dict[str, Any]]:
    """Return scored segments that meet the minimum score threshold."""

    return [dict(segment) for segment in segments if float(segment["score"]) >= min_score]


def merge_overlapping_segments(segments: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge overlapping scored segments, preserving max score and combined reasons."""

    ordered = sorted(segments, key=lambda segment: (float(segment["start"]), float(segment["end"])))
    merged: list[dict[str, Any]] = []
    for segment in ordered:
        current = {
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "score": float(segment["score"]),
            "reason": str(segment["reason"]).strip(),
        }
        if not merged or current["start"] >= float(merged[-1]["end"]):
            merged.append(current)
            continue
        previous = merged[-1]
        previous["start"] = min(float(previous["start"]), current["start"])
        previous["end"] = max(float(previous["end"]), current["end"])
        previous["score"] = max(float(previous["score"]), current["score"])
        reasons = [reason for reason in [str(previous.get("reason", "")).strip(), current["reason"]] if reason]
        combined: list[str] = []
        for reason in reasons:
            if reason not in combined:
                combined.append(reason)
        previous["reason"] = "; ".join(combined)
    return merged


def build_clip_entries(segments: Iterable[dict[str, Any]], layout: ArtifactLayout) -> list[dict[str, Any]]:
    """Build chronological clip manifest entries with stable sequential IDs."""

    clips: list[dict[str, Any]] = []
    for index, segment in enumerate(sorted(segments, key=lambda segment: float(segment["start"])), start=1):
        clip_id = f"clip-{index:04d}"
        clip_path = (layout.clips_dir / f"{clip_id}.mp4").relative_to(layout.root).as_posix()
        clips.append(
            {
                "id": clip_id,
                "path": clip_path,
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "duration": float(segment["end"]) - float(segment["start"]),
                "score": float(segment["score"]),
                "reason": str(segment["reason"]),
            }
        )
    return clips


def ffmpeg_cut_command(*, source: Path, output: Path, start: float, end: float, silent: bool) -> list[str]:
    """Build an accurate re-encoding FFmpeg cut command."""

    duration = end - start
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:g}",
        "-i",
        str(source),
        "-t",
        f"{duration:g}",
        "-map",
        "0:v:0",
    ]
    if silent:
        command.append("-an")
    else:
        command.extend(["-map", "0:a?"])
    command.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"])
    if not silent:
        command.extend(["-c:a", "aac"])
    command.extend(["-movflags", "+faststart", str(output)])
    return command


def _cleanup(paths: Iterable[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def cut_video(
    *,
    store: Path,
    video: str | None,
    options: CutOptions | None = None,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    progress: CliProgress | None = None,
    project: str | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Cut scored segments for a video workspace and write work/clips.json."""

    options = options or CutOptions()
    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name).for_project(project)

    if reuse:
        manifest = read_validated_json(layout.clips_manifest, "clips")
        missing = [clip["path"] for clip in manifest["clips"] if not (layout.root / clip["path"]).exists()]
        if missing:
            raise ArtifactError(f"--reuse requires existing clip files; missing: {', '.join(missing)}")
        return layout.video, layout.clips_manifest, manifest, True

    scores = read_validated_json(layout.scores, "scores")
    passing = filter_segments_by_score(scores["segments"], min_score=options.min_score)
    merged = merge_overlapping_segments(passing)
    if not merged:
        raise ArtifactError(f"no scored segments met --min-score {options.min_score:g}; no clips were created")

    layout.create_dirs()
    layout.clips_dir.mkdir(parents=True, exist_ok=True)
    clips = build_clip_entries(merged, layout)
    output_paths = [layout.root / clip["path"] for clip in clips]
    output_policy([layout.clips_manifest, *output_paths], reuse=False, force=force, schema="clips")

    created: list[Path] = []
    source = layout.root / scores["source_file"]
    if not source.exists():
        raise ArtifactError(f"source video not found: {scores['source_file']}")
    if progress:
        progress.log(f"cutting {len(clips)} clip(s) for video {layout.video}: min_score={options.min_score:g} silent={options.silent}")
    try:
        for clip in clips:
            output = layout.root / clip["path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            command = ffmpeg_cut_command(source=source, output=output, start=float(clip["start"]), end=float(clip["end"]), silent=options.silent)
            if progress:
                progress.log("ffmpeg: " + " ".join(command))
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise ArtifactError(f"ffmpeg cut failed for {clip['id']}: {result.stderr.strip() or result.stdout.strip()}")
            created.append(output)
    except Exception:
        _cleanup([*created, *output_paths, layout.clips_manifest])
        raise

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_file": scores["source_file"],
        "clips": clips,
        "min_score": float(options.min_score),
        "silent": bool(options.silent),
    }
    write_json(layout.clips_manifest, manifest)
    return layout.video, layout.clips_manifest, manifest, False
