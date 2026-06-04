# Issue 032 — Include Source in Project

## Type

AFK

## What to build

Add an `include` command that attaches a source and optional time range to a project. This replaces the proposed `add-source` wording with editorial language: a project includes source evidence. The command updates the project config; later commands read only the project config to know which sources and ranges to use.

Command shape:

```bash
clipper include PROJECT SOURCE [--start TIME] [--end TIME]
```

Project JSON example:

```json
{
  "schema_version": 1,
  "name": "nowak-vs-floyd",
  "sources": [
    {
      "name": "breakfast-beau-nowak",
      "start": 5160,
      "end": 5520
    }
  ],
  "created_at": "2026-06-04T12:00:00Z"
}
```

## Acceptance criteria

- [ ] `clipper include PROJECT SOURCE` validates that both project and source exist.
- [ ] `--start` and `--end` accept seconds, `MM:SS`, and `HH:MM:SS`.
- [ ] If both range endpoints are present, `end` must be greater than `start`.
- [ ] The command appends or updates the matching source entry in `project.json` deterministically.
- [ ] A project can include more than one source.
- [ ] JSON and human output show the updated source list.
- [ ] Tests cover whole-source includes, ranged includes, invalid ranges, missing projects, and missing sources.

## Blocked by

- plans/issues/028-source-and-project-layouts.md
- plans/issues/031-create-empty-project.md
