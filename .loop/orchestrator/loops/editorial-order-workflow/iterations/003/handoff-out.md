# Handoff out

## Summary

Completed issue 039 for `clipper order PROJECT`:

- Added `--move CLIP_ID --to POSITION` with 1-based position validation.
- Added `--swap CLIP_A CLIP_B`.
- Move/swap initialize from `clips.json` when `clip-order.json` is absent, then write `clip-order.json`.
- Move/swap update `updated_at`.
- Move/swap reject unknown clip IDs with clear artifact errors.
- Order actions (`--reset`, `--show`, explicit IDs, `--move`, `--swap`) are mutually exclusive.
- Human move/swap output prints numbered resulting order and total duration.
- JSON output includes resulting order and total duration via the existing success envelope.
- Added tests for move to beginning/middle/end, swap, invalid position, and missing clip IDs.

## Changed files

- `clipper/order.py`
- `clipper/cli.py`
- `tests/test_issue037.py`

## Verification

See `verification.md`. Full test suite passed.

## Commit subject

Add order move and swap operations

## Decisions

- Kept move/swap helpers in `clipper/order.py` alongside existing order read/write helpers.
- Reused existing `read_clip_order()` so missing `clip-order.json` starts from `clips.json` order before editing.
- Treated `--show` as mutually exclusive with write operations, per issue guidance.

## Risks

- Missing clip ID errors for move/swap mention `clip-order.json`; when the file is absent the operation still initialized from `clips.json` first. The message remains clear enough for the edited order context.

## Next suggested task

Proceed to the next planned Subagent Loop todo.
