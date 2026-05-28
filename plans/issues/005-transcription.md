# Issue 005 — Transcription

## Goal

Implement local video transcription with faster-whisper.

## Depends On

- Issue 002
- Issue 004 for source metadata conventions

## Tasks

- Implement transcription library function.
- Support configurable model, device, compute type, and language.
- Default to model `small`, device `cpu`, and compute type `int8`.
- Support `--language` to force language; otherwise auto-detect; transcript `language` may be `null` if not detected.
- Persist transcript JSON using the shared schema with `source_file`, `language`, `duration`, and timestamped `segments`.
- Respect fail/reuse/force output policy.
- Wire `clipper transcribe`.
- Add optional env-gated real Whisper integration test.

## Acceptance Criteria

- Transcription behavior is unit-tested with mocked faster-whisper output.
- Transcript JSON schema is tested, including segment `id`, `start`, `end`, and `text` fields.
- Whisper model load failures produce actionable errors.
- `clipper transcribe --help` and command routing work.
- Real Whisper test only runs with `CLIPPER_RUN_WHISPER_TESTS=1`.
