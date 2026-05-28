# Ralph handoff-out

Loop: clipper-prd-issues
Iteration: 13
Todo: 11 — Complete `plans/issues/011-cli-polish-and-docs.md` only.

## Summary

Completed the bounded CLI polish/docs slice by strengthening canonical README guidance and adding CLI smoke coverage for representative help, JSON output, JSON errors, usage exit codes, and verbose+JSON behavior.

## Changed files

- `README.md`
  - Added setup notes explaining `uv sync`, `.env`, and `doctor` expectations.
  - Added a quickstart local smoke flow using a generated FFmpeg video.
  - Added a subcommand reference covering every implemented command.
  - Added manual local-file and URL validation flows.
  - Added troubleshooting notes for `uv`, FFmpeg/ffprobe, `.env`, doctor flags, reuse/force, JSON output, and optional real LLM/Whisper test flags.
- `tests/test_cli.py`
  - Added representative pipeline help coverage.
  - Added JSON error envelope/failure exit coverage.
  - Added usage error exit-code coverage.
  - Added verbose+JSON parseability coverage.

## Decisions

- Preserved existing CLI behavior; no production CLI code changes were needed because the current implementation already exposes normalized shared options and JSON envelopes.
- Kept expensive/manual flows documented rather than exercised in default tests, consistent with existing deterministic test constraints.

## Verification

See `verification.md`.

## Risks / notes

- `uv run clipper doctor` can still report environment-specific failures if a user has not installed FFmpeg/ffprobe or dependencies; README now documents those fixes.
- Default test suite skips real Whisper and LLM integration unless opt-in environment flags are set.

## Next suggested task

Proceed to the next planned issue/iteration; do not expand this iteration further.
