# Issue 015 — Score Dialogue Enrichment

## Goal

Enrich scored candidate clip segments with the transcript sentences and dialogue that overlap each selected time range.

## Depends On

- Issue 014 for sentence transcript artifacts
- Issue 006 for existing LLM scoring

## Tasks

- Update transcript-context scoring to prompt from the sentence transcript instead of raw faster-whisper segments.
- After candidate segments are validated and merged, attach overlapping sentence objects to each scored segment.
- Add a joined `dialogue` string to each scored segment when overlapping dialogue exists.
- Preserve sentence timestamps and traceability fields in score output so selected dialogue remains auditable.
- Ensure dialogue enrichment is deterministic and does not ask the LLM to restate or rewrite transcript text.
- Handle segments with no overlapping dialogue gracefully.
- Update score schema validation and documentation for enriched score segments.

## Acceptance Criteria

- Tests verify scoring prompts use sentence-level transcript text when transcript context is requested.
- Tests verify score output includes overlapping sentence objects and joined dialogue text.
- Tests verify dialogue enrichment is derived from sentence artifacts, not model-generated prose.
- Tests cover scored segments with no overlapping sentences.
- Existing score validation behavior for start, end, score, reason, warnings, and overlap merging remains intact.
