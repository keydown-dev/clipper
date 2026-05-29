"""Local video transcription with faster-whisper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .progress import CliProgress
from .schemas import SCHEMA_VERSION


@dataclass(frozen=True)
class TranscriptionOptions:
    """Configuration for faster-whisper transcription."""

    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None


def _video_relative(layout: ArtifactLayout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _load_model(options: TranscriptionOptions) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - doctor catches this in normal installs
        raise ArtifactError("faster-whisper is not installed; install project dependencies with `uv sync`") from exc

    try:
        return WhisperModel(options.model, device=options.device, compute_type=options.compute_type)
    except Exception as exc:
        raise ArtifactError(
            "could not load Whisper model "
            f"{options.model!r} with device={options.device!r} compute_type={options.compute_type!r}: {exc}. "
            "Check the model name, device support, compute type, downloaded model files, and available memory."
        ) from exc


def _word_to_json(segment_index: int, word_index: int, word: Any) -> dict[str, Any]:
    try:
        start = float(word.start)
        end = float(word.end)
        text = str(word.word).strip()
    except AttributeError as exc:
        raise ArtifactError(f"Whisper returned a malformed word timestamp at segment {segment_index}, word {word_index}: missing {exc.name}") from exc
    return {"word": text, "start": start, "end": end}


def _segment_to_json(index: int, segment: Any) -> dict[str, Any]:
    try:
        start = float(segment.start)
        end = float(segment.end)
        text = str(segment.text).strip()
    except AttributeError as exc:
        raise ArtifactError(f"Whisper returned a malformed segment at index {index}: missing {exc.name}") from exc

    raw_words = getattr(segment, "words", None)
    if raw_words is None:
        raise ArtifactError(
            f"Whisper did not return word timestamps for segment {index}; "
            "rerun transcription with a faster-whisper build that supports word_timestamps=True"
        )
    words = [_word_to_json(index, word_index, word) for word_index, word in enumerate(raw_words)]
    if text and not words:
        raise ArtifactError(f"Whisper returned no word timestamps for non-empty segment {index}")
    return {"id": index, "start": start, "end": end, "text": text, "words": words}


def build_transcript(*, source_file: str, duration: float, segments: Iterable[Any], info: Any, progress: CliProgress | None = None) -> dict[str, Any]:
    """Convert faster-whisper output to the shared transcript schema."""

    language = getattr(info, "language", None)
    if language is not None:
        language = str(language)
    transcript_duration = float(getattr(info, "duration", duration) or duration)
    progress_tracker = progress.transcription(duration=transcript_duration) if progress else None
    transcript_segments = []
    for index, segment in enumerate(segments):
        segment_json = _segment_to_json(index, segment)
        transcript_segments.append(segment_json)
        if progress_tracker:
            progress_tracker.update(segment_json["end"])
    if progress_tracker:
        progress_tracker.finish()
    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": source_file,
        "language": language,
        "duration": transcript_duration,
        "segments": transcript_segments,
    }


def transcribe_video(
    *,
    store: Path,
    video: str | None,
    options: TranscriptionOptions,
    reuse: bool = False,
    force: bool = False,
    json_output: bool = False,
    progress: CliProgress | None = None,
) -> tuple[str, Path, dict[str, Any], bool]:
    """Transcribe a video workspace and persist work/transcript.json."""

    root = resolve_video(store, video, json_output=json_output)
    layout = ArtifactLayout.for_video(root.parent, root.name)
    metadata = read_validated_json(layout.metadata, "metadata")
    policy = output_policy([layout.transcript], reuse=reuse, force=force, schema="transcript")
    if policy == "reuse":
        if progress:
            progress.log(f"reusing existing transcript for video {layout.video}: {layout.transcript}")
        return layout.video, layout.transcript, read_validated_json(layout.transcript, "transcript"), True

    source_file = str(metadata["source_path"])
    source_path = layout.root / source_file
    if not source_path.exists():
        raise ArtifactError(f"source file missing for {layout.video}: {source_file}")

    if progress:
        language_mode = options.language or "auto-detect"
        progress.log(f"video {layout.video}: source={source_path}")
        progress.log(f"Whisper model={options.model} device={options.device} compute_type={options.compute_type} language={language_mode}")
        progress.log("loading Whisper model")
        progress.log("first use of this model may download files from Hugging Face and may be slow")
    model = _load_model(options)
    try:
        if progress:
            progress.log("starting transcription")
        segments, info = model.transcribe(str(source_path), language=options.language, word_timestamps=True)
    except Exception as exc:
        raise ArtifactError(f"Whisper transcription failed for {source_file}: {exc}") from exc

    transcript = build_transcript(source_file=source_file, duration=float(metadata["duration"]), segments=segments, info=info, progress=progress)
    write_json(layout.transcript, transcript)
    if progress:
        progress.log(
            "completed transcription: "
            f"segments={len(transcript['segments'])} detected_language={transcript['language']} "
            f"duration={transcript['duration']} transcript={layout.transcript}"
        )
    return layout.video, layout.transcript, transcript, False
