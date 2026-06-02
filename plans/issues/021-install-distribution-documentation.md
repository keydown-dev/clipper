# Issue 021 — Install and Distribution Documentation

## Goal

Document supported ways to install and verify Clipper Core across projects, with honest coverage of Python, uv, FFmpeg/ffprobe, Whisper, and LLM requirements.

## Depends On

- Issue 003 for `clipper doctor`
- ADR 0002 for the CLI Contract and surface separation

## Tasks

- Document local development install from a checkout: `uv sync`, `.env`, `uv run clipper doctor`.
- Document expected future installed-CLI usage: `clipper doctor`.
- Document the first supported non-dev installation path as `uv tool install` from the project git repository, once Issue 026 verifies the exact command.
- Keep PyPI publishing explicitly out of scope for the first install documentation.
- Explain required system dependencies: Python 3.11+, uv, FFmpeg, ffprobe.
- Explain Python/media/model dependencies: yt-dlp, faster-whisper, model downloads, OpenAI-compatible LLM config, optional vision model config.
- Explain how to use `--store` and `CLIPPER_STORE_PATH` across projects.
- Add troubleshooting guidance for missing CLI, missing FFmpeg, failed Whisper import/model load, failed LLM config, and failed yt-dlp downloads.
- Ensure install docs are referenced by the root skill from Issue 019.

## Acceptance Criteria

- A new user can follow docs to verify whether Clipper can run on their machine.
- Docs distinguish local dev checkout commands from installed CLI commands.
- Docs do not claim packaging capabilities that are not implemented yet, especially PyPI or bundled native dependency installation.
- `clipper doctor` remains the recommended first verification command.
