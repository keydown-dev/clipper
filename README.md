# Clipper

Clipper is a local-first Python toolkit for turning long videos or podcasts into scored clips and montages from the terminal.

It runs locally on macOS, uses FFmpeg for media work, faster-whisper for transcription, and an OpenAI-compatible LLM endpoint for transcript scoring. It exposes one CLI, `clipper`, with subcommands for each pipeline step.

## Goals

- Download or register reusable source videos.
- Transcribe and visually analyze sources locally.
- Create editorial projects that include one or more sources, optionally with per-source time ranges.
- Score transcript/visual evidence using an LLM and a user directive.
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
- `scenedetect`

Expected test dependency:

- `pytest`

## Install

The first supported non-development install path is a uv tool install from the Clipper git repository:

```bash
uv tool install git+https://github.com/keydown-dev/clipper.git
clipper doctor --json
```

This installs the `clipper` command and Python runtime dependencies declared in `pyproject.toml`. It does not install native system dependencies, model weights, or LLM services. Install FFmpeg/ffprobe separately, for example with `brew install ffmpeg`; faster-whisper downloads model files when a model is first loaded; transcript and visual scoring require OpenAI-compatible LLM configuration in `.env` or the process environment.

PyPI installation is not supported yet.

## Local development setup

Use these commands when working from a Clipper source checkout:

```bash
uv sync
cp .env.example .env
uv run clipper doctor
```

`uv sync` creates the project virtual environment and installs the CLI entry point used by `uv run clipper ...`. `clipper doctor` is the first command to run from a clean checkout or installed CLI; it checks Python, FFmpeg/ffprobe, Python dependencies, artifact-store write access, `.env`/LLM configuration, and faster-whisper import readiness without contacting external services by default.

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
uv run clipper source /tmp/clipper-smoke.mp4 --name smoke-demo
uv run clipper create smoke-project
uv run clipper include smoke-project smoke-demo
uv run clipper list
uv run clipper list --json
```

For an installed CLI, replace `uv run clipper` with `clipper` and run from any project directory where you want the default `.clipper/` Artifact Store to be created.

The `source` command copies the local file into `.clipper/sources/smoke-demo/source.mp4` and writes `.clipper/sources/smoke-demo/metadata.json`. Re-run the same `source` command with `--reuse` to validate reuse behavior, or `--force` to replace the source. `create` writes `.clipper/projects/smoke-project/project.json`, and `include` records which sources the project will use for project-level scoring, cutting, and montage assembly.

## CLI Overview

Clipper now separates reusable **sources** from editorial **projects**:

- `source` ingests one remote or local recording into `.clipper/sources/{source}/`.
- `transcribe`, `shots`, and `visual` operate on a source because those artifacts are reusable evidence.
- `create` creates an editorial project in `.clipper/projects/{project}/`.
- `include` adds a source to a project, optionally constrained by `--start`/`--end`.
- `score`, `cut`, and `montage` can run against a project by passing the project slug positionally, or can keep the legacy single-source flow with `[SOURCE] --project PROJECT` for scoped outputs under a legacy video/source workspace.

Commands that operate on an existing source accept an optional positional `[SOURCE]`. When omitted in legacy-compatible commands, Clipper still resolves old video workspaces under `.clipper/` as before. Project names are resolved from `.clipper/projects/{project}/project.json` for project-level `score`, `cut`, and `montage`.

```bash
uv run clipper doctor
uv run clipper source URL_OR_VIDEO_PATH --name source-name
uv run clipper transcribe source-name
uv run clipper shots source-name --contact-sheet
uv run clipper visual source-name
uv run clipper create project-name
uv run clipper include project-name source-name --start 00:30 --end 02:00
uv run clipper score project-name --with-transcript --with-visuals --directive "Find expressive moments"
uv run clipper cut project-name --min-score 6
uv run clipper montage project-name
uv run clipper pipeline URL_OR_VIDEO_PATH --name optional-source-name --directive "Find expressive moments"
```

All commands should support clean human-readable output. Commands that produce structured results should also support:

```bash
--json
```

JSON CLI output should use a consistent result envelope. Successful commands should print:

```json
{"ok":true,"video":"source-a","artifact_path":".clipper/sources/source-a/transcript.json","result":{}}
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
| `source INPUT --name SOURCE` | Register/download a reusable source. | `uv run clipper source ./video.mp4 --name local-demo` |
| `create PROJECT` | Create an empty editorial project. | `uv run clipper create story-a` |
| `include PROJECT SOURCE` | Include a source in a project, optionally ranged. | `uv run clipper include story-a local-demo --start 60 --end 120` |
| `list` | Show known legacy video workspaces and artifact flags. | `uv run clipper list --json` |
| `transcribe [SOURCE]` | Produce source-level `transcript.json` and `sentences.json`. | `uv run clipper transcribe --help` |
| `score PROJECT` | Produce project-level `scores.json` with an OpenAI-compatible LLM. | `uv run clipper score --help` |
| `shots [SOURCE]` | Detect visual shots and produce `shots.json` plus representative frames. | `uv run clipper shots --help` |
| `visual [SOURCE]` | Analyze representative shot frames with a multimodal OpenAI-compatible model. | `uv run clipper visual --help` |
| `cut PROJECT` | Cut passing scored project segments into project `clips/` and `clips.json`. | `uv run clipper cut --help` |
| `montage PROJECT` | Assemble project clips into `montage.mp4` and `montage.json`. | `uv run clipper montage --help` |
| `pipeline INPUT` | Run the compatibility single-source pipeline. | `uv run clipper pipeline --help` |

Use `uv run clipper COMMAND --help` for the exact options accepted by each subcommand.

## Output and Re-run Semantics

Artifacts are organized under a project-local `.clipper/` Artifact Store. The store defaults to `.clipper/`, and may be overridden with per-command `--store PATH` or `CLIPPER_STORE_PATH`.

Current source/project layout:

```text
.clipper/
  sources/{source}/
    source.{ext}
    metadata.json
    transcript.json
    sentences.json
    shots.json
    frames/shot-0001.jpg
    visual-index.json
    shot-contact-sheet.jpg
  projects/{project}/
    project.json
    scores.json
    clips.json
    clips/clip-0001.mp4
    montage.mp4
    montage.json
```

A **source** is a named reusable recording rooted at `.clipper/sources/{source}/`. A **project** is an editorial assembly rooted at `.clipper/projects/{project}/`; it references sources in `project.json` and owns scoring, cutting, and montage outputs. Local video files are copied into the source directory by default so artifacts remain self-contained. For remote inputs, only `http` and `https` URLs are supported in v1, and the canonical input reference is the normalized URL. For local inputs, it is the resolved absolute path.

Default behavior when a command's target step output already exists, including `clipper source` against an existing named source:

- fail loudly

Explicit alternatives:

- `--reuse` validates and uses existing step outputs, then continues with missing downstream outputs; for `clipper source`, existing metadata must match the same canonical input reference
- `--force` overwrites each target step output as needed

This behavior should be consistent across commands. The policy is step-output based, not whole-source or whole-project based: an existing transcript should not prevent scoring unless scoring's own output already exists. Steps with multiple outputs, such as project montage's `montage.mp4` and `montage.json`, treat those files as one output set: default fails if any target exists, `--reuse` requires the complete set to exist and validate, and `--force` overwrites the set. `--reuse` and `--force` are mutually exclusive. Reused JSON artifacts must be loaded and schema-validated; malformed or schema-invalid reused artifacts fail clearly. Artifact schemas should require stable core fields, include top-level `schema_version: 1`, store artifact paths relative to the owning source or project directory, and allow additional provider/tool fields for traceability and future extension. Artifacts may include top-level `warnings: []` for non-fatal validation repairs, dropped candidates, or degraded behavior.

## Default Directories

By default, source evidence is flat inside `.clipper/sources/{source}/`, while project outputs are flat inside `.clipper/projects/{project}/`. Paths inside JSON manifests are relative to the owning source or project directory.

Standard artifact filenames should be fixed so commands and agents can discover them consistently:

```text
.clipper/sources/{source}/
  source.{ext}
  metadata.json
  transcript.json
  sentences.json
  shots.json
  frames/shot-0001.jpg
  visual-index.json
  shot-contact-sheet.jpg

.clipper/projects/{project}/
  project.json
  scores.json
  clips.json
  clips/clip-0001.mp4
  montage.mp4
  montage.json
```

Core artifact schema examples:

```json
{"schema_version":1,"input_ref":"./video.mp4","input_type":"local","canonical_input_ref":"/abs/video.mp4","source_path":"source.mp4","title":"video","duration":123.4,"created_at":"2026-05-26T12:00:00Z"}
```

```json
{"schema_version":1,"source_file":"source.mp4","language":"en","duration":123.4,"segments":[{"id":0,"start":0.0,"end":5.2,"text":"Welcome","words":[{"word":"Welcome","start":0.0,"end":0.6}]}]}
```

```json
{"schema_version":1,"source_file":"source.mp4","language":"en","duration":123.4,"source_transcript_path":"transcript.json","sentences":[{"id":0,"start":0.0,"end":0.6,"text":"Welcome.","source_segments":[0],"word_ranges":[{"segment_id":0,"start_word_index":0,"end_word_index":0}]}]}
```

```json
{"schema_version":1,"name":"story-a","sources":[{"name":"source-a","start":12.5,"end":120.0}],"created_at":"2026-05-26T12:00:00Z"}
```

```json
{"schema_version":1,"source_file":"project.json","directive":"Find expressive moments","segments":[{"source":"source-a","start":12.5,"end":22.0,"score":8,"reason":"Strong reaction"}]}
```

```json
{"schema_version":1,"source_file":"project.json","clips":[{"id":"clip-0001","path":"clips/clip-0001.mp4","source":"source-a","start":12.5,"end":22.0,"duration":9.5,"score":8,"reason":"Strong reaction"}]}
```

```json
{"schema_version":1,"source_file":"source.mp4","shots":[{"id":"shot-0001","start":0.0,"end":4.2,"duration":4.2,"representative_frame_path":"frames/shot-0001.jpg","representative_time":2.1,"quality":{"score":0.82,"sharpness":0.9,"contrast":0.7,"exposure":0.8}}],"detection":{"tool":"pyscenedetect","threshold":27.0,"min_duration":0.5,"samples_per_shot":5}}
```

```json
{"schema_version":1,"montage_path":"montage.mp4","clips":["clips/clip-0001.mp4"],"duration":9.5,"width":1920,"height":1080,"silent":false}
```

```json
{"schema_version":1,"metadata_path":"metadata.json","transcript_path":"transcript.json","scores_path":"scores.json","clips_path":"clips.json","montage_path":"montage.mp4","clip_count":1,"runtime_seconds":42.0}
```

All scripts should handle absolute and relative paths and create required directories automatically.

## Migration and Compatibility

The source/project layout supersedes the original single video workspace layout, but the compatibility surface is intentionally conservative:

- Prefer `clipper source INPUT --name SOURCE` instead of `clipper start INPUT --name SOURCE` for new workflows.
- `clipper start` remains as a deprecated alias. It ingests the source under `.clipper/sources/{source}/`, mirrors a legacy `.clipper/{source}/` workspace for older commands/scripts, and prints a deprecation warning on human-readable runs.
- Existing legacy workspaces under `.clipper/{video}/` still resolve for commands that historically accepted `[VIDEO]`.
- `transcribe`, `shots`, and `visual` prefer `.clipper/sources/{name}/` when a source and a legacy video share the same name.
- `score PROJECT`, `cut PROJECT`, and `montage PROJECT` prefer a project when `.clipper/projects/{project}/project.json` exists. Use `--project PROJECT` with a source/video positional argument only for the older scoped single-source output layout.
- Legacy scoped outputs still use paths such as `.clipper/{video}/work/projects/{project}/scores.json`, `.clipper/{video}/clips/projects/{project}/`, and `.clipper/{video}/output/projects/{project}/`. New project-level outputs live directly under `.clipper/projects/{project}/`.
- To migrate an old single-video workflow, ingest or re-ingest the source with `clipper source ... --name SOURCE`, run source-level analysis if needed, then create a project and include the source:

```bash
uv run clipper source ./episode.mp4 --name episode
uv run clipper transcribe episode --reuse
uv run clipper shots episode --reuse
uv run clipper visual episode --reuse
uv run clipper create episode-highlights
uv run clipper include episode-highlights episode
uv run clipper score episode-highlights --with-transcript --directive "Find highlights"
uv run clipper cut episode-highlights --min-score 6
uv run clipper montage episode-highlights --max-duration 60
```

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

## Source Ingestion

`clipper source INPUT --name SOURCE` creates a named source under `.clipper/sources/`. For a remote input, it downloads a video from YouTube or any yt-dlp-supported site. For a local input, it copies the local file into the source directory. `source` only prepares source media and metadata; later commands or a project perform transcription, scoring, cutting, and montage assembly.

Important behavior:

- Require `--name` to set the source slug. User-provided names must be slug-safe: lowercase letters, numbers, dashes, and underscores only.
- Use yt-dlp for remote inputs.
- Prefer best video at or below 720p plus best audio.
- Copy local inputs into `source.{ext}`.
- For remote downloads, let yt-dlp/FFmpeg choose the actual final extension, discover the resulting `source.{ext}` path, and store that source-relative path in metadata `source_path`.
- Save source metadata as JSON.
- Support `--proxy` for remote inputs and forward it to yt-dlp.
- Keep `clipper start INPUT --name SOURCE` as a deprecated compatibility alias that also mirrors a legacy `.clipper/{source}/` workspace.

Recommended yt-dlp format:

```text
bestvideo[height<=720]+bestaudio/best[height<=720]
```

## List

`clipper list` lists existing legacy videos in `.clipper/` for humans or automation. It should show at least the video name, path, title, duration, and artifact flags for whether metadata, transcript, scores, clips, and montage outputs currently exist. Source/project listing is intentionally separate future work; inspect `.clipper/sources/` and `.clipper/projects/` directly until that CLI surface is added.

Metadata should require the traceability core fields `schema_version`, `input_ref`, `input_type`, `canonical_input_ref`, `source_path`, `title`, `duration`, and `created_at`. Timestamps such as `created_at` should be UTC ISO-8601 strings ending in `Z`, e.g. `2026-05-26T12:00:00Z`. `input_type` should be either `remote` for URL inputs or `local` for local file inputs. `title` should come from provider metadata or local filename fallback. `duration` should be numeric and determined via yt-dlp metadata or ffprobe; metadata creation should fail clearly if duration cannot be determined. Metadata may include provider extras such as thumbnail URL, video ID, source URL, extractor, and raw yt-dlp metadata.

## Transcription

`clipper transcribe [SOURCE]` transcribes a source with faster-whisper. It prefers `.clipper/sources/{source}/` and falls back to legacy `.clipper/{video}/` workspaces for compatibility.

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
  "source_file": "source.mp4",
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

New transcripts enable faster-whisper `word_timestamps` by default and require each generated segment to include word-level timing in `words`. `clipper transcribe` also writes `sentences.json`, a readable sentence-grouped transcript derived from those word timestamps. Sentence `start`/`end` values come from the first and last word in each sentence, and `source_segments` plus inclusive `word_ranges` preserve traceability back to `transcript.json`. Older transcript artifacts without `words` remain schema-compatible for raw transcript reuse, but sentence transcript generation requires word timings; rerun transcription with `--force` to regenerate both artifacts.

## Scoring

`clipper score PROJECT` asks an OpenAI-compatible LLM to identify candidate segments using explicitly selected evidence from all sources included in the project. Callers must choose at least one context flag: `--with-transcript`, `--with-visuals`, or both. Default generation settings are temperature `0` and timeout `60` seconds. For a single-source compatibility flow, `clipper score SOURCE --project PROJECT` writes scoped outputs under the legacy source/video workspace instead of `.clipper/projects/PROJECT/`.

Examples:

```bash
# Sound-bite scoring from sentence-level dialogue.
uv run clipper score story-a \
  --with-transcript \
  --directive "Find moments where hosts laugh, react strongly, or discuss surprising topics"

# Silent visual montage scoring from cached shot/vision artifacts.
uv run clipper score story-a \
  --with-visuals \
  --directive "Find scenic, kinetic, or visually striking silent shots"

# Combined multimodal scoring.
uv run clipper score story-a \
  --with-transcript --with-visuals \
  --directive "Find moments where strong dialogue is reinforced by expressive visuals"
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
- Use each source's `sentences.json` as the transcript prompt context when available, so the LLM sees complete sentence-level dialogue instead of raw faster-whisper segments.
- Chunk long transcripts into overlapping windows of about 10 minutes with about 30 seconds of overlap.
- Score each window independently.
- Parse valid JSON arrays, including extracting the first JSON array from common markdown/code-fence wrappers.
- Retry once with stricter instructions if extraction/parsing fails.
- Validate each segment has `start`, `end`, `score`, and `reason`.
- Reject individual segments with scores outside 0-10 and report validation warnings.
- Clamp segment times to transcript bounds when safe, and drop segments with `end <= start` or unusable times.
- Normalize segment values where safe.
- Merge or deduplicate overlapping segments, preferring higher scores.
- After validation and merging, deterministically attach overlapping sentence objects from the matching source's `sentences.json` to each scored segment and add a joined `dialogue` string when overlapping sentence text exists. The LLM should not rewrite or restate dialogue for this field.

If scoring produces zero valid candidate segments, `clipper score` should still write `scores.json` with an empty `segments` array and a warning; `clipper cut` is responsible for failing clearly when no clips pass the threshold.

Score JSON shape:

```json
{
  "schema_version": 1,
  "source_file": "project.json",
  "directive": "Find moments where hosts laugh...",
  "segments": [
    {
      "source": "source-a",
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
uv run clipper score VIDEO --with-transcript --directive "Find compelling clips" --verbose
```

Verbose scoring writes lifecycle diagnostics, model/config details, window progress, warnings, and token usage summaries to stderr. Stdout remains reserved for the normal human result, or for a single parseable JSON envelope when combined with `--json`:

```bash
uv run clipper score VIDEO --with-transcript --directive "Find compelling clips" --json --verbose
```

Token usage is shown only when the configured OpenAI-compatible endpoint returns usage metadata; Clipper does not estimate tokens locally when usage is absent.

## Cutting Clips

`clipper cut PROJECT` extracts scored project segments from their referenced sources.

Important behavior:

- Default `--min-score` is `6`.
- Merge segments that overlap at all before cutting; merged clips use the earliest start, latest end, maximum score, and combined reasons.
- Sort merged passing segments chronologically and name clip files/IDs sequentially as `clip-0001`, `clip-0002`, etc.
- Accurate re-encoding is the default so clip audio/video stays aligned even when source keyframes do not match scored start times.
- Do not add padding by default; cut exactly the scored/merged start and end times.
- Audio is preserved by default and encoded as AAC.
- `--silent` strips audio.
- If no segments pass the threshold, fail clearly and do not create or update project `clips.json`, clip files, or an empty montage.

Example FFmpeg shape:

```bash
ffmpeg -ss START -i source.mp4 -t DURATION \
  -map 0:v:0 -map 0:a? \
  -c:v libx264 -preset veryfast -crf 18 \
  -c:a aac -movflags +faststart output_clip.mp4
```

Silent mode should add audio stripping behavior, e.g. `-an`.

## Montage

`clipper montage PROJECT` concatenates clips from a project into one normalized video.

First-version behavior:

- chronological ordering by default
- use project `clips.json` exactly as produced by `clipper cut`; score filtering belongs to `cut`
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

`clipper pipeline INPUT` is the compatibility single-source pipeline. It creates or reuses a source/legacy workspace, then runs the full flow:

1. source preparation
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

Stage 2 narrative edit planning is intentionally deferred. Its extension point is after project scoring and before cutting: a future planner can consume the source transcripts plus project `scores.json` candidate segments and write an ordered clip plan compatible with the existing cut/montage artifact flow.

## Manual Validation Flows

### Local source and project

```bash
uv run clipper doctor
uv run clipper source ./source/example.mp4 --name local-example
uv run clipper transcribe local-example --verbose
uv run clipper create local-highlights
uv run clipper include local-highlights local-example
uv run clipper score local-highlights --with-transcript --directive "Find expressive reactions" --json
uv run clipper cut local-highlights --min-score 6
uv run clipper montage local-highlights --max-duration 60
```

### URL input

```bash
uv run clipper doctor
uv run clipper source "https://youtube.com/watch?v=XXX" --name url-example
uv run clipper create url-highlights
uv run clipper include url-highlights url-example
uv run clipper pipeline "https://youtube.com/watch?v=XXX" --name url-example --reuse \
  --directive "Find laughter and strong reactions" --max-duration 60
```

Use `--proxy PROXY_URL` with `start` or `pipeline` when yt-dlp needs a proxy. URL validation requires network access and yt-dlp support for the provider.

## Troubleshooting

- `uv run clipper doctor` reports missing `ffmpeg` or `ffprobe`: install FFmpeg with `brew install ffmpeg` and make sure Homebrew's bin directory is on `PATH`.
- `.env` or LLM configuration fails: copy `.env.example` to `.env`, set `LLM_BASE_URL` and `LLM_MODEL`, and set `LLM_API_KEY` only if the endpoint requires authentication.
- Want to test real services: run `uv run clipper doctor --check-llm` for LLM connectivity and `uv run clipper doctor --check-whisper` to load the configured Whisper model.
- `source` says the output already exists: use `--reuse` to validate and reuse matching artifacts, or `--force` to overwrite the target source.
- `score PROJECT`, `cut PROJECT`, or `montage PROJECT` is using the wrong target: if `.clipper/projects/PROJECT/project.json` exists, the positional name is treated as a project; use a source name plus `--project PROJECT` only for legacy scoped single-source outputs.
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
