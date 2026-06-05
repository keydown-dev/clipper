"""Command-line interface for Clipper."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from dotenv import load_dotenv

from .artifacts import ArtifactError, ArtifactLayout, ProjectArtifactLayout, SourceArtifactLayout, canonical_input_ref, default_video_name, is_remote, list_videos, read_json, read_validated_json, validate_video_name, write_json
from .config import load_config
from .cutting import CutOptions, cut_project, cut_video
from .montage import MontageOptions, montage_project, montage_video
from .order import move_clip_order, read_clip_order, swap_clip_order, total_duration, write_clip_order
from .progress import CliProgress
from .scoring import score_project, score_video
from .shots import ShotOptions, shots_video
from .transcription import TranscriptionOptions, transcribe_video
from .visual import visual_video

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_CANCELLED = 130

PLACEHOLDER_COMMANDS = (
    "start",
    "list",
    "score",
    "cut",
    "montage",
)


@dataclass(frozen=True)
class CommandConfig:
    """Shared per-command configuration parsed from common CLI options."""

    store: Path
    json_output: bool
    verbose: int


@dataclass(frozen=True)
class DoctorCheck:
    """Single doctor check result."""

    name: str
    status: str
    message: str


def build_common_parent() -> argparse.ArgumentParser:
    """Build the shared argparse parent used by every subcommand."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--store",
        default=None,
        help="Artifact store path (default: .clipper or CLIPPER_STORE_PATH).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON output.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase diagnostic verbosity; may be passed more than once.",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> CommandConfig:
    """Create shared command config from parsed arguments."""

    return CommandConfig(
        store=Path(args.store or os.environ.get("CLIPPER_STORE_PATH", ".clipper")),
        json_output=bool(args.json_output),
        verbose=int(args.verbose or 0),
    )


def success_envelope(*, video: str | None = None, artifact_path: str | None = None, result: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    """Build a successful CLI JSON envelope."""

    envelope: dict[str, Any] = {"ok": True, "result": {} if result is None else result}
    if video is not None:
        envelope["video"] = video
    if artifact_path is not None:
        envelope["artifact_path"] = artifact_path
    return envelope


def error_envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    """Build a failed CLI JSON envelope."""

    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"ok": False, "error": error}


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, separators=(",", ":")))


def emit_result(config: CommandConfig, command: str, message: str) -> None:
    """Emit a placeholder success result for a command."""

    if config.json_output:
        print_json(success_envelope(result={"command": command, "message": message}))
    else:
        print(message)


def _check_python_version() -> DoctorCheck:
    minimum = (3, 11)
    current = sys.version_info[:3]
    version = platform.python_version()
    if current >= minimum:
        return DoctorCheck("python", "pass", f"Python {version} meets >= 3.11.")
    return DoctorCheck("python", "fail", f"Python {version} is too old; install Python 3.11 or newer.")


def _check_executable(name: str) -> DoctorCheck:
    path = shutil.which(name)
    if path:
        return DoctorCheck(name, "pass", f"Found {name} at {path}.")
    return DoctorCheck(name, "fail", f"{name} was not found on PATH; install FFmpeg and ensure {name} is available.")


def _check_python_dependency(module_name: str, package_name: str | None = None) -> DoctorCheck:
    package = package_name or module_name
    if importlib.util.find_spec(module_name) is not None:
        return DoctorCheck(f"python dependency: {package}", "pass", f"Import target {module_name} is available.")
    return DoctorCheck(f"python dependency: {package}", "fail", f"Cannot import {module_name}; install project dependencies with `uv sync`.")


def _check_artifact_store_writable(store: Path) -> DoctorCheck:
    try:
        store.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".doctor-", dir=store, delete=True):
            pass
    except OSError as exc:
        return DoctorCheck("artifact store writable", "fail", f"Cannot write to {store}: {exc}")
    return DoctorCheck("artifact store writable", "pass", f"Artifact store {store} is writable.")


def _check_llm_config(*, check_connectivity: bool) -> DoctorCheck:
    try:
        cfg = load_config(env_file=None)
    except (OSError, ValueError) as exc:
        return DoctorCheck("llm configuration", "fail", f"Invalid LLM configuration: {exc}")
    if not cfg.llm_base_url or not cfg.llm_model:
        return DoctorCheck("llm configuration", "fail", "Set LLM_BASE_URL and LLM_MODEL before scoring clips.")
    if not check_connectivity:
        key_note = "LLM_API_KEY is set" if cfg.llm_api_key else "LLM_API_KEY is not set; this is OK only for local endpoints that do not require auth"
        return DoctorCheck("llm configuration", "pass", f"Configured {cfg.llm_model} at {cfg.llm_base_url}. {key_note}. Use --check-llm to test connectivity.")
    try:
        from openai import OpenAI

        client = OpenAI(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key or "not-needed", timeout=cfg.llm_timeout_seconds)
        client.models.list()
    except Exception as exc:  # pragma: no cover - depends on user's network/service
        return DoctorCheck("llm connectivity", "fail", f"Could not reach LLM endpoint {cfg.llm_base_url}: {exc}")
    return DoctorCheck("llm connectivity", "pass", f"Connected to LLM endpoint {cfg.llm_base_url}.")


def _check_whisper(*, load_model: bool) -> DoctorCheck:
    try:
        cfg = load_config(env_file=None)
    except (OSError, ValueError) as exc:
        return DoctorCheck("whisper configuration", "fail", f"Invalid Whisper configuration: {exc}")
    if importlib.util.find_spec("faster_whisper") is None:
        return DoctorCheck("whisper readiness", "fail", "faster-whisper is not importable; install project dependencies with `uv sync`.")
    if not load_model:
        return DoctorCheck("whisper readiness", "pass", f"faster-whisper is importable; configured model={cfg.whisper_model}, device={cfg.whisper_device}, compute_type={cfg.whisper_compute_type}. Use --check-whisper to load the model.")
    try:
        from faster_whisper import WhisperModel

        WhisperModel(cfg.whisper_model, device=cfg.whisper_device, compute_type=cfg.whisper_compute_type)
    except Exception as exc:  # pragma: no cover - may download/use local hardware
        return DoctorCheck("whisper model", "fail", f"Could not load Whisper model {cfg.whisper_model}: {exc}")
    return DoctorCheck("whisper model", "pass", f"Loaded Whisper model {cfg.whisper_model}.")


def build_doctor_checks(config: CommandConfig, *, check_llm: bool = False, check_whisper: bool = False) -> list[DoctorCheck]:
    """Build doctor results without requiring external connectivity by default."""

    checks = [
        _check_python_version(),
        _check_executable("ffmpeg"),
        _check_executable("ffprobe"),
        _check_python_dependency("yt_dlp", "yt-dlp"),
        _check_python_dependency("openai"),
        _check_python_dependency("dotenv", "python-dotenv"),
        _check_python_dependency("questionary"),
        _check_python_dependency("scenedetect", "PySceneDetect"),
        _check_artifact_store_writable(config.store),
        _check_llm_config(check_connectivity=check_llm),
        _check_whisper(load_model=check_whisper),
    ]
    return checks


def doctor_result(checks: list[DoctorCheck]) -> dict[str, Any]:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    serialized = []
    for check in checks:
        counts[check.status] += 1
        serialized.append({"name": check.name, "status": check.status, "message": check.message})
    return {"checks": serialized, "summary": counts}


def run_doctor(args: argparse.Namespace) -> int:
    """Validate local Clipper environment."""

    config = config_from_args(args)
    result = doctor_result(build_doctor_checks(config, check_llm=args.check_llm, check_whisper=args.check_whisper))
    if config.json_output:
        print_json(success_envelope(result=result))
    else:
        for check in result["checks"]:
            print(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
        summary = result["summary"]
        print(f"Summary: pass={summary['pass']} warn={summary['warn']} fail={summary['fail']}")
    return EXIT_SUCCESS


def run_placeholder(args: argparse.Namespace) -> int:
    """Run a placeholder command until implementation-specific issues fill it in."""

    config = config_from_args(args)
    message = f"clipper {args.command}: placeholder command; implementation pending."
    emit_result(config, args.command, message)
    return EXIT_SUCCESS


def run_transcribe(args: argparse.Namespace) -> int:
    """Transcribe a video workspace with faster-whisper."""

    command_config = config_from_args(args)
    app_config = load_config(store_override=command_config.store)
    options = TranscriptionOptions(
        model=args.model or app_config.whisper_model,
        device=args.device or app_config.whisper_device,
        compute_type=args.compute_type or app_config.whisper_compute_type,
        language=args.language,
    )
    video, transcript_path, transcript, reused = transcribe_video(
        store=command_config.store,
        video=args.video,
        options=options,
        reuse=args.reuse,
        force=args.force,
        json_output=command_config.json_output,
        progress=CliProgress(enabled=command_config.verbose > 0),
    )
    sentence_transcript_path = transcript_path.parent / "sentences.json"
    sentence_transcript = read_validated_json(sentence_transcript_path, "sentence_transcript")
    result = {
        "transcript_path": str(transcript_path),
        "sentence_transcript_path": str(sentence_transcript_path),
        "source_file": transcript["source_file"],
        "language": transcript["language"],
        "duration": transcript["duration"],
        "segments": len(transcript["segments"]),
        "sentences": len(sentence_transcript["sentences"]),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(transcript_path), result=result))
    else:
        action = "Reused" if reused else "Transcribed"
        print(f"{action} video {video}")
        print(f"Transcript: {transcript_path}")
        print(f"Sentence transcript: {sentence_transcript_path}")
        print(f"Segments: {result['segments']}")
        print(f"Sentences: {result['sentences']}")
    return EXIT_SUCCESS


def parse_time(value: str | None) -> float | None:
    """Parse seconds, MM:SS, or HH:MM:SS into seconds."""

    if value is None:
        return None
    parts = value.split(":")
    try:
        if len(parts) == 1:
            seconds = float(parts[0])
        elif len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            raise ValueError
    except ValueError as exc:
        raise ArtifactError(f"invalid time value {value!r}; use seconds, MM:SS, or HH:MM:SS") from exc
    if seconds < 0:
        raise ArtifactError(f"invalid time value {value!r}; time must be non-negative")
    return seconds


def run_score(args: argparse.Namespace) -> int:
    """Score transcript segments with an OpenAI-compatible LLM."""

    command_config = config_from_args(args)
    app_config = load_config(store_override=command_config.store)
    project_arg = args.video if args.video and args.project is None and (command_config.store / "projects" / args.video / "project.json").exists() else None
    if project_arg is not None:
        if args.start or args.end:
            raise ArtifactError("project scoring ranges are configured per source with `clipper include`; --start/--end are for single-source scoring")
        video, scores_path, scores, reused = score_project(
            store=command_config.store,
            project=project_arg,
            directive=args.directive,
            config=app_config,
            reuse=args.reuse,
            force=args.force,
            progress=CliProgress(enabled=command_config.verbose > 0),
            with_transcript=args.with_transcript,
            with_visuals=args.with_visuals,
        )
        result_project = project_arg
        result_start = None
        result_end = None
    else:
        video, scores_path, scores, reused = score_video(
            store=command_config.store,
            video=args.video,
            directive=args.directive,
            config=app_config,
            reuse=args.reuse,
            force=args.force,
            json_output=command_config.json_output,
            progress=CliProgress(enabled=command_config.verbose > 0),
            with_transcript=args.with_transcript,
            with_visuals=args.with_visuals,
            project=args.project,
            start=parse_time(args.start),
            end=parse_time(args.end),
        )
        result_project = args.project
        result_start = parse_time(args.start)
        result_end = parse_time(args.end)
    result = {
        "scores_path": str(scores_path),
        "project": result_project,
        "start": result_start,
        "end": result_end,
        "source_file": scores["source_file"],
        "directive": scores["directive"],
        "segments": len(scores["segments"]),
        "warnings": scores.get("warnings", []),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(scores_path), result=result))
    else:
        action = "Reused" if reused else "Scored"
        print(f"{action} video {video}")
        print(f"Scores: {scores_path}")
        print(f"Segments: {result['segments']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return EXIT_SUCCESS


def run_shots(args: argparse.Namespace) -> int:
    """Detect visual shots and extract representative frames."""

    command_config = config_from_args(args)
    video, shots_path, manifest, reused = shots_video(
        store=command_config.store,
        video=args.video,
        options=ShotOptions(
            threshold=args.threshold,
            min_duration=args.min_duration,
            samples_per_shot=args.samples_per_shot,
            contact_sheet=args.contact_sheet,
        ),
        reuse=args.reuse,
        force=args.force,
        json_output=command_config.json_output,
        progress=CliProgress(enabled=command_config.verbose > 0),
    )
    result = {
        "shots_path": str(shots_path),
        "source_file": manifest["source_file"],
        "shot_count": len(manifest["shots"]),
        "shots": manifest["shots"],
        "contact_sheet_path": manifest.get("contact_sheet_path"),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(shots_path), result=result))
    else:
        action = "Reused" if reused else "Detected"
        print(f"{action} shots for video {video}")
        print(f"Shots: {shots_path}")
        print(f"Shot count: {result['shot_count']}")
        if result["contact_sheet_path"]:
            print(f"Contact sheet: {result['contact_sheet_path']}")
    return EXIT_SUCCESS


def run_visual(args: argparse.Namespace) -> int:
    """Analyze representative shot frames with a multimodal model."""

    command_config = config_from_args(args)
    app_config = load_config(store_override=command_config.store)
    video, visual_path, visual_index, reused = visual_video(
        store=command_config.store,
        video=args.video,
        config=app_config,
        reuse=args.reuse,
        force=args.force,
        json_output=command_config.json_output,
        progress=CliProgress(enabled=command_config.verbose > 0),
    )
    result = {
        "visual_index_path": str(visual_path),
        "source_file": visual_index["source_file"],
        "shots_path": visual_index["shots_path"],
        "observations": len(visual_index["observations"]),
        "provider": visual_index["provider"],
        "warnings": visual_index.get("warnings", []),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(visual_path), result=result))
    else:
        action = "Reused" if reused else "Analyzed"
        print(f"{action} visual frames for video {video}")
        print(f"Visual index: {visual_path}")
        print(f"Observations: {result['observations']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return EXIT_SUCCESS


def run_cut(args: argparse.Namespace) -> int:
    """Cut scored segments into individual clip files."""

    command_config = config_from_args(args)
    project_arg = args.video if args.video and args.project is None and (command_config.store / "projects" / args.video / "project.json").exists() else None
    if project_arg is not None:
        video, clips_path, manifest, reused = cut_project(
            store=command_config.store,
            project=project_arg,
            options=CutOptions(min_score=args.min_score, silent=args.silent),
            reuse=args.reuse,
            force=args.force,
            progress=CliProgress(enabled=command_config.verbose > 0),
        )
        result_project = project_arg
    else:
        video, clips_path, manifest, reused = cut_video(
            store=command_config.store,
            video=args.video,
            options=CutOptions(min_score=args.min_score, silent=args.silent),
            reuse=args.reuse,
            force=args.force,
            json_output=command_config.json_output,
            progress=CliProgress(enabled=command_config.verbose > 0),
            project=args.project,
        )
        result_project = args.project
    result = {
        "clips_path": str(clips_path),
        "project": result_project,
        "source_file": manifest["source_file"],
        "clip_count": len(manifest["clips"]),
        "clips": manifest["clips"],
        "min_score": manifest.get("min_score", args.min_score),
        "silent": manifest.get("silent", args.silent),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(clips_path), result=result))
    else:
        action = "Reused" if reused else "Cut"
        print(f"{action} video {video}")
        print(f"Clips: {clips_path}")
        print(f"Clip count: {result['clip_count']}")
    return EXIT_SUCCESS


def run_order(args: argparse.Namespace) -> int:
    """Create, replace, and show project editorial clip order."""

    command_config = config_from_args(args)
    project = validate_video_name(args.project)
    requested_actions = sum(bool(action) for action in (args.reset, args.show, args.clip_ids, args.move, args.swap))
    if requested_actions > 1:
        raise ArtifactError("--reset, --show, explicit clip IDs, --move, and --swap are mutually exclusive")
    if (args.move is None) != (args.to is None):
        raise ArtifactError("--move requires --to, and --to requires --move")
    if args.reset:
        order_path, order = write_clip_order(command_config.store, project)
        wrote = True
    elif args.move:
        order_path, order = move_clip_order(command_config.store, project, args.move, args.to)
        wrote = True
    elif args.swap:
        order_path, order = swap_clip_order(command_config.store, project, args.swap[0], args.swap[1])
        wrote = True
    elif args.clip_ids:
        order_path, order = write_clip_order(command_config.store, project, list(args.clip_ids))
        wrote = True
    else:
        order_path, order = read_clip_order(command_config.store, project)
        wrote = False
    total = total_duration(order)
    result = {"project": project, "order_path": str(order_path), "order": order["order"], "total_duration": total}
    if command_config.json_output:
        print_json(success_envelope(artifact_path=str(order_path), result=result))
    elif args.show or not wrote or args.move or args.swap:
        print(f"Clip order: {order_path}")
        for index, entry in enumerate(order["order"], start=1):
            print(f"{index}. {entry['id']} {entry['duration']:.3f}s")
        print(f"Total duration: {total:.3f}s")
    else:
        print(f"Wrote clip order: {order_path}")
        print(f"Clips: {len(order['order'])}")
        print(f"Total duration: {total:.3f}s")
    return EXIT_SUCCESS


def run_montage(args: argparse.Namespace) -> int:
    """Assemble clip files into a normalized montage."""

    command_config = config_from_args(args)
    app_config = load_config(store_override=command_config.store)
    options = MontageOptions(
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        width=app_config.default_width,
        height=app_config.default_height,
        silent=args.silent,
        chronological=args.chronological,
    )
    project_arg = args.video if args.video and args.project is None and (command_config.store / "projects" / args.video / "project.json").exists() else None
    if project_arg is not None:
        video, montage_path, montage, reused = montage_project(
            store=command_config.store,
            project=project_arg,
            options=options,
            reuse=args.reuse,
            force=args.force,
            progress=CliProgress(enabled=command_config.verbose > 0),
        )
        result_project = project_arg
    else:
        video, montage_path, montage, reused = montage_video(
            store=command_config.store,
            video=args.video,
            options=options,
            reuse=args.reuse,
            force=args.force,
            json_output=command_config.json_output,
            progress=CliProgress(enabled=command_config.verbose > 0),
            project=args.project,
        )
        result_project = args.project
    result = {
        "montage_json": str(montage_path),
        "project": result_project,
        "montage_path": montage["montage_path"],
        "clip_count": len(montage["clips"]),
        "duration": montage["duration"],
        "width": montage["width"],
        "height": montage["height"],
        "silent": montage["silent"],
        "order_source": montage.get("order_source", "clips.json"),
        "reused": reused,
    }
    if command_config.json_output:
        print_json(success_envelope(video=video, artifact_path=str(montage_path), result=result))
    else:
        action = "Reused" if reused else "Assembled"
        owner_label = "project" if result_project is not None else "video"
        print(f"{action} montage for {owner_label} {video}")
        print(f"Montage: {montage_path}")
        print(f"Clip count: {result['clip_count']}")
    return EXIT_SUCCESS


def run_pipeline_cli(args: argparse.Namespace) -> int:
    """Run the full pipeline for a URL or local source."""

    if not args.input:
        raise ArtifactError("clipper pipeline requires INPUT")
    command_config = config_from_args(args)
    from .pipeline import run_pipeline

    result = run_pipeline(
        input_ref=args.input,
        name=args.name,
        store=command_config.store,
        directive=args.directive,
        min_score=args.min_score,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        silent=args.silent,
        proxy=args.proxy,
        project=args.project,
        reuse=args.reuse,
        force=args.force,
        json_output=command_config.json_output,
        progress=CliProgress(enabled=command_config.verbose > 0),
    )
    layout = ArtifactLayout.for_video(command_config.store, result["video"]).for_project(args.project)
    if command_config.json_output:
        print_json(success_envelope(video=result["video"], artifact_path=str(layout.pipeline), result=result))
    else:
        action = "Reused" if all(result.get("reused", {}).values()) else "Ran"
        print(f"{action} pipeline for video {result['video']}")
        print(f"Pipeline: {layout.pipeline}")
        print(f"Clips: {result['clip_count']}")
        print(f"Montage: {result['montage_path']}")
    return EXIT_SUCCESS


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _video_relative(layout: ArtifactLayout | SourceArtifactLayout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _probe_duration(path: Path) -> float:
    try:
        output = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            text=True,
            stderr=subprocess.STDOUT,
        )
        duration = float(json.loads(output)["format"]["duration"])
    except (OSError, subprocess.CalledProcessError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"could not determine video duration with ffprobe for {path}: {exc}") from exc
    if duration <= 0:
        raise ArtifactError(f"could not determine positive video duration with ffprobe for {path}")
    return duration


def _source_media_dir(layout: ArtifactLayout | SourceArtifactLayout) -> Path:
    return layout.source_dir if isinstance(layout, ArtifactLayout) else layout.root


def _prepare_local_source(input_ref: str, layout: ArtifactLayout | SourceArtifactLayout) -> tuple[Path, float, dict[str, Any]]:
    src = Path(input_ref).expanduser()
    if not src.exists() or not src.is_file():
        raise ArtifactError(f"local input file not found: {input_ref}")
    duration = _probe_duration(src)
    ext = src.suffix or ".mp4"
    dest = _source_media_dir(layout) / f"source{ext}"
    shutil.copy2(src, dest)
    return dest, duration, {"title": src.stem}


def _prepare_remote_source(input_ref: str, layout: ArtifactLayout | SourceArtifactLayout, *, proxy: str | None = None) -> tuple[Path, float, dict[str, Any]]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:  # pragma: no cover - doctor catches this in normal installs
        raise ArtifactError("yt-dlp is not installed; install project dependencies with `uv sync`") from exc

    source_dir = _source_media_dir(layout)
    options: dict[str, Any] = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "outtmpl": str(source_dir / "source.%(ext)s"),
        "noplaylist": True,
    }
    if proxy:
        options["proxy"] = proxy
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(input_ref, download=True)
    except Exception as exc:
        raise ArtifactError(f"download failed for {input_ref}; check the URL, network, proxy, and yt-dlp support: {exc}") from exc

    candidates = sorted(
        path
        for path in source_dir.glob("source.*")
        if path.is_file() and path.suffix not in {".part", ".ytdl", ".json"}
    )
    if not candidates:
        raise ArtifactError("download completed but no source/source.{ext} file was produced")
    source = candidates[0]
    duration = info.get("duration") if isinstance(info, dict) else None
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        duration = _probe_duration(source)
    extras = info if isinstance(info, dict) else {}
    return source, float(duration), extras


def _start_metadata(input_ref: str, input_type: str, canonical: str, source_path: str, duration: float, extras: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "input_ref": input_ref,
        "input_type": input_type,
        "canonical_input_ref": canonical,
        "source_path": source_path,
        "title": str(extras.get("title") or Path(input_ref).stem or input_ref),
        "duration": float(duration),
        "created_at": _utc_now(),
    }
    for src_key, dst_key in [("thumbnail", "thumbnail_url"), ("id", "video_id"), ("webpage_url", "source_url"), ("extractor", "extractor")]:
        if extras.get(src_key) is not None:
            metadata[dst_key] = extras[src_key]
    if extras:
        metadata["provider_metadata"] = _json_safe(extras)
    return metadata


def _source_ingestion_result(args: argparse.Namespace, *, command_name: str) -> tuple[CommandConfig, str, SourceArtifactLayout, dict[str, Any]]:
    if not args.input:
        raise ArtifactError(f"clipper {command_name} requires INPUT")
    config = config_from_args(args)
    input_ref = args.input
    remote = is_remote(input_ref)
    canonical = canonical_input_ref(input_ref)
    name = validate_video_name(args.name) if args.name else default_video_name(input_ref)
    layout = SourceArtifactLayout.for_source(config.store, name)

    if args.reuse:
        if not layout.metadata.exists():
            raise ArtifactError(f"--reuse requires existing metadata: {layout.metadata}")
        metadata = read_validated_json(layout.metadata, "metadata")
        if metadata.get("canonical_input_ref") != canonical:
            raise ArtifactError("--reuse target metadata does not match the requested input")
        if not (layout.root / metadata["source_path"]).exists():
            raise ArtifactError(f"--reuse requires existing source: {metadata['source_path']}")
        result = {"source": name, "path": str(layout.root), "metadata_path": str(layout.metadata), "source_path": metadata["source_path"], "reused": True}
    else:
        if layout.root.exists() and not args.force:
            raise ArtifactError(f"output already exists: {layout.root}")
        if args.force:
            shutil.rmtree(layout.root, ignore_errors=True)
        layout.create_dirs()
        if remote:
            source, duration, extras = _prepare_remote_source(input_ref, layout, proxy=args.proxy)
            input_type = "remote"
        else:
            source, duration, extras = _prepare_local_source(input_ref, layout)
            input_type = "local"
        source_path = _video_relative(layout, source)
        metadata = _start_metadata(input_ref, input_type, canonical, source_path, duration, extras)
        write_json(layout.metadata, metadata)
        result = {"source": name, "path": str(layout.root), "metadata_path": str(layout.metadata), "source_path": source_path, "reused": False}
    return config, name, layout, result


def run_source(args: argparse.Namespace) -> int:
    """Ingest exactly one remote or local media source into the source namespace."""

    config, name, layout, result = _source_ingestion_result(args, command_name="source")
    if config.json_output:
        print_json(success_envelope(result={"source": name, **result}, artifact_path=str(layout.metadata)))
    else:
        action = "Reused" if result["reused"] else "Ingested"
        print(f"{action} source {name} at {layout.root}")
        print(f"Metadata: {layout.metadata}")
        print(f"Source: {result['source_path']}")
    return EXIT_SUCCESS


def run_create(args: argparse.Namespace) -> int:
    """Create an empty editorial project config."""

    config = config_from_args(args)
    name = validate_video_name(args.project)
    layout = ProjectArtifactLayout.for_project(config.store, name)
    if layout.root.exists() and not args.force:
        raise ArtifactError(f"project already exists: {layout.root}")
    if args.force:
        shutil.rmtree(layout.root, ignore_errors=True)
    layout.root.mkdir(parents=True, exist_ok=True)
    project = {"schema_version": 1, "name": name, "sources": [], "created_at": _utc_now()}
    write_json(layout.project_json, project)
    result = {"project": name, "path": str(layout.root), "config_path": str(layout.project_json)}
    if config.json_output:
        print_json(success_envelope(result=result, artifact_path=str(layout.project_json)))
    else:
        print(f"Created project {name} at {layout.root}")
        print(f"Config: {layout.project_json}")
    return EXIT_SUCCESS


def _read_project_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ArtifactError(f"project not found: {path}")
    project = read_json(path)
    if not isinstance(project, dict):
        raise ArtifactError(f"project config must be a JSON object: {path}")
    if not isinstance(project.get("sources"), list):
        raise ArtifactError(f"project config sources must be a list: {path}")
    return project


def run_include(args: argparse.Namespace) -> int:
    """Include a source, optionally ranged, in an editorial project."""

    config = config_from_args(args)
    project_name = validate_video_name(args.project)
    source_name = validate_video_name(args.source)
    project_layout = ProjectArtifactLayout.for_project(config.store, project_name)
    source_layout = SourceArtifactLayout.for_source(config.store, source_name)
    project = _read_project_config(project_layout.project_json)
    if not source_layout.metadata.exists():
        raise ArtifactError(f"source not found: {source_layout.root}")

    start = parse_time(args.start)
    end = parse_time(args.end)
    if start is not None and end is not None and end <= start:
        raise ArtifactError("range end must be greater than start")

    entry: dict[str, Any] = {"name": source_name}
    if start is not None:
        entry["start"] = start
    if end is not None:
        entry["end"] = end

    sources = project["sources"]
    updated = False
    for index, existing in enumerate(sources):
        if isinstance(existing, dict) and existing.get("name") == source_name:
            sources[index] = entry
            updated = True
            break
    if not updated:
        sources.append(entry)
    write_json(project_layout.project_json, project)

    result = {"project": project_name, "source": source_name, "sources": sources, "config_path": str(project_layout.project_json)}
    if config.json_output:
        print_json(success_envelope(result=result, artifact_path=str(project_layout.project_json)))
    else:
        action = "Updated" if updated else "Included"
        print(f"{action} source {source_name} in project {project_name}")
        print(f"Config: {project_layout.project_json}")
        for source in sources:
            if not isinstance(source, dict):
                continue
            range_text = ""
            if "start" in source or "end" in source:
                range_text = f" start={source.get('start', '-')} end={source.get('end', '-')}"
            print(f"- {source.get('name')}{range_text}")
    return EXIT_SUCCESS


def _mirror_source_to_legacy_start(args: argparse.Namespace, name: str, source_layout: SourceArtifactLayout, result: dict[str, Any]) -> None:
    """Keep deprecated start's legacy video workspace available while ingesting a source."""

    legacy = ArtifactLayout.for_video(config_from_args(args).store, name)
    if args.force:
        shutil.rmtree(legacy.root, ignore_errors=True)
    legacy.create_dirs()
    source_rel = str(result["source_path"])
    source_path = source_layout.root / source_rel
    legacy_source_rel = f"source/{source_path.name}"
    shutil.copy2(source_path, legacy.source_dir / source_path.name)
    metadata = read_validated_json(source_layout.metadata, "metadata")
    metadata["source_path"] = legacy_source_rel
    write_json(legacy.metadata, metadata)


def run_start(args: argparse.Namespace) -> int:
    """Deprecated compatibility alias for source ingestion."""

    config, name, layout, result = _source_ingestion_result(args, command_name="start")
    _mirror_source_to_legacy_start(args, name, layout, result)
    legacy = ArtifactLayout.for_video(config.store, name)
    legacy_source_path = f"source/{Path(str(result['source_path'])).name}"
    alias_result = {"source": name, "deprecated_alias": "start", **result, "path": str(legacy.root), "metadata_path": str(legacy.metadata), "source_path": legacy_source_path}
    if config.json_output:
        print_json(success_envelope(video=name, result=alias_result, artifact_path=str(legacy.metadata)))
    else:
        action = "Reused" if result["reused"] else "Ingested"
        print("warning: clipper start is deprecated; use clipper source", file=sys.stderr)
        print(f"{action} source {name} at {layout.root}")
        print(f"Metadata: {layout.metadata}")
        print(f"Source: {result['source_path']}")
    return EXIT_SUCCESS


def run_list(args: argparse.Namespace) -> int:
    """List existing video workspaces in the artifact store."""

    config = config_from_args(args)
    videos = list_videos(config.store)
    if config.json_output:
        print_json(success_envelope(result={"videos": videos}))
    else:
        if not videos:
            print(f"No videos found in {config.store}")
        else:
            for video in videos:
                flags = video["artifacts"]
                flag_text = " ".join(f"{name}={'yes' if present else 'no'}" for name, present in flags.items())
                print(f"{video['name']}\t{video['path']}\t{video.get('title') or '-'}\t{video.get('duration') or '-'}\t{flag_text}")
    return EXIT_SUCCESS


def add_reuse_force(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reuse", action="store_true", help="Reuse existing artifacts when valid.")
    group.add_argument("--force", action="store_true", help="Overwrite target artifacts.")


def add_project(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Optional project slug for scoped score/cut/montage outputs.")


def add_placeholder_subcommands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], common: argparse.ArgumentParser) -> None:
    """Register all first-version placeholder subcommands."""

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {name: run_placeholder for name in PLACEHOLDER_COMMANDS}
    handlers["source"] = run_source
    handlers["create"] = run_create
    handlers["include"] = run_include
    handlers["start"] = run_start
    handlers["list"] = run_list
    handlers["transcribe"] = run_transcribe
    handlers["score"] = run_score
    handlers["shots"] = run_shots
    handlers["visual"] = run_visual
    handlers["cut"] = run_cut
    handlers["montage"] = run_montage
    handlers["order"] = run_order
    handlers["pipeline"] = run_pipeline_cli

    doctor = subparsers.add_parser("doctor", parents=[common], help="Validate local Clipper environment.")
    doctor.add_argument("--check-llm", action="store_true", help="Also check LLM connectivity.")
    doctor.add_argument("--check-whisper", action="store_true", help="Also load/check Whisper model.")
    doctor.set_defaults(handler=run_doctor)

    source = subparsers.add_parser("source", parents=[common], help="Ingest a remote URL or local media file into the source store.")
    source.add_argument("input", nargs="?", metavar="URL_OR_PATH", help="Remote URL or local media file path.")
    source.add_argument("--name", required=True, help="Slug-safe source name.")
    source.add_argument("--proxy", help="Proxy URL for remote downloads.")
    add_reuse_force(source)
    source.set_defaults(handler=handlers["source"])

    create = subparsers.add_parser("create", parents=[common], help="Create an empty editorial project.")
    create.add_argument("project", metavar="PROJECT", help="Slug-safe project name.")
    create.add_argument("--force", action="store_true", help="Overwrite an existing project.")
    create.set_defaults(handler=handlers["create"])

    include = subparsers.add_parser("include", parents=[common], help="Include a source in an editorial project.")
    include.add_argument("project", metavar="PROJECT", help="Slug-safe project name.")
    include.add_argument("source", metavar="SOURCE", help="Slug-safe source name.")
    include.add_argument("--start", help="Include source evidence at or after this time (seconds, MM:SS, or HH:MM:SS).")
    include.add_argument("--end", help="Include source evidence at or before this time (seconds, MM:SS, or HH:MM:SS).")
    include.set_defaults(handler=handlers["include"])

    start = subparsers.add_parser("start", parents=[common], help="Deprecated alias for source ingestion.")
    start.add_argument("input", nargs="?", metavar="URL_OR_PATH", help="Remote URL or local media file path.")
    start.add_argument("--name", help="Optional slug-safe source name.")
    start.add_argument("--proxy", help="Proxy URL for remote downloads.")
    add_reuse_force(start)
    start.set_defaults(handler=handlers["start"])

    list_cmd = subparsers.add_parser("list", parents=[common], help="List existing videos in the artifact store.")
    list_cmd.set_defaults(handler=handlers["list"])

    transcribe = subparsers.add_parser("transcribe", parents=[common], help="Transcribe a video workspace.")
    transcribe.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    transcribe.add_argument("--model", help="Whisper model name (default: WHISPER_MODEL or small).")
    transcribe.add_argument("--device", help="Whisper device (default: WHISPER_DEVICE or cpu).")
    transcribe.add_argument("--compute-type", help="Whisper compute type (default: WHISPER_COMPUTE_TYPE or int8).")
    transcribe.add_argument("--language", help="Force transcription language; omit to auto-detect.")
    add_reuse_force(transcribe)
    transcribe.set_defaults(handler=handlers["transcribe"])

    score = subparsers.add_parser("score", parents=[common], help="Score transcript segments with an LLM.")
    score.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    score.add_argument("--directive", default="Find expressive, visually interesting, or emotionally engaging moments.", help="Scoring directive.")
    score.add_argument("--with-transcript", action="store_true", help="Use work/sentences.json as scoring evidence.")
    score.add_argument("--with-visuals", action="store_true", help="Use cached work/shots.json and work/visual-index.json as scoring evidence.")
    score.add_argument("--start", help="Limit scoring to evidence at or after this time (seconds, MM:SS, or HH:MM:SS).")
    score.add_argument("--end", help="Limit scoring to evidence at or before this time (seconds, MM:SS, or HH:MM:SS).")
    add_project(score)
    add_reuse_force(score)
    score.set_defaults(handler=handlers["score"])

    shots = subparsers.add_parser("shots", parents=[common], help="Detect shots and extract representative frames.")
    shots.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    shots.add_argument("--threshold", type=float, default=27.0, help="PySceneDetect content threshold (default: 27).")
    shots.add_argument("--min-duration", type=float, default=0.5, help="Minimum shot duration in seconds (default: 0.5).")
    shots.add_argument("--samples-per-shot", type=int, default=5, help="Candidate frames sampled per shot (default: 5).")
    shots.add_argument("--contact-sheet", action="store_true", help="Also generate output/shot-contact-sheet.jpg for review.")
    add_reuse_force(shots)
    shots.set_defaults(handler=handlers["shots"])

    visual = subparsers.add_parser(
        "visual",
        parents=[common],
        help="Analyze representative shot frames with a multimodal model.",
        description="Analyze representative shot frames with a multimodal model.",
    )
    visual.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    add_reuse_force(visual)
    visual.set_defaults(handler=handlers["visual"])

    cut = subparsers.add_parser("cut", parents=[common], help="Cut scored segments into clip files.")
    cut.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    cut.add_argument("--min-score", type=float, default=6, help="Minimum score to cut (default: 6).")
    cut.add_argument("--silent", action="store_true", help="Strip audio from generated clips.")
    add_project(cut)
    add_reuse_force(cut)
    cut.set_defaults(handler=handlers["cut"])

    order = subparsers.add_parser("order", parents=[common], help="Create, replace, and show project clip order.")
    order.add_argument("project", metavar="PROJECT", help="Slug-safe project name.")
    order.add_argument("clip_ids", nargs="*", metavar="CLIP_ID", help="Full replacement order by clip ID.")
    order.add_argument("--reset", action="store_true", help="Reset order to the current clips.json order.")
    order.add_argument("--show", action="store_true", help="Show the current order.")
    order.add_argument("--move", metavar="CLIP_ID", help="Move clip ID to a 1-based position.")
    order.add_argument("--to", type=int, metavar="POSITION", help="1-based destination position for --move.")
    order.add_argument("--swap", nargs=2, metavar=("CLIP_A", "CLIP_B"), help="Swap two clip IDs in the order.")
    order.set_defaults(handler=handlers["order"])

    montage = subparsers.add_parser("montage", parents=[common], help="Assemble clips into a montage.")
    montage.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    montage.add_argument("--min-duration", type=float, help="Require a minimum montage duration in seconds.")
    montage.add_argument("--max-duration", type=float, help="Limit montage duration in seconds.")
    montage.add_argument("--silent", action="store_true", help="Strip audio from the montage.")
    montage.add_argument("--chronological", action="store_true", help="Sort selected clips by source/start/end time instead of preserving editorial order.")
    add_project(montage)
    add_reuse_force(montage)
    montage.set_defaults(handler=handlers["montage"])

    pipeline = subparsers.add_parser("pipeline", parents=[common], help="Run start, transcribe, score, cut, and montage.")
    pipeline.add_argument("input", nargs="?", metavar="URL_OR_VIDEO_PATH", help="Remote URL or local source video path.")
    pipeline.add_argument("--name", help="Optional slug-safe video name.")
    pipeline.add_argument("--directive", default="Find expressive, visually interesting, or emotionally engaging moments.", help="Scoring directive.")
    pipeline.add_argument("--min-score", type=float, default=6, help="Minimum score to cut (default: 6).")
    pipeline.add_argument("--min-duration", type=float, help="Require a minimum montage duration in seconds.")
    pipeline.add_argument("--max-duration", type=float, help="Limit montage duration in seconds.")
    pipeline.add_argument("--silent", action="store_true", help="Strip audio from clips and montage.")
    pipeline.add_argument("--proxy", help="Proxy URL for remote downloads.")
    add_project(pipeline)
    add_reuse_force(pipeline)
    pipeline.set_defaults(handler=handlers["pipeline"])


def build_parser() -> argparse.ArgumentParser:
    """Build the root Clipper argument parser."""

    parser = argparse.ArgumentParser(
        prog="clipper",
        description="Local-first toolkit for turning long videos or podcasts into clips and montages.",
    )
    parser.set_defaults(handler=None)
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    common = build_common_parent()
    add_placeholder_subcommands(subparsers, common)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Clipper CLI."""

    environ_before_dotenv = dict(os.environ)
    load_dotenv()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.handler is None:
            parser.print_help()
            return EXIT_USAGE
        try:
            return int(args.handler(args))
        except KeyboardInterrupt:
            return EXIT_CANCELLED
        except ArtifactError as exc:
            config = config_from_args(args)
            if config.json_output:
                print_json(error_envelope("artifact_error", str(exc)))
            else:
                print(f"error: {exc}", file=sys.stderr)
            return EXIT_FAILURE
    finally:
        for key in set(os.environ) - set(environ_before_dotenv):
            os.environ.pop(key, None)
        os.environ.update(environ_before_dotenv)


if __name__ == "__main__":
    sys.exit(main())
