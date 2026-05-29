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
- FFmpeg and ffprobe installed with Homebrew:

```bash
brew install ffmpeg
```

Python dependencies should be declared in `pyproject.toml` and installed with `uv`. Expected runtime dependencies include:

- `yt-dlp`
- `faster-whisper`
- `openai`
- `python-dotenv`
- `questionary`

Expected test dependency:

- `pytest`

## Setup

```bash
uv sync
cp .env.example .env
uv run clipper doctor
```

`uv sync` creates the project virtual environment and installs the CLI entry point used by `uv run clipper ...`. `clipper doctor` is the first command to run from a clean checkout; it checks Python, FFmpeg/ffprobe, Python dependencies, artifact-store write access, `.env`/LLM configuration, and faster-whisper import readiness without contacting external services by default.

Example `.env` values:

```env
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=your-key-here  # optional for local endpoints that do not require auth
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0
LLM_TIMEOUT_SECONDS=60
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## Quickstart Local Smoke Flow

This smoke flow validates setup and local-file handling without requiring network access, real LLM credentials, or a Whisper model download:

```bash
uv sync
cp .env.example .env
uv run clipper doctor
ffmpeg -f lavfi -i testsrc2=size=320x180:rate=30 -f lavfi -i sine=frequency=1000 \
  -t 3 -pix_fmt yuv420p /tmp/clipper-smoke.mp4 -y
uv run clipper start /tmp/clipper-smoke.mp4 --name smoke-demo
uv run clipper list
uv run clipper list --json
```

The `start` command copies the local file into `.clipper/smoke-demo/source/` and writes `.clipper/smoke-demo/work/metadata.json`. Re-run the same `start` command with `--reuse` to validate reuse behavior, or `--force` to replace the workspace.

## CLI Overview

Commands that operate on an existing video accept an optional positional `[VIDEO]`. When provided, `[VIDEO]` may be either a video name under `.clipper/` or a path to a video directory. When omitted, Clipper resolves the video as follows: if exactly one video exists in `.clipper/`, use it automatically; if multiple videos exist and the terminal is interactive, use `questionary` to prompt the user to select one; if multiple videos exist under `--json` or non-interactive execution, fail clearly and ask for `[VIDEO]`. If interactive selection is cancelled, exit with code 130 without changing artifacts.

```bash
uv run clipper doctor
uv run clipper start URL_OR_VIDEO_PATH --name optional-video-name
uv run clipper list
uv run clipper transcribe [VIDEO]
uv run clipper score [VIDEO] --directive "Find expressive moments"
uv run clipper cut [VIDEO] --min-score 6
uv run clipper montage [VIDEO]
uv run clipper pipeline URL_OR_VIDEO_PATH --name optional-video-name --directive "Find expressive moments"
```

All commands should support clean human-readable output. Commands that produce structured results should also support:

```bash
--json
```

JSON CLI output should use a consistent result envelope. Successful commands should print:

```json
{"ok":true,"video":"my-video","artifact_path":"work/transcript.json","result":{}}
```

Successful envelopes require `ok` and `result`, and may include `video` and `artifact_path` when applicable.

Failures should print the JSON error envelope to stdout and exit non-zero:

```json
{"ok":false,"error":{"code":"message_code","message":"Human-readable failure"}}
```

When `--json` is active, stdout must remain parseable JSON; verbose diagnostics may go to stderr. Error envelopes require stable `code` and human-readable `message`, and may include optional `details` when useful.

Shared command options should be available after every subcommand through a shared parser/config helper to avoid drift:

```bash
--store PATH
--json
-v
--verbose
```

Examples:

```bash
uv run clipper list --json
uv run clipper transcribe my-video --store .clipper --verbose
```

### Subcommand Reference

| Command | Purpose | Help/smoke command |
| --- | --- | --- |
| `doctor` | Check local dependencies and configuration. | `uv run clipper doctor --json` |
| `start INPUT` | Register/download a source into a video workspace. | `uv run clipper start ./video.mp4 --name local-demo` |
| `list` | Show known video workspaces and artifact flags. | `uv run clipper list --json` |
| `transcribe [VIDEO]` | Produce `work/transcript.json` with faster-whisper. | `uv run clipper transcribe --help` |
| `score [VIDEO]` | Produce `work/scores.json` with an OpenAI-compatible LLM. | `uv run clipper score --help` |
| `cut [VIDEO]` | Cut passing scored segments into `clips/` and `work/clips.json`. | `uv run clipper cut --help` |
| `montage [VIDEO]` | Assemble clips into `output/montage.mp4` and `output/montage.json`. | `uv run clipper montage --help` |
| `pipeline INPUT` | Run start, transcribe, score, cut, and montage. | `uv run clipper pipeline --help` |

Use `uv run clipper COMMAND --help` for the exact options accepted by each subcommand.

## Output and Re-run Semantics

Artifacts should be organized per video under a project-local `.clipper/` artifact store to avoid collisions between runs. The artifact store defaults to `.clipper/`, and may be overridden with per-command `--store PATH` or `CLIPPER_STORE_PATH`. In Clipper, a **video** is a named unit of work rooted at `.clipper/{video}/`. Local video files are copied into the video source directory by default so artifacts remain self-contained. By default, each video directory should use a human-readable lowercase safe source/title stem plus a short stable hash of the canonical input reference, e.g. `.clipper/my-video-a1b2c3d4/`. For remote inputs, only `http` and `https` URLs are supported in v1, and the canonical input reference is the normalized URL. For local inputs, it is the resolved absolute path.

Default behavior when a command's target step output already exists, including `clipper start` against an existing named video:

- fail loudly

Explicit alternatives:

- `--reuse` validates and uses existing step outputs, then continues with missing downstream outputs; for `clipper start`, existing metadata must match the same canonical input reference
- `--force` overwrites each target step output as needed

This behavior should be consistent across commands. The policy is step-output based, not whole-video based: an existing transcript should not prevent scoring unless scoring's own output already exists. Steps with multiple outputs, such as montage's `output/montage.mp4` and `output/montage.json`, treat those files as one output set: default fails if any target exists, `--reuse` requires the complete set to exist and validate, and `--force` overwrites the set. `--reuse` and `--force` are mutually exclusive. Reused JSON artifacts must be loaded and schema-validated; malformed or schema-invalid reused artifacts fail clearly. Artifact schemas should require stable core fields, include top-level `schema_version: 1`, store artifact paths relative to the video directory, and allow additional provider/tool fields for traceability and future extension. Artifacts may include top-level `warnings: []` for non-fatal validation repairs, dropped candidates, or degraded behavior.

## Default Directories

By default, Clipper writes these under per-video directories inside `.clipper/` or the configured artifact store. Each video directory uses exactly these artifact groups:

- `source/` — source videos
- `work/` — metadata, transcripts, scores, manifests
- `clips/` — extracted clips
- `output/` — final montages

Standard artifact filenames within a video should be fixed so commands and agents can discover them consistently:

```text
.clipper/{video}/
  source/source.{ext}
  work/metadata.json
  work/transcript.json
  work/sentences.json
  work/scores.json
  work/clips.json
  work/pipeline.json
  output/montage.mp4
  output/montage.json
```

Core artifact schema examples:

```json
{"schema_version":1,"input_ref":"./video.mp4","input_type":"local","canonical_input_ref":"/abs/video.mp4","source_path":"source/source.mp4","title":"video","duration":123.4,"created_at":"2026-05-26T12:00:00Z"}
```

```json
{"schema_version":1,"source_file":"source/source.mp4","language":"en","duration":123.4,"segments":[{"id":0,"start":0.0,"end":5.2,"text":"Welcome","words":[{"word":"Welcome","start":0.0,"end":0.6}]}]}
```

```json
{"schema_version":1,"source_file":"source/source.mp4","language":"en","duration":123.4,"source_transcript_path":"work/transcript.json","sentences":[{"id":0,"start":0.0,"end":0.6,"text":"Welcome.","source_segments":[0],"word_ranges":[{"segment_id":0,"start_word_index":0,"end_word_index":0}]}]}
```

```json
{"schema_version":1,"source_file":"source/source.mp4","directive":"Find expressive moments","segments":[{"start":12.5,"end":22.0,"score":8,"reason":"Strong reaction"}]}
```

```json
{"schema_version":1,"source_file":"source/source.mp4","clips":[{"id":"clip-0001","path":"clips/clip-0001.mp4","start":12.5,"end":22.0,"duration":9.5,"score":8,"reason":"Strong reaction"}]}
```

```json
{"schema_version":1,"montage_path":"output/montage.mp4","clips":["clips/clip-0001.mp4"],"duration":9.5,"width":1920,"height":1080,"silent":false}
```

```json
{"schema_version":1,"metadata_path":"work/metadata.json","transcript_path":"work/transcript.json","scores_path":"work/scores.json","clips_path":"work/clips.json","montage_path":"output/montage.mp4","clip_count":1,"runtime_seconds":42.0}
```

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
CLIPPER_STORE_PATH=.clipper
```

## Doctor Command

`clipper doctor` should validate the local environment before expensive media steps run.

`clipper doctor --json` should return a result with `checks: [{name, status, message}]` plus summary counts. Check `status` values should be `pass`, `warn`, or `fail`.

Checks should include:

- Python version
- FFmpeg and ffprobe availability
- Python dependency imports
- writable artifact directories
- `.env` / LLM configuration; `LLM_API_KEY` is optional for local/OpenAI-compatible endpoints that do not require auth
- optional LLM connectivity only when explicitly requested, e.g. `--check-llm`
- faster-whisper import/config readiness by default, with real model loading only when explicitly requested, e.g. `--check-whisper`

## Start

`clipper start INPUT` creates a named video workspace under `.clipper/`. For a remote input, it downloads a video from YouTube or any yt-dlp-supported site. For a local input, it copies the local file into the video workspace. `start` only prepares source and metadata; later commands or `pipeline` perform transcription, scoring, cutting, and montage assembly.

Important behavior:

- Accept `--name` to set the video name explicitly; otherwise default to `safe-stem-short-hash`. User-provided names must be slug-safe: lowercase letters, numbers, dashes, and underscores only.
- Use yt-dlp for remote inputs.
- Prefer best video at or below 720p plus best audio.
- Copy local inputs into `source/source.{ext}`.
- For remote downloads, let yt-dlp/FFmpeg choose the actual final extension, discover the resulting `source/source.{ext}` path, and store that video-relative path in metadata `source_path`.
- Save source metadata as JSON.
- Support `--proxy` for remote inputs and forward it to yt-dlp.

Recommended yt-dlp format:

```text
bestvideo[height<=720]+bestaudio/best[height<=720]
```

## List

`clipper list` lists existing videos in `.clipper/` for humans or automation. It should show at least the video name, path, title, duration, and artifact flags for whether metadata, transcript, scores, clips, and montage outputs currently exist.

Metadata should require the traceability core fields `schema_version`, `input_ref`, `input_type`, `canonical_input_ref`, `source_path`, `title`, `duration`, and `created_at`. Timestamps such as `created_at` should be UTC ISO-8601 strings ending in `Z`, e.g. `2026-05-26T12:00:00Z`. `input_type` should be either `remote` for URL inputs or `local` for local file inputs. `title` should come from provider metadata or local filename fallback. `duration` should be numeric and determined via yt-dlp metadata or ffprobe; metadata creation should fail clearly if duration cannot be determined. Metadata may include provider extras such as thumbnail URL, video ID, source URL, extractor, and raw yt-dlp metadata.

## Transcription

`clipper transcribe [VIDEO]` transcribes a source video workspace with faster-whisper.

Defaults:

- model: `small`
- device: `cpu`
- compute type: `int8`

It should support `--language` to force a language, otherwise auto-detect. Transcript `language` may be `null` if faster-whisper does not provide a detected language.

Use `--verbose` to observe long-running transcription without changing stdout output. Verbose lifecycle messages and approximate transcription progress are written to stderr, including model loading, transcription start, progress, detected language, segment count, and transcript path. When combined with `--json`, stdout remains a single parseable JSON envelope and all diagnostics stay on stderr. The first use of a Whisper model may download model files from Hugging Face and can be slow.

Transcript JSON shape:

```json
{
  "schema_version": 1,
  "source_file": "source/source.mp4",
  "language": "en",
  "duration": 3600.5,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.2,
      "text": "Welcome to the show everyone",
      "words": [
        {"word": "Welcome", "start": 0.0, "end": 0.5},
        {"word": "to", "start": 0.5, "end": 0.7}
      ]
    }
  ]
}
```

New transcripts enable faster-whisper `word_timestamps` by default and require each generated segment to include word-level timing in `words`. `clipper transcribe` also writes `work/sentences.json`, a readable sentence-grouped transcript derived from those word timestamps. Sentence `start`/`end` values come from the first and last word in each sentence, and `source_segments` plus inclusive `word_ranges` preserve traceability back to `work/transcript.json`. Older transcript artifacts without `words` remain schema-compatible for raw transcript reuse, but sentence transcript generation requires word timings; rerun transcription with `--force` to regenerate both artifacts.

## Scoring

`clipper score [VIDEO]` takes a video workspace transcript and asks an OpenAI-compatible LLM to identify candidate segments using the chat completions API shape (`client.chat.completions.create`). Default generation settings are temperature `0` and timeout `60` seconds.

The directive is critical:

```bash
uv run clipper score my-video \
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
- Use `work/sentences.json` as the transcript prompt context when available, so the LLM sees complete sentence-level dialogue instead of raw faster-whisper segments.
- Chunk long transcripts into overlapping windows of about 10 minutes with about 30 seconds of overlap.
- Score each window independently.
- Parse valid JSON arrays, including extracting the first JSON array from common markdown/code-fence wrappers.
- Retry once with stricter instructions if extraction/parsing fails.
- Validate each segment has `start`, `end`, `score`, and `reason`.
- Reject individual segments with scores outside 0-10 and report validation warnings.
- Clamp segment times to transcript bounds when safe, and drop segments with `end <= start` or unusable times.
- Normalize segment values where safe.
- Merge or deduplicate overlapping segments, preferring higher scores.
- After validation and merging, deterministically attach overlapping sentence objects from `work/sentences.json` to each scored segment and add a joined `dialogue` string when overlapping sentence text exists. The LLM should not rewrite or restate dialogue for this field.

If scoring produces zero valid candidate segments, `clipper score` should still write `scores.json` with an empty `segments` array and a warning; `clipper cut` is responsible for failing clearly when no clips pass the threshold.

Score JSON shape:

```json
{
  "schema_version": 1,
  "source_file": "source/source.mp4",
  "directive": "Find moments where hosts laugh...",
  "segments": [
    {
      "start": 120.5,
      "end": 135.2,
      "score": 8,
      "reason": "Hosts laugh loudly and gesture expressively",
      "dialogue": "That was unbelievable.",
      "sentences": [
        {
          "id": 12,
          "start": 121.0,
          "end": 123.5,
          "text": "That was unbelievable.",
          "source_segments": [7],
          "word_ranges": [{"segment_id": 7, "start_word_index": 3, "end_word_index": 5}]
        }
      ]
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

### Verbose scoring progress

Use `--verbose` to observe long-running scoring runs:

```bash
uv run clipper score VIDEO --directive "Find compelling clips" --verbose
```

Verbose scoring writes lifecycle diagnostics, model/config details, window progress, warnings, and token usage summaries to stderr. Stdout remains reserved for the normal human result, or for a single parseable JSON envelope when combined with `--json`:

```bash
uv run clipper score VIDEO --directive "Find compelling clips" --json --verbose
```

Token usage is shown only when the configured OpenAI-compatible endpoint returns usage metadata; Clipper does not estimate tokens locally when usage is absent.

## Cutting Clips

`clipper cut [VIDEO]` extracts scored segments from a source video workspace.

Important behavior:

- Default `--min-score` is `6`.
- Merge segments that overlap at all before cutting; merged clips use the earliest start, latest end, maximum score, and combined reasons.
- Sort merged passing segments chronologically and name clip files/IDs sequentially as `clip-0001`, `clip-0002`, etc.
- Accurate re-encoding is the default so clip audio/video stays aligned even when source keyframes do not match scored start times.
- Do not add padding by default; cut exactly the scored/merged start and end times.
- Audio is preserved by default and encoded as AAC.
- `--silent` strips audio.
- If no segments pass the threshold, fail clearly and do not create or update `work/clips.json`, clip files, or an empty montage.

Example FFmpeg shape:

```bash
ffmpeg -ss START -i source.mp4 -t DURATION \
  -map 0:v:0 -map 0:a? \
  -c:v libx264 -preset veryfast -crf 18 \
  -c:a aac -movflags +faststart output_clip.mp4
```

Silent mode should add audio stripping behavior, e.g. `-an`.

## Montage

`clipper montage [VIDEO]` concatenates clips from a video workspace into one normalized video.

First-version behavior:

- chronological ordering by default
- use `work/clips.json` exactly as produced by `clipper cut`; score filtering belongs to `cut`
- support `--min-duration`; fail clearly without creating a montage if selected clips cannot meet it
- support `--max-duration`
- include clips chronologically and trim the final included clip when needed to fit `--max-duration`
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

`clipper pipeline INPUT` creates or reuses a video workspace, then runs the full flow:

1. start source preparation
2. transcribe
3. score
4. cut
5. montage

Example:

```bash
uv run clipper pipeline "https://youtube.com/watch?v=XXX" \
  --name optional-video-name \
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
from clipper.pipeline import run_pipeline

result = run_pipeline(
    input_ref="https://youtube.com/watch?v=XXX",
    directive="Find expressive moments",
    min_score=6,
    force=False,
    reuse=False,
)
```

The result should include paths and summary data for source video, metadata, transcript, scores, clips, montage, counts, durations, and runtime.

Stage 2 narrative edit planning is intentionally deferred. Its extension point is after scoring and before cutting: a future planner can consume the transcript plus `work/scores.json` candidate segments and write an ordered clip plan compatible with the existing cut/montage artifact flow.

## Manual Validation Flows

### Local file

```bash
uv run clipper doctor
uv run clipper start ./source/example.mp4 --name local-example
uv run clipper transcribe local-example --verbose
uv run clipper score local-example --directive "Find expressive reactions" --json
uv run clipper cut local-example --min-score 6
uv run clipper montage local-example --max-duration 60
```

### URL input

```bash
uv run clipper doctor
uv run clipper start "https://youtube.com/watch?v=XXX" --name url-example
uv run clipper pipeline "https://youtube.com/watch?v=XXX" --name url-example --reuse \
  --directive "Find laughter and strong reactions" --max-duration 60
```

Use `--proxy PROXY_URL` with `start` or `pipeline` when yt-dlp needs a proxy. URL validation requires network access and yt-dlp support for the provider.

## Troubleshooting

- `uv run clipper doctor` reports missing `ffmpeg` or `ffprobe`: install FFmpeg with `brew install ffmpeg` and make sure Homebrew's bin directory is on `PATH`.
- `.env` or LLM configuration fails: copy `.env.example` to `.env`, set `LLM_BASE_URL` and `LLM_MODEL`, and set `LLM_API_KEY` only if the endpoint requires authentication.
- Want to test real services: run `uv run clipper doctor --check-llm` for LLM connectivity and `uv run clipper doctor --check-whisper` to load the configured Whisper model.
- `start` says the output already exists: use `--reuse` to validate and reuse matching artifacts, or `--force` to overwrite the target workspace.
- `--json` output is not parseable: rerun without `--verbose`, or check stderr; diagnostics are expected on stderr while stdout remains a single JSON envelope.
- Whisper or LLM tests are skipped by default. Opt in with `CLIPPER_RUN_WHISPER_TESTS=1` or `CLIPPER_RUN_LLM_TESTS=1` when credentials/models are available.

## Error Handling

Exit codes should be minimal and conventional: `0` for success, `1` for command/domain failure, `2` for CLI usage errors, and `130` for user cancellation.

- Commands should exit with clear messages and non-zero status on failure.
- yt-dlp failures should stop the run.
- Whisper model failures should explain how to fix or download/load the model.
- LLM invalid JSON should retry once, then fail clearly.
- No clips above threshold should stop before montage creation; pipeline should exit non-zero and avoid writing/updating the pipeline result, while preserving valid upstream artifacts.
- FFmpeg failures should include the failed operation and relevant stderr. If a cut or montage operation fails after writing partial outputs, Clipper should clean up outputs from the failed operation and avoid writing/updating the result manifest.

## Testing

Default tests should be deterministic and should not require:

- network access
- real LLM credentials
- Whisper model downloads

Testing expectations:

- use pytest
- test schemas and JSON IO
- test scorer prompt/chunking/parsing/retry/validation/overlap behavior
- test cut and montage behavior with generated FFmpeg videos, using ±0.5s tolerance for duration assertions
- test CLI routing, `--json`, `--reuse`, and `--force`
- generate low-resolution 10-second deterministic test videos during tests instead of committing binary video fixtures; fixture helpers should allow duration/size overrides

Generated video fixture helpers live in `tests/helpers/generated_media.py`. Use `generate_test_video(tmp_path)` for the default 10-second 320x180 MP4 with sine-wave audio, or override `duration`, `width`, `height`, and `audio` for cut/montage edge cases. The helper skips FFmpeg-dependent pytest tests when `ffmpeg` or `ffprobe` is unavailable. Use `probe_duration()` with `assert_duration_close()` for duration checks so FFmpeg/ffprobe rounding stays within the project ±0.5s tolerance.

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
