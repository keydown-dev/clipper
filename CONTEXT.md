# Clipper

Clipper is a local-first video clipping context for turning a source recording into scored clips and montages while preserving traceable artifacts for each run.

## Language

**Artifact Store**:
The project-local `.clipper/` directory where Clipper writes per-video source, work, clip, and output artifacts.
_Avoid_: cache, temp folder

**Video**:
A named unit of work rooted at `.clipper/{video}/` containing the source, work, clips, and output artifacts for one canonical input reference.
_Avoid_: job, run, project

**Remote Input**:
A user-provided `http` or `https` URL that Clipper downloads into a Video before processing.
_Avoid_: URL input, download input

**Local Input**:
A user-provided local video file that Clipper copies into a Video before processing.
_Avoid_: file input, source file

## Relationships

- An **Artifact Store** contains one or more **Videos**.
- A **Video** contains the source, work, clips, and output artifacts for one canonical input reference.
- A **Remote Input** and a **Local Input** both produce a source artifact inside a **Video**.
- A **Local Input** is copied into its **Video** by default so the video workspace remains self-contained.

## Example dialogue

> **Dev:** "Should this transcript go in a global cache?"
> **Domain expert:** "No — it belongs in the project's **Artifact Store** so a human or agent can inspect the run outputs."

## Flagged ambiguities

- "artifact directory" could mean a visible `artifacts/` folder, hidden project-local state, or user cache; resolved: the default **Artifact Store** is project-local `.clipper/`.
- "job" was considered for `.clipper/{name}/`, but user-facing language should be **Video** because the unit of work is source-video-centric.
- "video directory" could mean a new directory per run or a stable directory per source; resolved: a **Video** is stable for a canonical input reference and named either by the user or by default as `safe-stem-short-hash`.
- "source identity" could mean URL/path, provider metadata ID, or file contents; resolved: source identity means the canonical input reference — normalized URL for remote inputs, resolved absolute path for local inputs.
- "input type" could use `url`/`local_file`, `download`/`local`, or provider names; resolved: core metadata uses `remote` and `local`.
- "remote" could include many URI schemes; resolved: v1 **Remote Input** means only `http` and `https` URLs.
