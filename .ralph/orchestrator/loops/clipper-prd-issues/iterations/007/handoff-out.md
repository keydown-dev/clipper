# Ralph handoff-out

## Summary

Completed Issue 006 robust LLM scoring slice.

Implemented `clipper score` backed by a new scoring module that:
- Builds prompts from the README baseline system prompt and includes directive + timestamped transcript text.
- Uses an OpenAI-compatible chat completions client with env-derived defaults.
- Chunks long transcripts into ~10 minute windows with ~30 second overlap.
- Extracts JSON arrays from plain/markdown-wrapped responses and retries once with stricter instructions on parse failure.
- Validates, normalizes, clamps, warns, drops invalid scored segments, and writes empty `segments` with warnings when no valid candidates remain.
- Merges/deduplicates overlapping scored segments, preferring stronger scores.
- Persists `work/scores.json` and supports `--reuse` / `--force` output policy.

## Changed files

- `clipper/scoring.py` — new scoring implementation.
- `clipper/cli.py` — wired `run_score` into `clipper score`.
- `clipper/schemas.py` — strengthened score artifact validation.
- `tests/test_issue006.py` — coverage for prompts, directive/timestamps, chunking, JSON extraction/retry, validation, overlap merge, CLI persistence, empty-result warnings, env-gated real LLM test.
- `tests/test_cli.py` — removed `score` from placeholder command expectations.
- `tests/test_issue002.py` — updated missing `score` target expectation now that score is implemented.

## Decisions

- Kept downstream default minimum score documentation unchanged; README already documents `DEFAULT_MIN_SCORE=6` and `clipper cut --min-score 6`.
- Default test path mocks the OpenAI client; no real LLM call is made unless `CLIPPER_RUN_LLM_TESTS=1`.
- LLM request failures surface as `ArtifactError` so CLI JSON mode emits the standard error envelope.

## Risks / follow-up

- Segment length preference is expressed in prompts, but the implementation does not force-resize model-selected segments to 5–15 seconds because that could change model intent.
- Future cut implementation should consume `work/scores.json` and apply default min score 6.

## Verification

See `verification.md`.

## Next suggested task

Proceed to the next planned issue/iteration only after orchestrator approval; do not start it from this worker.
