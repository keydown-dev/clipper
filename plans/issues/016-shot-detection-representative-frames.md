# Issue 016 — Shot Detection and Representative Frames

## Goal

Detect significant visual shots in a video and extract one clear representative frame for each shot.

## Depends On

- Issue 002 for artifact conventions
- Issue 004 for source metadata conventions

## Tasks

- Add a PySceneDetect-based shot detection command.
- Detect shot boundaries from the source video and write a shot manifest artifact.
- Extract representative frame images for each detected shot by default.
- Choose representative frames using deterministic image quality metrics such as sharpness, exposure, and contrast.
- Avoid choosing obvious transition, black, overexposed, or blurry frames where possible.
- Support configurable scene threshold, minimum shot duration, and candidate samples per shot.
- Respect fail/reuse/force output policy for shot manifest and frame outputs.
- Optionally generate a contact sheet for human review.
- Document the shot manifest, representative frame outputs, and contact sheet option.

## Acceptance Criteria

- Tests verify detected shot ranges are persisted with start, end, duration, representative frame path, representative time, and quality metadata.
- Tests verify representative frame selection prefers clearer generated image fixtures over blurry or poorly exposed candidates.
- Tests verify output policy behavior for shot artifacts and frame outputs.
- `clipper shots --help` and command routing work.
- Contact sheet generation is optional and does not run unless requested.
