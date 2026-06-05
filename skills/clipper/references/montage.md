# Montage and editorial order

`clipper montage PROJECT` assembles project clips into `.clipper/projects/{project}/montage.mp4` and writes `montage.json`.

Prerequisites:

```bash
uv run clipper cut interview-highlights --min-score 6
```

By default, montage preserves the canonical editorial order in `clip-order.json`:

```bash
uv run clipper montage interview-highlights
```

Render in source/start/end time order only when explicitly requested:

```bash
uv run clipper montage interview-highlights --chronological
```

Limit duration:

```bash
uv run clipper montage interview-highlights --max-duration 60
```

Require a minimum duration:

```bash
uv run clipper montage interview-highlights --min-duration 30
```

Silent visual montage:

```bash
uv run clipper montage broll-selects --max-duration 45 --silent
```

Automation and reruns:

```bash
uv run clipper montage interview-highlights --json
uv run clipper montage interview-highlights --reuse
uv run clipper montage interview-highlights --force
```

## Review and order before rendering

Use Clipper commands instead of custom Python/FFmpeg scripting:

```bash
uv run clipper contact-sheet interview-highlights
uv run clipper order interview-highlights --show
uv run clipper order interview-highlights --reset
uv run clipper order interview-highlights clip-0003 clip-0001 clip-0002
uv run clipper order interview-highlights --move clip-0002 --to 1
uv run clipper order interview-highlights --swap clip-0001 clip-0003
```

Use `clipper trim PROJECT CLIP_ID` for clip-level timing edits before the final montage:

```bash
uv run clipper trim interview-highlights clip-0001 --duration 7 --force
uv run clipper trim interview-highlights clip-0001 --start 42.5 --force
uv run clipper trim interview-highlights clip-0001 --end 00:55 --force
uv run clipper trim interview-highlights clip-0001 --start 00:42 --end 00:55 --force
```

Montage uses `clips.json` for clip metadata and `clip-order.json` for order. Score filtering belongs to `cut`, not `montage`. `candidate-order.json` is obsolete.
