# Clipper

Clipper is a local-first video clipping context for turning a source recording into scored clips and montages while preserving traceable artifacts for each run.

## Language

**Artifact Store**:
The project-local `.clipper/` directory where Clipper writes source evidence and project outputs.
_Avoid_: cache, temp folder

**Source**:
A named reusable recording rooted at `.clipper/sources/{source}/` containing source media, metadata, transcript, sentence, shot, and visual artifacts for one canonical input reference.
_Avoid_: job, run, project, video workspace for new flows

**Project**:
A named editorial assembly rooted at `.clipper/projects/{project}/` that references one or more Sources and owns scoring, clip, and montage outputs.
_Avoid_: source, video, cache

**Video**:
Legacy name for the pre-source/project workspace rooted at `.clipper/{video}/`; keep only when documenting compatibility with older commands and artifacts.
_Avoid_: using Video for new source/project flows

**Remote Input**:
A user-provided `http` or `https` URL that Clipper downloads into a Source before processing.
_Avoid_: URL input, download input

**Local Input**:
A user-provided local video file that Clipper copies into a Source before processing.
_Avoid_: file input, source file

**Clipper Core**:
The Python CLI and importable Python package that own Clipper's media processing behavior, artifact schemas, and command semantics.
_Avoid_: backend, engine when referring to the whole product

**Surface**:
A consumer of Clipper Core, such as a Pi skill package, documentation site, script, or future desktop app.
_Avoid_: frontend when the surface may not have a UI

**CLI Contract**:
The public compatibility boundary made up of Clipper commands, flags, exit codes, JSON stdout envelopes, stderr diagnostics, and Artifact Store schemas.
_Avoid_: internal API contract

**Workflow Skill**:
Agent instructions that explain how to compose primitive Clipper commands for a user goal without adding a bespoke Clipper command for that goal.
_Avoid_: workflow command, custom command

## Relationships

- An **Artifact Store** contains zero or more **Sources** and **Projects**.
- A **Source** contains reusable evidence artifacts for one canonical input reference.
- A **Project** references Sources and owns directive-specific scoring, clips, and montage outputs.
- A **Remote Input** and a **Local Input** both produce a source artifact inside a **Source**.
- A **Local Input** is copied into its **Source** by default so the source remains self-contained.
- **Clipper Core** owns behavior; a **Surface** invokes, documents, visualizes, or orchestrates it.
- The **CLI Contract** is the stable boundary that external **Surfaces** should rely on.
- A **Workflow Skill** composes primitive commands such as `source`, `transcribe`, `shots`, `visual`, `create`, `include`, `score`, `cut`, and `montage` for a specific user goal.

## Example dialogue

> **Dev:** "Should this transcript go in a global cache?"
> **Domain expert:** "No — it belongs in the project's **Artifact Store** so a human or agent can inspect the run outputs."

## Flagged ambiguities

- "artifact directory" could mean a visible `artifacts/` folder, hidden project-local state, or user cache; resolved: the default **Artifact Store** is project-local `.clipper/`.
- "job" was considered for `.clipper/{name}/`, but user-facing language should now distinguish reusable **Source** evidence from directive-specific **Project** outputs.
- "video directory" could mean a new directory per run or a stable directory per source; resolved: new flows use **Source** for canonical input evidence, while **Video** means legacy compatibility only.
- "source identity" could mean URL/path, provider metadata ID, or file contents; resolved: source identity means the canonical input reference — normalized URL for remote inputs, resolved absolute path for local inputs.
- "input type" could use `url`/`local_file`, `download`/`local`, or provider names; resolved: core metadata uses `remote` and `local`.
- "remote" could include many URI schemes; resolved: v1 **Remote Input** means only `http` and `https` URLs.
- "app" could mean the Python CLI, Pi package, docs site, or future desktop UI; resolved: user-facing product surfaces are **Surfaces**, and the Python CLI/package is **Clipper Core**.
- "workflow command" could mean adding bespoke commands such as hero montage or topic clips; resolved: prefer **Workflow Skills** that compose primitive commands, with `score --directive` and explicit scoring context carrying user intent.
