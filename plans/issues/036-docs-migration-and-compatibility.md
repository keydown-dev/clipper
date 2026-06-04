# Issue 036 — Docs, Migration, and Compatibility

## Type

AFK

## What to build

Update documentation, examples, and compatibility behavior for the source/project architecture. The old one-folder video workflow should either continue through compatibility aliases or fail with clear migration guidance. The README and skill references should teach the new lifecycle: source ingestion and analysis first, then project creation, inclusion, scoring, cutting, and montage.

Final intended workflow:

```bash
clipper source "https://www.youtube.com/watch?v=rSCi5O9tLxQ" --name beau-nowak
clipper transcribe beau-nowak
clipper shots beau-nowak --contact-sheet
clipper visual beau-nowak

clipper create nowak-vs-floyd
clipper include nowak-vs-floyd beau-nowak --start 86:00 --end 92:00

clipper score nowak-vs-floyd --with-transcript --with-visuals --directive "Create a coherent one-minute narrative montage..."
clipper cut nowak-vs-floyd --min-score 6
clipper montage nowak-vs-floyd --max-duration 60
```

## Acceptance criteria

- [ ] README command references describe sources and projects as separate concepts.
- [ ] Artifact store documentation shows flattened source folders and project folders.
- [ ] Existing references to `start` explain that `source` is the preferred command and `start` is a deprecated alias.
- [ ] Examples cover single-source and multi-source projects.
- [ ] Error messages for old or ambiguous paths direct users to the new source/project commands.
- [ ] Full test suite passes after documentation and compatibility updates.

## Blocked by

- plans/issues/029-source-command-ingestion.md
- plans/issues/030-source-analysis-commands.md
- plans/issues/031-create-empty-project.md
- plans/issues/032-include-source-in-project.md
- plans/issues/033-project-level-scoring.md
- plans/issues/034-project-level-cutting.md
- plans/issues/035-project-level-montage.md
