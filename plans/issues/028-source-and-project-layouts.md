# Issue 028 — Source and Project Layouts

## Type

AFK

## What to build

Introduce first-class source and project artifact layouts while keeping the existing video layout available during migration. A source is exactly one reusable media asset plus flattened analysis artifacts. A project is an editorial workspace that references one or more sources and owns scoring, clip, and montage outputs.

Clarification: a source and a project may reuse the same slug safely because they live in separate namespaces, e.g. `.clipper/sources/foo/` and `.clipper/projects/foo/`. They do not literally share one folder in the proposed structure; the separation prevents source analysis artifacts and editorial outputs from colliding.

Target layout:

```text
.clipper/
  sources/
    source-name/
      source.webm
      metadata.json
      transcript.json
      sentences.json
      shots.json
      visual-index.json
      shot-contact-sheet.jpg
      frames/

  projects/
    project-name/
      project.json
      scores.json
      clips.json
      montage.mp4
      montage.json
      clips/
```

## Acceptance criteria

- [ ] The codebase exposes source layout resolution for `.clipper/sources/{source}/` with flattened artifact paths.
- [ ] The codebase exposes project layout resolution for `.clipper/projects/{project}/` with project-owned editorial outputs.
- [ ] Source/project names use the existing slug-safe validation rules.
- [ ] Existing video layout behavior remains available for compatibility while later issues migrate commands.
- [ ] Tests cover source and project layout path generation, including same-slug source/project coexistence.

## Blocked by

None - can start immediately
