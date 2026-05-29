# Ralph handoff-out

## Summary

Implemented Issue 015 — Score Dialogue Enrichment.

- Scoring now uses `work/sentences.json` as transcript prompt context when available.
- Scored segments are enriched after validation/merge with overlapping sentence objects and deterministic joined `dialogue` text.
- Score schema validation accepts and validates enriched `sentences` traceability fields plus optional `dialogue`.
- Added deterministic tests for sentence-context prompting, dialogue enrichment, no-overlap behavior, and schema validation.
- Updated README scoring documentation and score JSON example.

## Changed files

- `clipper/scoring.py`
- `clipper/schemas.py`
- `tests/test_issue015.py`
- `README.md`

## Commit subject

feat: Enrich scores with sentence dialogue

## Verification

See `verification.md`.

## Decisions

- `clipper score` uses sentence transcript context when `work/sentences.json` exists, with fallback to the raw transcript for older workspaces/tests.
- Dialogue is derived only from sentence artifact text, not from LLM output.
- Segments with no overlapping sentences get `sentences: []` and omit `dialogue`.

## Risks

- Sentence overlap uses inclusive boundary checks (`sentence.end >= segment.start` and `sentence.start <= segment.end`), matching existing transcript-window overlap behavior.
- Fallback to raw transcript preserves compatibility but means missing sentence artifacts do not fail until later explicit context-selection work.

## Next suggested task

Implement the next queued issue for transcript visual scoring; likely explicit context scoring controls if Issue 018 is next.
