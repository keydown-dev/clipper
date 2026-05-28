# Ralph handoff-out

## Summary

Completed iteration 4 / issue 004: `clipper start` now creates video workspaces for local files and remote HTTP(S) URLs, writes metadata, supports `--reuse`/`--force`, forwards download proxy settings, and emits human or JSON output.

## Changed files

- `clipper/cli.py`
  - Added start implementation.
  - Added ffprobe duration probing for local files and remote fallback.
  - Added yt-dlp remote download integration using `bestvideo[height<=720]+bestaudio/best[height<=720]`.
  - Added metadata generation with traceability fields and provider extras.
- `tests/test_cli.py`
  - Removed `start` from placeholder command expectations.
- `tests/test_issue004.py`
  - Added local start, output policy, mock remote download/proxy, and remote failure tests.
- `.ralph/orchestrator/loops/clipper-prd-issues/iterations/004/verification.md`
  - Recorded verification results.

## Decisions

- Only `http`/`https` inputs are treated as remote via existing artifact helpers; all other inputs resolve as local files.
- `--reuse` requires existing valid metadata, matching `canonical_input_ref`, and an existing metadata `source_path`.
- `--force` removes/recreates the `source/` start output and rewrites `work/metadata.json`, without touching later-step outputs.

## Risks / notes

- Real remote downloads were not executed; yt-dlp integration is mock-tested as requested.
- A bare `pytest` command is unavailable in this environment; `uv run pytest -q` passes.
- The harness modified `worker-output.jsonl` during execution; this was not part of the source changes.

## Next suggested task

Proceed to iteration 5 / issue 005 only when instructed by the orchestrator.
