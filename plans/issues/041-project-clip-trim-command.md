# Issue 041 — Project Clip Trim Command

## Type

AFK

## What to build

Add `clipper trim PROJECT CLIP_ID` so users and LLM agents can tighten individual project clips after review while preserving clip IDs, clip paths, and editorial order.

## Acceptance criteria

- [ ] `clipper trim PROJECT CLIP_ID --duration SECONDS` trims the selected clip to the requested duration from its current start.
- [ ] `clipper trim PROJECT CLIP_ID --start TIME` updates the clip start while preserving its current end unless `--duration` or `--end` is also provided.
- [ ] `clipper trim PROJECT CLIP_ID --end TIME` updates the clip end.
- [ ] `--start`, `--end`, and `--duration` combinations are validated clearly.
- [ ] The command rejects non-positive durations.
- [ ] The command rejects trims outside the source media bounds.
- [ ] The command regenerates only the affected clip file from the original source media.
- [ ] The command preserves the clip ID and path in `clips.json`.
- [ ] The command updates `start`, `end`, and `duration` in `clips.json`.
- [ ] If `clip-order.json` exists, the matching order entry duration is updated.
- [ ] `--silent` controls whether regenerated clip audio is stripped, defaulting to the existing `clips.json`/project cut silent setting when possible.
- [ ] `--force` overwrites the existing clip file.
- [ ] JSON output reports the updated clip entry and paths touched.
- [ ] Tests cover duration-only trim, end trim, start trim, invalid time ranges, missing clip ID, project source lookup, and `clip-order.json` duration update.

## Suggested implementation notes

- Reuse project source media lookup from `cut_project`.
- Reuse `ffmpeg_cut_command` for accurate re-encoding.
- Write to a temporary file first, then replace the existing clip file only after FFmpeg succeeds.
- Preserve clip reasons/scores/source metadata.
- Update contact-sheet previews only in Issue 042 or leave them stale with a warning; avoid expanding scope here unless simple.

## Blocked by

- plans/issues/037-clip-order-artifact-and-order-command.md
