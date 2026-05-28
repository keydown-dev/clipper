# Issue 007 — Generated Video Test Fixtures

## Goal

Provide deterministic generated media for smoke tests without committing binary video files.

## Depends On

- Issue 001

## Tasks

- Add test helper that generates a tiny low-resolution 10-second video with FFmpeg by default, e.g. 320x180 testsrc video with optional sine-wave audio and duration/size overrides.
- Include optional audio in generated test media where needed.
- Add skip/failure behavior when FFmpeg is unavailable.
- Document generated fixture usage for tests and manual validation.
- Use ±0.5s tolerance for FFmpeg/ffprobe duration assertions.

## Acceptance Criteria

- Tests can create a 10-second low-resolution video in a temporary directory, with duration/size overrides when needed.
- Generated media is usable by cut and montage tests.
- No binary video fixture is committed.
