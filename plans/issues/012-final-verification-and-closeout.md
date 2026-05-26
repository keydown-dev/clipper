# Issue 012 — Final Verification and Closeout

## Goal

Run a final verification pass and fix issues found before declaring the first build complete.

## Depends On

- Issue 011

## Tasks

- Run `uv sync`.
- Run `uv run clipper --help`.
- Run `uv run clipper doctor`.
- Run the default test suite.
- Run generated-video smoke tests.
- Optionally run env-gated LLM and Whisper tests when configured.
- Fix failures or document intentional skips.
- Confirm Stage 2 narrative edit planning remains deferred but has a clear extension point.

## Acceptance Criteria

- Default tests pass.
- CLI help works.
- Doctor works locally or reports actionable failures.
- Generated-video smoke path passes.
- README accurately describes known optional checks.
- The project is ready for manual real-video validation.
