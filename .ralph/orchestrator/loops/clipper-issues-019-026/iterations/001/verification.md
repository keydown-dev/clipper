# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

## Commands

```bash
python - <<'PY'
# basic skill doc checks
PY
```

Result: failed because `python` is not available on PATH in this environment (`/bin/bash: line 1: python: command not found`). Re-ran with `uv run python`.

```bash
uv run python - <<'PY'
from pathlib import Path
root=Path('skills/clipper')
required=[root/'SKILL.md']+[root/'references'/name for name in ['install.md','doctor.md','store.md','start.md','transcribe.md','transcript-scoring.md','visual-scoring.md','cut.md','montage.md','troubleshooting.md']]
missing=[str(p) for p in required if not p.exists()]
assert not missing, missing
text=(root/'SKILL.md').read_text()
assert text.startswith('---\n'), 'missing frontmatter'
assert 'name: clipper' in text
assert 'description:' in text
for p in required:
    s=p.read_text()
    assert '```bash' in s or p.name=='SKILL.md', f'no bash examples in {p}'
print('skill docs present and frontmatter/basic examples verified')
PY
uv run clipper --help >/tmp/clipper-help.txt
uv run clipper score --help >/tmp/clipper-score-help.txt
grep -q -- '--with-transcript' /tmp/clipper-score-help.txt
grep -q -- '--with-visuals' /tmp/clipper-score-help.txt
printf 'cli help verified\n'
```

Result: passed.

Output:

```text
skill docs present and frontmatter/basic examples verified
cli help verified
```
