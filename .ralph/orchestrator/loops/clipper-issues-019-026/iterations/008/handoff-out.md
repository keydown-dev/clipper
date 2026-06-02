# Handoff Out

## Summary

Completed Issue 026 by documenting the first supported non-development CLI install path as `uv tool install git+https://github.com/keydown-dev/clipper.git`, preserving PyPI as out of scope, and recording the verified git-tool install behavior in the issue plan.

## Changed files

- `README.md` — added supported install section and clarified installed CLI smoke usage.
- `skills/clipper/references/install.md` — replaced future/install expectation language with the supported uv tool git command and limitations.
- `packages/pi-clipper/README.md` — clarified that the Pi package does not install Clipper Core and points users to the supported uv tool install path.
- `packages/pi-clipper/skills/clipper/references/install.md` — kept packaged skill install reference aligned with the canonical skill reference.
- `plans/issues/026-supported-cli-install-path.md` — added implementation/verification note for the supported install path.

## Commit subject

docs: Document supported CLI install path

## Verification performed

- `uv run pytest` — passed, 108 passed and 3 skipped.
- Isolated `uv tool install "git+file://$PWD"` plus `clipper doctor --json` from `/tmp` — passed with 11 pass, 0 warn, 0 fail.
- Confirmed root and packaged skill install references match.
- Checked git status/diff stat for bounded changes.

## Decisions

- Supported first install target is `uv tool install` from the git repository.
- PyPI publishing remains explicitly unsupported for this issue.
- FFmpeg/ffprobe, model weights, and LLM services/configuration remain external requirements not handled by Python packaging.
- Verification used a local git URL to avoid depending on remote GitHub network/auth while still validating git-based uv tool installation.

## Risks or blockers

- No blocker.
- The documented HTTPS GitHub command assumes the public repository URL remains accessible; local verification used `git+file://$PWD` because this checkout's remote is SSH-based.

## Next suggested task

Proceed to loop closeout/final verification for issues 019-026; do not start additional implementation from this worker.
