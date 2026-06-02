# Transcript scoring

`clipper score [VIDEO] --with-transcript` scores candidate segments from `work/sentences.json` using an OpenAI-compatible LLM.

Prerequisites:

```bash
uv run clipper doctor --json
uv run clipper transcribe interview --verbose
```

Score from transcript context:

```bash
uv run clipper score interview \
  --with-transcript \
  --directive "Find moments where hosts laugh, react strongly, or discuss surprising topics"
```

JSON output for automation:

```bash
uv run clipper score interview \
  --with-transcript \
  --directive "Find expressive reactions" \
  --json --verbose
```

`--verbose` writes progress and token usage, when available, to stderr. Stdout remains JSON when `--json` is used.

## Combined context

When visual artifacts also exist, request both contexts explicitly:

```bash
uv run clipper score interview \
  --with-transcript --with-visuals \
  --directive "Find moments where strong dialogue is reinforced by expressive visuals"
```

## Important constraints

- Do not call `clipper score VIDEO --directive "..."` without a context flag; it must fail.
- Use `--with-transcript` only after `work/sentences.json` exists.
- Use `--reuse` to keep a valid existing `work/scores.json`, or `--force` to replace it.
- Keep directives focused on selecting timestamped clip candidates. Detailed transcript QA and summarization workflows are out of scope for this skill.
