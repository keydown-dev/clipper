# Issue 009 — Montage Assembly

## Goal

Assemble selected clips into a normalized montage video.

## Depends On

- Issue 002
- Issue 007
- Issue 008

## Tasks

- Read clips from `work/clips.json` exactly as produced by `clipper cut`; do not re-filter scores in montage.
- Sort clips chronologically by default.
- Support `--min-duration` and `--max-duration`; fail clearly without creating a montage if selected clips cannot meet `--min-duration`.
- Include clips chronologically and trim the final included clip when needed to fit maximum duration.
- Concatenate with FFmpeg concat demuxer.
- Normalize dimensions with the documented scale/pad filter, defaulting to 1920x1080.
- Encode with a broadly compatible H.264 output, e.g. libx264 with CRF/preset defaults from `README.md`.
- Preserve audio by default.
- Add `--silent` to strip audio.
- Write montage result JSON.
- Wire `clipper montage`.

## Acceptance Criteria

- Generated clips can be assembled into a montage.
- Maximum duration behavior is tested within FFmpeg tolerance.
- Output dimension normalization is tested or verified with FFmpeg/ffprobe where practical.
- Audio default and silent behavior are tested.
- CLI supports human and `--json` output.
- Tests verify partial-output cleanup on FFmpeg failure.
