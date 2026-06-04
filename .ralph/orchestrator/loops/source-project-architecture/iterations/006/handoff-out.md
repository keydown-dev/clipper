# Handoff out

## Summary

Completed issue 033 project-level scoring.

`clipper score PROJECT` now detects when the positional target is an editorial project and scores included sources from `.clipper/projects/{project}/project.json`. It loads flattened source transcript and visual artifacts, applies per-source include ranges, builds a combined source-labelled scoring context, writes project-owned `scores.json`, and ensures scored segments include valid `source` tags.

## Changed files

- `clipper/cli.py`
  - Routes `clipper score PROJECT` to project scoring when `.clipper/projects/PROJECT/project.json` exists.
  - Rejects global `--start/--end` for project scoring because ranges live on project source entries.
- `clipper/scoring.py`
  - Added project scoring helpers and `score_project`.
  - Added source-aware context construction, validation, merging, and dialogue enrichment.
  - Preserves existing single-video scoring behavior.
- `clipper/schemas.py`
  - Allows optional `source` on score segments.
- `tests/test_issue033.py`
  - Covers single-source ranged project scoring, multi-source source-tagged scoring, and empty-project failure.

## Commit subject

Add project-level scoring

## Decisions

- Project scoring is selected by `clipper score PROJECT` only when the positional target names an existing project and `--project` is not supplied, preserving legacy video scoring and video-scoped project outputs.
- Single-source project scoring defaults missing LLM `source` fields to that included source; multi-source scoring requires returned sources to match configured included source names.
- Overlap merging is source-aware so equal timestamps from different sources are not merged together.

## Risks

- Multi-source LLM prompts rely on the model returning `source` for each segment; invalid or missing source values are dropped except in the single-source default case.
- Project-level `scores.json` uses `source_file: "project.json"` to satisfy the existing scores schema while segment-level source identifies media origin.

## Next suggested task

Proceed to issue 034 — project-level cutting, using the new per-segment `source` field to resolve source media paths.
