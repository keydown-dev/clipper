"""Artifact layout, JSON IO, video resolution, and output policies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .schemas import SchemaError, VALIDATORS

SLUG_RE = re.compile(r"^[a-z0-9_-]+$")
SAFE_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
GROUPS = ("source", "work", "clips", "output")


class ArtifactError(ValueError):
    """Raised for artifact-store failures."""


@dataclass(frozen=True)
class ArtifactLayout:
    store: Path
    video: str
    root: Path
    source_dir: Path
    work_dir: Path
    clips_dir: Path
    output_dir: Path
    metadata: Path
    transcript: Path
    sentence_transcript: Path
    scores: Path
    shots_manifest: Path
    shot_frames_dir: Path
    visual_index: Path
    clips_manifest: Path
    pipeline: Path
    montage_video: Path
    montage_json: Path
    shot_contact_sheet: Path

    @classmethod
    def for_video(cls, store: Path, video: str) -> "ArtifactLayout":
        root = store / video
        return cls(
            store=store,
            video=video,
            root=root,
            source_dir=root / "source",
            work_dir=root / "work",
            clips_dir=root / "clips",
            output_dir=root / "output",
            metadata=root / "work" / "metadata.json",
            transcript=root / "work" / "transcript.json",
            sentence_transcript=root / "work" / "sentences.json",
            scores=root / "work" / "scores.json",
            shots_manifest=root / "work" / "shots.json",
            shot_frames_dir=root / "work" / "frames",
            visual_index=root / "work" / "visual-index.json",
            clips_manifest=root / "work" / "clips.json",
            pipeline=root / "work" / "pipeline.json",
            montage_video=root / "output" / "montage.mp4",
            montage_json=root / "output" / "montage.json",
            shot_contact_sheet=root / "output" / "shot-contact-sheet.jpg",
        )

    def create_dirs(self) -> None:
        for directory in (self.source_dir, self.work_dir, self.clips_dir, self.output_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def fixed_paths(self, source_ext: str = ".mp4") -> dict[str, str]:
        ext = source_ext if source_ext.startswith(".") else f".{source_ext}"
        return {
            "source": f"source/source{ext}",
            "metadata": "work/metadata.json",
            "transcript": "work/transcript.json",
            "sentence_transcript": "work/sentences.json",
            "scores": "work/scores.json",
            "clips": "work/clips.json",
            "pipeline": "work/pipeline.json",
            "montage_video": "output/montage.mp4",
            "montage_json": "output/montage.json",
        }


def is_remote(input_ref: str) -> bool:
    return urlsplit(input_ref).scheme in {"http", "https"}


def canonical_input_ref(input_ref: str) -> str:
    if is_remote(input_ref):
        parts = urlsplit(input_ref)
        query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", query, ""))
    return str(Path(input_ref).expanduser().resolve())


def safe_stem(value: str) -> str:
    stem = Path(urlsplit(value).path).stem if is_remote(value) else Path(value).stem
    slug = SAFE_CHARS_RE.sub("-", stem.lower()).strip("-_")
    return slug or "video"


def validate_video_name(name: str) -> str:
    if not SLUG_RE.match(name):
        raise ArtifactError("video name must contain only lowercase letters, numbers, dashes, and underscores")
    return name


def default_video_name(input_ref: str) -> str:
    canonical = canonical_input_ref(input_ref)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]
    return f"{safe_stem(input_ref)}-{digest}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"malformed JSON in {path}: {exc.msg}") from exc


def read_validated_json(path: Path, schema: str) -> dict[str, Any]:
    data = read_json(path)
    try:
        return VALIDATORS[schema](data)
    except KeyError as exc:
        raise ArtifactError(f"unknown schema: {schema}") from exc
    except SchemaError as exc:
        raise ArtifactError(f"schema-invalid JSON in {path}: {exc}") from exc


def output_policy(paths: Iterable[Path], *, reuse: bool = False, force: bool = False, schema: str | None = None) -> str:
    """Apply fail/reuse/force policy to a step output set."""

    path_list = list(paths)
    if reuse and force:
        raise ArtifactError("--reuse and --force are mutually exclusive")
    existing = [path for path in path_list if path.exists()]
    if force:
        return "overwrite"
    if reuse:
        missing = [str(path) for path in path_list if not path.exists()]
        if missing:
            raise ArtifactError(f"--reuse requires the complete output set; missing: {', '.join(missing)}")
        if schema:
            for path in path_list:
                if path.suffix == ".json":
                    read_validated_json(path, schema)
        return "reuse"
    if existing:
        raise ArtifactError(f"output already exists: {', '.join(str(path) for path in existing)}")
    return "create"


def list_videos(store: Path) -> list[dict[str, Any]]:
    if not store.exists():
        return []
    videos: list[dict[str, Any]] = []
    for root in sorted(path for path in store.iterdir() if path.is_dir()):
        layout = ArtifactLayout.for_video(store, root.name)
        metadata: dict[str, Any] = {}
        if layout.metadata.exists():
            try:
                metadata = read_validated_json(layout.metadata, "metadata")
            except ArtifactError:
                metadata = {}
        videos.append(
            {
                "name": root.name,
                "path": str(root),
                "title": metadata.get("title"),
                "duration": metadata.get("duration"),
                "artifacts": {
                    "metadata": layout.metadata.exists(),
                    "transcript": layout.transcript.exists(),
                    "scores": layout.scores.exists(),
                    "shots": layout.shots_manifest.exists(),
                    "visual_index": layout.visual_index.exists(),
                    "clips": layout.clips_manifest.exists(),
                    "montage": layout.montage_video.exists() and layout.montage_json.exists(),
                },
            }
        )
    return videos


def resolve_video(store: Path, video: str | None, *, json_output: bool = False, prompt: Callable[[list[str]], str | None] | None = None) -> Path:
    """Resolve [VIDEO] as a name/path, auto-select sole video, or prompt interactively."""

    if video:
        path = Path(video).expanduser()
        if path.exists() and path.is_dir():
            return path
        candidate = store / video
        if candidate.exists() and candidate.is_dir():
            return candidate
        raise ArtifactError(f"video not found: {video}")
    videos = [item["name"] for item in list_videos(store)]
    if len(videos) == 1:
        return store / videos[0]
    if not videos:
        raise ArtifactError(f"no videos found in {store}")
    if prompt is None:
        if json_output or not sys.stdin.isatty():
            raise ArtifactError("multiple videos found; pass [VIDEO] explicitly")
        import questionary

        answer = questionary.select("Select video", choices=videos).ask()
    else:
        answer = prompt(videos)
    if answer is None:
        raise KeyboardInterrupt
    return store / answer
