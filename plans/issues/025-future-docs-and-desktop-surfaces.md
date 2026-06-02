# Issue 025 — Future Docs Site and Desktop Surface Roadmap

## Goal

Create a lightweight roadmap for future non-Pi surfaces: an Astro documentation/marketing site and a Tauri desktop app. This issue should preserve architectural intent without forcing immediate scaffolding.

## Depends On

- ADR 0002 for the core-first monorepo surfaces decision

## Tasks

- Document intended future surface layout under `apps/docs-site/` and `apps/desktop/`.
- Define the first useful Astro site scope: human docs, examples, install instructions, workflow recipes.
- Define the first useful Tauri app scope: read-only Artifact Store browser for transcripts, shots, scores, clips, and montages.
- Document that the Tauri app should consume the CLI Contract and Artifact Store before becoming an interactive editor/orchestrator.
- Identify what additional CLI/artifact contracts Tauri might need later, such as progress events, cancellation, artifact indexes, or preview thumbnails.
- Decide whether to create placeholder folders now or defer scaffolding until implementation begins.

## Acceptance Criteria

- Roadmap clearly states that neither Astro nor Tauri owns Clipper behavior.
- First Tauri milestone is read-only artifact visualization.
- Interactive desktop editing/orchestration is explicitly later.
- No substantial app implementation is required unless this issue is amended.

## Roadmap Note — Future Surfaces

Clipper should preserve room for two future non-Pi surfaces without creating them yet:

```text
apps/docs-site/   # future Astro documentation and marketing site
apps/desktop/     # future Tauri desktop artifact browser, editor later
```

Neither surface owns Clipper behavior. Clipper Core remains the source of truth for media processing, workflow semantics, command behavior, artifact schemas, and compatibility guarantees. Both surfaces should consume the **CLI Contract** and the project-local Artifact Store rather than importing or duplicating Python workflow logic.

### Astro docs site scope

The first useful `apps/docs-site/` milestone should be a lightweight static Astro site focused on helping humans understand and operate Clipper:

- Product/marketing overview: what Clipper does, supported workflows, and expected inputs/outputs.
- Install instructions for the supported CLI/package path.
- Command reference derived from or checked against the CLI Contract.
- Workflow recipes for common jobs such as transcript QA, dialogue-driven clips, hero background montages, and batch/topic-oriented review.
- Examples of Artifact Store outputs, including transcripts, sentences, shots, scores, clips, and montages.
- Links to the Pi skill package and any future extension surface, while explaining that those are orchestration/documentation layers over Clipper Core.

The docs site should not become a separate behavior specification. When documentation and CLI behavior diverge, Clipper Core tests and CLI contract documentation win; the site should be updated.

### Tauri desktop scope

The first useful `apps/desktop/` milestone should be a **read-only Artifact Store browser**. It should make existing Clipper runs easier to inspect without changing how artifacts are produced:

- Open a project-local `.clipper/` store or an explicit store selected by the user.
- List videos/runs and show available artifacts: transcripts, sentence artifacts, shot data, frame/visual analysis, scores, clips, and montages.
- Preview transcript text with timestamps, top scored moments, shot/contact-sheet references, clip paths, and montage outputs.
- Surface CLI-produced warnings/errors and artifact metadata in human-readable form.
- Launch or reveal media/artifact files using platform affordances where practical.

This first milestone should not edit timelines, select new clips, mutate artifacts, or orchestrate long-running workflows. Interactive desktop editing and orchestration are explicitly later milestones after the Artifact Store and CLI Contract are stable enough for a GUI consumer.

### Later desktop capabilities

After the read-only browser proves useful, later Tauri work may add controlled interaction through the CLI Contract only:

- Run core commands such as `doctor`, `start`, `transcribe`, `score`, `cut`, and `montage` as child processes.
- Display structured progress and support cancellation for long-running commands.
- Let users adjust scoring directives or cut thresholds, then re-run commands through the CLI instead of editing private state.
- Compare artifact versions/runs when the Artifact Store supports stable indexes or run metadata.
- Add timeline/editor affordances only once Clipper Core exposes safe contracts for the required operations.

Tauri should remain an Artifact Store visualizer/orchestrator, not an independent editor that reimplements segmentation, scoring, cutting, or montage logic.

### Additional contracts likely needed

Before a rich desktop app or docs examples can depend on them, Clipper Core should consider formalizing:

- Structured progress events on stderr, for example JSONL events with phase, percent, message, counters, and artifact paths.
- Cancellation semantics for child CLI processes, including how partial artifacts are marked or cleaned up.
- A stable Artifact Store index listing videos, runs, artifact paths, timestamps, schema versions, and warnings.
- Preview-friendly artifact summaries for transcripts, sentences, shots, scores, clips, and montages.
- Thumbnail/contact-sheet conventions for visual artifacts and clip/montage previews.
- Contract tests for JSON stdout envelopes, stderr diagnostics/progress, artifact schemas, and backward-compatible schema evolution.

These contracts should be implemented in Clipper Core before Tauri relies on them.

### Scaffolding decision

Defer placeholder folders for `apps/docs-site/` and `apps/desktop/` until implementation begins. The ADR already records the intended monorepo layout, and empty folders would add churn without improving current CLI, skill, or documentation workflows. When either surface starts, create the folder with a real minimal app, README, package metadata, and contract-focused tests or smoke checks in the same change.
