# Issue 022 — Transcript QA and Summarization Workflow Docs

## Goal

Document how agents should use Clipper transcript artifacts with the agent's own LLM context for transcript-only workflows such as summarization, quizzing, study guides, and extracting key points without cutting video.

This is documentation/skill guidance only. Do not add a `transcript-qa` CLI command, do not call Clipper's configured LLM, and do not introduce external LLM CLI/API assumptions unless a later issue establishes that need.

## Depends On

- Issue 014 for `work/sentences.json`
- Issue 019 for the reusable Clipper skill structure

## Tasks

- Add transcript QA/summarization guidance to the Clipper skill references.
- Explain when to run only `start` + `transcribe` and stop.
- Teach agents to prefer `work/sentences.json` for readable transcript context.
- Explain when `work/transcript.json` is useful for raw segment/word timing traceability.
- Provide example agent prompts for summary, quiz generation, glossary extraction, and topic outline generation using the agent's own model context.
- Avoid examples that require external LLM CLIs/APIs or new Clipper commands.
- Explain artifact paths and expected JSON fields.
- Warn agents not to invent transcript content and to cite timestamps when useful.

## Acceptance Criteria

- Docs show a minimal transcript-only workflow from YouTube/local input to usable transcript artifact.
- Docs include agent instructions for summarizing and quizzing from transcript artifacts.
- No new CLI commands are added.
- Examples use current artifact names and schemas.
