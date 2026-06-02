# Issue 023 — Multi-Video Hero Background Workflow Docs

## Goal

Document how agents should compose primitive Clipper commands to create visual-first, often silent, background clips and montages while preserving Clipper's clean model: one Video owns one source and one set of managed outputs.

This is workflow guidance only. Do not add `hero-montage`, cross-video montage artifacts, or other bespoke workflow commands. Multi-video hero work should be agent-guided composition across outputs from multiple Videos, outside Clipper's first-class artifact model for now.

## Depends On

- Issue 017 for visual frame analysis
- Issue 018 for `--with-visuals` scoring
- Issue 019 for the reusable Clipper skill structure

## Tasks

- Add hero/background montage guidance to the Clipper skill references.
- Explain visual-first workflow: `start`, `shots`, `visual`, `score --with-visuals`, `cut --silent`, `montage --silent`.
- Provide directive-writing guidance for calm, aesthetic, loop-friendly, non-dialogue-dependent footage.
- Explain how to repeat the primitive workflow for multiple Videos in a project-local Artifact Store, potentially with different directives per Video.
- Document that each Video has its own clips and montage outputs; Clipper does not currently create a first-class cross-video montage artifact.
- Teach agents to stop at `clips/` or per-Video `output/montage.mp4` when appropriate, then enter a more manual user-guided review/editing process across outputs from multiple Videos.
- Optionally include an external FFmpeg concat example for normalized per-Video montages, clearly labeled as outside Clipper's managed Artifact Store.

## Acceptance Criteria

- Docs teach the visual-first scoring path using implemented commands.
- Docs do not imply unsupported cross-video montage behavior or cross-video managed artifacts.
- Docs preserve the model that one Video owns one source and one set of Clipper-managed outputs.
- Silent output examples use `--silent` on cut and montage.
- Multi-video limitations and manual/agent workarounds are explicit.
