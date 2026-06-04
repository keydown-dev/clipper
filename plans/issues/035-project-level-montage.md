# Issue 035 — Project-Level Montage

## Type

AFK

## What to build

Make `clipper montage PROJECT` assemble project-owned clips into a project-owned montage. The command should no longer depend on a source/video workspace; it should use the project clip manifest and write montage artifacts directly in the project folder.

## Acceptance criteria

- [ ] `clipper montage PROJECT` reads `.clipper/projects/{project}/clips.json`.
- [ ] The command concatenates clips from `.clipper/projects/{project}/clips/`.
- [ ] The montage video is written to `.clipper/projects/{project}/montage.mp4`.
- [ ] The montage manifest is written to `.clipper/projects/{project}/montage.json`.
- [ ] `--min-duration`, `--max-duration`, `--silent`, `--reuse`, and `--force` retain existing semantics.
- [ ] Montage manifest paths are project-relative and schema-valid.
- [ ] Tests cover project montage creation, max-duration trimming, reuse, and failure cleanup.

## Blocked by

- plans/issues/034-project-level-cutting.md
