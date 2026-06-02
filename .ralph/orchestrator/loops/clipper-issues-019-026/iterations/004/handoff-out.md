# Handoff out

## Summary

Completed Issue 022 documentation for transcript-only QA and summarization workflows.

Added a dedicated Clipper skill reference that explains:

- Minimal `doctor` + `start` + `transcribe` workflow for local and YouTube/remote inputs.
- When to stop after transcription instead of running scoring/cutting/montage commands.
- Why agents should prefer `work/sentences.json` for readable timestamped context.
- When `work/transcript.json` is useful for raw segment and word-level traceability.
- Expected artifact paths and JSON fields.
- Agent-grounding rules, including not inventing transcript content and citing timestamps.
- Example prompts for summary, quiz generation, glossary extraction, and topic outlines using the agent's own model context.

## Changed files

- `skills/clipper/references/transcript-qa.md` — new transcript QA/summarization guidance.
- `skills/clipper/SKILL.md` — linked the new reference and added a minimal transcript-only flow.
- `skills/clipper/references/transcribe.md` — clarified `sentences.json` use for QA/summarization and `transcript.json` traceability.
- `skills/clipper/references/transcript-scoring.md` — pointed non-clip transcript tasks to the agent-context QA workflow instead of `clipper score`.

## Commit subject

feat: Document transcript QA workflow

## Decisions

- Kept this as documentation-only skill guidance.
- Did not add a `transcript-qa` CLI command.
- Did not introduce external LLM CLI/API assumptions.
- Framed summarization and quizzing as agent-context workflows using existing Clipper artifacts.

## Risks

- No automated markdown/link checker was available or run; verification was manual diff and search based.

## Next suggested task

Proceed to Issue 023: document multi-video hero/background workflow guidance.
