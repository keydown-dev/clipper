# Issue 034 — Project-Level Cutting

## Type

AFK

## What to build

Make `clipper cut PROJECT` read project-owned `scores.json`, select passing source-tagged segments, cut each selected segment from the correct source media file, and write project-owned clip files and `clips.json`.

## Acceptance criteria

- [ ] `clipper cut PROJECT --min-score N` reads `.clipper/projects/{project}/scores.json`.
- [ ] The command requires every selected scored segment to include a valid `source` field.
- [ ] Each clip is cut from `.clipper/sources/{source}/source.{ext}` for that segment's source.
- [ ] Generated clips are written to `.clipper/projects/{project}/clips/`.
- [ ] `clips.json` is written to `.clipper/projects/{project}/clips.json`.
- [ ] Clip manifest entries preserve `source`, `start`, `end`, `duration`, `score`, and `reason`.
- [ ] `--reuse`, `--force`, `--silent`, and failure cleanup behave consistently with existing cutting semantics.
- [ ] Tests cover cutting from one source and cutting from multiple sources in the same project.

## Blocked by

- plans/issues/033-project-level-scoring.md
