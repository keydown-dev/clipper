# Ralph handoff-out

Loop: clipper-prd-issues  
Iteration: 5  
Todo: Iteration 5: Complete plans/issues/005-transcription.md only, preserving prior behavior; verify acceptance criteria.

## Summary

Implemented local transcription with faster-whisper and wired `clipper transcribe`.

## Changed files

- `clipper/transcription.py` — new transcription library, faster-whisper model loading, transcript building, output policy handling.
- `clipper/cli.py` — routed `transcribe` to implementation and added `--model`, `--device`, `--compute-type`, and `--language` options.
- `clipper/schemas.py` — tightened transcript segment schema validation for `id`, `start`, `end`, and `text`.
- `tests/test_issue005.py` — added mocked faster-whisper tests, schema tests, output policy tests, actionable load failure test, help routing test, and env-gated real Whisper integration test.
- `tests/test_cli.py` — removed `transcribe` from placeholder expectations and isolated list test store.
- `tests/test_issue002.py` — updated placeholder-envelope assertion to use remaining placeholder command `score`.

## Decisions

- Defaults come from existing config/env (`WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`) with config defaults `small`, `cpu`, `int8`; CLI flags override them.
- `--language` is passed through only when supplied; otherwise faster-whisper auto-detects and the persisted `language` may be `null` if no language is reported.
- Transcript duration prefers faster-whisper info duration when present, falling back to source metadata duration.

## Verification

See `verification.md`.

## Risks / notes

- Real Whisper execution is intentionally skipped unless `CLIPPER_RUN_WHISPER_TESTS=1` because it may download/load model files.
- `.ralph/orchestrator/loops/clipper-prd-issues/iterations/005/worker-output.jsonl` was modified by the harness during this worker run.

## Next suggested task

Proceed to Issue 006 / next Ralph iteration for LLM scoring. Do not start it in this iteration.
