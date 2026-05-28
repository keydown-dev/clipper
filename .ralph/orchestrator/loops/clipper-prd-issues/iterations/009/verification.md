# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands run

```bash
uv run pytest tests/test_issue006.py
```

Result: passed — 15 passed, 1 skipped.

```bash
uv run pytest
```

Result: failed in pre-existing/unrelated config environment isolation test:
`tests/test_issue002.py::test_config_defaults_env_and_dotenv` expected `WHISPER_MODEL=base` from its temp dotenv but observed `small` after earlier tests loaded the project `.env` into process environment. All issue 006 scoring tests passed.

## Acceptance coverage

- Non-verbose scoring remains quiet on stderr.
- `--json --verbose` keeps stdout parseable JSON and sends diagnostics/progress to stderr.
- Verbose output includes video/transcript lifecycle, directive, LLM base URL/model/temperature/timeout, transcript segment count, window count, progress to 100%, scores path, warnings, and token usage.
- Token usage is accumulated when mocked OpenAI-style usage metadata is present, including retry responses.
- Missing usage metadata is reported without local token estimation.
- Reuse mode does not instantiate/call the LLM and does not show scoring progress.
- Non-TTY progress uses plain lines and no carriage-return/control-character animation.
