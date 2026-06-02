# Handoff Out

## Summary

Completed Issue 019 by adding a reusable, agent-agnostic Clipper skill at `skills/clipper/`. The root skill explains Clipper, routes agents through doctor/readiness checks, describes the project-local `.clipper/` Artifact Store, and points to focused reference docs instead of embedding all workflow details.

Added reference documentation with copy/pasteable CLI examples for install/readiness, doctor, Artifact Store, start, transcribe, transcript scoring, visual scoring prerequisites, cut, montage, and troubleshooting.

## Changed files

- `skills/clipper/SKILL.md`
- `skills/clipper/references/install.md`
- `skills/clipper/references/doctor.md`
- `skills/clipper/references/store.md`
- `skills/clipper/references/start.md`
- `skills/clipper/references/transcribe.md`
- `skills/clipper/references/transcript-scoring.md`
- `skills/clipper/references/visual-scoring.md`
- `skills/clipper/references/cut.md`
- `skills/clipper/references/montage.md`
- `skills/clipper/references/troubleshooting.md`

## Commit subject

feat: Add reusable Clipper agent skill

## Decisions

- Kept `SKILL.md` concise and used `references/` for detailed workflows.
- Used CLI examples that match the current parser/help, including explicit `--with-transcript` and `--with-visuals` scoring flags.
- Avoided Pi-specific tooling assumptions; docs refer to Agent Skills-compatible loading and the Clipper CLI contract.
- Deferred transcript QA/summarization and multi-video hero-background recipes as requested by the issue.

## Risks

- The skill frontmatter is intentionally minimal (`name` and `description`) for broad Agent Skills compatibility; future packaging surfaces may require extra metadata.
- Reference docs are CLI-contract documentation only and do not add automated schema validation for skill files.

## Verification

See `verification.md`. Final verification passed with `uv run python` checks and CLI help checks for scoring context flags.

## Next suggested task

Proceed to the next planned issue in the loop; do not expand this iteration into Pi packaging or specialized workflow recipes.
