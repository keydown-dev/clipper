# Issue 026 — Supported CLI Install Path

## Goal

Choose and implement the first supported way for users to install the `clipper` command outside a local development checkout.

This issue is separate from documentation because it may require packaging metadata, release process decisions, or smoke tests.

## Depends On

- Issue 021 for install/distribution documentation context
- ADR 0002 for the CLI Contract as the public surface boundary

## Tasks

- Implement and verify the first supported install target as `uv tool install` from the project git repository.
- Do not publish to PyPI in this issue.
- Verify that the installed `clipper` command can run `clipper doctor` from another project directory.
- Ensure package metadata includes all Python runtime dependencies needed by the CLI.
- Document system dependencies that cannot be installed by Python packaging, especially FFmpeg/ffprobe.
- Add a smoke test or manual verification note for installed CLI behavior if practical.
- Update README and skill install references with the chosen install path.

## Acceptance Criteria

- There is a documented `uv tool install` git command for installing Clipper Core as a CLI outside the repo checkout.
- `clipper doctor` works from an arbitrary consuming project after installation, assuming system dependencies are present.
- The install path does not depend on Pi.
- Limitations around heavy native/model dependencies are clear.

## Implementation Note

The first supported non-development install target is:

```bash
uv tool install git+https://github.com/keydown-dev/clipper.git
clipper doctor --json
```

This path installs the `clipper` console script and the Python runtime dependencies declared in `pyproject.toml`. It deliberately does not publish to PyPI and does not bundle native/system dependencies. Users must install FFmpeg/ffprobe separately, and model weights plus OpenAI-compatible LLM services/configuration remain external runtime requirements.

Manual verification installed the CLI through `uv tool install` from a git URL into an isolated uv tool directory, then ran `clipper doctor --json` from `/tmp` with a temporary `CLIPPER_STORE_PATH`. The doctor check passed with FFmpeg/ffprobe present and all declared Python runtime dependencies importable.
