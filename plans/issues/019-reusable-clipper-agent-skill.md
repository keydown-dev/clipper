# Issue 019 — Reusable Clipper Agent Skill

## Goal

Create an agent-agnostic root Clipper skill that teaches agents how to use Clipper Core through the CLI Contract and project-local Artifact Store.

The first version should cover core workflows only: install/readiness routing, doctor, artifact store basics, start, transcribe, score, visual scoring prerequisites, cut, montage, and troubleshooting. Specialized transcript QA/summarization and multi-video hero-background recipes belong to later issues.

The skill should be reusable outside Pi. Pi is one distribution surface, not the owner of the skill content.

## Depends On

- Issue 018 for explicit transcript/visual scoring context flags
- ADR 0002 for the core-first monorepo and CLI Contract decision

## Proposed Location

```text
skills/clipper/
  SKILL.md
  references/
    install.md
    doctor.md
    store.md (artifact store basics, eg .clipper/<project-name> structure)
    start.md (downloading/copying sources and starting clipper video projects)
    transcribe.md (transcribing sources)
    transcript-scoring.md (transcript scoring prerequisites)
    visual-scoring.md (visual scoring prerequisites)
    cut.md (cutting clips)
    montage.md (montaging clips)
    troubleshooting.md (troubleshooting common issues)
```

## Tasks

- Create `skills/clipper/SKILL.md` with concise routing guidance.
- Explain what Clipper is: a local-first Python CLI for source videos, transcripts, scored clips, and montages.
- Instruct agents to verify unknown environments with `clipper doctor --json` or `uv run clipper doctor --json` before expensive workflows.
- Explain the project-local `.clipper/` Artifact Store and when to pass `--store`.
- Reference detailed workflow files instead of putting all instructions in the root skill.
- Add reference docs for install, doctor, artifact store, YouTube start/local start, transcription, scoring, visual scoring prerequisites, cutting, montage, and troubleshooting.
- Do not include detailed transcript QA/summarization recipes; defer those to Issue 022.
- Do not include detailed multi-video hero-background recipes; defer those to Issue 023.
- Teach primitive command composition rather than bespoke workflow commands.
- Include examples using explicit scoring context flags: `--with-transcript`, `--with-visuals`, or both.

## Acceptance Criteria

- `skills/clipper/SKILL.md` has valid skill frontmatter and can be loaded by Pi or another Agent Skills-compatible harness.
- Root skill stays concise and points to reference docs for details.
- Reference docs include copy/pasteable CLI examples.
- Skill docs do not assume Pi-specific tools or extensions.
- Skill docs do not invent commands that Clipper does not implement.
- Skill docs tell agents to run doctor before first use on an unknown system.
