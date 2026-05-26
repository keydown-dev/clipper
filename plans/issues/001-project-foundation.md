# Issue 001 — Project Foundation and Clipper CLI Shell

## Goal

Create the Python project foundation and a single top-level `clipper` CLI that future issues build on.

## Depends On

- PRD only.

## Tasks

- Create `uv`/`pyproject.toml` project metadata.
- Declare expected runtime dependencies: `yt-dlp`, `faster-whisper`, `openai`, and `python-dotenv`.
- Declare expected test dependency: `pytest`.
- Add package skeleton.
- Add `clipper` console script entry point.
- Add argparse root command and placeholder subcommands.
- Add pytest setup.
- Keep `README.md` as the canonical project context and make sure initial commands match it.

## Acceptance Criteria

- `uv sync` succeeds.
- `uv run clipper --help` works.
- Placeholder help works for doctor, download, transcribe, score, cut, montage, and pipeline.
- `uv run pytest` passes.
- `README.md` remains accurate for setup and CLI shape.
