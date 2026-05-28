# Ralph handoff-out

Loop: clipper-prd-issues
Iteration: 2
Todo: Iteration 2 — Complete `plans/issues/002-config-schemas-and-artifacts.md` only, preserving Issue 001 behavior; verify acceptance criteria.

## Summary

Completed Issue 002 foundations:

- Added configuration loading with defaults, `.env` support, env overrides, and explicit store override support.
- Added artifact helpers for pathlib JSON IO, fixed per-video layout, safe/default video names, URL/local canonical references, video listing, video resolution, and existing-output policy.
- Added typed artifact contracts and lightweight validators for metadata, transcript, scores, clip manifests, montage results, and pipeline results.
- Added shared CLI JSON success/failure envelope helpers and implemented real `clipper list` while leaving other Issue 001 placeholder commands runnable.
- Made `--reuse` and `--force` mutually exclusive via argparse shared helper.
- Updated `.env.example` with documented LLM/Whisper/artifact defaults.
- Added Issue 002 test coverage and adjusted Issue 001 CLI tests for the now-implemented `list` command.

## Changed files

- `.env.example`
- `clipper/cli.py`
- `clipper/config.py`
- `clipper/artifacts.py`
- `clipper/schemas.py`
- `tests/test_cli.py`
- `tests/test_issue002.py`

## Decisions

- Kept schema validation lightweight and dependency-free using `TypedDict` contracts plus explicit validators instead of adding a runtime schema dependency.
- `clipper list` treats malformed metadata as absent for listing resilience, while explicit reused JSON validation fails clearly.
- `output_policy(..., schema=...)` validates JSON members of an output set and skips non-JSON members such as `output/montage.mp4`.
- Common CLI `--store` defaults are resolved at config creation time so `CLIPPER_STORE_PATH` changes after parser construction are respected.

## Risks / follow-up

- Validators cover required Issue 002 core fields but are intentionally minimal; later pipeline implementation may add stricter semantic checks.
- Start/transcribe/score/cut/montage/pipeline execution remains placeholder except for shared config/artifact semantics and list support, as later issues own those steps.
- CLI parse errors from argparse are still argparse-formatted rather than JSON envelopes; command runtime failures use the shared envelope.

## Verification

See `verification.md`.

## Next suggested task

Proceed to Issue 003: implement the doctor command using the shared config and JSON envelope helpers.
