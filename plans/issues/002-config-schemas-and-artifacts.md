# Issue 002 — Config, Schemas, JSON IO, and Artifact Layout

## Goal

Create the shared contracts and artifact semantics used by every pipeline step.

## Depends On

- Issue 001

## Tasks

- Implement environment/config loading with `.env` support.
- Add `.env.example` with LLM and Whisper defaults from `README.md`.
- Implement path and JSON IO helpers using `pathlib.Path`.
- Define typed contracts for metadata, transcript, scores, clip manifests, montage results, and pipeline results.
- Include defaults for source/work/clips/output artifact groups, Whisper CPU/int8 settings, LLM base URL/model, 1920x1080 output dimensions, and default min score 6.
- Implement per-video/job artifact directory creation.
- Implement existing-output policy: default fail, `--reuse`, `--force`.
- Implement shared JSON result formatting helpers for CLI commands.

## Acceptance Criteria

- Config defaults and env overrides are tested, including `.env` loading.
- `.env.example` documents the required LLM and Whisper values.
- JSON read/write behavior is tested.
- Artifact layout generation is tested.
- Existing-output policy is tested for fail, reuse, and force.
