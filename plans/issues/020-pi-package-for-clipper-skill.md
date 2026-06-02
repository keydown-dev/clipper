# Issue 020 — Pi Package for Clipper Skill

## Goal

Create a Pi package that distributes the reusable root Clipper skill. The first package version should be skills-only: no extension tools, commands, custom TUI, or renderers yet.

## Depends On

- Issue 019 for the reusable `skills/clipper` skill
- ADR 0002 for the decision to start with skills-only Pi integration

## Proposed Location

```text
packages/pi-clipper/
  package.json
```

The root `skills/clipper` directory is the source of truth. For package portability, the Pi package should include a copied/generated copy under the package during packaging or preparation, not manually maintain divergent duplicate content.

## Tasks

- Create `packages/pi-clipper/package.json` with `pi-package` metadata.
- Add a packaging/preparation step that copies root `skills/clipper` into `packages/pi-clipper/skills/clipper` for a portable Pi package.
- Configure the `pi.skills` manifest entry to load the packaged skill copy.
- Document that root `skills/clipper` remains the source of truth and the package copy is generated/updated from it.
- Keep the initial package skills-only.
- Add README or package notes showing local install/use with Pi.
- Document that future Pi-specific enhancements may include typed tools, progress UI, custom renderers, or TUI previews, but are intentionally deferred.

## Acceptance Criteria

- Pi can discover the Clipper skill when the package is installed or loaded locally.
- There is one source of truth for skill content: root `skills/clipper`.
- The Pi package can be installed or loaded without relying on `../../skills/clipper` existing beside it.
- Package metadata makes clear that the package requires Clipper CLI/Core to be installed separately.
- No Pi extension tools are added in this issue.
