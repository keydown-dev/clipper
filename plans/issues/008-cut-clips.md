# Issue 008 — Cut Clips

## Goal

Extract scored segments from source videos into individual clip files.

## Depends On

- Issue 002
- Issue 006
- Issue 007

## Tasks

- Filter scored segments by `--min-score`, default 6.
- Merge overlapping segments before cutting.
- Use fast FFmpeg stream-copy by default with the shape `ffmpeg -ss START -to END -i source.mp4 -c copy output.mp4`.
- Preserve audio by default.
- Add `--silent` to strip audio, e.g. with `-an`.
- If no segments pass `--min-score`, fail clearly and do not create an empty clip set or montage.
- Write clip manifest/result JSON.
- Respect fail/reuse/force output policy.
- Wire `clipper cut`.

## Acceptance Criteria

- Generated test video can be cut into clips.
- Tests verify filtering, overlap merging, FFmpeg invocation, no-passing-segments behavior, and audio/silent behavior.
- CLI supports human and `--json` output.
