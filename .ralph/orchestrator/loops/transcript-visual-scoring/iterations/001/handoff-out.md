# Ralph handoff-out

## Summary

Implemented Issue 013 word timestamp transcription. New faster-whisper transcriptions now pass `word_timestamps=True`, generated transcript segments include a `words` array, and transcription fails clearly if word timestamp data is missing. Transcript schema validation remains backward-compatible with older artifacts without `words` while validating word entries when present. README transcript examples now document word timestamp output.

## Changed files

- `clipper/transcription.py`
- `clipper/schemas.py`
- `tests/test_issue005.py`
- `README.md`

## Verification

See `verification.md`.

## Commit subject

Add word timestamps to transcripts

## Decisions

- Kept `words` optional in schema validation so existing transcript artifacts can still be reused.
- Required generated non-empty transcript segments to have word timestamp entries.
- Stored word text under `word`, matching faster-whisper's word object field name.

## Risks

- Empty-text segments with empty `words` are allowed; downstream sentence grouping should decide whether to ignore or reject them.

## Next suggested task

Implement Issue 014 — Sentence Transcript Artifact.
