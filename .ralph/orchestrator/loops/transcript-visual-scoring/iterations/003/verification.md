# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands

- `pytest tests/test_issue015.py tests/test_issue006.py tests/test_issue014.py`
  - Result: failed (`pytest: command not found`; project uses local venv command)
- `.venv/bin/pytest tests/test_issue015.py tests/test_issue006.py tests/test_issue014.py`
  - Result: passed — 24 passed, 1 skipped
- `.venv/bin/pytest`
  - Result: passed — 87 passed, 3 skipped
