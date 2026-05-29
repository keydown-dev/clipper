# Handoff out

## Summary

Implemented Issue 017 visual frame analysis:

- Added `clipper visual` command.
- Added `clipper.visual` module to read `work/shots.json`, send representative JPEG frames to an OpenAI-compatible multimodal chat endpoint, validate/normalize structured observations, and write `work/visual-index.json`.
- Added `VISION_*` configuration overrides with fallback to existing `LLM_*` settings.
- Added visual index artifact schema validation and artifact-store visibility.
- Added mocked tests for structured output, validation repairs/errors, missing artifacts, output policy, and CLI routing.

## Changed files

- `.env.example`
- `clipper/artifacts.py`
- `clipper/cli.py`
- `clipper/config.py`
- `clipper/schemas.py`
- `clipper/visual.py`
- `tests/test_issue017.py`

## Commit subject

feat: Add visual frame analysis

## Decisions

- The visual index artifact path is `work/visual-index.json`.
- `VISION_BASE_URL`, `VISION_API_KEY`, `VISION_MODEL`, `VISION_TEMPERATURE`, and `VISION_TIMEOUT_SECONDS` are optional; unset values fall back to existing `LLM_*` settings.
- Invalid model JSON fails with an actionable `ArtifactError`; non-fatal field shape issues are repaired and recorded in artifact warnings.
- Tests use fake clients only; no real vision model calls are made.

## Risks

- The OpenAI multimodal message shape is standard `image_url` data URLs, but individual OpenAI-compatible providers may vary in support.
- Large frame images are sent inline as base64 data URLs; future work may need resizing or file-size controls.

## Next suggested task

Implement Issue 018 explicit context scoring by feeding transcript, shot, and visual index context into the scoring stage.
