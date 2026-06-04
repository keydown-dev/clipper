# Handoff out — iteration 005

## Summary

Implemented `clipper include PROJECT SOURCE [--start TIME] [--end TIME]` for issue 032.

The command now:
- validates project and source existence,
- accepts seconds, `MM:SS`, and `HH:MM:SS` through the existing `parse_time`,
- rejects `end <= start` when both endpoints are present,
- appends new source entries or updates an existing matching source entry by name,
- writes deterministic `project.json` via existing sorted JSON writer,
- emits updated source lists in both JSON and human output.

## Changed files

- `clipper/cli.py`
- `tests/test_issue032.py`

## Commit subject

Add project source include command

## Decisions

- Used editorial command name `include`, not `add-source`.
- Kept project config validation lightweight because no project schema validator exists yet.
- Updating an included source replaces the whole entry, so changing from a ranged include to whole-source include removes stale `start`/`end` keys.

## Risks

- Project configs with malformed non-dict entries in `sources` are tolerated unless they match nothing; this preserves minimal scope for issue 032.
- Source existence checks require `sources/<name>/metadata.json`, not just a directory.

## Verification

See `verification.md`. Full test suite passed.

## Next suggested task

Proceed to issue 033 — Project-Level Scoring.
