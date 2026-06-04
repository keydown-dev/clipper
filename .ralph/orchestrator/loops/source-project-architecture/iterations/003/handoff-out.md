# Handoff out

## Summary

Completed issue 030 by moving source-level analysis commands onto `.clipper/sources/{source}/` layouts while preserving legacy video workspace compatibility. `transcribe`, `shots`, and `visual` now prefer source names under `.clipper/sources/` and write/read flattened source artifacts.

## Changed files

- `clipper/transcription.py`
  - Added source-aware analysis layout resolution.
  - Writes `transcript.json` and `sentences.json` in the source root when targeting a source.
  - Uses flattened source-relative paths like `source.mp4` and `transcript.json`.
- `clipper/shots.py`
  - Added source-aware analysis layout resolution.
  - Writes `shots.json`, `frames/`, and optional `shot-contact-sheet.jpg` in the source root when targeting a source.
  - Keeps `--reuse` validation over complete manifest/frame/contact-sheet output sets.
- `clipper/visual.py`
  - Added source-aware analysis layout resolution.
  - Reads source `shots.json`/`frames/` and writes `visual-index.json` in the source root.
- `tests/test_issue030.py`
  - Added source analysis coverage for transcribe, reuse validation, shots/contact-sheet output, and visual analysis.

## Commit subject

cli: Move analysis commands to sources

## Verification performed

See `verification.md`. Full test suite passes: 129 passed, 3 skipped.

## Decisions

- Source names are preferred over legacy video workspaces when `.clipper/sources/{name}` exists, but existing video-name/path behavior is retained as fallback compatibility.
- Kept the CLI JSON envelope `video` field unchanged for compatibility, populated with the source name for source-targeted commands.
- Duplicated the small source-layout resolver in each analysis module to keep this bounded slice local and avoid a broader artifacts API migration.

## Risks or blockers

- No blocker encountered.
- The source-layout resolver duplication could be consolidated in a later cleanup if more commands need the same behavior.
- Bare `clipper transcribe`/`shots`/`visual` without an explicit source still auto-resolves legacy videos only; source auto-select/list behavior was outside this issue.

## Next suggested task

Proceed to issue 031 — create empty project.
