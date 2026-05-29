# Handoff out

## Summary

Implemented Issue 014 — Sentence Transcript Artifact. `clipper transcribe` now writes `work/transcript.json` and `work/sentences.json`, derives sentence timings from first/last word timestamps, preserves source segment and inclusive word-range traceability, and reports sentence path/counts in CLI output.

## Changed files

- `clipper/artifacts.py` — added fixed `work/sentences.json` artifact path.
- `clipper/transcription.py` — added sentence grouping and writes sentence artifact during transcription/reuse policy.
- `clipper/schemas.py` — added sentence transcript typed contract and validator.
- `clipper/cli.py` — includes sentence transcript path/counts in human and JSON transcribe results.
- `README.md` — documents sentence transcript artifact and raw transcript relationship.
- `tests/test_issue014.py` — adds coverage for sentence grouping, traceability, CLI artifact write/reporting, and missing word timestamp guidance.
- `tests/test_issue002.py` — updates artifact layout expectation.
- `tests/test_issue005.py` — updates reuse fixture for complete transcript output set.

## Commit subject

feat: Add sentence transcript artifact.

## Decisions

- Used `work/sentences.json` as the fixed sentence transcript artifact path.
- Sentence `word_ranges` use inclusive `start_word_index` and `end_word_index` per source segment.
- Sentence boundary detection flushes on word text ending with `.`, `!`, or `?` plus optional closing quote/bracket punctuation; remaining words flush as the final sentence.
- `--reuse` now requires both raw and sentence transcript artifacts and validates both.

## Risks

- Sentence splitting is intentionally simple punctuation-based logic; abbreviations may split imperfectly.
- Existing workspaces with only `work/transcript.json` must rerun `clipper transcribe --force` to produce `work/sentences.json` before `--reuse` succeeds.

## Verification

See `verification.md`. Full suite passed: 83 passed, 3 skipped.

## Next suggested task

Implement Issue 015 — Score Dialogue Enrichment.
