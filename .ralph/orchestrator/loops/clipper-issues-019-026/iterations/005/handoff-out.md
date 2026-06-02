# Handoff out

## Summary

Completed issue 023 documentation for multi-video hero/background workflows in the Clipper skill.

## Changed files

- `skills/clipper/references/hero-background.md` — added visual-first, silent, multi-video hero/background workflow guidance, directive examples, per-Video Artifact Store limitations, manual review handoff points, and optional external FFmpeg concat example.
- `skills/clipper/SKILL.md` — linked the new reference and clarified that multi-video hero/background work remains primitive composition across independent Video workspaces.
- `skills/clipper/references/visual-scoring.md` — pointed multi-video hero/background guidance to the new reference.

## Commit subject

feat: Document multi-video hero background workflow

## Decisions

- Kept the workflow documentation-only and avoided adding or implying any new Clipper command.
- Preserved the one-Video/one-source/one-managed-output model.
- Labeled cross-video assembly and FFmpeg concat as outside Clipper's managed Artifact Store.

## Risks

- The optional FFmpeg concat example assumes compatible normalized inputs; the doc warns users to transcode first if stream copy fails.

## Next suggested task

Proceed to the next planned issue after issue 023; no follow-up is needed for this iteration unless reviewers want wording adjustments.
