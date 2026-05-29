# PRD — Clipper Local Video Pipeline

## Problem Statement

Build a local-first video clipping toolkit that can turn long videos or podcasts into useful clips and montages from the terminal. The user wants one coherent `clipper` CLI, not a loose collection of scripts, and wants the system to be reliable enough for humans and automation agents to run through a staged set of implementation tasks.

The tool should run locally on macOS, use `uv` for Python dependency management, rely on local FFmpeg, support both downloaded URLs and existing local video files, transcribe with faster-whisper, score transcript segments with an OpenAI-compatible LLM, cut clips, and assemble montages.

## Solution

Create a Python package exposing a single console command:

- `clipper doctor`
- `clipper start`
- `clipper list`
- `clipper transcribe`
- `clipper score`
- `clipper cut`
- `clipper montage`
- `clipper pipeline`

The implementation should be library-first. Each command delegates to tested importable functions. CLI output is human-readable by default and machine-readable with `--json`.

The first version builds the deterministic core pipeline. Stage 2 narrative edit planning via a secondary LLM pass is explicitly deferred.

## User Stories

1. As a local user, I want to run Clipper without Docker, so that it works directly with my local videos.
2. As a developer, I want setup through `uv`, so that dependency installation is reproducible.
3. As a terminal user, I want a single `clipper` command, so that the workflow is easy to remember.
4. As an automation agent, I want `--json` output, so that command results are parseable.
5. As a first-time user, I want `clipper doctor`, so that local environment failures are caught early.
6. As a user, I want to start a named video from either a remote URL or local file, so that I can use downloaded or existing media.
7. As a user, I want per-video artifacts, so that runs do not collide.
8. As a user, I want default fail-loud output behavior, so that stale artifacts are not silently reused.
9. As a user, I want `--reuse`, so that I can intentionally resume previous work.
10. As a user, I want `--force`, so that I can intentionally overwrite previous artifacts.
11. As a user, I want video metadata saved, so that outputs remain traceable.
12. As a user, I want local transcription, so that I do not need a hosted speech API.
13. As a user, I want configurable Whisper settings, so that speed and quality can be tuned.
14. As a user, I want directive-based LLM scoring, so that I can ask for different kinds of clips.
15. As a user, I want robust scoring, so that long transcripts and imperfect JSON responses do not break easily.
16. As a user, I want a default minimum score of 6, so that low-quality clips are filtered out.
17. As a user, I want accurate clip cutting by default, so that generated clips preserve audio/video sync.
18. As a user, I want audio preserved by default, so that generated clips are normal highlights.
19. As a user, I want `--silent`, so that I can create silent background footage when needed.
20. As a user, I want chronological montage assembly, so that the first version preserves source order.
21. As a user, I want `--min-duration` and `--max-duration`, so that montage length can be constrained.
22. As a tester, I want generated test videos, so that binary fixtures are not committed.
23. As a tester, I want default tests to avoid real network, Whisper model downloads, and real LLM calls.
24. As a tester, I want env-gated real LLM tests, so that configured models can be validated intentionally.
25. As a tester, I want env-gated real Whisper tests, so that transcription can be validated intentionally.

## Implementation Decisions

- Use `uv` and `pyproject.toml` as the source of truth.
- Expose one top-level `clipper` CLI.
- Keep module internals importable and testable.
- Add typed schemas/contracts for metadata, transcripts, scores, clips, montages, and pipeline results.
- Use per-video artifact directories.
- Existing outputs fail by default; `--reuse` validates and reuses step outputs; `--force` overwrites step outputs.
- Preserve audio by default; `--silent` strips audio.
- Use FFmpeg re-encoding for clipping by default to avoid keyframe-related audio/video sync drift.
- Default `--min-score` is 6.
- Montage v1 is chronological and can constrain duration.
- Robust LLM scoring includes chunking, retry, validation, and overlap handling.
- Stage 2 LLM narrative edit planning is deferred.

## Testing Decisions

- Test external behavior and public contracts, not private implementation details.
- Explicitly test schemas/JSON IO, scoring, cut/montage, pipeline, and CLI.
- Generate low-resolution 10-second deterministic test videos with FFmpeg.
- Mock external network/LLM/Whisper behavior by default.
- Gate real LLM tests behind `CLIPPER_RUN_LLM_TESTS=1`.
- Gate real Whisper tests behind `CLIPPER_RUN_WHISPER_TESTS=1`.

## Out of Scope

- Docker-first operation.
- Web UI.
- Deployment/VPS.
- Social scheduling.
- Remotion/branding overlays.
- Stage 2 narrative edit planner in first build.
- Rich terminal UI.
- Guaranteed deterministic real LLM or Whisper behavior in default tests.
