# Cut clips

`clipper cut [VIDEO]` reads `work/scores.json`, cuts passing scored segments into `clips/`, and writes `work/clips.json`.

Prerequisites:

```bash
uv run clipper score interview --with-transcript --directive "Find expressive reactions"
```

Cut clips at the default threshold (`6`):

```bash
uv run clipper cut interview
```

Choose a threshold:

```bash
uv run clipper cut interview --min-score 7
```

Create silent clips for visual montages:

```bash
uv run clipper cut broll --min-score 6 --silent
```

Automation and reruns:

```bash
uv run clipper cut interview --json
uv run clipper cut interview --reuse
uv run clipper cut interview --force
```

If no scored segments meet the threshold, `cut` fails clearly and should not create or update `work/clips.json` or clip files. Lower `--min-score` only if that matches the user's selection criteria.
