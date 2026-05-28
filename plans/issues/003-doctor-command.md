# Issue 003 — Doctor Command

## Goal

Implement `clipper doctor` to validate the local environment before users run expensive media processing.

## Depends On

- Issue 002

## Tasks

- Check Python version.
- Check FFmpeg and ffprobe availability.
- Check importable Python dependencies.
- Check writable artifact directories.
- Check LLM env configuration by default and real LLM connectivity only when explicitly requested, e.g. `--check-llm`.
- Check faster-whisper import/config readiness with actionable warnings by default and real model loading only when explicitly requested, e.g. `--check-whisper`.
- Support human output and `--json` output. JSON `result` should include `checks: [{name, status, message}]` plus summary counts; check `status` values are `pass`, `warn`, or `fail`.

## Acceptance Criteria

- `uv run clipper doctor` reports pass/warn/fail checks clearly.
- `uv run clipper doctor --json` returns parseable JSON with `checks: [{name, status, message}]` plus summary counts using `pass`, `warn`, or `fail` statuses.
- Tests simulate passing and failing checks without requiring real missing system dependencies or real LLM connectivity by default.
