"""Local video transcription with faster-whisper."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactLayout, SourceArtifactLayout, output_policy, read_validated_json, resolve_video, write_json
from .progress import CliProgress
from .schemas import SCHEMA_VERSION

SENTENCE_END_RE = re.compile(r"[.!?][\"')\]}»”’]*$")


@dataclass(frozen=True)
class TranscriptionOptions:
    """Configuration for faster-whisper transcription."""

    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None


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


def _has_sentence_ending(text: str) -> bool:
    return bool(SENTENCE_END_RE.search(text.strip()))


def build_sentence_transcript(*, transcript: dict[str, Any], source_transcript_path: str) -> dict[str, Any]:
    """Build a sentence-grouped transcript from word timestamp data."""

    sentences: list[dict[str, Any]] = []
    current_words: list[str] = []
    current_ranges: list[dict[str, int]] = []
    current_source_segments: list[int] = []
    current_start: float | None = None
    current_end: float | None = None

    def append_word(*, segment_id: int, word_index: int, word: dict[str, Any]) -> None:
        nonlocal current_start, current_end
        text = str(word["word"]).strip()
        if not text:
            return
        start = float(word["start"])
        end = float(word["end"])
        if current_start is None:
            current_start = start
        current_end = end
        current_words.append(text)
        if not current_ranges or current_ranges[-1]["segment_id"] != segment_id or current_ranges[-1]["end_word_index"] + 1 != word_index:
            current_ranges.append({"segment_id": segment_id, "start_word_index": word_index, "end_word_index": word_index})
        else:
            current_ranges[-1]["end_word_index"] = word_index
        if segment_id not in current_source_segments:
            current_source_segments.append(segment_id)

    def flush_sentence() -> None:
        nonlocal current_words, current_ranges, current_source_segments, current_start, current_end
        if current_start is None or current_end is None or not current_words:
            return
        sentences.append(
            {
                "id": len(sentences),
                "start": current_start,
                "end": current_end,
                "text": " ".join(current_words),
                "source_segments": current_source_segments,
                "word_ranges": current_ranges,
            }
        )
        current_words = []
        current_ranges = []
        current_source_segments = []
        current_start = None
        current_end = None

    for segment_index, segment in enumerate(transcript.get("segments", [])):
        segment_id = int(segment.get("id", segment_index))
        words = segment.get("words")
        if words is None:
            raise ArtifactError(
                f"transcript segment {segment_id} is missing word timestamps; "
                "rerun `clipper transcribe --force` to regenerate the transcript with word timings"
            )
        for word_index, word in enumerate(words):
            append_word(segment_id=segment_id, word_index=word_index, word=word)
            if _has_sentence_ending(str(word["word"])):
                flush_sentence()
    flush_sentence()

    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": transcript["source_file"],
        "language": transcript["language"],
        "duration": transcript["duration"],
        "source_transcript_path": source_transcript_path,
        "sentences": sentences,
    }


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

    layout = _resolve_analysis_layout(store, video, json_output=json_output)
    target_name = layout.source if isinstance(layout, SourceArtifactLayout) else layout.video
    metadata = read_validated_json(layout.metadata, "metadata")
    policy = output_policy([layout.transcript, layout.sentence_transcript], reuse=reuse, force=force)
    if policy == "reuse":
        transcript = read_validated_json(layout.transcript, "transcript")
        read_validated_json(layout.sentence_transcript, "sentence_transcript")
        if progress:
            progress.log(f"reusing existing transcript for source {target_name}: {layout.transcript}")
            progress.log(f"reusing existing sentence transcript for source {target_name}: {layout.sentence_transcript}")
        return target_name, layout.transcript, transcript, True

    source_file = str(metadata["source_path"])
    source_path = layout.root / source_file
    if not source_path.exists():
        raise ArtifactError(f"source file missing for {target_name}: {source_file}")

    if progress:
        language_mode = options.language or "auto-detect"
        progress.log(f"source {target_name}: source={source_path}")
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
    sentence_transcript = build_sentence_transcript(transcript=transcript, source_transcript_path=_video_relative(layout, layout.transcript))
    write_json(layout.transcript, transcript)
    write_json(layout.sentence_transcript, sentence_transcript)
    if progress:
        progress.log(
            "completed transcription: "
            f"segments={len(transcript['segments'])} sentences={len(sentence_transcript['sentences'])} detected_language={transcript['language']} "
            f"duration={transcript['duration']} transcript={layout.transcript} sentence_transcript={layout.sentence_transcript}"
        )
    return target_name, layout.transcript, transcript, False
