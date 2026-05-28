# Issue 002 — Config, Schemas, JSON IO, and Artifact Layout

## Goal

Create the shared contracts and artifact semantics used by every pipeline step.

## Depends On

- Issue 001

## Tasks

- Implement environment/config loading with `.env` support.
- Add `.env.example` with LLM and Whisper defaults from `README.md`, documenting that `LLM_API_KEY` is optional for local/OpenAI-compatible endpoints that do not require auth.
- Implement path and JSON IO helpers using `pathlib.Path`.
- Implement video resolution helpers: explicit `[VIDEO]` may be either a video name under `.clipper/` or a path to a video directory; omitted `[VIDEO]` uses the sole video automatically, uses `questionary` to prompt when multiple videos exist in an interactive terminal, exits 130 without changing artifacts when selection is cancelled, and fails clearly when multiple videos exist under `--json` or non-interactive execution.
- Implement shared video listing support for `clipper list`, including video name, path, title, duration, and artifact flags for metadata, transcript, scores, clips, and montage outputs.
- Define typed contracts for metadata, transcript, scores, clip manifests, montage results, and pipeline results, with top-level `schema_version: 1`, optional top-level `warnings: []`, video-relative artifact paths, strict required core fields, and allowance for additional provider/tool fields.
- Require metadata core fields: `schema_version`, `input_ref`, `input_type`, `canonical_input_ref`, `source_path`, `title`, numeric `duration`, and `created_at`; timestamps such as `created_at` must be UTC ISO-8601 strings ending in `Z`; `input_type` must be `remote` for URL inputs or `local` for local file inputs; `title` may fall back to local filename, but `duration` must be probed or obtained from provider metadata.
- Require transcript core fields: `schema_version`, `source_file`, `language`, numeric `duration`, and `segments` with `id`, `start`, `end`, `text`; `language` may be `null` if not detected.
- Require score core fields: `schema_version`, `source_file`, `directive`, and `segments` with `start`, `end`, `score`, `reason`.
- Require clip manifest core fields: `schema_version`, `source_file`, and `clips` with `id`, `path`, `start`, `end`, `duration`, `score`, `reason`.
- Require montage result core fields: `schema_version`, `montage_path`, `clips`, numeric `duration`, `width`, `height`, and `silent`.
- Require pipeline result core fields in `work/pipeline.json`: `schema_version`, `metadata_path`, `transcript_path`, `scores_path`, `clips_path`, `montage_path`, `clip_count`, and `runtime_seconds`.
- Include defaults for a project-local `.clipper/` artifact store configurable via per-command `--store PATH` or `CLIPPER_STORE_PATH`, exactly four video artifact groups (`source/`, `work/`, `clips/`, `output/`), Whisper CPU/int8 settings, LLM base URL/model, 1920x1080 output dimensions, and default min score 6.
- Implement per-video artifact directory creation under `.clipper/`, named by the user when provided or defaulting to a lowercase safe source/title stem plus a short stable hash of the canonical input reference: normalized URL for URLs, resolved absolute path for local files. User-provided names must be slug-safe: lowercase letters, numbers, dashes, and underscores only.
- Standardize fixed artifact filenames within each video: `source/source.{ext}`, `work/metadata.json`, `work/transcript.json`, `work/scores.json`, `work/clips.json`, `work/pipeline.json`, `output/montage.mp4`, and `output/montage.json`.
- Implement step-output existing-output policy: default fail when a target step output exists, `--reuse` validates and uses existing step outputs, and `--force` overwrites target step outputs as needed. Steps with multiple outputs treat those files as one output set: default fails if any target exists, `--reuse` requires the complete set to exist and validate, and `--force` overwrites the set.
- Make `--reuse` and `--force` mutually exclusive.
- Ensure reused JSON artifacts are loaded and schema-validated; malformed or schema-invalid reused artifacts fail clearly.
- Implement shared JSON result formatting helpers for CLI commands using a consistent envelope: success `{"ok": true, "video": "...", "artifact_path": "...", "result": {...}}` where `video`/`artifact_path` are included when applicable; failure `{"ok": false, "error": {"code": "...", "message": "..."}}` with optional `details`.
- When `--json` is active, print both success and failure envelopes to stdout, keep stdout parseable JSON, and send verbose diagnostics to stderr.

## Acceptance Criteria

- Config defaults and env overrides are tested, including `.env` loading.
- `.env.example` documents the required LLM and Whisper values.
- JSON read/write behavior and CLI JSON result envelopes are tested.
- Artifact layout generation is tested, including the default `.clipper/` artifact store, `--store PATH`/`CLIPPER_STORE_PATH` overrides, user-provided video naming, default `safe-stem-short-hash` video directory naming, and fixed artifact filenames.
- Existing-output policy is tested for fail, reuse, force, mutual exclusion, and invalid reused JSON at step-output granularity.
- Schema validation is tested to require `schema_version: 1`, video-relative artifact paths, and core fields while allowing additional provider/tool fields.
