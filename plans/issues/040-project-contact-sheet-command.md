# Issue 040 — Project Contact Sheet Command

## Type

AFK

## What to build

Add `clipper contact-sheet PROJECT` to render a grid of representative stills for project clips in the same order that montage will use by default.

This provides a Clipper-native review artifact for agent/user back-and-forth instead of requiring custom FFmpeg scripting.

## Acceptance criteria

- [ ] `clipper contact-sheet PROJECT` creates `.clipper/projects/{project}/contact-sheet.jpg` by default.
- [ ] The command uses `clip-order.json` order when present.
- [ ] If `clip-order.json` is absent, the command uses `clips.json` order.
- [ ] `--chronological` sorts clips by source/start/end time.
- [ ] The command creates/reuses per-clip preview stills under `.clipper/projects/{project}/previews/`.
- [ ] The default still time is reasonable, e.g. `min(0.5s, clip_duration / 2)` from the clip start.
- [ ] Supports `--columns`, `--thumb-width`, and `--thumb-height`.
- [ ] Supports `--output PATH` for an alternate contact sheet location.
- [ ] Supports `--force` to overwrite existing contact sheet/previews.
- [ ] JSON output reports contact sheet path, clip count, order source, columns, thumbnail size, and output dimensions.
- [ ] Human output prints the contact sheet path and clip count.
- [ ] Tests cover default order, clip-order order, chronological order, and JSON output.

## Suggested implementation notes

- Add a module such as `clipper/contact_sheet.py`.
- Use FFmpeg to extract preview JPEGs and tile them.
- Consider using a temporary ordered directory or FFmpeg concat/list equivalent so tile order is deterministic.
- Keep generated preview paths project-relative in any optional manifest if one is introduced later.

## Blocked by

- plans/issues/037-clip-order-artifact-and-order-command.md
- plans/issues/038-montage-preserve-editorial-order.md
