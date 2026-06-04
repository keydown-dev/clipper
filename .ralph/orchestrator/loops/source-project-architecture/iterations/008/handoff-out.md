# Handoff out — iteration 008

## Summary

Completed todo #008-035-project-level-montage. `clipper montage PROJECT` now detects a positional project when `.clipper/projects/{project}/project.json` exists and assembles from project-owned `clips.json` into project-owned `montage.mp4` / `montage.json`.

## Changed files

- `clipper/montage.py`
  - Added `montage_project(...)` using `ProjectArtifactLayout`.
  - Extracted shared montage assembly into `_montage_from_layout(...)` so video and project paths keep the same min/max duration, silent, reuse, force, validation, and cleanup behavior.
- `clipper/cli.py`
  - Routes positional `clipper montage PROJECT` to `montage_project(...)` when a project exists.
  - Preserves the existing video/`--project` path as fallback compatibility.
- `tests/test_issue035.py`
  - Added coverage for project montage creation, max-duration trimming, reuse, failure cleanup, and CLI positional project routing.

## Commit subject

Implement project-level montage assembly

## Decisions

- Kept existing `montage_video(..., project=...)` behavior for compatibility with previous scoped video outputs, while adding first-class project montage support.
- Project montage manifests are project-relative (`montage.mp4`, `clips/clip-0001.mp4`) because `ProjectArtifactLayout.root` is the project directory.

## Risks

- `clipper montage NAME` now prefers a project over a video only when `.clipper/projects/NAME/project.json` exists and `--project` is not supplied. If a video and project share a name, the project wins for `montage`, matching the new project-level lifecycle but potentially surprising old callers.

## Verification

See `verification.md`. Full test suite passed: 147 passed, 3 skipped.

## Next suggested task

Proceed to todo #009 / issue 036: update docs, migration guidance, and compatibility messaging for the source/project architecture.
