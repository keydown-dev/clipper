# Handoff out

## Summary

Completed issue 029 by adding `clipper source INPUT --name SOURCE` for source ingestion into `.clipper/sources/{source}/` with flattened `source.{ext}` and `metadata.json` artifacts. Remote ingestion still uses yt-dlp and forwards `--proxy`; local ingestion copies one media file into the source folder. `clipper start` now acts as a deprecated source-ingestion alias while also mirroring legacy video workspace artifacts for existing compatibility tests.

## Changed files

- `clipper/cli.py`
  - Added `run_source` and source-ingestion helper using `SourceArtifactLayout`.
  - Updated local/remote preparation helpers to support flattened source layouts and legacy video layouts.
  - Registered `source` CLI command with required `--name`, `--proxy`, `--reuse`, and `--force`.
  - Converted `start` to a deprecated alias and preserved legacy workspace mirroring.
- `tests/test_cli.py`
  - Added `source` to command help coverage.
- `tests/test_issue029.py`
  - Added local source, reuse/force, remote yt-dlp/proxy, and deprecated start-alias coverage.

## Commit subject

cli: Add source ingestion command

## Verification performed

See `verification.md`. Full test suite passes: 125 passed, 3 skipped.

## Decisions

- Required `--name` for `clipper source` to match the issue wording and make source identity explicit.
- Kept `clipper start --name` optional for compatibility, falling back to the existing default-name behavior.
- Mirrored deprecated `start` runs into the old `.clipper/{video}/source` and `.clipper/{video}/work/metadata.json` layout so existing downstream behavior and tests remain intact during migration.

## Risks or blockers

- `clipper start` now writes both the new source namespace and legacy video namespace, so it can duplicate media bytes until later migration issues remove or retire the legacy path.
- Downstream analysis commands still target legacy video layouts; later issues should migrate them to source/project layouts.

## Next suggested task

Proceed to issue 030 — source analysis commands.
