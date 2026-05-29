# Issue 008 — Cut Clips

## Goal

Extract scored segments from source videos into individual clip files.

## Depends On

- Issue 002
- Issue 006
- Issue 007

## Tasks

- Filter scored segments by `--min-score`, default 6.
- Merge segments that overlap at all before cutting; merged clips use the earliest start, latest end, maximum score, and combined reasons.
- Sort merged passing segments chronologically and name clip files/IDs sequentially as `clip-0001`, `clip-0002`, etc.
- Use accurate FFmpeg re-encoding by default so source keyframe boundaries do not create audio/video sync drift.
- Do not add padding by default; cut exactly the scored/merged start and end times.
- Preserve audio by default, encoded as AAC.
- Add `--silent` to strip audio, e.g. with `-an`.
- If no segments pass `--min-score`, fail clearly and do not create or update `work/clips.json`, clip files, or an empty montage.
- Write clip manifest/result JSON.
- Respect fail/reuse/force output policy.
- Wire `clipper cut`.

## Acceptance Criteria

- Generated test video can be cut into clips.
- Tests verify filtering, overlap merging, FFmpeg invocation, no-passing-segments behavior, partial-output cleanup on FFmpeg failure, and audio/silent behavior.
- CLI supports human and `--json` output.
