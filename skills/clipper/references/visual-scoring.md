# Visual scoring prerequisites

Visual scoring uses cached shot and vision artifacts, then `clipper score --with-visuals`. It is useful for silent b-roll, scenic shots, kinetic moments, or multimodal scoring.

Prerequisites:

```bash
uv run clipper doctor --json
uv run clipper shots broll --contact-sheet
uv run clipper visual broll
```

Artifacts:

- `work/shots.json` from `clipper shots`
- `work/frames/shot-0001.jpg` and related representative frames
- `work/visual-index.json` from `clipper visual`
- optional `output/shot-contact-sheet.jpg` when `--contact-sheet` is used

Visual-only scoring:

```bash
uv run clipper score broll \
  --with-visuals \
  --directive "Find scenic, kinetic, or visually striking silent shots"
```

Combined transcript and visual scoring:

```bash
uv run clipper score interview \
  --with-transcript --with-visuals \
  --directive "Find moments where expressive visuals strengthen the spoken point"
```

Rerun visual prerequisites explicitly when artifacts are stale:

```bash
uv run clipper shots broll --force --contact-sheet
uv run clipper visual broll --force
uv run clipper score broll --with-visuals --directive "Find strong visual moments" --force
```

Do not invent multi-video hero/background commands. Compose primitive commands per video; detailed multi-video recipes are deferred to a separate workflow skill.
