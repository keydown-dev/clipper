# Handoff out

## Summary

Completed issue 031 by adding `clipper create PROJECT` for empty editorial project creation. The command writes `.clipper/projects/{project}/project.json` with `schema_version`, `name`, empty `sources`, and `created_at`, fails on existing projects by default, and supports `--force` overwrite.

## Changed files

- `clipper/cli.py`
  - Imported `ProjectArtifactLayout`.
  - Added `run_create` command handler.
  - Registered `clipper create PROJECT [--force]`.
- `tests/test_issue031.py`
  - Added coverage for project creation success, existing-project failure, and force overwrite.
- `tests/test_project_outputs.py`
  - Narrowed root help assertion to exclude only `--project`, allowing the new `create` command help to mention projects.

## Commit subject

cli: Add empty project creation

## Verification performed

See `verification.md`. Full test suite passes: 132 passed, 3 skipped.

## Decisions

- `clipper create` creates only the project root and `project.json`; output folders such as `clips/` remain deferred until downstream commands need them.
- `--force` removes and recreates the project folder to guarantee stale project output/config files do not survive overwrite.

## Risks or blockers

- No blocker encountered.
- No project schema validator was added in this slice because acceptance only requires writing the initial config and no command reads it yet.

## Next suggested task

Proceed to issue 032 — include source in project.
