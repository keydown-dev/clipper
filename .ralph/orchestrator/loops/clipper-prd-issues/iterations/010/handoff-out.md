# Ralph handoff-out

## Summary

Completed Issue 008 — Cut Clips.

Implemented `clipper cut` with:
- `--min-score` filtering, defaulting to 6 via existing CLI option.
- Overlap merging before cutting, preserving earliest start, latest end, maximum score, and combined reasons.
- Chronological sequential clip IDs/paths (`clip-0001`, `clip-0002`, ...).
- Fast FFmpeg stream-copy command shape with exact scored/merged start and end times.
- Audio preserved by default; `--silent` adds `-an`.
- Clear failure with no manifest/clip creation when no segments pass.
- `work/clips.json` manifest writing.
- fail/reuse/force output behavior and reuse validation.
- Partial-output cleanup on FFmpeg failures.
- Human and `--json` CLI output.

## Changed files

- `clipper/cutting.py` — new cutting implementation and FFmpeg command builder.
- `clipper/cli.py` — wired `run_cut`; also scoped CLI `.env` loading so CLI invocations do not pollute process environment across tests.
- `tests/test_cli.py` — removed `cut` from placeholder command expectations.
- `tests/test_issue008.py` — added cut acceptance/unit/integration tests.

## Decisions

- Treat segments whose boundaries merely touch (`end == next start`) as non-overlapping; only actual overlap merges.
- Combine merged reasons with `; ` while preserving unique reason text.
- Include `min_score` and `silent` in the clip manifest as additional allowed traceability fields.

## Risks / notes

- FFmpeg stream-copy exactness depends on codec/keyframes, but tests use project tolerance and generated fixture passes.
- Montage and pipeline remain future issues; this iteration did not begin them.

## Verification

See `verification.md`.

## Next suggested task

Proceed to Issue 009 — Montage Assembly.
