# Artifact Store

Clipper writes artifacts to a project-local store. The default store is `.clipper/` relative to the current working directory.

```text
.clipper/{video}/
  source/source.{ext}
  work/metadata.json
  work/transcript.json
  work/sentences.json
  work/scores.json
  work/shots.json
  work/frames/shot-0001.jpg
  work/visual-index.json
  work/clips.json
  work/pipeline.json
  clips/clip-0001.mp4
  output/montage.mp4
  output/montage.json
```

A Clipper "video" is the named workspace rooted at `.clipper/{video}/`.

## Selecting a store

Prefer the default unless the user explicitly needs another store:

```bash
uv run clipper list --json
uv run clipper list --store /path/to/artifact-store --json
CLIPPER_STORE_PATH=/path/to/artifact-store uv run clipper list --json
```

Use the same `--store` value for every command in a workflow.

## Re-run policy

Most artifact-producing commands fail if their target output already exists. Choose explicitly:

```bash
uv run clipper transcribe my-video --reuse
uv run clipper score my-video --with-transcript --directive "Find strong moments" --force
```

- `--reuse` validates and uses existing target artifacts.
- `--force` overwrites target artifacts.
- Do not pass both together.

## Discover workspaces

```bash
uv run clipper list
uv run clipper list --json
```

When multiple videos exist, pass `[VIDEO]` explicitly in non-interactive or JSON workflows.
