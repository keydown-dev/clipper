# Issue 042 — Documentation for Editorial LLM Montage Workflow

## Type

AFK

## What to build

Document the supported Clipper-native workflow for iterative LLM/user montage editing: candidate generation, contact sheet review, order editing, trimming, and final montage render.

## Acceptance criteria

- [ ] README documents `clip-order.json` as a canonical project artifact.
- [ ] README documents `clipper order` examples: `--show`, `--reset`, full replacement, `--move`, and `--swap`.
- [ ] README documents `clipper montage --chronological` and explains that editorial order is the default.
- [ ] README documents `clipper contact-sheet PROJECT`.
- [ ] README documents `clipper trim PROJECT CLIP_ID` with `--duration`, `--start`, and `--end` examples.
- [ ] The project artifact layout section includes `clip-order.json`, `contact-sheet.jpg`, and `previews/`.
- [ ] Troubleshooting explains what to do when order references missing clips.
- [ ] The Clipper skill docs are updated so agents use Clipper commands rather than custom Python/FFmpeg scripting for this workflow.
- [ ] Manual validation flow shows a complete LLM-style editorial session.

## Suggested implementation notes

- Update `README.md`.
- Update `skills/clipper/SKILL.md` and any relevant reference files under `skills/clipper/references/` if present.
- Include concise examples using project-level commands.
- Emphasize that ad-hoc `candidate-order.json` is obsolete; `clip-order.json` is canonical.

## Blocked by

- plans/issues/037-clip-order-artifact-and-order-command.md
- plans/issues/038-montage-preserve-editorial-order.md
- plans/issues/039-order-move-swap-operations.md
- plans/issues/040-project-contact-sheet-command.md
- plans/issues/041-project-clip-trim-command.md
