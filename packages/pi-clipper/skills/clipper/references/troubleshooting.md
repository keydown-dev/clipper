# Troubleshooting

Start with doctor. From a source checkout use:

```bash
uv run clipper doctor --json
```

When the CLI is installed on `PATH`, use:

```bash
clipper doctor --json
```

## Missing `clipper` command

If `clipper` is not found, you are probably in a checkout without a globally installed entry point. Use the checkout form:

```bash
uv sync
uv run clipper doctor --json
```

The first supported non-dev install path is expected to be `uv tool install` from the project git repository once Issue 026 verifies the exact command. PyPI install is not part of the first documented distribution path.

## Missing ffmpeg or ffprobe

Install FFmpeg and ensure Homebrew's bin directory is on `PATH`:

```bash
brew install ffmpeg
uv run clipper doctor --json
```

For an installed CLI, rerun `clipper doctor --json` instead.

## Python dependency import failures

In a checkout, install project dependencies:

```bash
uv sync
uv run clipper doctor --json
```

For an installed CLI, reinstall or upgrade the tool after Issue 026 defines the supported `uv tool install` command.

## LLM configuration problems

Copy `.env.example` to `.env` and set `LLM_BASE_URL` and `LLM_MODEL`. Set `LLM_API_KEY` only if the endpoint requires authentication. Visual scoring can also use `VISION_BASE_URL`, `VISION_MODEL`, and `VISION_API_KEY`; when unset, vision settings fall back to `LLM_*` defaults.

```bash
cp .env.example .env
uv run clipper doctor --check-llm --json
```

Use `--check-llm` only when you intentionally want to contact the configured endpoint.

## Whisper readiness problems

Check configured `WHISPER_MODEL`, `WHISPER_DEVICE`, and `WHISPER_COMPUTE_TYPE`. Loading the model may download files from Hugging Face and can be slow:

```bash
uv run clipper doctor --check-whisper --json
```

Use `--check-whisper` only when you intentionally want to load the configured model; normal `doctor` checks import/config readiness without a model load.

## yt-dlp download failures

Remote `start` and `pipeline` inputs depend on yt-dlp and network/provider availability. Retry with a local file to isolate setup from provider issues, or pass a proxy when needed:

```bash
uv run clipper start ./source/interview.mp4 --name local-check
uv run clipper start "https://youtube.com/watch?v=XXX" --name url-check --proxy PROXY_URL
```

If local input works and URL input fails, inspect the provider URL, network access, proxy, and yt-dlp support for that site.

## Artifact Store path confusion

Clipper writes to `.clipper/` by default. Use `--store PATH` for one command or `CLIPPER_STORE_PATH=PATH` for a session when working across projects:

```bash
uv run clipper list --store ../shared-clipper-store --json
CLIPPER_STORE_PATH=../shared-clipper-store uv run clipper doctor --json
```

## Existing outputs

Most commands fail when target artifacts already exist. Choose explicitly:

```bash
uv run clipper start ./source/interview.mp4 --name interview --reuse
uv run clipper transcribe interview --force
```

## Scoring fails with no context

`score` requires at least one context flag:

```bash
uv run clipper score interview --with-transcript --directive "Find strong sound bites"
uv run clipper score broll --with-visuals --directive "Find visually striking shots"
uv run clipper score interview --with-transcript --with-visuals --directive "Find dialogue supported by visuals"
```

## Missing visual artifacts

Run the visual prerequisites before `--with-visuals` scoring:

```bash
uv run clipper shots broll --contact-sheet
uv run clipper visual broll
```

## JSON output is not parseable

When using `--json`, stdout should be one JSON envelope. Diagnostics from `--verbose` go to stderr. Capture streams separately if needed.
