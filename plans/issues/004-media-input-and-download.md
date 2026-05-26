# Issue 004 — Media Input and Download

## Goal

Support both local video files and downloadable URL inputs.

## Depends On

- Issue 002
- Issue 003 useful but not blocking

## Tasks

- Implement URL versus local-file detection.
- Register local video files into the artifact layout or reference them safely.
- Implement yt-dlp download integration.
- Use yt-dlp format `bestvideo[height<=720]+bestaudio/best[height<=720]`.
- Save metadata JSON for local and downloaded sources, including available title, duration, thumbnail URL, video ID, source URL, and local path.
- Add proxy support for downloads and forward it to yt-dlp.
- Wire `clipper download`.

## Acceptance Criteria

- Local file input works without network access.
- Download integration is mock-tested.
- Metadata output follows the shared schema and contains traceability fields where available.
- Download failures stop the command with an actionable error.
- CLI supports human and `--json` output.
