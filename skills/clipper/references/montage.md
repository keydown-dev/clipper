# Montage

`clipper montage [VIDEO]` assembles clips listed in `work/clips.json` into `output/montage.mp4` and writes `output/montage.json`.

Prerequisites:

```bash
uv run clipper cut interview --min-score 6
```

Basic montage:

```bash
uv run clipper montage interview
```

Limit duration:

```bash
uv run clipper montage interview --max-duration 60
```

Require a minimum duration:

```bash
uv run clipper montage interview --min-duration 30
```

Silent visual montage:

```bash
uv run clipper montage broll --max-duration 45 --silent
```

Automation and reruns:

```bash
uv run clipper montage interview --json
uv run clipper montage interview --reuse
uv run clipper montage interview --force
```

Montage uses the clips manifest produced by `cut`; score filtering belongs to `cut`, not `montage`.
