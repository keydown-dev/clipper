# Install and readiness

Use this reference when Clipper might not be installed or the environment is unknown. Always run `clipper doctor --json` (or `uv run clipper doctor --json` from a source checkout) before expensive downloads, Whisper transcription, LLM scoring, cuts, or montages.

## Supported environments and system dependencies

Clipper Core is a Python CLI that shells out to media tools and downloads/loads model files on demand. Python packaging does not install native media binaries or Whisper model weights for you.

Required:

- macOS
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg and ffprobe on `PATH`
- Python runtime dependencies declared by the project, including `yt-dlp`, `faster-whisper`, `openai`, `python-dotenv`, `questionary`, and `scenedetect`
- OpenAI-compatible LLM settings in `.env` or the process environment for transcript/visual scoring

Install FFmpeg/ffprobe with Homebrew:

```bash
brew install ffmpeg
```

## Local development checkout

Use these commands when you are inside a Clipper source checkout and have not installed the `clipper` command globally:

```bash
uv sync
cp .env.example .env
uv run clipper doctor --json
```

`uv sync` creates the project virtual environment and installs Python dependencies. `uv run clipper ...` invokes the CLI entry point from that checkout.

## Installed CLI usage

The first supported non-development install path is `uv tool install` from the Clipper git repository:

```bash
uv tool install git+https://github.com/keydown-dev/clipper.git
clipper doctor --json
```

Use this form when `clipper` is already installed and available on `PATH`:

```bash
clipper doctor --json
```

Do not claim PyPI installation or bundled native dependency installation. Python packaging installs the `clipper` command and declared Python runtime dependencies only; FFmpeg/ffprobe, model weights, and LLM services remain external requirements.

## Configuration

Typical `.env` values:

```env
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=your-key-here
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0
LLM_TIMEOUT_SECONDS=60

# Optional multimodal vision overrides. Defaults fall back to LLM_* when unset.
VISION_BASE_URL=https://api.openai.com/v1
VISION_API_KEY=your-key-here
VISION_MODEL=gpt-4o-mini
VISION_TEMPERATURE=0
VISION_TIMEOUT_SECONDS=60

WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
CLIPPER_STORE_PATH=.clipper
```

`LLM_API_KEY` and `VISION_API_KEY` may be omitted only for local/OpenAI-compatible endpoints that do not require authentication.

Whisper model weights are downloaded by `faster-whisper` when a configured model is first loaded. `clipper doctor --json` checks import/config readiness by default; use `--check-whisper` only when you intentionally want to load the model. Use `--check-llm` only when you intentionally want to contact the configured LLM endpoint.

## Artifact Store location

Clipper writes video workspaces to a project-local `.clipper/` Artifact Store by default. From either a checkout or installed CLI, pass `--store PATH` for one command or set `CLIPPER_STORE_PATH` for a session when a workflow must target a different project/store:

```bash
clipper doctor --store ./my-clips --json
CLIPPER_STORE_PATH=./my-clips clipper list --json
uv run clipper start ./source/interview.mp4 --store ../shared-clipper-store --name interview
```

Prefer the default `.clipper/` when running inside a project so artifacts remain easy for agents and humans to find.

## Smoke test without Whisper or LLM calls

This validates the CLI, FFmpeg/ffprobe, local-file registration, and Artifact Store writes without network access, real LLM credentials, or Whisper model downloads:

```bash
uv run clipper doctor --json
ffmpeg -f lavfi -i testsrc2=size=320x180:rate=30 -f lavfi -i sine=frequency=1000 \
  -t 3 -pix_fmt yuv420p /tmp/clipper-smoke.mp4 -y
uv run clipper start /tmp/clipper-smoke.mp4 --name smoke-demo
uv run clipper list --json
```

For an installed CLI, replace `uv run clipper` with `clipper`:

```bash
clipper doctor --json
clipper start /tmp/clipper-smoke.mp4 --name smoke-demo
clipper list --json
```

Use `--reuse` if rerunning against the same existing workspace, or `--force` to replace it.
