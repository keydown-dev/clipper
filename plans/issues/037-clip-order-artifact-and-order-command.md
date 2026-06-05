# Issue 037 — Clip Order Artifact and Order Command

## Type

AFK

## What to build

Add a canonical project-level `clip-order.json` artifact and a `clipper order PROJECT` command for creating, resetting, and showing editorial clip order.

This replaces ad-hoc session artifacts such as `candidate-order.json` and makes iterative LLM/editorial ordering part of the supported Clipper workflow.

## Acceptance criteria

- [ ] Project artifact `.clipper/projects/{project}/clip-order.json` is supported.
- [ ] `clip-order.json` has `schema_version`, `source_file`, `created_at`, `updated_at`, `order`, and optional `warnings`.
- [ ] Each order entry includes at least `id`, `path`, and `duration`.
- [ ] Order validation fails if `clips.json` is missing.
- [ ] Order validation fails if any ordered clip ID does not exist in `clips.json`.
- [ ] Order validation fails on duplicate clip IDs.
- [ ] `clipper order PROJECT --reset` writes an order matching the current `clips.json` order.
- [ ] `clipper order PROJECT clip-0001 clip-0006 ...` replaces the full order with the specified clip IDs.
- [ ] `clipper order PROJECT --show` prints a numbered list with clip IDs, durations, and total duration.
- [ ] `clipper order PROJECT --show --json` returns a success envelope with order entries and total duration.
- [ ] Human output is concise and includes the `clip-order.json` path when writing.
- [ ] Tests cover reset, full replacement, show, JSON output, missing IDs, duplicate IDs, and missing clips manifest.

## Suggested implementation notes

- Add schema validation in `clipper/schemas.py`, e.g. `validate_clip_order`.
- Add order helpers in a new module such as `clipper/order.py`.
- Keep `clips.json` authoritative for start/end/source/reason/score; duplicate only display-friendly fields in `clip-order.json`.
- Use 1-based positions in human output.
- Do not implement move/swap in this issue; defer to Issue 039.

## Blocked by

- None
