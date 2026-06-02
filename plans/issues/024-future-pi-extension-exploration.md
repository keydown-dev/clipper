# Issue 024 — Future Pi Extension Exploration

## Goal

Explore and document whether/when Clipper should add a Pi extension after the skills-only package, especially for typed CLI wrappers, progress UI, custom rendering, and TUI artifact previews.

This issue is exploratory/design-oriented unless explicitly expanded later. Do not implement extension tools in the first pass unless the issue is amended.

## Depends On

- Issue 020 for the initial skills-only Pi package
- ADR 0002 for the decision to defer Pi-specific tools

## Tasks

- Review Pi extension capabilities relevant to Clipper: custom tools, command wrappers, status/progress UI, custom renderers, custom TUI components.
- Identify which Clipper CLI behaviors would need improvement to support good progress bars or previews.
- Propose a minimal typed-tool set, if any, such as wrappers around `doctor`, `start`, `transcribe`, `score`, `cut`, and `montage`.
- Propose how progress should be surfaced without breaking JSON stdout contracts.
- Consider artifact preview affordances for transcripts, shots, clips, and montage outputs.
- Record recommendation: keep deferred, implement now, or split into concrete follow-up issues.

## Acceptance Criteria

- A design note or amended issue explains whether Pi extension tools are worth building next.
- No business logic is proposed inside the extension; Clipper Core remains authoritative.
- Any proposed tools are thin wrappers over the CLI Contract.
- Progress/UI ideas preserve machine-readable CLI behavior.

## Design Note — Recommendation

Recommendation: **keep Pi extension work deferred**, but split it into concrete follow-up issues once Clipper has one or two real users of the skills-only package. The current skill package already gives Pi enough guidance to operate the CLI, while an extension would add TypeScript code, package dependencies, and UI behavior before the pain points are proven.

A future extension is still worth preserving as an option because Pi extensions can register typed tools, slash commands, lifecycle/event hooks, status/widgets, custom renderers, and custom TUI components. Those capabilities map well to Clipper's workflow, but they should remain orchestration and presentation only. Clipper Core and the CLI Contract must stay authoritative for media processing, schemas, command semantics, errors, and artifact paths.

### Candidate thin tool set

If implemented later, start with a small typed wrapper set over `clipper ... --json` commands:

- `clipper_doctor`: run `clipper doctor --json`, optionally with connectivity/model checks.
- `clipper_start`: run `clipper start INPUT --json` with `--name`, `--proxy`, `--reuse`, or `--force` options.
- `clipper_transcribe`: run `clipper transcribe VIDEO --json` with model/device/language and reuse/force options.
- `clipper_score`: run `clipper score VIDEO --json` with directive and evidence flags.
- `clipper_shots` / `clipper_visual`: run visual analysis preparation commands when artifact previews are useful.
- `clipper_cut`: run `clipper cut VIDEO --json` with threshold and silent options.
- `clipper_montage`: run `clipper montage VIDEO --json` with duration and silent options.
- Optional `clipper_pipeline`: run the complete tracer-bullet path when the user asks for a single end-to-end operation.

Each wrapper should invoke the CLI as a child process, parse the JSON envelope, and return paths/counts/warnings. It should not import Python internals, inspect private files beyond returned artifact paths, or decide clipping/scoring behavior outside CLI flags.

### CLI behavior needed before good progress UI

The current CLI already protects JSON stdout by emitting result envelopes on stdout and progress/diagnostics on stderr. `CliProgress` is also stderr-only, and transcription progress can update TTY output or log lines when verbose mode is enabled. That is enough for safe wrappers, but not enough for rich Pi progress bars across the whole workflow.

Before building progress UI, add or harden CLI support in Clipper Core:

- Keep `--json` stdout as exactly one final JSON envelope for machine consumers.
- Add a structured stderr progress mode, for example newline-delimited events behind a flag such as `--progress jsonl` or `--progress-events`.
- Include stable event fields: `phase`, `video`, `percent` when known, `message`, `artifact_path` when produced, and optional counters such as `current`/`total`.
- Preserve existing human stderr behavior for non-JSON and verbose users.
- Cover the event stream with CLI contract tests so Pi/Tauri consumers can depend on it.

Pi extension progress should consume stderr events and surface them through `ctx.ui.setStatus`, widgets, or tool `onUpdate` calls. It must never require progress data to be mixed into JSON stdout.

### Artifact preview affordances

Preview work is more valuable than typed wrappers, but should be scoped to artifacts returned by the CLI:

- Transcripts: render segment/sentence counts, searchable excerpts, top timestamp ranges, and links to `work/transcript.json` / `work/sentences.json`.
- Scores: show top-ranked segments with timestamps, score/reason, warnings, and directive summary.
- Shots/visuals: show shot counts, contact sheet path when present, and representative frame paths/observations.
- Clips: show clip count, min score, output paths, and terse timestamp ranges.
- Montage: show montage path, duration, dimensions, clip count, and any source clips included.

A custom renderer or TUI component can make those previews pleasant inside Pi, but the renderer should only read validated Artifact Store JSON and media paths produced by Clipper Core.

### Follow-up issue split

Do not implement the extension now. Recommended follow-ups, in order:

1. Add structured CLI progress events while preserving the JSON stdout contract.
2. Add contract tests for command JSON envelopes, stderr diagnostics, and progress events.
3. Prototype a `packages/pi-clipper` extension with only `doctor`, `start`, and `pipeline` wrappers plus result rendering.
4. Add artifact preview renderers for transcripts, scores, shots/contact sheets, clips, and montage outputs.

This keeps Issue 020's skills-only package intact and honors ADR 0002: future surfaces may invoke, document, visualize, or orchestrate Clipper Core, but must not reimplement workflow logic.
