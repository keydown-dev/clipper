# Clipper

Clipper is a local-first Python toolkit for turning long videos or podcasts into scored clips and montages from the terminal.

It runs locally on macOS, uses FFmpeg for media work, faster-whisper for transcription, and an OpenAI-compatible LLM endpoint for transcript scoring. It exposes one CLI, `clipper`, with subcommands for each pipeline step.

## Goals

- Download or register source videos.
- Transcribe videos locally.
- Score transcript segments using an LLM and a user directive.
- Cut scored segments into clips.
- Assemble clips into a montage.
- Keep each step independently runnable and importable.
- Support automation agents through stable JSON outputs.

## Non-goals

- No Docker-first workflow.
- No server/VPS deployment.
- No web UI.
- No social scheduling.
- No Remotion/branding overlay system.
- No GPU requirement.
- No Stage 2 narrative edit planner in the first implementation.

## Requirements

- macOS
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg installed with Homebrew:

```bash
brew install ffmpeg
```

Python dependencies should be declared in `pyproject.toml` and installed with `uv`. Expected runtime dependencies include:

- `yt-dlp`
- `faster-whisper`
- `openai`
- `python-dotenv`

Expected test dependency:

- `pytest`

## Setup

```bash
uv sync
cp .env.example .env
uv run clipper doctor
```

Example `.env` values:

```env
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=your-key-here
LLM_MODEL=deepseek-v4-flash
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## CLI Overview

```bash
uv run clipper doctor
uv run clipper download URL
uv run clipper transcribe VIDEO_PATH
uv run clipper score TRANSCRIPT_JSON --directive "Find expressive moments"
uv run clipper cut SCORES_JSON --min-score 6
uv run clipper montage CLIP_MANIFEST_OR_DIR
uv run clipper pipeline URL_OR_VIDEO_PATH --directive "Find expressive moments"
```

All commands should support clean human-readable output. Commands that produce structured results should also support:

```bash
--json
```

Verbose debugging should be available with:

```bash
-v
--verbose
```

## Output and Re-run Semantics

Artifacts should be organized per video/job to avoid collisions between runs.

Default behavior when outputs already exist:

- fail loudly

Explicit alternatives:

- `--reuse` reuses existing outputs
- `--force` overwrites existing outputs

This behavior should be consistent across commands.

## Default Directories

The implementation may organize these under per-video/job artifact directories, but the conceptual artifact groups are:

- `source/` — source videos
- `work/` — metadata, transcripts, scores, manifests
- `clips/` — extracted clips
- `output/` — final montages

All scripts should handle absolute and relative paths and create required directories automatically.

## Config Defaults

Recommended defaults:

```text
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
LLM_BASE_URL=https://ollama.com/v1
LLM_MODEL=deepseek-v4-flash
DEFAULT_WIDTH=1920
DEFAULT_HEIGHT=1080
DEFAULT_MIN_SCORE=6
```

## Doctor Command

`clipper doctor` should validate the local environment before expensive media steps run.

Checks should include:

- Python version
- FFmpeg availability
- Python dependency imports
- writable artifact directories
- `.env` / LLM configuration
- optional LLM connectivity
- faster-whisper/model readiness or actionable warnings

## Download

`clipper download` downloads a video from YouTube or any yt-dlp-supported site.

Important behavior:

- Use yt-dlp.
- Prefer best video at or below 720p plus best audio.
- Save source metadata as JSON.
- Support `--proxy` and forward it to yt-dlp.

Recommended yt-dlp format:

```text
bestvideo[height<=720]+bestaudio/best[height<=720]
```

Metadata should include available fields such as title, duration, thumbnail URL, video ID, source URL, and local source path.

## Transcription

`clipper transcribe` transcribes a source video with faster-whisper.

Defaults:

- model: `small`
- device: `cpu`
- compute type: `int8`

It should support `--language` to force a language, otherwise auto-detect.

Transcript JSON shape:

```json
{
  "source_file": "podcast_episode.mp4",
  "language": "en",
  "duration": 3600.5,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.2,
      "text": "Welcome to the show everyone"
    }
  ]
}
```

## Scoring

`clipper score` takes a transcript JSON and asks an OpenAI-compatible LLM to identify candidate segments.

The directive is critical:

```bash
uv run clipper score work/example_transcript.json \
  --directive "Find moments where hosts laugh, react strongly, or discuss surprising topics"
```

Default directive should look for visually interesting or engaging moments: expressive reactions, laughter, surprise, disagreement, animated discussion, or strong emotional beats.

### LLM System Prompt

Use this system prompt as the baseline scorer contract:

```text
You are a video clip scorer. Given a transcript with timestamps, identify the most visually interesting segments based on the user's directive.

For each segment, provide:
- start: start time in seconds (float)
- end: end time in seconds (float) — segments should be 5-15 seconds long
- score: 0-10 rating of how well this matches the directive
- reason: one-sentence explanation of why this segment scores highly

Return ONLY a JSON array of objects. No markdown, no explanation, no code fences. Example:
[{"start": 12.5, "end": 22.0, "score": 8, "reason": "Hosts laugh and gesture expressively"}]
```

### Robust Scoring Requirements

- Include timestamps in the transcript prompt.
- Chunk long transcripts into overlapping windows of about 10 minutes.
- Score each window independently.
- Parse only valid JSON.
- Retry once with stricter instructions if the model returns invalid JSON.
- Validate each segment has `start`, `end`, `score`, and `reason`.
- Normalize segment values where safe.
- Merge or deduplicate overlapping segments, preferring higher scores.

Score JSON shape:

```json
{
  "source_file": "podcast_episode.mp4",
  "directive": "Find moments where hosts laugh...",
  "segments": [
    {
      "start": 120.5,
      "end": 135.2,
      "score": 8,
      "reason": "Hosts laugh loudly and gesture expressively"
    }
  ]
}
```

Directive examples:

```text
Find moments of genuine laughter and physical comedy
Find segments with strong emotional reactions — surprise, disagreement, awe
Find quiet, contemplative moments with thoughtful discussion
Find any segment where someone says something controversial or surprising
```

## Cutting Clips

`clipper cut` extracts scored segments from a source video.

Important behavior:

- Default `--min-score` is `6`.
- Merge segments that overlap significantly before cutting.
- Fast stream-copy cutting is the default.
- Audio is preserved by default.
- `--silent` strips audio.
- If no segments pass the threshold, fail clearly and do not create an empty montage.

Example fast FFmpeg shape:

```bash
ffmpeg -ss START -to END -i source.mp4 -c copy output_clip.mp4
```

Silent mode should add audio stripping behavior, e.g. `-an`.

## Montage

`clipper montage` concatenates clips into one normalized video.

First-version behavior:

- chronological ordering by default
- include clips above the selected score threshold
- support `--min-duration`
- support `--max-duration`
- eliminate or trim clips as needed to fit maximum duration
- preserve audio by default
- `--silent` strips audio
- normalize output dimensions, default `1920x1080`

Recommended FFmpeg concat/filter shape:

```bash
ffmpeg -f concat -safe 0 -i filelist.txt \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -preset medium -crf 23 montage.mp4
```

Silent mode should add `-an`.

## Pipeline

`clipper pipeline` runs the full flow:

1. download/register source
2. transcribe
3. score
4. cut
5. montage

Example:

```bash
uv run clipper pipeline "https://youtube.com/watch?v=XXX" \
  --directive "Find moments of laughter and expressiveness" \
  --min-score 6 \
  --max-duration 60
```

Local file example:

```bash
uv run clipper pipeline ./source/example.mp4 \
  --directive "Find surprising moments" \
  --reuse
```

The pipeline should also be importable:

```python
from clip_pipe.pipeline import run_pipeline

result = run_pipeline(
    input_ref="https://youtube.com/watch?v=XXX",
    directive="Find expressive moments",
    min_score=6,
    force=False,
    reuse=False,
)
```

The result should include paths and summary data for source video, metadata, transcript, scores, clips, montage, counts, durations, and runtime.

## Error Handling

- Commands should exit with clear messages and non-zero status on failure.
- yt-dlp failures should stop the run.
- Whisper model failures should explain how to fix or download/load the model.
- LLM invalid JSON should retry once, then fail clearly.
- No clips above threshold should stop before montage creation.
- FFmpeg failures should include the failed operation and relevant stderr.

## Testing

Default tests should be deterministic and should not require:

- network access
- real LLM credentials
- Whisper model downloads

Testing expectations:

- use pytest
- test schemas and JSON IO
- test scorer prompt/chunking/parsing/retry/validation/overlap behavior
- test cut and montage behavior with generated FFmpeg videos
- test CLI routing, `--json`, `--reuse`, and `--force`
- generate tiny test videos during tests instead of committing binary video fixtures

Optional integration tests:

```bash
CLIPPER_RUN_LLM_TESTS=1 uv run pytest
CLIPPER_RUN_WHISPER_TESTS=1 uv run pytest
```

## Style

- Clean, well-typed Python 3.11+.
- Use `pathlib.Path` for paths.
- Use dataclasses or TypedDicts for structured data.
- Use argparse for the CLI.
- Use python-dotenv for `.env` loading.
- Add docstrings to public functions.
- Add type hints to public function signatures.
