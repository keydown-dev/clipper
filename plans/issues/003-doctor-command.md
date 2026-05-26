# Issue 003 — Doctor Command

## Goal

Implement `clipper doctor` to validate the local environment before users run expensive media processing.

## Depends On

- Issue 002

## Tasks

- Check Python version.
- Check FFmpeg availability.
- Check importable Python dependencies.
- Check writable artifact directories.
- Check LLM env configuration and optional connectivity.
- Check faster-whisper/model readiness with actionable warnings.
- Support human output and `--json` output.

## Acceptance Criteria

- `uv run clipper doctor` reports pass/warn/fail checks clearly.
- `uv run clipper doctor --json` returns parseable JSON.
- Tests simulate passing and failing checks without requiring real missing system dependencies.
