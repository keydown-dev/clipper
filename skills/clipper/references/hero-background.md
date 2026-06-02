# Multi-video hero/background workflows

Use this reference when a user wants calm hero footage, background loops, visual b-roll, or a montage drawn from multiple source videos. This is an agent-guided composition workflow over Clipper primitives. Do not invent or invoke a `hero-montage`, `multi-video montage`, or other bespoke workflow command.

Clipper's managed model stays one Video at a time: one Video owns one source file or URL, one workspace, its own `clips/`, and its own `output/montage.mp4`. Clipper does not currently create a first-class cross-video montage artifact in the Artifact Store.

## Visual-first silent workflow

For each source video, create or reuse a Video workspace, analyze shots and visuals, score with visual context, cut silent clips, and optionally assemble a per-Video silent montage:

```bash
uv run clipper doctor --json
uv run clipper start ./source/broll-01.mp4 --name broll-01
uv run clipper shots broll-01 --contact-sheet
uv run clipper visual broll-01
uv run clipper score broll-01 \
  --with-visuals \
  --directive "Find calm, aesthetic, loop-friendly visual moments that work without dialogue"
uv run clipper cut broll-01 --min-score 6 --silent
uv run clipper montage broll-01 --max-duration 45 --silent
```

Use `clipper ...` instead of `uv run clipper ...` when Clipper is installed and available on `PATH`. If targeting a non-default Artifact Store, pass the same `--store PATH` to every command or set `CLIPPER_STORE_PATH=PATH`.

## Directive writing

Hero/background directives should bias toward footage that remains useful without narration or exact story context. Prefer concrete visual criteria:

- calm camera motion, stable composition, pleasing color, balanced light, clean backgrounds
- scenic establishing shots, hands at work, product/environment details, crowds, travel, nature, architecture, or abstract texture
- loop-friendly starts and ends, minimal abrupt action, no essential dialogue dependence
- moments with enough motion to feel alive but not so much that they distract from foreground text or UI
- avoid talking heads, slides with tiny text, jump cuts, heavy camera shake, or shots whose meaning depends on spoken audio

Example directives:

```text
Find calm, aesthetic background shots with stable composition, soft motion, and no reliance on dialogue.
Prioritize scenic or environmental footage that can loop behind title text.
Avoid talking heads, abrupt cuts, visible slide text, or moments that need audio to make sense.
```

```text
Find premium-looking b-roll for a website hero: smooth movement, clean framing, expressive light,
interesting textures, and enough negative space for text overlays. Ignore dialogue quality.
```

Different Videos can use different directives. For example, score conference footage for crowd energy, product footage for close-up detail, and landscape footage for calm establishing shots.

## Repeat per Video in one project store

A project-local store can hold many Video workspaces, but each workspace remains independent:

```bash
uv run clipper start ./source/city.mp4 --name city
uv run clipper shots city --contact-sheet
uv run clipper visual city
uv run clipper score city --with-visuals --directive "Find calm city establishing shots with smooth motion"
uv run clipper cut city --min-score 6 --silent

uv run clipper start ./source/product.mp4 --name product
uv run clipper shots product --contact-sheet
uv run clipper visual product
uv run clipper score product --with-visuals --directive "Find clean product detail shots with negative space"
uv run clipper cut product --min-score 6 --silent
```

After this, review outputs such as:

- `.clipper/city/clips/`
- `.clipper/city/output/montage.mp4` if `clipper montage city --silent` was run
- `.clipper/product/clips/`
- `.clipper/product/output/montage.mp4` if `clipper montage product --silent` was run

Stop at `clips/` when the next step is human selection, manual ordering, or a design-led edit across many sources. Stop at each per-Video `output/montage.mp4` when the user wants quick previews before choosing a final direction. Do not describe these per-Video outputs as a single Clipper-managed cross-video montage.

## Manual cross-video assembly

Cross-video ordering, pacing, music selection, transitions, overlays, and final editorial taste are currently manual or agent-guided work outside Clipper's first-class artifact model. Recommended handoff points:

1. Produce silent clips or per-Video silent montages for each source Video.
2. Ask the user which clips, moods, or source Videos they prefer.
3. Assemble the final hero/background edit in an external editor or with an explicit external FFmpeg command.
4. Keep any cross-video export outside `.clipper/{video}/output/` unless the user deliberately chooses an unmanaged project path.

## Optional external FFmpeg concat

This example is outside Clipper's managed Artifact Store. It assumes per-Video montages have already been normalized to compatible codecs, resolution, frame rate, and audio expectations. If they are not normalized, transcode them first before concat.

Create `concat.txt`:

```text
file '.clipper/city/output/montage.mp4'
file '.clipper/product/output/montage.mp4'
file '.clipper/landscape/output/montage.mp4'
```

Then run an unmanaged external concat:

```bash
ffmpeg -f concat -safe 0 -i concat.txt -c copy ./hero-background-combined.mp4
```

If stream copy fails because the files differ, use an explicit FFmpeg filter/transcode workflow instead of treating the output as a Clipper artifact.
