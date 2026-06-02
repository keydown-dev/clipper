# Handoff out

## Summary

Completed Issue 021's install/distribution documentation slice by expanding the Clipper skill install and troubleshooting references. The docs now distinguish source-checkout usage from installed CLI usage, keep PyPI and bundled native dependency installation out of scope, describe the expected future `uv tool install` git path pending Issue 026 verification, document system/Python/media/model/LLM requirements, explain `--store` and `CLIPPER_STORE_PATH`, and add troubleshooting for missing CLI, FFmpeg/ffprobe, Python dependency imports, Whisper, LLM/vision config, yt-dlp downloads, and artifact-store path confusion.

Synced the root skill changes into the packaged Pi skill copy using the existing sync script.

## Changed files

- `skills/clipper/references/install.md`
- `skills/clipper/references/troubleshooting.md`
- `packages/pi-clipper/skills/clipper/references/install.md`
- `packages/pi-clipper/skills/clipper/references/troubleshooting.md`

## Commit subject

feat: Document Clipper install readiness

## Verification performed

See `verification.md`. Final verification status: passed.

## Decisions made

- Treated `skills/clipper` as the source of truth and synced the generated package copy after edits.
- Documented `uv tool install git+https://github.com/keydown-dev/clipper.git` as an expected future command shape only, with explicit wording that Issue 026 must verify the exact supported install command.
- Left PyPI installation and bundled native dependency installation explicitly out of scope.

## Risks or blockers

- No blocker. The exact `uv tool install` command still needs Issue 026 verification before docs should present it as fully supported.

## Next suggested bounded task

Complete Issue 022 by adding transcript QA/summarization workflow documentation without expanding the root skill beyond references.
