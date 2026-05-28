"""Command-line interface for Clipper."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from dotenv import load_dotenv

from .artifacts import ArtifactError, list_videos

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_CANCELLED = 130

PLACEHOLDER_COMMANDS = (
    "doctor",
    "start",
    "list",
    "transcribe",
    "score",
    "cut",
    "montage",
    "pipeline",
)


@dataclass(frozen=True)
class CommandConfig:
    """Shared per-command configuration parsed from common CLI options."""

    store: Path
    json_output: bool
    verbose: int


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


def run_placeholder(args: argparse.Namespace) -> int:
    """Run a placeholder command until implementation-specific issues fill it in."""

    config = config_from_args(args)
    message = f"clipper {args.command}: placeholder command; implementation pending."
    emit_result(config, args.command, message)
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


def add_placeholder_subcommands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], common: argparse.ArgumentParser) -> None:
    """Register all first-version placeholder subcommands."""

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {name: run_placeholder for name in PLACEHOLDER_COMMANDS}
    handlers["list"] = run_list

    doctor = subparsers.add_parser("doctor", parents=[common], help="Validate local Clipper environment.")
    doctor.add_argument("--check-llm", action="store_true", help="Also check LLM connectivity when implemented.")
    doctor.add_argument("--check-whisper", action="store_true", help="Also load/check Whisper model when implemented.")
    doctor.set_defaults(handler=handlers["doctor"])

    start = subparsers.add_parser("start", parents=[common], help="Create a video workspace from a URL or local video.")
    start.add_argument("input", nargs="?", metavar="URL_OR_VIDEO_PATH", help="Remote URL or local source video path.")
    start.add_argument("--name", help="Optional slug-safe video name.")
    start.add_argument("--proxy", help="Proxy URL for remote downloads.")
    add_reuse_force(start)
    start.set_defaults(handler=handlers["start"])

    list_cmd = subparsers.add_parser("list", parents=[common], help="List existing videos in the artifact store.")
    list_cmd.set_defaults(handler=handlers["list"])

    transcribe = subparsers.add_parser("transcribe", parents=[common], help="Transcribe a video workspace.")
    transcribe.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    transcribe.add_argument("--language", help="Force transcription language.")
    add_reuse_force(transcribe)
    transcribe.set_defaults(handler=handlers["transcribe"])

    score = subparsers.add_parser("score", parents=[common], help="Score transcript segments with an LLM.")
    score.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    score.add_argument("--directive", default="Find expressive, visually interesting, or emotionally engaging moments.", help="Scoring directive.")
    add_reuse_force(score)
    score.set_defaults(handler=handlers["score"])

    cut = subparsers.add_parser("cut", parents=[common], help="Cut scored segments into clip files.")
    cut.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    cut.add_argument("--min-score", type=float, default=6, help="Minimum score to cut (default: 6).")
    cut.add_argument("--silent", action="store_true", help="Strip audio from generated clips.")
    add_reuse_force(cut)
    cut.set_defaults(handler=handlers["cut"])

    montage = subparsers.add_parser("montage", parents=[common], help="Assemble clips into a montage.")
    montage.add_argument("video", nargs="?", metavar="VIDEO", help="Video name or video directory path.")
    montage.add_argument("--min-duration", type=float, help="Require a minimum montage duration in seconds.")
    montage.add_argument("--max-duration", type=float, help="Limit montage duration in seconds.")
    montage.add_argument("--silent", action="store_true", help="Strip audio from the montage.")
    add_reuse_force(montage)
    montage.set_defaults(handler=handlers["montage"])

    pipeline = subparsers.add_parser("pipeline", parents=[common], help="Run start, transcribe, score, cut, and montage.")
    pipeline.add_argument("input", nargs="?", metavar="URL_OR_VIDEO_PATH", help="Remote URL or local source video path.")
    pipeline.add_argument("--name", help="Optional slug-safe video name.")
    pipeline.add_argument("--directive", default="Find expressive, visually interesting, or emotionally engaging moments.", help="Scoring directive.")
    pipeline.add_argument("--min-score", type=float, default=6, help="Minimum score to cut (default: 6).")
    pipeline.add_argument("--max-duration", type=float, help="Limit montage duration in seconds.")
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

    load_dotenv()
    parser = build_parser()
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


if __name__ == "__main__":
    sys.exit(main())
