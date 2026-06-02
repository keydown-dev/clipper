# pi-clipper

Pi package for the reusable Clipper skill.

This first package is intentionally **skills-only**. It does not register Pi extension tools, commands, custom TUI components, renderers, or execution wrappers.

## Requirements

This package teaches Pi how to operate Clipper through the CLI contract. It does **not** install Clipper Core, Python dependencies, FFmpeg/ffprobe, model weights, or LLM services.

Install Clipper Core separately with the supported uv tool path, then verify the command before using the skill:

```bash
uv tool install git+https://github.com/keydown-dev/clipper.git
clipper doctor --json
```

Or, from a Clipper source checkout:

```bash
uv run clipper doctor --json
```

## Source of truth

The canonical skill content lives at the repository root:

```text
skills/clipper/
```

The packaged copy is generated at:

```text
packages/pi-clipper/skills/clipper/
```

Do not edit the packaged copy directly. Update `skills/clipper/`, then regenerate the package copy:

```bash
cd packages/pi-clipper
npm run sync:skill
```

`prepare` and `prepack` also run the same sync step so local preparation and npm packaging refresh the portable copy.

## Local Pi use

From the repository root, load this package for a single Pi session:

```bash
pi -e ./packages/pi-clipper
```

Or install it into project settings:

```bash
pi install -l ./packages/pi-clipper
```

Pi discovers the packaged skill through this manifest entry in `package.json`:

```json
{
  "pi": {
    "skills": ["./skills"]
  }
}
```

Because the skill copy is included under `packages/pi-clipper/skills/clipper`, the package remains portable after publishing or installing without relying on `../../skills/clipper` existing beside it.

## Deferred Pi enhancements

Future Pi-specific enhancements may include typed tools, progress UI, custom renderers, or TUI previews. Those are deliberately deferred until Clipper has demonstrated needs that justify extension code beyond a reusable skill.
