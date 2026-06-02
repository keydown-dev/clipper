# Troubleshooting

Start with doctor:

```bash
uv run clipper doctor --json
```

## Missing ffmpeg or ffprobe

Install FFmpeg and ensure Homebrew's bin directory is on `PATH`:

```bash
brew install ffmpeg
uv run clipper doctor --json
```

## Python dependency import failures

Install project dependencies:

```bash
uv sync
uv run clipper doctor --json
```

## LLM configuration problems

Copy `.env.example` to `.env` and set `LLM_BASE_URL` and `LLM_MODEL`. Set `LLM_API_KEY` only if the endpoint requires authentication.

```bash
cp .env.example .env
uv run clipper doctor --check-llm --json
```

## Whisper readiness problems

Check configured model/device/compute type. Loading the model may download files and can be slow:

```bash
uv run clipper doctor --check-whisper --json
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
