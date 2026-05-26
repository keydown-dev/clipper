# Issue 010 — Pipeline Orchestrator

## Goal

Implement the end-to-end importable pipeline and `clipper pipeline` command.

## Depends On

- Issue 004
- Issue 005
- Issue 006
- Issue 008
- Issue 009

## Tasks

- Implement `run_pipeline` as a stable public function.
- Accept URL or local video file input.
- Orchestrate download/register, transcribe, score, cut, and montage.
- Propagate directive, min score, min/max duration, silent, proxy, reuse, and force options.
- Return a structured pipeline result containing source, metadata, transcript, scores, clips, montage, counts, durations, and runtime.
- Stop before montage creation when no clips pass the threshold.
- Wire `clipper pipeline`.

## Acceptance Criteria

- Pipeline can run against a generated local video with mocked transcription/scoring where appropriate.
- Pipeline fail/reuse/force behavior is tested.
- Programmatic result contract is tested and matches the README example.
- CLI supports human and `--json` output.
