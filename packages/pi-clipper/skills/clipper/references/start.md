# Start videos

`clipper start` creates a video workspace and prepares `source/source.{ext}` plus `work/metadata.json`. It does not transcribe, score, cut, or montage.

Always run doctor first on unknown systems:

```bash
uv run clipper doctor --json
```

## Local file

```bash
uv run clipper start ./source/interview.mp4 --name interview
```

Local inputs are copied into the workspace so artifacts remain self-contained.

## YouTube or remote URL

Remote inputs use yt-dlp. Only use network workflows when the user expects downloads.

```bash
uv run clipper start "https://youtube.com/watch?v=VIDEO_ID" --name interview-url
```

Use a proxy when required by the provider/network:

```bash
uv run clipper start "https://youtube.com/watch?v=VIDEO_ID" --name interview-url --proxy http://127.0.0.1:8080
```

## Naming and reruns

Names must be slug-safe: lowercase letters, numbers, dashes, and underscores.

```bash
uv run clipper start ./source/interview.mp4 --name interview --reuse
uv run clipper start ./source/interview.mp4 --name interview --force
```

Use `--reuse` only when the existing metadata matches the same canonical input. Use `--force` to replace the workspace source/metadata.

## JSON for automation

```bash
uv run clipper start ./source/interview.mp4 --name interview --json
```
