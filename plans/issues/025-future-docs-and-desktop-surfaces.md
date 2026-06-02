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
