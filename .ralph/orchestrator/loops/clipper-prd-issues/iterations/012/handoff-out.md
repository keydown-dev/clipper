# Ralph handoff-out

Loop: clipper-prd-issues
Iteration: 12
Todo: 10 — Complete `plans/issues/010-pipeline-orchestrator.md` only.

## Summary

Implemented the end-to-end importable pipeline and wired `clipper pipeline`.

## Changed files

- `clipper/pipeline.py`
  - Implemented `run_pipeline` public API.
  - Orchestrates source preparation, transcription, scoring, cutting, and montage.
  - Propagates name, directive, min score, min/max duration, silent, proxy, reuse, and force options.
  - Writes `work/pipeline.json` only after successful montage creation.
  - Returns a structured result with source, metadata, transcript, scores, clips, montage, counts, durations, runtime, and reuse flags.
- `clipper/cli.py`
  - Replaced pipeline placeholder with real CLI handler.
  - Added pipeline `--min-duration`, `--silent`, and `--proxy` options.
  - Supports human and `--json` output.
- `tests/test_cli.py`
  - Removed pipeline from placeholder-command expectations.
- `tests/test_issue010.py`
  - Added pipeline acceptance coverage for generated local video with mocked transcription/scoring, fail/reuse/force behavior, no-clips stop behavior, programmatic result contract, and CLI output modes.

## Decisions

- `--reuse` returns an existing valid `work/pipeline.json` immediately when present; otherwise it reuses upstream artifacts and writes the missing pipeline result after successful completion.
- No-clips behavior relies on `cut_video` raising before clip manifest/montage creation; `run_pipeline` writes no pipeline result in that failure path.

## Risks / notes

- `clipper.pipeline` lazily imports start-source helper functions from `clipper.cli` to avoid duplicating source preparation logic while avoiding an import cycle.
- Existing extra clip files from older forced runs may remain if a later forced run creates fewer clips; manifests remain authoritative, matching prior step behavior.

## Verification

See `verification.md`.

## Next suggested task

Proceed to the next planned issue/iteration (likely CLI polish/docs/final verification) after orchestrator review.
