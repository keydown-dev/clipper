---
name: clipper
description: Use when working with Clipper, a local-first Python CLI for source videos, transcripts, scored clips, visual shot analysis, cuts, and montages.
---

# Clipper

Clipper is a local-first Python CLI for turning source videos or podcasts into transcripts, scored clip candidates, cut clips, and montages. It is operated through the `clipper` CLI contract and a project-local Artifact Store, not by importing internal Python modules.

## Route first

On an unknown system, verify readiness before expensive media, Whisper, LLM, or download work:

```bash
clipper doctor --json
# or, in a source checkout
uv run clipper doctor --json
```

Use `uv run clipper ...` inside a Clipper checkout that has not installed the `clipper` entry point globally. Use `clipper ...` when the CLI is already installed and on `PATH`.

## Core concepts

- The default Artifact Store is project-local `.clipper/`.
- A video workspace lives at `.clipper/{video}/` with `source/`, `work/`, `clips/`, and `output/` subdirectories.
- Use `--store PATH` or `CLIPPER_STORE_PATH=PATH` only when the workflow must target a non-default store.
- Commands that operate on an existing video accept `[VIDEO]` as either a video name or a video directory path.
- Prefer primitive command composition (`start`, `transcribe`, `shots`, `visual`, `score`, `cut`, `montage`) over inventing bespoke workflow commands.
- Do not assume transcript scoring context: `score` requires `--with-transcript`, `--with-visuals`, or both.

## Reference workflows

Read only the references needed for the task:

- [Install and readiness](references/install.md)
- [Doctor](references/doctor.md)
- [Artifact Store](references/store.md)
- [Start videos](references/start.md)
- [Transcribe](references/transcribe.md)
- [Transcript scoring](references/transcript-scoring.md)
- [Transcript QA and summarization](references/transcript-qa.md)
- [Visual scoring prerequisites](references/visual-scoring.md)
- [Multi-video hero/background workflows](references/hero-background.md)
- [Cut clips](references/cut.md)
- [Montage](references/montage.md)
- [Troubleshooting](references/troubleshooting.md)

## Minimal composed flows

Transcript-based clips:

```bash
uv run clipper doctor --json
uv run clipper start ./source/interview.mp4 --name interview
uv run clipper transcribe interview --verbose
uv run clipper score interview --with-transcript --directive "Find surprising or emotionally expressive sound bites"
uv run clipper cut interview --min-score 6
uv run clipper montage interview --max-duration 60
```

Visual-only montage candidates:

```bash
uv run clipper doctor --json
uv run clipper start ./source/broll.mp4 --name broll
uv run clipper shots broll --contact-sheet
uv run clipper visual broll
uv run clipper score broll --with-visuals --directive "Find scenic, kinetic, or visually striking silent shots"
uv run clipper cut broll --min-score 6 --silent
uv run clipper montage broll --max-duration 45 --silent
```

Combined transcript and visual scoring:

```bash
uv run clipper score interview --with-transcript --with-visuals \
  --directive "Find moments where strong dialogue is reinforced by expressive visuals"
```

Transcript-only QA/summarization:

```bash
uv run clipper doctor --json
uv run clipper start ./source/interview.mp4 --name interview
uv run clipper transcribe interview --verbose
# Stop here. Read .clipper/interview/work/sentences.json into the agent's own context.
```

Use this flow for summaries, quizzes, study guides, glossary extraction, and topic outlines. Prefer `work/sentences.json` for readable timestamped context; use `work/transcript.json` only when raw segment or word timing traceability is needed. Do not invent a `transcript-qa` command or call Clipper's configured LLM for transcript-only QA.

For multi-video hero/background work, use the detailed reference workflow. Keep it as primitive command composition across independent Video workspaces; do not invent cross-video Clipper artifacts or bespoke workflow commands.
