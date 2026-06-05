# Cut clips

`clipper cut PROJECT` reads project `scores.json`, cuts passing scored segments into `clips/`, writes `clips.json`, and initializes canonical `clip-order.json`.

Prerequisites:

```bash
uv run clipper score interview-highlights --with-transcript --directive "Find expressive reactions"
```

Cut clips at the default threshold (`6`):

```bash
uv run clipper cut interview-highlights
```

Choose a threshold:

```bash
uv run clipper cut interview-highlights --min-score 7
```

Create silent clips for visual montages:

```bash
uv run clipper cut broll-selects --min-score 6 --silent
```

Automation and reruns:

```bash
uv run clipper cut interview-highlights --json
uv run clipper cut interview-highlights --reuse
uv run clipper cut interview-highlights --force
```

If no scored segments meet the threshold, `cut` fails clearly and should not create or update `clips.json`, `clip-order.json`, or clip files. Lower `--min-score` only if that matches the user's selection criteria.

After cutting, use Clipper's editorial commands rather than custom scripts:

```bash
uv run clipper contact-sheet interview-highlights
uv run clipper order interview-highlights --show
uv run clipper trim interview-highlights clip-0001 --duration 8 --force
uv run clipper montage interview-highlights
```
