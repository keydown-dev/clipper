# Install and readiness

Use this reference when Clipper might not be installed or the environment is unknown.

## Requirements

- macOS
- Python 3.11+
- `uv`
- FFmpeg and ffprobe on `PATH`
- Python dependencies installed from the project
- LLM settings in `.env` or the environment for scoring

```bash
brew install ffmpeg
uv sync
cp .env.example .env
uv run clipper doctor --json
```

If `clipper` is installed globally or in an activated virtualenv, the equivalent readiness check is:

```bash
clipper doctor --json
```

## Configuration

Typical `.env` values:

```env
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=your-key-here
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0
LLM_TIMEOUT_SECONDS=60
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

`LLM_API_KEY` may be omitted only for local/OpenAI-compatible endpoints that do not require authentication.

## Smoke test without Whisper or LLM calls

```bash
uv run clipper doctor --json
ffmpeg -f lavfi -i testsrc2=size=320x180:rate=30 -f lavfi -i sine=frequency=1000 \
  -t 3 -pix_fmt yuv420p /tmp/clipper-smoke.mp4 -y
uv run clipper start /tmp/clipper-smoke.mp4 --name smoke-demo
uv run clipper list --json
```

Use `--reuse` if rerunning against the same existing workspace, or `--force` to replace it.
