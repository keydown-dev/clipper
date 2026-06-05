# Transcribe

`clipper transcribe [VIDEO]` creates `work/transcript.json` and `work/sentences.json` using faster-whisper.

Prerequisites:

```bash
uv run clipper doctor --json
# Optional when model/device readiness is uncertain:
uv run clipper doctor --check-whisper --json
```

Basic transcription:

```bash
uv run clipper transcribe interview --verbose
```

Force language or Whisper settings when known:

```bash
uv run clipper transcribe interview --language en --model small --device cpu --compute-type int8 --verbose
```

Machine-readable output with diagnostics on stderr:

```bash
uv run clipper transcribe interview --json --verbose
```

Reruns:

```bash
uv run clipper transcribe interview --reuse
uv run clipper transcribe interview --force
```

Use `work/sentences.json` for transcript scoring and transcript-only QA/summarization. It is the preferred readable artifact for summaries, quizzes, study guides, glossary extraction, and topic outlines because it preserves sentence text with timestamps. Use `work/transcript.json` when raw segment or word-level timing traceability is needed.

If sentence generation fails because an old transcript lacks word timings, rerun transcription with `--force`.
