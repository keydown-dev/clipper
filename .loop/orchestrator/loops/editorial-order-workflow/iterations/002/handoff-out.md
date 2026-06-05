# Handoff out — iteration 002

## Summary

Implemented Issue 038 for montage ordering:

- `clipper montage PROJECT` now preserves project `clip-order.json` order when present.
- Falls back to `clips.json` order when no `clip-order.json` exists.
- Added `--chronological` to sort by source/start/end only when explicitly requested.
- `--max-duration` trimming now happens after the selected ordering is applied.
- `montage.json` and CLI JSON output include `order_source`.
- Legacy/video montage now preserves `clips.json` order by default and supports chronological mode through the same option.

## Changed files

- `clipper/montage.py`
- `clipper/cli.py`
- `tests/test_issue009.py`
- `tests/test_issue038.py`

## Verification

See `verification.md`.

## Commit subject

Preserve editorial order in montage

## Decisions

- Used `order_source` values: `clip-order.json`, `clips.json`, and `chronological`.
- `--chronological` ignores project editorial order and sorts the full clips manifest by source/start/end.
- Existing reused montage manifests without `order_source` remain readable; CLI JSON defaults missing reused `order_source` to `clips.json`.

## Risks

- No schema migration was added because the montage schema validator does not reject extra fields and existing manifests remain valid.
- Project clip-order hydration validates duplicate and missing IDs locally in montage rather than sharing `order.py` internals.

## Next suggested task

Proceed to the next planned editorial-order workflow issue.
