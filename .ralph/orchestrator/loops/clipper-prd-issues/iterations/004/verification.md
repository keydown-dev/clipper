# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands

- `pytest -q`
  - Result: not_run
  - Output: `/bin/bash: pytest: command not found`

- `uv run pytest -q`
  - Result: passed
  - Output: `30 passed in 0.06s`

## Acceptance criteria checked

- Local file start is covered by tests: source is copied to `source/source.{ext}` and metadata contains required traceability fields.
- Existing workspace policy is covered by tests: default fail, `--reuse` validates matching canonical input/source, `--force` overwrites start outputs.
- Remote download integration is mock-tested, including yt-dlp format and proxy forwarding.
- Download failure emits an actionable artifact error.
- Human/JSON output is implemented; JSON includes resolved video name/path and metadata artifact path.
