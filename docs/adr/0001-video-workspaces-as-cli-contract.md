# Use source/project workspaces as the CLI contract

Status: supersedes the original single video workspace contract while preserving compatibility.

Clipper commands now distinguish reusable source evidence from editorial project outputs. Source-level commands operate on named sources rooted at `.clipper/sources/{source}/`; project-level commands operate on named projects rooted at `.clipper/projects/{project}/`. This keeps expensive, reusable artifacts such as metadata, transcripts, shots, frames, and visual indexes attached to one canonical input, while directive-specific artifacts such as scores, clips, and montages belong to an editorial project.

Compatibility remains part of the CLI contract. Legacy `.clipper/{video}/` workspaces still resolve for older commands and scripts. `clipper start` remains a deprecated alias for source ingestion and mirrors a legacy workspace. For `score`, `cut`, and `montage`, a positional name is treated as a project when `.clipper/projects/{project}/project.json` exists; otherwise the older source/video flow remains available, including `--project` scoped outputs under a legacy workspace.

This makes the staged workflow easier for humans and automation agents because each command can infer standard inputs and outputs from the source/project layout, while still allowing older video names or paths during migration. The trade-off is a slightly larger vocabulary, which is acceptable because it prevents reusable source analysis from being duplicated for every editorial directive.
