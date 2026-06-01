"""Pipeline entry points for Clipper."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .artifacts import ArtifactError, ArtifactLayout, canonical_input_ref, default_video_name, is_remote, output_policy, read_validated_json, validate_video_name, write_json
from .config import ClipperConfig, load_config
from .cutting import CutOptions, cut_video
from .montage import MontageOptions, montage_video
from .progress import CliProgress
from .schemas import SCHEMA_VERSION
from .scoring import score_video
from .transcription import TranscriptionOptions, transcribe_video


def _video_relative(layout: ArtifactLayout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _prepare_source(*, input_ref: str, layout: ArtifactLayout, reuse: bool, force: bool, proxy: str | None) -> tuple[Path, dict[str, Any], bool]:
    """Create or reuse source/metadata for the pipeline."""

    # Reuse the start-command implementation without coupling the public API to
    # argparse. Import lazily to avoid a cli <-> pipeline import cycle.
    from .cli import _prepare_local_source, _prepare_remote_source, _start_metadata

    remote = is_remote(input_ref)
    canonical = canonical_input_ref(input_ref)
    if reuse:
        metadata = read_validated_json(layout.metadata, "metadata")
        if metadata.get("canonical_input_ref") != canonical:
            raise ArtifactError("--reuse target metadata does not match the requested input")
        source = layout.root / metadata["source_path"]
        if not source.exists():
            raise ArtifactError(f"--reuse requires existing source: {metadata['source_path']}")
        return source, metadata, True

    if layout.root.exists() and not force:
        raise ArtifactError(f"output already exists: {layout.root}")
    layout.create_dirs()
    if force:
        import shutil

        shutil.rmtree(layout.source_dir, ignore_errors=True)
        layout.source_dir.mkdir(parents=True, exist_ok=True)
        layout.metadata.unlink(missing_ok=True)
        layout.pipeline.unlink(missing_ok=True)

    if remote:
        source, duration, extras = _prepare_remote_source(input_ref, layout, proxy=proxy)
        input_type = "remote"
    else:
        source, duration, extras = _prepare_local_source(input_ref, layout)
        input_type = "local"
    metadata = _start_metadata(input_ref, input_type, canonical, _video_relative(layout, source), duration, extras)
    write_json(layout.metadata, metadata)
    return source, metadata, False


def _build_result(
    *,
    layout: ArtifactLayout,
    source: Path,
    metadata: dict[str, Any],
    transcript: dict[str, Any],
    scores: dict[str, Any],
    clips: dict[str, Any],
    montage: dict[str, Any],
    runtime_seconds: float,
    reused: dict[str, bool],
) -> dict[str, Any]:
    clip_entries = list(clips.get("clips", []))
    montage_duration = float(montage.get("duration") or 0.0)
    source_duration = float(metadata.get("duration") or transcript.get("duration") or 0.0)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_path": _video_relative(layout, source),
        "metadata_path": "work/metadata.json",
        "transcript_path": "work/transcript.json",
        "scores_path": "work/scores.json",
        "clips_path": "work/clips.json",
        "montage_path": str(montage["montage_path"]),
        "montage_json_path": "output/montage.json",
        "input_ref": metadata.get("input_ref"),
        "input_type": metadata.get("input_type"),
        "video": layout.video,
        "metadata": metadata,
        "transcript": transcript,
        "scores": scores,
        "clips": clip_entries,
        "montage": montage,
        "score_count": len(scores.get("segments", [])),
        "clip_count": len(clip_entries),
        "source_duration": source_duration,
        "transcript_duration": float(transcript.get("duration") or source_duration),
        "clips_duration": sum(float(clip.get("duration") or 0.0) for clip in clip_entries),
        "montage_duration": montage_duration,
        "runtime_seconds": float(runtime_seconds),
        "reused": reused,
    }


def run_pipeline(
    input_ref: str,
    directive: str = "Find expressive, visually interesting, or emotionally engaging moments.",
    min_score: float = 6,
    *,
    name: str | None = None,
    store: str | Path | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
    silent: bool = False,
    proxy: str | None = None,
    force: bool = False,
    reuse: bool = False,
    config: ClipperConfig | None = None,
    transcription_options: TranscriptionOptions | None = None,
    scoring_client: Any | None = None,
    json_output: bool = False,
    progress: CliProgress | None = None,
) -> dict[str, Any]:
    """Run start, transcribe, score, cut, montage and write work/pipeline.json.

    On success, returns the same structured result persisted to
    ``work/pipeline.json``. If no clips meet ``min_score``, the cut step raises
    ``ArtifactError`` before montage creation and this function does not write or
    update the pipeline result.
    """

    if reuse and force:
        raise ArtifactError("--reuse and --force are mutually exclusive")
    started = time.monotonic()
    app_config = config or load_config(store_override=Path(store) if store is not None else None)
    store_path = Path(store) if store is not None else app_config.store_path
    video = validate_video_name(name) if name else default_video_name(input_ref)
    layout = ArtifactLayout.for_video(store_path, video)

    if reuse and layout.pipeline.exists():
        return read_validated_json(layout.pipeline, "pipeline")
    output_policy([layout.pipeline], reuse=False, force=force, schema="pipeline")

    source, metadata, source_reused = _prepare_source(input_ref=input_ref, layout=layout, reuse=reuse, force=force, proxy=proxy)

    _, _, transcript, transcript_reused = transcribe_video(
        store=store_path,
        video=video,
        options=transcription_options or TranscriptionOptions(model=app_config.whisper_model, device=app_config.whisper_device, compute_type=app_config.whisper_compute_type),
        reuse=reuse,
        force=force,
        json_output=json_output,
        progress=progress,
    )
    _, _, scores, scores_reused = score_video(
        store=store_path,
        video=video,
        directive=directive,
        config=app_config,
        reuse=reuse,
        force=force,
        json_output=json_output,
        client=scoring_client,
        progress=progress,
        with_transcript=True,
    )
    _, _, clips, clips_reused = cut_video(
        store=store_path,
        video=video,
        options=CutOptions(min_score=min_score, silent=silent),
        reuse=reuse,
        force=force,
        json_output=json_output,
        progress=progress,
    )
    _, _, montage, montage_reused = montage_video(
        store=store_path,
        video=video,
        options=MontageOptions(min_duration=min_duration, max_duration=max_duration, width=app_config.default_width, height=app_config.default_height, silent=silent),
        reuse=reuse,
        force=force,
        json_output=json_output,
        progress=progress,
    )

    result = _build_result(
        layout=layout,
        source=source,
        metadata=metadata,
        transcript=transcript,
        scores=scores,
        clips=clips,
        montage=montage,
        runtime_seconds=time.monotonic() - started,
        reused={"source": source_reused, "transcript": transcript_reused, "scores": scores_reused, "clips": clips_reused, "montage": montage_reused},
    )
    write_json(layout.pipeline, result)
    return result
