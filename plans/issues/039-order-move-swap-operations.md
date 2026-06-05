# Issue 039 — Order Move and Swap Operations

## Type

AFK

## What to build

Extend `clipper order PROJECT` with ergonomic editing operations for iterative editorial workflows: moving one clip to a numbered position and swapping two clips.

## Acceptance criteria

- [ ] `clipper order PROJECT --move CLIP_ID --to POSITION` moves the clip to a 1-based position.
- [ ] `clipper order PROJECT --swap CLIP_A CLIP_B` swaps the two clips.
- [ ] If `clip-order.json` does not exist, move/swap operations initialize from `clips.json` order before editing.
- [ ] `--to` rejects positions less than 1 or greater than the number of clips.
- [ ] Move/swap fail clearly when clip IDs are unknown.
- [ ] Move/swap update `updated_at`.
- [ ] Human output shows the resulting numbered order and total duration.
- [ ] JSON output returns the resulting order and total duration.
- [ ] Tests cover move to beginning, middle, and end.
- [ ] Tests cover swap.
- [ ] Tests cover invalid position and missing clip ID errors.

## Suggested implementation notes

- Reuse order load/write helpers from Issue 037.
- Keep operations mutually exclusive: full replacement, reset, show, move, and swap should not run together.
- Use stable ID-based operations, not path-based operations, so agent commands are concise.

## Blocked by

- plans/issues/037-clip-order-artifact-and-order-command.md
