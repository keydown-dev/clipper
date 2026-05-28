# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

Commands run:

```bash
uv run pytest tests/test_issue006.py
```

Result: passed — 9 passed, 1 skipped (real LLM test gated by `CLIPPER_RUN_LLM_TESTS=1`).

```bash
uv run pytest
```

Result: passed — 49 passed, 2 skipped.

Notes:
- Default tests use mocked OpenAI-compatible clients and do not call a real LLM.
- Real LLM smoke test is skipped unless `CLIPPER_RUN_LLM_TESTS=1` is set.
