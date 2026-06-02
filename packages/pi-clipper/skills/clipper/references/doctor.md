# Doctor

Run doctor before first use on an unknown system and before expensive downloads, transcription, scoring, or media generation.

```bash
uv run clipper doctor --json
```

Successful JSON output is an envelope with check results:

```json
{"ok":true,"result":{"checks":[{"name":"python","status":"pass","message":"Python 3.13.0 meets >= 3.11."}]}}
```

Check statuses are `pass`, `warn`, or `fail`. Treat `fail` as a blocker for the relevant workflow.

## Optional live checks

Default doctor avoids external connectivity and model loading. Opt in only when needed:

```bash
uv run clipper doctor --check-llm --json
uv run clipper doctor --check-whisper --json
uv run clipper doctor --check-llm --check-whisper --json
```

Use `--check-llm` before scoring if credentials or endpoint health are uncertain. Use `--check-whisper` before transcription if model availability/device configuration is uncertain; this may download or load the configured Whisper model.

## Custom Artifact Store

Doctor validates write access to the selected store:

```bash
uv run clipper doctor --store /path/to/.clipper --json
CLIPPER_STORE_PATH=/path/to/.clipper uv run clipper doctor --json
```
