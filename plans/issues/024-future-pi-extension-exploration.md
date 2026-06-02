# Issue 024 — Future Pi Extension Exploration

## Goal

Explore and document whether/when Clipper should add a Pi extension after the skills-only package, especially for typed CLI wrappers, progress UI, custom rendering, and TUI artifact previews.

This issue is exploratory/design-oriented unless explicitly expanded later. Do not implement extension tools in the first pass unless the issue is amended.

## Depends On

- Issue 020 for the initial skills-only Pi package
- ADR 0002 for the decision to defer Pi-specific tools

## Tasks

- Review Pi extension capabilities relevant to Clipper: custom tools, command wrappers, status/progress UI, custom renderers, custom TUI components.
- Identify which Clipper CLI behaviors would need improvement to support good progress bars or previews.
- Propose a minimal typed-tool set, if any, such as wrappers around `doctor`, `start`, `transcribe`, `score`, `cut`, and `montage`.
- Propose how progress should be surfaced without breaking JSON stdout contracts.
- Consider artifact preview affordances for transcripts, shots, clips, and montage outputs.
- Record recommendation: keep deferred, implement now, or split into concrete follow-up issues.

## Acceptance Criteria

- A design note or amended issue explains whether Pi extension tools are worth building next.
- No business logic is proposed inside the extension; Clipper Core remains authoritative.
- Any proposed tools are thin wrappers over the CLI Contract.
- Progress/UI ideas preserve machine-readable CLI behavior.
