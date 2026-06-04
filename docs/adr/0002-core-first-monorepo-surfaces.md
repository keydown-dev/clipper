# Keep Clipper Core as the stable product boundary for future surfaces

Clipper will evolve as a monorepo, but the Python CLI/package remains **Clipper Core** and owns media processing behavior, artifact schemas, and command semantics. Future surfaces such as a Pi package, static documentation site, and Tauri desktop app should invoke, document, visualize, or orchestrate Clipper Core rather than reimplementing workflow logic.

The public compatibility boundary is the **CLI Contract**: commands, flags, exit codes, JSON stdout envelopes, stderr diagnostics, and Artifact Store schemas. External surfaces should prefer the CLI Contract over importing Python functions directly. The importable Python API remains useful for internal composition and tests, but is not the primary cross-surface contract yet.

The default Artifact Store remains project-local `.clipper/`. Shared or cross-project stores must be explicit via `--store` or `CLIPPER_STORE_PATH`. New surfaces should understand `.clipper/sources/{source}/` for reusable analysis artifacts and `.clipper/projects/{project}/` for editorial outputs, while preserving read access to legacy `.clipper/{video}/` workspaces during migration.

The first Pi integration should be a skills-only package with one root `clipper` skill and reference files for detailed workflows. Extension tools are deferred until there is demonstrated need for typed wrappers, custom rendering, or safer execution. Workflow-specific commands such as `hero-montage` or `topic-clips` are also deferred; skills should teach agents how to compose primitive commands and write effective scoring directives.

This preserves a path to future surfaces:

```text
clipper/                    # Python Clipper Core and CLI
packages/pi-clipper/        # future skills-only Pi package, optional tools later
apps/docs-site/             # future static Astro documentation site
apps/desktop/               # future Tauri artifact browser/editor
```

Consequences:

- CLI JSON behavior and artifact schemas need strong contract tests.
- Progress, errors, and artifact paths should remain machine-readable enough for Pi and future Tauri consumers.
- Future Tauri work should start as a read-only Artifact Store browser before becoming an interactive editor/orchestrator.
- New user goals should usually be handled by clearer directives, explicit scoring context, and Workflow Skills before adding bespoke commands.
