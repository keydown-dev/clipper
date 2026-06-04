# Issue 030 — Source Analysis Commands

## Type

AFK

## What to build

Move analysis commands to operate on source folders. `transcribe`, `shots`, and `visual` should resolve source names under `.clipper/sources/` and write flattened analysis artifacts into that source folder. These commands remain source-level because transcription and visual analysis are reusable across projects.

## Acceptance criteria

- [ ] `clipper transcribe SOURCE` reads `.clipper/sources/{source}/source.{ext}`.
- [ ] Transcription writes `.clipper/sources/{source}/transcript.json` and `.clipper/sources/{source}/sentences.json`.
- [ ] `clipper shots SOURCE --contact-sheet` writes `.clipper/sources/{source}/shots.json`, `.clipper/sources/{source}/frames/`, and `.clipper/sources/{source}/shot-contact-sheet.jpg`.
- [ ] `clipper visual SOURCE` reads source shots/frames and writes `.clipper/sources/{source}/visual-index.json`.
- [ ] `--reuse` and `--force` continue to validate complete output sets.
- [ ] Existing tests or compatibility paths are updated so source analysis is verified end-to-end.

## Blocked by

- plans/issues/028-source-and-project-layouts.md
- plans/issues/029-source-command-ingestion.md
