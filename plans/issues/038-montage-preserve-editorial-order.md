# Issue 038 — Montage Preserves Editorial Order by Default

## Type

AFK

## What to build

Change `clipper montage PROJECT` so it preserves editorial order by default instead of forcing chronological ordering. Chronological montage assembly should happen only when an explicit `--chronological` flag is present.

## Acceptance criteria

- [ ] `clipper montage PROJECT` uses `.clipper/projects/{project}/clip-order.json` when present.
- [ ] If `clip-order.json` is absent, `clipper montage PROJECT` uses the order of clips as they appear in `clips.json`.
- [ ] `clipper montage PROJECT --chronological` sorts selected clips by source/start/end time.
- [ ] `--max-duration` still trims only the final selected clip after the chosen ordering has been applied.
- [ ] `--min-duration`, `--silent`, `--reuse`, and `--force` retain existing behavior.
- [ ] `montage.json` includes an `order_source` field, e.g. `clip-order.json`, `clips.json`, or `chronological`.
- [ ] JSON CLI output includes `order_source`.
- [ ] Legacy/video montage behavior remains backward-compatible where possible; if no project order exists, it should preserve `clips.json` order unless `--chronological` is provided.
- [ ] Tests cover project montage with non-chronological `clip-order.json`.
- [ ] Tests cover fallback to `clips.json` order.
- [ ] Tests cover `--chronological` sorting.
- [ ] Tests cover `--max-duration` with a non-chronological order.

## Suggested implementation notes

- Update `MontageOptions` with `chronological: bool = False`.
- Replace unconditional sorting in `select_clips_for_montage` with order-preserving default behavior.
- Add a separate chronological sort path only when `chronological=True`.
- For project montage, load and validate `clip-order.json` before selection when present.
- Treat `clip-order.json` as an ordered list of clip IDs; hydrate full clip entries from `clips.json`.

## Blocked by

- plans/issues/037-clip-order-artifact-and-order-command.md
