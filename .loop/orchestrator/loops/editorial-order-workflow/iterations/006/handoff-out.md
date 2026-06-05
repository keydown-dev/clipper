# Handoff out — iteration 006

## Summary

Updated docs for Issue 042. README now documents the canonical editorial LLM montage workflow, `clip-order.json`, project review artifacts, `clipper order`, `contact-sheet`, `trim`, and `montage --chronological`. The Clipper skill now directs agents to use supported Clipper commands/artifacts instead of custom Python/FFmpeg scripting or obsolete `candidate-order.json` sidecars.

## Changed files

- `README.md`
- `skills/clipper/SKILL.md`
- `skills/clipper/references/cut.md`
- `skills/clipper/references/montage.md`
- `skills/clipper/references/store.md`
- `skills/clipper/references/troubleshooting.md`
- `packages/pi-clipper/skills/clipper/**` (regenerated packaged skill copy with `npm run sync:skill`)
- `.loop/orchestrator/loops/editorial-order-workflow/iterations/006/verification.md`
- `.loop/orchestrator/loops/editorial-order-workflow/iterations/006/handoff-out.md`

## Commit subject

Document editorial LLM montage workflow

## Decisions

- Treated `clip-order.json` as the only canonical editable order artifact and explicitly marked `candidate-order.json` obsolete.
- Documented editorial order as the default montage behavior and `--chronological` as opt-in.
- Synced the packaged Pi skill copy after editing root `skills/clipper/`, following `packages/pi-clipper/README.md` guidance.

## Risks

- Packaged skill sync also refreshed previously stale generated reference files under `packages/pi-clipper/skills/clipper/`; source skill files remain the source of truth.

## Verification

See `verification.md`. `uv run pytest` passed: 177 passed, 3 skipped.

## Next suggested task

Review the generated package skill diff and commit if acceptable.
