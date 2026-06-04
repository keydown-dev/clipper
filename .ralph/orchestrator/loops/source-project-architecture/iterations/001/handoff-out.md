# Handoff out

## Summary

Completed issue 028 by adding first-class source and project artifact layout resolvers while preserving the existing video layout.

## Changed files

- `clipper/artifacts.py`
  - Added `SourceArtifactLayout` for `.clipper/sources/{source}/` with flattened source, metadata, transcript, sentence, shots, visual index, contact sheet, and frames paths.
  - Added `ProjectArtifactLayout` for `.clipper/projects/{project}/` with project-owned `project.json`, scores, clips manifest, montage outputs, and `clips/` directory.
  - Both new layouts use existing slug-safe validation via `validate_video_name`.
- `tests/test_issue028.py`
  - Added coverage for source layout path generation.
  - Added coverage for project layout path generation.
  - Added coverage for same-slug source/project coexistence and invalid names.
  - Added compatibility coverage for existing `.clipper/{video}/` video layout.

## Commit subject

artifacts: Add source and project layouts

## Decisions

- Kept the existing `ArtifactLayout.for_video(...)` API unchanged for compatibility.
- Introduced separate layout dataclasses instead of overloading the existing video layout, because sources and projects live in different namespaces and have different artifact sets.
- Reused `validate_video_name` to satisfy the existing slug-safe validation rule without changing current error behavior.

## Risks

- The new source/project layout APIs are not yet wired into CLI commands; later issues are expected to migrate command behavior.
- Validation error wording still says "video name" because it intentionally reuses existing validation behavior.

## Verification

See `verification.md`. Full test suite passes: 120 passed, 3 skipped.

## Next suggested task

Proceed to issue 029 — source command ingestion.
