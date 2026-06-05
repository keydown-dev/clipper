# Handoff out

Completed iteration 005 / Issue 041.

## Summary

Implemented `clipper trim PROJECT CLIP_ID` for project clips. The command:

- accepts `--duration`, `--start`, and `--end` trim options with clear validation;
- rejects non-positive and out-of-source-bounds trims;
- looks up the original project source media via source metadata;
- regenerates only the selected clip file through FFmpeg using a temp file then replace;
- preserves clip ID/path and other clip metadata;
- updates `start`, `end`, and `duration` in `clips.json`;
- updates the matching `clip-order.json` duration when present;
- defaults regenerated audio behavior to the manifest `silent` setting, with `--silent` override;
- emits JSON with the updated clip and touched paths.

## Changed files

- `clipper/cli.py`
- `tests/test_issue041.py`

## Commit subject

Add project clip trim command

## Decisions

- `--duration` is measured from the chosen/current start.
- `--start` alone preserves the existing end.
- `--duration` and `--end` together are rejected as ambiguous; users can use `--start --duration` or `--start --end`.
- Trim overwrites the existing clip path atomically because preserving paths is core to the command; `--force` is accepted and reported but not required for normal in-place trim examples.

## Risks

- The current implementation only supports project clips with a `source` field, which matches project clip manifests.
- Contact-sheet previews are intentionally left stale per issue notes / future docs issue.

## Verification

See `verification.md`. Full test suite passed.

## Next suggested task

Proceed to Issue 042 docs/editorial workflow updates.
