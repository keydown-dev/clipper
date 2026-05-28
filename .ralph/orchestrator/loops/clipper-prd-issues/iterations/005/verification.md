# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands

- `uv run pytest`

## Results

- Test suite passed: 38 passed, 1 skipped.
- The skipped test is the env-gated real Whisper integration test, which only runs when `CLIPPER_RUN_WHISPER_TESTS=1`.

## Acceptance criteria checked

- Transcription behavior unit-tested with mocked faster-whisper output.
- Transcript JSON schema tested, including segment `id`, `start`, `end`, and `text` fields.
- Whisper model load failures produce actionable JSON/CLI errors through `ArtifactError`.
- `clipper transcribe --help` and command routing are covered by tests.
- Real Whisper integration test is gated by `CLIPPER_RUN_WHISPER_TESTS=1`.
