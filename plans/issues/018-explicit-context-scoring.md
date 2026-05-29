# Issue 018 — Explicit Context Scoring

## Goal

Make scoring context explicit so callers choose transcript context, visual context, or both, and scoring fails when required evidence artifacts are missing.

## Depends On

- Issue 015 for sentence-based transcript scoring and dialogue enrichment
- Issue 017 for cached visual frame analysis

## Tasks

- Update `clipper score` so callers must provide at least one context flag.
- Add `--with-transcript` to score using the sentence transcript artifact.
- Add `--with-visuals` to score using the cached visual index artifact and its underlying shot metadata.
- Fail clearly when no scoring context is selected.
- Fail clearly when `--with-transcript` is selected but the sentence transcript artifact is missing.
- Fail clearly when `--with-visuals` is selected but the shot manifest or visual index artifact is missing.
- Build scoring prompts from only the explicitly requested contexts.
- Support transcript-only, visual-only, and combined transcript-plus-visual scoring.
- Preserve validation, retry, warning, token usage, fail/reuse/force, JSON output, and verbose progress behavior.
- Document examples for sound-bite scoring, silent visual montage scoring, and combined multimodal scoring.

## Acceptance Criteria

- Tests verify `clipper score` fails when neither `--with-transcript` nor `--with-visuals` is supplied.
- Tests verify transcript-only scoring consumes sentence transcript context and enriches scores with dialogue.
- Tests verify visual-only scoring consumes visual index and shot metadata without requiring transcript artifacts.
- Tests verify combined scoring includes both transcript and visual context.
- Tests verify missing requested artifacts produce actionable errors.
- Existing LLM scoring validation, retry, warning, and output policy behavior remains intact.
