# Issue 017 — Visual Frame Analysis

## Goal

Analyze representative shot frames with an OpenAI-compatible multimodal chat endpoint and cache structured visual observations.

## Depends On

- Issue 016 for shot detection and representative frame artifacts

## Tasks

- Add a visual analysis command that consumes the shot manifest and representative frame images.
- Configure an OpenAI-compatible multimodal chat endpoint with base URL, API key, model, temperature, and timeout settings.
- Send representative frame images to the configured model using an OpenAI-style multimodal message shape where supported.
- Prompt the model to return structured JSON observations for each frame, including description, visible people, actions, objects, mood, setting, and visible text where available.
- Validate and normalize visual analysis responses.
- Persist a visual index artifact keyed by shot/frame time and representative frame path.
- Store provider/model metadata and warnings for non-fatal validation repairs or dropped observations.
- Respect fail/reuse/force output policy for the visual index artifact.
- Keep default tests fully mocked and avoid real model calls.

## Acceptance Criteria

- Tests verify visual analysis reads shot/frame artifacts and writes a structured visual index.
- Tests verify invalid model JSON is handled with clear validation errors or warnings according to documented policy.
- Tests verify provider/model metadata is persisted.
- Tests verify missing shot/frame artifacts produce actionable errors.
- Default tests do not call a real vision model.
- Real vision-model tests, if added, are gated behind an explicit environment variable.
