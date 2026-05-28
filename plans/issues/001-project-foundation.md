# Issue 001 — Project Foundation and Clipper CLI Shell

## Goal

Create the Python project foundation and a single top-level `clipper` CLI that future issues build on.

## Depends On

- PRD only.

## Tasks

- Create `uv`/`pyproject.toml` project metadata.
- Declare expected runtime dependencies: `yt-dlp`, `faster-whisper`, `openai`, `python-dotenv`, and `questionary`.
- Declare expected test dependency: `pytest`.
- Add `clipper` package skeleton.
- Add `clipper` console script entry point.
- Add argparse root command and placeholder subcommands.
- Add a shared per-command argparse parent/config helper for common options (`--store`, `--json`, `-v`/`--verbose`) so every subcommand accepts them after the command without drift.
- Establish minimal exit code conventions: `0` success, `1` command/domain failure, `2` CLI usage error, `130` user cancellation.
- Add pytest setup.
- Keep `README.md` as the canonical project context and make sure initial commands match it.

## Acceptance Criteria

- `uv sync` succeeds.
- `uv run clipper --help` works.
- Placeholder help works for doctor, start, list, transcribe, score, cut, montage, and pipeline.
- `uv run pytest` passes.
- `README.md` remains accurate for setup and CLI shape.
