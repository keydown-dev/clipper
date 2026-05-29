# Handoff out

## Summary

Implemented Issue 016: added `clipper shots` to detect PySceneDetect shots, choose deterministic representative frames via sharpness/exposure/contrast metrics, write `work/shots.json`, emit `work/frames/shot-000N.jpg`, and optionally create `output/shot-contact-sheet.jpg`.

## Changed files

- `clipper/shots.py` — new shot detection, representative frame scoring/extraction, contact sheet, and output policy handling.
- `clipper/cli.py` — registered `shots` command and PySceneDetect doctor check.
- `clipper/schemas.py` — added shot manifest typed contract and validator.
- `clipper/artifacts.py` — added shot paths to layout and list artifact flags.
- `tests/test_issue016.py` — added issue acceptance coverage.
- `README.md` — documented dependency, command, artifacts, and manifest example.
- `pyproject.toml`, `uv.lock` — added `scenedetect` dependency.

## Commit subject

feat: Add shot detection and representative frames

## Decisions

- Stored the manifest at `work/shots.json` and representative frames at `work/frames/shot-000N.jpg`.
- Used PySceneDetect `ContentDetector` with configurable threshold/min duration.
- Representative frame quality uses deterministic standard-library scoring over FFmpeg-extracted PPM frames, then writes the winning frame as JPEG.
- Contact sheet generation is opt-in with `--contact-sheet`.

## Risks

- PySceneDetect pulls OpenCV; the smoke command passed, but OpenCV/PyAV emitted macOS duplicate AVFoundation class warnings to stderr.
- Shot detection for videos with no cuts falls back to one full-duration shot.

## Next suggested task

Proceed to Issue 017 — visual frame analysis using the `work/shots.json` manifest and representative frames.
