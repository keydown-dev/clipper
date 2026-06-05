# Handoff out

## Summary

Implemented Issue 037: canonical project-level `.clipper/projects/{project}/clip-order.json`, schema validation, order helpers, and `clipper order PROJECT` CLI support for reset, full replacement, show, and JSON output.

## Changed files

- `clipper/artifacts.py` — added `ProjectArtifactLayout.clip_order` and fixed path entry.
- `clipper/schemas.py` — added `ClipOrder` typed schema and `validate_clip_order` registration.
- `clipper/order.py` — new helpers for building, writing, reading, and validating clip order against `clips.json`.
- `clipper/cli.py` — added `clipper order PROJECT [CLIP_ID...] --reset --show` command.
- `tests/test_issue037.py` — added coverage for reset, replacement, show, JSON output, missing IDs, duplicates, and missing `clips.json`.
- `tests/test_issue028.py` — updated project fixed-path expectation for the new canonical artifact.

## Commit subject

feat: add project clip order command

## Decisions

- `--reset` writes order entries matching current `clips.json` order.
- Positional clip IDs perform a full replacement with exactly those IDs; omitted IDs are allowed so editors can intentionally narrow/reorder a selection.
- `--show` reads existing `clip-order.json`; if absent, it displays the default order derived from `clips.json` without writing.
- `created_at` is preserved when replacing an existing valid `clip-order.json`; `updated_at` is refreshed on writes.
- `clip-order.json` duplicates only display-friendly `id`, `path`, and `duration`, keeping `clips.json` authoritative for other clip fields.

## Risks

- Future Issue 038/039 may want montage/move/swap behavior to consume or mutate `clip-order.json`; this task intentionally did not wire montage to the new artifact.
- The CLI currently accepts `--show` together with replacement/reset and still writes first because argparse permits that combination; tests cover the requested standalone `--show` behavior.

## Next suggested task

Implement Issue 038: make project montage preserve and consume canonical editorial order where appropriate.
