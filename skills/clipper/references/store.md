# Artifact Store

Clipper writes artifacts to a project-local store. The default store is `.clipper/` relative to the current working directory.

```text
.clipper/
  sources/{source}/
    source.{ext}
    metadata.json
    transcript.json
    sentences.json
    shots.json
    frames/shot-0001.jpg
    visual-index.json
    shot-contact-sheet.jpg
  projects/{project}/
    project.json
    scores.json
    clips.json
    clip-order.json
    contact-sheet.jpg
    previews/clip-0001.jpg
    clips/clip-0001.mp4
    montage.mp4
    montage.json
```

A Clipper **source** is reusable media/evidence. A Clipper **project** is an editorial assembly that references one or more sources and owns scoring, cutting, ordering, review, trimming, and montage outputs.

`clip-order.json` is the canonical editable order for LLM/user montage workflows. Agents should modify it with `clipper order`; do not create obsolete `candidate-order.json` sidecars.

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
uv run clipper transcribe my-source --reuse
uv run clipper score my-project --with-transcript --directive "Find strong moments" --force
uv run clipper contact-sheet my-project --force
uv run clipper trim my-project clip-0001 --duration 8 --force
```

- `--reuse` validates and uses existing target artifacts when supported.
- `--force` overwrites target artifacts when supported.
- Do not pass both together.

## Discover workspaces

```bash
uv run clipper list
uv run clipper list --json
```

When multiple projects or sources exist, pass the source/project name explicitly in non-interactive or JSON workflows.
