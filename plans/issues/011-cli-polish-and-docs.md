# Issue 011 — CLI Polish and Documentation

## Goal

Make the first version understandable and usable from a clean checkout.

## Depends On

- Issue 010

## Tasks

- Normalize CLI help text and option names across subcommands.
- Normalize error messages and exit codes.
- Ensure `--verbose` and `--json` behavior is consistent.
- Update README quickstart to match implemented behavior.
- Document every subcommand.
- Document directive examples and the baseline scoring prompt contract.
- Document `uv`, FFmpeg, `.env`, doctor, and troubleshooting.
- Document optional real LLM and Whisper test flags.
- Document manual local-file and URL validation flows.

## Acceptance Criteria

- README commands match implemented behavior.
- README remains the canonical implementation context for future contributors and sub-agents.
- A new user can run setup, doctor, and a local smoke flow from the docs.
- CLI smoke tests cover representative help and JSON behavior.
