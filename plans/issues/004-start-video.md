# Issue 004 — Start Video from Media Input

## Goal

Support `clipper start` for both local video files and downloadable remote URL inputs.

## Depends On

- Issue 002
- Issue 003 useful but not blocking

## Tasks

- Implement remote versus local-file detection: only `http` and `https` URLs count as remote inputs in v1; everything else must resolve as a local file or fail clearly.
- Implement `clipper start INPUT [--name NAME]` to create a named video workspace, prepare source, and write metadata only; later commands or `pipeline` handle transcription, scoring, cutting, and montage assembly.
- Register local video files by copying them into the video artifact layout as `source/source.{ext}` by default.
- Implement yt-dlp download integration for remote inputs; let yt-dlp/FFmpeg choose the actual final extension, discover the resulting `source/source.{ext}` path, and store that video-relative path in metadata `source_path`.
- Use yt-dlp format `bestvideo[height<=720]+bestaudio/best[height<=720]`.
- Save metadata JSON for local and downloaded sources, including required traceability core fields (`schema_version`, `input_ref`, `input_type`, `canonical_input_ref`, `source_path`, `title`, numeric `duration`, `created_at`) plus available provider extras such as thumbnail URL, video ID, source URL, extractor, and raw yt-dlp metadata. `input_type` must be `remote` for URL inputs or `local` for local file inputs.
- Determine local-file duration with ffprobe; fail clearly if duration cannot be determined.
- Add proxy support for downloads and forward it to yt-dlp.
- Wire `clipper start`.

## Acceptance Criteria

- Local file input works without network access and copies the source into the video directory.
- `clipper start INPUT --name NAME` follows the shared output policy when `.clipper/NAME/` already exists: default fail, `--reuse` validates that metadata matches the same canonical input reference, and `--force` overwrites start outputs.
- Download integration is mock-tested.
- Metadata output follows the shared schema and contains required traceability core fields.
- Download failures stop the command with an actionable error.
- CLI supports human and `--json` output, including the resolved video name/path.
