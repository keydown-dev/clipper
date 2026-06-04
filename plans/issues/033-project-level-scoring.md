# Issue 033 — Project-Level Scoring

## Type

AFK

## What to build

Make `clipper score PROJECT` operate on a project instead of a single source/video workspace. Scoring should load `.clipper/projects/{project}/project.json`, require at least one included source, gather transcript and/or visual evidence from each included source, apply each source's optional time range, and write project-owned `scores.json`.

Every scored segment must identify its source so cutting can resolve the correct media file later.

Example scored segment:

```json
{
  "source": "breakfast-beau-nowak",
  "start": 5162.0,
  "end": 5177.0,
  "score": 9,
  "reason": "The host contrasts immediate George Floyd outrage with silence after Henry Nowak."
}
```

## Acceptance criteria

- [ ] `clipper score PROJECT --with-transcript`, `--with-visuals`, or both reads included sources from project config.
- [ ] The command fails clearly when the project has no included sources.
- [ ] Source transcript evidence is loaded from flattened source artifacts and filtered by the source's configured time range.
- [ ] Source visual evidence is loaded from flattened source artifacts and filtered by the source's configured time range.
- [ ] Multi-source evidence can be combined into a single scoring context.
- [ ] `scores.json` is written to `.clipper/projects/{project}/scores.json`.
- [ ] Each scored segment includes a valid `source` field.
- [ ] Tests cover single-source ranged scoring and multi-source source-tagged scoring with a fake LLM.

## Blocked by

- plans/issues/030-source-analysis-commands.md
- plans/issues/032-include-source-in-project.md
