# Verification

Status: passed

## Commands

- `worker-reported verification` → 0: # Verification

Status: passed

Commands run:

```bash
uv run pytest tests/test_issue016.py tests/test_issue002.py -q
```

Result: passed (`12 passed`).

```bash
uv run pytest -q
```

Result: passed (`92 passed, 3 skipped`).

```bash
uv run clipper shots --help >/tmp/clipper-shots-help.txt
```

Result: passed (exit 0; help routed for `clipper shots`).

```bash
tmpdir=$(mktemp -d); ffmpeg -hide_banner -loglevel error -y -f lavfi -i testsrc=size=160x90:rate=10:duration=1 -pix_fmt yuv420p "$tmpdir/source.mp4" && uv run clipper start "$tmpdir/source.mp4" --name shot-smoke --store "$tmpdir/store" --json >/tmp/clipper-start.json && uv run clipper shots shot-smoke --store "$tmpdir/store" --json >/tmp/clipper-shots.json && uv run python -m json.tool /tmp/clipper-shots.json >/tmp/clipper-shots.pretty.json; status=$?; rm -rf "$tmpdir"; exit $status
```

Result: passed (exit 0). PySceneDetect/OpenCV emitted macOS duplicate AVFoundation class warnings to stderr; stdout JSON remained parseable.
