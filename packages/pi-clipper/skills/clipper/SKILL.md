---
name: clipper
description: Use when working with Clipper, a local-first Python CLI for source videos, transcripts, scored clips, visual shot analysis, cuts, clip ordering, contact sheets, trims, and montages.
---

# Clipper

Clipper is a local-first Python CLI for turning source videos or podcasts into transcripts, scored clip candidates, cut clips, editorial orders, review sheets, trims, and montages. Operate it through the `clipper` CLI contract and project-local Artifact Store; do not import internal Python modules or write custom Python/FFmpeg scripts for supported workflows.

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
- A reusable source lives at `.clipper/sources/{source}/`.
- An editorial project lives at `.clipper/projects/{project}/` and owns `scores.json`, `clips.json`, canonical `clip-order.json`, `contact-sheet.jpg`, `previews/`, `montage.mp4`, and `montage.json`.
- `clip-order.json` is the canonical editable montage order. Do not create or maintain obsolete ad-hoc files such as `candidate-order.json`.
- Use `--store PATH` or `CLIPPER_STORE_PATH=PATH` only when the workflow must target a non-default store.
- Prefer project-level primitive command composition (`source`, `transcribe`, `shots`, `visual`, `create`, `include`, `score`, `cut`, `contact-sheet`, `order`, `trim`, `montage`) over bespoke workflow commands or hand-written media scripts.
- Do not assume transcript scoring context: `score` requires `--with-transcript`, `--with-visuals`, or both.
- `clipper montage PROJECT` preserves editorial order by default; pass `--chronological` only when the user explicitly wants source-time order.

## Reference workflows

Read only the references needed for the task:

- [Install and readiness](references/install.md)
- [Doctor](references/doctor.md)
- [Artifact Store](references/store.md)
- [Start/source videos](references/start.md)
- [Transcribe](references/transcribe.md)
- [Transcript scoring](references/transcript-scoring.md)
- [Transcript QA and summarization](references/transcript-qa.md)
- [Visual scoring prerequisites](references/visual-scoring.md)
- [Multi-video hero/background workflows](references/hero-background.md)
- [Cut clips](references/cut.md)
- [Montage and editorial order](references/montage.md)
- [Troubleshooting](references/troubleshooting.md)

## Minimal project flow

Transcript-based clips:

```bash
uv run clipper doctor --json
uv run clipper source ./source/interview.mp4 --name interview
uv run clipper transcribe interview --verbose
uv run clipper create interview-highlights
uv run clipper include interview-highlights interview
uv run clipper score interview-highlights --with-transcript \
  --directive "Find surprising or emotionally expressive sound bites"
uv run clipper cut interview-highlights --min-score 6
uv run clipper montage interview-highlights --max-duration 60
```

Visual-only montage candidates:

```bash
uv run clipper doctor --json
uv run clipper source ./source/broll.mp4 --name broll
uv run clipper shots broll --contact-sheet
uv run clipper visual broll
uv run clipper create broll-selects
uv run clipper include broll-selects broll
uv run clipper score broll-selects --with-visuals \
  --directive "Find scenic, kinetic, or visually striking silent shots"
uv run clipper cut broll-selects --min-score 6 --silent
uv run clipper montage broll-selects --max-duration 45 --silent
```

Combined transcript and visual scoring:

```bash
uv run clipper score interview-highlights --with-transcript --with-visuals \
  --directive "Find moments where strong dialogue is reinforced by expressive visuals"
```

## LLM-assisted editorial review loop

For iterative montage editing, use Clipper commands and artifacts instead of custom scripts:

```bash
uv run clipper contact-sheet interview-highlights
uv run clipper order interview-highlights --show
uv run clipper order interview-highlights clip-0003 clip-0001 clip-0002
uv run clipper order interview-highlights --move clip-0002 --to 1
uv run clipper order interview-highlights --swap clip-0001 clip-0003
uv run clipper trim interview-highlights clip-0002 --duration 8 --force
uv run clipper trim interview-highlights clip-0003 --start 01:12 --end 01:20 --force
uv run clipper montage interview-highlights --max-duration 60
```

Use `contact-sheet.jpg` and `previews/` for visual review. Use `clipper order --reset` when the order should return to the current `clips.json` sequence. Use `clipper montage PROJECT --chronological` only for source-time renders; editorial order is the default.

Transcript-only QA/summarization:

```bash
uv run clipper doctor --json
uv run clipper source ./source/interview.mp4 --name interview
uv run clipper transcribe interview --verbose
# Stop here. Read .clipper/sources/interview/sentences.json into the agent's own context.
```

Use this flow for summaries, quizzes, study guides, glossary extraction, and topic outlines. Prefer `sentences.json` for readable timestamped context; use `transcript.json` only when raw segment or word timing traceability is needed. Do not invent a `transcript-qa` command or call Clipper's configured LLM for transcript-only QA.
