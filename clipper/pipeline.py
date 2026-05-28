"""Pipeline entry points for Clipper.

The implementation is intentionally deferred to later issues; this module establishes
an importable API shape for the project foundation.
"""

from __future__ import annotations

from typing import Any


def run_pipeline(
    input_ref: str,
    directive: str,
    min_score: float = 6,
    force: bool = False,
    reuse: bool = False,
) -> dict[str, Any]:
    """Run the full Clipper pipeline.

    Later implementation issues will fill in source preparation, transcription,
    scoring, cutting, and montage assembly.
    """

    raise NotImplementedError("clipper.pipeline.run_pipeline is not implemented yet")
