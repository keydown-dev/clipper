# Issue 006 — Robust LLM Scoring

## Goal

Convert transcripts into validated, scored candidate clip segments using an OpenAI-compatible LLM.

## Depends On

- Issue 002
- Issue 005 for transcript schema

## Tasks

- Build scoring prompts with directive support using the baseline system prompt from `README.md`.
- Include timestamped transcript text and the user directive in prompts.
- Configure OpenAI-compatible client from env, defaulting to the documented Ollama-compatible base URL/model and using the chat completions API shape (`client.chat.completions.create`) with default temperature `0` and timeout `60` seconds.
- Chunk long transcripts into overlapping windows of about 10 minutes with about 30 seconds of overlap.
- Parse model JSON responses that should contain only an array of segment objects, including extracting the first JSON array from common markdown/code-fence wrappers.
- Retry once with stricter instructions if extraction/parsing fails.
- Validate and normalize segments with `start`, `end`, `score` from 0-10, and `reason`; reject individual segments with scores outside 0-10 and report validation warnings; clamp segment times to transcript bounds when safe and drop segments with `end <= start` or unusable times.
- Prefer 5-15 second segment lengths where possible.
- Merge/deduplicate overlapping segments, preferring stronger scores.
- Persist score JSON; if zero valid candidate segments remain, write an empty `segments` array with a warning rather than failing.
- Wire `clipper score`.
- Add env-gated real LLM test.

## Acceptance Criteria

- Tests cover prompt construction, directive examples, chunking, invalid JSON retry, validation, and overlap handling.
- Default tests do not call a real LLM.
- Real LLM test only runs with `CLIPPER_RUN_LLM_TESTS=1`.
- Default minimum score for downstream cutting is documented as 6.
