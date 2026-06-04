# Issue 031 — Create Empty Project

## Type

AFK

## What to build

Add `clipper create PROJECT` to create an empty editorial project folder with a minimal `project.json`. This command should not attach sources yet and should not be interactive. Downstream project commands can later require at least one included source before scoring, cutting, or montage creation.

Initial project shape:

```json
{
  "schema_version": 1,
  "name": "project-name",
  "sources": [],
  "created_at": "2026-06-04T12:00:00Z"
}
```

## Acceptance criteria

- [ ] `clipper create PROJECT` creates `.clipper/projects/{project}/project.json`.
- [ ] The project JSON includes `schema_version`, `name`, `sources`, and `created_at`.
- [ ] `sources` starts as an empty list.
- [ ] The command fails if the project already exists unless `--force` is provided.
- [ ] JSON and human output identify the project name and config path.
- [ ] Tests cover create success, existing-project failure, and force overwrite behavior.

## Blocked by

- plans/issues/028-source-and-project-layouts.md
