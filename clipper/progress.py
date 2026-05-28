"""Small stderr-only progress/logging helpers for CLI operations."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TextIO


@dataclass
class CliProgress:
    """Verbose stderr logger with optional interactive progress updates."""

    enabled: bool = False
    stream: TextIO = field(default_factory=lambda: sys.stderr)

    @property
    def is_tty(self) -> bool:
        return bool(getattr(self.stream, "isatty", lambda: False)())

    def log(self, message: str) -> None:
        """Write a verbose diagnostic line to stderr when enabled."""

        if self.enabled:
            print(f"[clipper] {message}", file=self.stream)

    def transcription(self, *, duration: float) -> "TranscriptionProgress":
        return TranscriptionProgress(self, duration=max(float(duration or 0), 0.0))


@dataclass
class TranscriptionProgress:
    """Approximate transcription progress based on segment end timestamps."""

    progress: CliProgress
    duration: float
    _last_percent: int = -1
    _finished: bool = False

    def update(self, segment_end: float) -> None:
        if not self.progress.enabled or self.duration <= 0:
            return
        percent = int(max(0.0, min(float(segment_end) / self.duration, 1.0)) * 100)
        if percent <= self._last_percent:
            return
        self._last_percent = percent
        if self.progress.is_tty:
            print(f"\r[clipper] transcription progress: {percent:3d}%", end="", file=self.progress.stream, flush=True)
        else:
            self.progress.log(f"transcription progress: {percent}%")

    def finish(self) -> None:
        if not self.progress.enabled or self._finished:
            return
        self._finished = True
        if self.duration > 0 and self._last_percent < 100:
            self.update(self.duration)
        if self.progress.is_tty:
            print(file=self.progress.stream)
