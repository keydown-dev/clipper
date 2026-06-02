# Transcript QA and summarization

Use this reference when the user wants to understand, summarize, quiz, outline, or study a transcript without cutting video. This is an agent-context workflow: read Clipper transcript artifacts and use your own model context. Do not add or invoke a `transcript-qa` Clipper command, do not run `clipper score`, and do not call Clipper's configured LLM for these tasks.

## Minimal transcript-only workflow

Run only readiness, workspace creation, and transcription, then stop:

```bash
uv run clipper doctor --json
uv run clipper start ./source/interview.mp4 --name interview
uv run clipper transcribe interview --verbose
```

For YouTube or other remote inputs, use `start` with the URL only when the user expects a download:

```bash
uv run clipper doctor --json
uv run clipper start "https://youtube.com/watch?v=VIDEO_ID" --name interview-url
uv run clipper transcribe interview-url --verbose
```

Use `clipper ...` instead of `uv run clipper ...` when Clipper is installed and available on `PATH`. If targeting a non-default Artifact Store, pass the same `--store PATH` to every command or set `CLIPPER_STORE_PATH=PATH`.

Stop after `transcribe` when the task is summary, quiz, study guide, glossary, topic outline, quote lookup, or transcript review. Continue to `score`, `cut`, or `montage` only when the user asks for timestamped clip candidates or rendered video.

## Artifact paths

By default, artifacts are under `.clipper/{video}/`:

- `.clipper/{video}/work/sentences.json` — preferred readable transcript context.
- `.clipper/{video}/work/transcript.json` — raw faster-whisper transcript with segment and word timing details.

When a custom store is used, replace `.clipper/` with that store path.

## Preferred context: work/sentences.json

Prefer `work/sentences.json` for transcript QA because it groups text into complete, readable sentences while preserving timestamps and traceability. Expected fields include:

- `schema_version`
- `source_file`
- `language`
- `duration`
- `source_transcript_path` — usually `work/transcript.json`
- `sentences[]`
  - `id`
  - `start` and `end` in seconds
  - `text`
  - `source_segments[]`
  - `word_ranges[]` with `segment_id`, `start_word_index`, and `end_word_index`

For long transcripts, load or quote bounded ranges of sentences rather than pasting the entire artifact if it will exceed context. Keep timestamps with each excerpt.

## Raw traceability: work/transcript.json

Use `work/transcript.json` when you need lower-level traceability, segment boundaries, or word-level timings. Expected fields include:

- `schema_version`
- `source_file`
- `language`
- `duration`
- `segments[]`
  - `id`
  - `start` and `end` in seconds
  - `text`
  - `words[]` with `word`, `start`, and `end`

If `work/sentences.json` is missing because an older transcript lacks word timings, rerun transcription with `--force` when appropriate:

```bash
uv run clipper transcribe interview --force --verbose
```

## Agent instructions

- Base answers only on transcript artifact content supplied or read from the workspace.
- Do not invent quotes, topics, claims, speaker names, or chronology that are not present in the transcript.
- Say when the transcript does not contain enough evidence.
- Cite timestamps when useful, especially for quotes, key points, quiz answers, or claims the user may want to review.
- Prefer sentence timestamps from `work/sentences.json`; use raw word timings from `work/transcript.json` only when exact word-level evidence matters.
- Clearly distinguish transcript-grounded facts from your own synthesis.

## Example prompts for the agent's own model context

Summary:

```text
Using only the provided Clipper sentence transcript, write a concise summary.
Include 5-8 bullet key points with timestamps for the most important moments.
Do not add facts that are not in the transcript. If something is unclear, say so.
```

Quiz generation:

```text
Using only the provided Clipper sentence transcript, create 10 study questions.
Mix recall, chronology, and concept questions. Include an answer key with supporting timestamps.
Do not ask questions that require knowledge outside the transcript.
```

Glossary extraction:

```text
Using only the provided Clipper sentence transcript, extract domain terms, names, acronyms, and recurring concepts.
For each entry, provide a transcript-grounded definition or context note plus one timestamped occurrence.
If the transcript uses a term but does not define it, label the definition as inferred from local context.
```

Topic outline:

```text
Using only the provided Clipper sentence transcript, produce a chronological topic outline.
For each topic, include start/end timestamps, a short heading, and 1-3 supporting bullets.
Do not merge unrelated topics just to make the outline shorter.
```
