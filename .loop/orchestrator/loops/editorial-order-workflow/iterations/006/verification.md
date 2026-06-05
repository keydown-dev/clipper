# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: Status: passed

## Commands

```bash
uv run clipper order --help
uv run clipper montage --help
uv run clipper contact-sheet --help
uv run clipper trim --help
```

Result: passed. Verified documented flags exist: `order --show/--reset/--move/--swap`, full replacement positional IDs, `montage --chronological`, `contact-sheet`, and `trim --start/--end/--duration`.

```bash
cd packages/pi-clipper && npm run sync:skill
```

Result: passed. Regenerated packaged Clipper skill from `skills/clipper/`.

```bash
uv run pytest
```

Result: passed. 177 passed, 3 skipped.
