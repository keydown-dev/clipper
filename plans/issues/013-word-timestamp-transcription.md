# Issue 013 — Word Timestamp Transcription

## Goal

Enable faster-whisper word timestamps by default and persist word-level timing data in transcript artifacts.

## Depends On

- Issue 005 for existing faster-whisper transcription
- Issue 005.1 for transcription progress behavior

## Tasks

- Update transcription so faster-whisper is called with word timestamps enabled by default.
- Persist a `words` array for each generated transcript segment, with word text, start time, and end time.
- Keep the existing segment-level `id`, `start`, `end`, and `text` fields.
- Treat missing word timestamps from new faster-whisper output as a clear transcription failure.
- Keep schema validation tolerant of older transcript artifacts without `words` where practical, but ensure new generated transcripts include them.
- Preserve existing model, device, compute type, language, fail/reuse/force, JSON output, and verbose progress behavior.
- Document that word timestamps are now part of the default transcript artifact.

## Acceptance Criteria

- Mocked faster-whisper transcription tests verify that generated transcript segments include word-level timestamps.
- Tests verify that new transcription fails clearly if segment word data is unavailable.
- Existing transcript fields remain present and backwards-compatible for consumers.
- `--reuse` continues to validate and reuse existing transcript artifacts without loading faster-whisper.
- Verbose transcription progress still works when consuming the faster-whisper segment iterator.
