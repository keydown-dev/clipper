# Handoff Out

## Summary

Completed Issue 020 by adding a skills-only Pi package for Clipper under `packages/pi-clipper/`.

The package now:

- Declares `pi-package` metadata in `package.json`.
- Exposes the packaged skill via `pi.skills: ["./skills"]`.
- Includes package metadata noting that Clipper CLI/Core must be installed separately.
- Provides `sync:skill`, `prepare`, and `prepack` scripts to generate the package-local skill copy from root `skills/clipper`.
- Includes a README with local Pi usage, source-of-truth guidance, and deferred future Pi enhancement notes.
- Contains the generated portable copy at `packages/pi-clipper/skills/clipper`.

## Changed files

- `packages/pi-clipper/package.json`
- `packages/pi-clipper/README.md`
- `packages/pi-clipper/scripts/sync-clipper-skill.mjs`
- `packages/pi-clipper/skills/clipper/SKILL.md`
- `packages/pi-clipper/skills/clipper/references/*.md`

## Commit subject

feat: Add Pi package for Clipper skill

## Decisions

- Kept the package skills-only; no Pi extension tools, commands, custom UI, renderers, or wrappers were added.
- Treated root `skills/clipper` as canonical and package-local `skills/clipper` as generated content.
- Used a small Node sync script so the package has no runtime dependencies.
- Used `prepack` and `prepare` to refresh generated skill content for packaging/local preparation.

## Risks

- The generated skill copy can drift if root skill files are edited without running `npm run sync:skill`; README documents this, and verification currently confirms no drift.
- Local Pi discovery was verified indirectly through manifest/package checks and package contents, not by launching an interactive Pi session.

## Next suggested task

Proceed to Issue 021 in the loop.
