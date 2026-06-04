# Handoff out — iteration 009

## Summary

Completed todo #009-036-docs-migration-and-compatibility. Updated user-facing docs and domain docs for the source/project architecture, including source ingestion, project creation/inclusion, project-level score/cut/montage outputs, and migration/compatibility guidance for legacy video workspaces and deprecated `clipper start`.

## Changed files

- `README.md`
  - Reworked quickstart, CLI overview, subcommand reference, artifact layout, schema examples, source ingestion, scoring, cutting, montage, manual validation, troubleshooting, and migration guidance around `.clipper/sources/{source}/` and `.clipper/projects/{project}/`.
  - Documented compatibility behavior for `clipper start`, legacy `.clipper/{video}/` workspaces, positional project resolution, and legacy `--project` scoped single-source outputs.
- `CONTEXT.md`
  - Added Source and Project domain terms.
  - Reframed Video as legacy compatibility terminology.
  - Updated relationships and workflow command language for source/project flows.
- `docs/adr/0001-video-workspaces-as-cli-contract.md`
  - Superseded the single video workspace ADR with the source/project workspace CLI contract and migration compatibility notes.
- `docs/adr/0002-core-first-monorepo-surfaces.md`
  - Added guidance for future surfaces to understand source/project paths while preserving legacy read access.

## Commit subject

Document source/project migration compatibility

## Decisions

- Kept legacy video workspace and `clipper start` references where they explain compatibility or migration behavior.
- Documented `list` as still legacy-video-oriented because source/project listing is not implemented in the current CLI.
- Kept the JSON envelope `video` key in examples because the current CLI contract still uses that field name even for source-like targets.

## Risks

- README now describes the preferred source/project model, but `pipeline` remains a compatibility single-source flow; future work may need a first-class project pipeline or clearer generated help text.
- Source/project listing is documented as future work, so users may still need to inspect `.clipper/sources/` and `.clipper/projects/` manually.

## Verification

See `verification.md`. Full test suite passed: 147 passed, 3 skipped.

## Next suggested task

Review generated CLI help text and command output wording for any remaining user-facing "video" language that should become source/project terminology in a follow-up implementation slice.
