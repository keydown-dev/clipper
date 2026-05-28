# Ralph handoff-out

## Summary

Completed iteration 9 / todo #14: implemented verbose scoring progress for `clipper score` while preserving non-verbose behavior and JSON stdout cleanliness.

## Changed files

- `clipper/scoring.py`
  - Added optional `CliProgress` plumbing to scoring.
  - Added lifecycle/config diagnostics, deterministic window progress, warning summaries, reuse logging, and completion output.
  - Captures OpenAI-compatible `response.usage` token metadata when present and accumulates totals across windows/retries.
  - Reports unavailable token usage without estimating locally.
- `clipper/cli.py`
  - Passes CLI verbosity into `score_video` via `CliProgress(enabled=--verbose)`.
- `tests/test_issue006.py`
  - Extended fakes to support response usage metadata.
  - Added tests for quiet non-verbose scoring, verbose stderr/JSON stdout split, window progress to 100%, token usage present/absent, retry usage totals, reuse behavior, and non-TTY plain progress.
- `README.md`
  - Documented verbose scoring usage, stderr diagnostics, JSON stdout behavior, and token usage dependency on API metadata.

## Decisions

- Scoring progress uses plain deterministic milestone lines for both TTY and non-TTY contexts, avoiding animated/control-character progress output.
- Token usage is stored only in verbose logs, not in `scores.json`, preserving the score artifact schema and prior behavior.
- Retry request usage is counted independently when the API returns usage metadata.

## Verification

See `verification.md`.

## Risks / notes

- Additional full-suite run exposed an unrelated existing test-order/environment issue in `tests/test_issue002.py::test_config_defaults_env_and_dotenv` after project `.env` loading. The scoped issue 006 test suite passes.

## Next suggested task

Proceed to the next planned issue/todo. Do not expand this iteration further.
