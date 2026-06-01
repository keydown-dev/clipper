# Handoff out

## Summary

Implemented Issue 018 explicit context scoring:

- `clipper score` now requires at least one explicit context flag: `--with-transcript`, `--with-visuals`, or both.
- Transcript scoring now requires and consumes `work/sentences.json` rather than silently falling back to raw transcript artifacts.
- Visual scoring consumes cached `work/shots.json` and `work/visual-index.json` without requiring transcript artifacts.
- Combined scoring builds a single timestamped prompt context containing requested transcript and visual evidence only.
- Existing scoring validation, retry, warning, token usage, output policy, JSON output, and verbose behavior are preserved.
- Pipeline scoring opts into transcript context explicitly.
- README examples document sound-bite, silent visual montage, and combined multimodal scoring.

## Changed files

- `README.md`
- `clipper/cli.py`
- `clipper/pipeline.py`
- `clipper/scoring.py`
- `tests/test_issue006.py`
- `tests/test_issue018.py`
- `.ralph/orchestrator/loops/transcript-visual-scoring/iterations/006/verification.md`
- `.ralph/orchestrator/loops/transcript-visual-scoring/iterations/006/handoff-out.md`

## Commit subject

feat: Require explicit scoring context

## Decisions

- `--with-transcript` uses only the sentence transcript artifact and fails if `work/sentences.json` is missing.
- `--with-visuals` requires both shot metadata and the cached visual index, then includes shot IDs, frame paths, duration, descriptions, actions, objects, people, mood, setting, and visible text in timestamped prompt evidence.
- Reusing an existing `scores.json` still validates/reuses the score artifact before loading requested evidence artifacts.
- `clipper pipeline` keeps its current audio-first behavior by calling scoring with `with_transcript=True` internally.

## Risks

- Combined prompt context is a simple chronological merge of transcript sentences and visual observations; future work may want richer grouping by shot or retrieval for very dense videos.
- Score artifacts do not record which context flags were used; only prompt behavior and resulting segments reflect the selected context.

## Next suggested task

Run an end-to-end local smoke workflow with `transcribe`, `shots`, `visual`, and combined `score --with-transcript --with-visuals` against a real short clip to validate prompt quality outside mocked tests.
