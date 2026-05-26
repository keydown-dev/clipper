# Issue 007 — Generated Video Test Fixtures

## Goal

Provide deterministic generated media for smoke tests without committing binary video files.

## Depends On

- Issue 001

## Tasks

- Add test helper that generates a tiny video with FFmpeg.
- Include optional audio in generated test media where needed.
- Add skip/failure behavior when FFmpeg is unavailable.
- Document generated fixture usage for tests and manual validation.

## Acceptance Criteria

- Tests can create a short video in a temporary directory.
- Generated media is usable by cut and montage tests.
- No binary video fixture is committed.
