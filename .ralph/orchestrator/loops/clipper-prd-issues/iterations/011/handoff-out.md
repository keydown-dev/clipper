# Ralph handoff-out

## Summary

Completed Issue 009 montage assembly. Added an importable montage implementation and wired `clipper montage` to assemble `work/clips.json` into `output/montage.mp4` plus `output/montage.json`.

## Changed files

- `clipper/montage.py` — new montage selection, FFmpeg concat-demuxer command construction, trim handling, output policy/reuse/force handling, manifest writing, and cleanup on failure.
- `clipper/cli.py` — wired `run_montage` and `MontageOptions` into the existing CLI parser/handler flow.
- `tests/test_cli.py` — removed `montage` from placeholder-command expectations.
- `tests/test_issue009.py` — added unit/CLI/generated-media coverage for montage acceptance criteria.

## Decisions

- Reads `work/clips.json` directly and does not re-filter by score.
- Sorts clips chronologically by `start`/`end`.
- Applies `--max-duration` by trimming the final included clip via a temporary FFmpeg output before concat-demuxing.
- Uses README defaults: scale/pad to configured dimensions (default `1920x1080`), `libx264`, `preset medium`, `crf 23`.
- Preserves audio by default with AAC output for MP4 compatibility; `--silent` adds `-an`.
- Treats `output/montage.mp4` and `output/montage.json` as one output set for default/reuse/force semantics.

## Verification

See `verification.md`.

## Risks / notes

- The concat-demuxer path assumes compatible enough input clips for FFmpeg to decode through the concat demuxer before normalization; this matches the requested implementation shape and generated clip tests.
- Montage JSON duration is the selected/target duration sum; tests also verify actual FFprobe duration within project tolerance.

## Next suggested task

Proceed to the next planned issue/todo after Issue 009; do not continue from this worker.
