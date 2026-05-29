# Issue 014 — Sentence Transcript Artifact

## Goal

Create a readable sentence-grouped transcript artifact from word-level timestamps during transcription.

## Depends On

- Issue 013 for word timestamp transcript data

## Tasks

- Add sentence grouping that consumes transcript segment words and punctuation.
- Derive each sentence start time from its first word and end time from its last word.
- Preserve traceability from each sentence back to source segment IDs and word index ranges.
- Write a sentence transcript artifact automatically when `clipper transcribe` succeeds.
- Ensure sentence grouping fails clearly when word timestamps are missing, with guidance to rerun transcription with force.
- Respect fail/reuse/force output policy for the sentence artifact alongside the raw transcript artifact.
- Include sentence transcript path and counts in human and JSON command results where appropriate.
- Document the raw transcript and sentence transcript relationship.

## Acceptance Criteria

- Tests cover sentence grouping across one segment and across multiple source segments.
- Tests verify sentence start/end timestamps come from first/last word timings rather than estimated segment proportions.
- Tests cover source segment and word-range traceability fields.
- `clipper transcribe` writes both raw and sentence transcript artifacts for new transcriptions.
- Missing word timestamps produce an actionable error rather than guessed sentence timings.
