# Handoff out

## Summary

Completed issue 034 project-level cutting.

`clipper cut PROJECT` now detects when the positional argument is a project and cuts from project-owned `.clipper/projects/{project}/scores.json`. Selected segments must have valid included `source` tags, each clip is cut from that source's media file, and project clip outputs/manifests are written under `.clipper/projects/{project}/`.

## Changed files

- `clipper/cutting.py`
  - Added `cut_project` for project-owned score manifests and clip outputs.
  - Preserved `source` on merged segments and clip manifest entries.
  - Ensured project clip reuse/force/failure cleanup follows existing cut semantics.
- `clipper/cli.py`
  - Routed `clipper cut PROJECT` to project cutting when the positional name resolves to a project.
- `clipper/schemas.py`
  - Allowed optional string `source` on clip entries.
- `tests/test_issue034.py`
  - Added single-source, multi-source, and missing-source-tag project cutting coverage.

## Verification

See `verification.md`.

## Commit subject

Implement project-level cutting

## Decisions

- Kept existing `clipper cut VIDEO --project PROJECT` video-scoped behavior intact for backwards compatibility.
- Used project-root-relative clip paths like `clips/clip-0001.mp4` in project `clips.json`.
- Validated project scored segment sources against the project's included sources before cutting.

## Risks

- Project cutting depends on source `metadata.json` to resolve the actual source media filename/extension.
- If a name exists as both a legacy video and a project, `clipper cut NAME` now prefers the project when `.clipper/projects/NAME/project.json` exists, matching issue 034.

## Next suggested task

Proceed to issue 035 — Project-Level Montage.
