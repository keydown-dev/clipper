# Editorial Clip Order Workflow Plan

## Problem

The current Clipper project workflow can create scored segments, cut candidate clips, and assemble a montage, but it does not yet support the iterative editorial workflow we need for LLM-assisted montage building.

In the Rupert farm montage session, we needed to:

1. create a candidate pool from a source/project,
2. review candidates visually,
3. move clips into a non-chronological editorial order,
4. trim individual candidates after discussion,
5. render the montage using the agreed order.

That workflow currently requires ad-hoc Python/FFmpeg scripting because `clipper montage PROJECT` sorts clips chronologically. This breaks the desired agent contract: an LLM should be able to perform the whole process through stable Clipper commands and canonical Clipper artifacts.

## Goals

- Make editorial clip order a first-class project artifact.
- Make `clipper montage PROJECT` preserve editorial order by default.
- Make chronological montage assembly opt-in via a flag.
- Add command surfaces for showing, creating, moving, swapping, and resetting clip order.
- Add a Clipper-native contact sheet command for reviewing candidates in editorial order.
- Add a Clipper-native trim command for tightening individual project clips while preserving clip IDs and manifests.
- Keep artifacts machine-readable and suitable for LLM/agent back-and-forth.

## Non-goals

- No GUI or timeline editor.
- No full nonlinear edit decision list with transitions/effects in this phase.
- No audio mixing or music bed support in this phase.
- No automatic narrative planner beyond preserving manually/agent-selected order.

## Canonical artifact: `clip-order.json`

Add a project-level artifact:

```text
.clipper/projects/{project}/clip-order.json
```

Recommended schema:

```json
{
  "schema_version": 1,
  "source_file": "clips.json",
  "created_at": "2026-06-05T12:00:00Z",
  "updated_at": "2026-06-05T12:10:00Z",
  "order": [
    {
      "id": "clip-0001",
      "path": "clips/clip-0001.mp4",
      "duration": 1.95,
      "note": "trimmed flags opener"
    },
    {
      "id": "clip-0006",
      "path": "clips/clip-0006.mp4",
      "duration": 4.0
    }
  ],
  "warnings": []
}
```

Notes:

- `id` must match a clip ID in `clips.json`.
- `path` should normally match the current path for that ID in `clips.json`.
- `duration` is duplicated for easy agent display, but `clips.json` remains authoritative for clip metadata.
- A validator should fail if ordered clip IDs do not exist in `clips.json`.
- Duplicate IDs should fail.
- Missing clips are allowed only if explicitly supported later; initially fail clearly.

## Montage behavior

Change `clipper montage PROJECT` behavior:

1. If `.clipper/projects/{project}/clip-order.json` exists, assemble clips in that order.
2. If no `clip-order.json` exists, assemble clips in the order they appear in `clips.json`.
3. Only sort chronologically when the user passes `--chronological`.

Example:

```bash
uv run clipper montage rb-montage --silent --force
uv run clipper montage rb-montage --chronological --silent --force
```

The montage manifest should report which order source was used:

```json
{
  "schema_version": 1,
  "montage_path": "montage.mp4",
  "clips": ["clips/clip-0001.mp4", "clips/clip-0006.mp4"],
  "duration": 23.49,
  "width": 1920,
  "height": 1080,
  "silent": true,
  "order_source": "clip-order.json"
}
```

## New command: `clipper order`

Add an order management command for project clip order.

Examples:

```bash
uv run clipper order rb-montage --show
uv run clipper order rb-montage clip-0001 clip-0002 clip-0006 clip-0005
uv run clipper order rb-montage --move clip-0006 --to 3
uv run clipper order rb-montage --swap clip-0004 clip-0005
uv run clipper order rb-montage --reset
```

Expected behavior:

- `--show` prints numbered clips with durations and total duration.
- Positional clip IDs replace the full order.
- `--move` moves one clip to a 1-based position.
- `--swap` swaps two clip IDs.
- `--reset` writes an order matching the current `clips.json` order.
- JSON output returns a stable envelope with the order entries and total duration.

## New command: `clipper contact-sheet`

Add a review command for project clips.

Examples:

```bash
uv run clipper contact-sheet rb-montage
uv run clipper contact-sheet rb-montage --columns 4 --thumb-width 480 --thumb-height 270
uv run clipper contact-sheet rb-montage --chronological
```

Expected behavior:

- Default order follows `clip-order.json` if present, otherwise `clips.json` order.
- `--chronological` sorts by source/start time.
- Generates `.clipper/projects/{project}/contact-sheet.jpg` by default.
- May also generate/reuse per-clip preview stills under `.clipper/projects/{project}/previews/`.
- JSON output reports the artifact path, clip count, order source, and dimensions.

## New command: `clipper trim`

Add a command to tighten a project clip after review.

Examples:

```bash
uv run clipper trim rb-montage clip-0007 --duration 3.5
uv run clipper trim rb-montage clip-0002 --end 6.45
uv run clipper trim rb-montage clip-0002 --start 3.45 --duration 3.0
```

Expected behavior:

- Operates on project clips from `.clipper/projects/{project}/clips.json`.
- Updates the matching clip entry in `clips.json`.
- Regenerates only the affected clip file from the original source media.
- Preserves clip ID and path.
- Updates `clip-order.json` duration if it exists.
- Fails clearly when requested trim is outside source bounds or produces non-positive duration.
- Supports `--force`/`--reuse` semantics where appropriate.

## Implementation phases

### Phase 1 — canonical order and montage behavior

- Add `clip-order.json` schema/validation helpers.
- Add `clipper order PROJECT --show`, positional replacement, and `--reset`.
- Change montage selection to preserve manifest/editorial order by default.
- Add `--chronological` to opt into time sorting.
- Update docs/tests.

### Phase 2 — order editing operations and contact sheet

- Add `clipper order --move` and `--swap`.
- Add `clipper contact-sheet PROJECT`.
- Ensure contact sheet uses editorial order by default.
- Update docs/tests.

### Phase 3 — project clip trim command

- Add `clipper trim PROJECT CLIP_ID`.
- Regenerate individual clip files safely.
- Update `clips.json` and `clip-order.json` durations.
- Update docs/tests.

## Agent workflow after completion

A future LLM/agent should be able to perform a session like this using only Clipper commands:

```bash
uv run clipper create rb-montage
uv run clipper include rb-montage rb-launch
uv run clipper score rb-montage --with-visuals --directive "Find Rupert farm-working shots"
uv run clipper cut rb-montage --min-score 8 --silent
uv run clipper order rb-montage --reset
uv run clipper contact-sheet rb-montage
uv run clipper order rb-montage --move clip-0006 --to 3
uv run clipper order rb-montage --swap clip-0004 clip-0005
uv run clipper trim rb-montage clip-0007 --duration 3.5 --force
uv run clipper trim rb-montage clip-0008 --duration 3.5 --force
uv run clipper order rb-montage --show
uv run clipper montage rb-montage --silent --force
```
