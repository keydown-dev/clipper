"""Configuration loading for Clipper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ClipperConfig:
    store_path: Path = Path(".clipper")
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    llm_base_url: str = "https://ollama.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 60.0
    vision_base_url: str | None = None
    vision_api_key: str | None = None
    vision_model: str | None = None
    vision_temperature: float | None = None
    vision_timeout_seconds: float | None = None
    default_width: int = 1920
    default_height: int = 1080
    default_min_score: float = 6.0


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return default if value in (None, "") else float(value)


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value in (None, "") else int(value)


def load_config(env_file: str | Path | None = ".env", *, store_override: str | Path | None = None) -> ClipperConfig:
    """Load configuration from defaults, .env, environment, and explicit store override."""

    if env_file is not None:
        load_dotenv(dotenv_path=env_file, override=False)
    store = Path(store_override) if store_override is not None else Path(os.environ.get("CLIPPER_STORE_PATH", ".clipper"))
    api_key = os.environ.get("LLM_API_KEY") or None
    vision_api_key = os.environ.get("VISION_API_KEY") or None
    return ClipperConfig(
        store_path=store,
        whisper_model=os.environ.get("WHISPER_MODEL", "small"),
        whisper_device=os.environ.get("WHISPER_DEVICE", "cpu"),
        whisper_compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        llm_base_url=os.environ.get("LLM_BASE_URL", "https://ollama.com/v1"),
        llm_api_key=api_key,
        llm_model=os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
        llm_temperature=_float("LLM_TEMPERATURE", 0.0),
        llm_timeout_seconds=_float("LLM_TIMEOUT_SECONDS", 60.0),
        vision_base_url=os.environ.get("VISION_BASE_URL") or None,
        vision_api_key=vision_api_key,
        vision_model=os.environ.get("VISION_MODEL") or None,
        vision_temperature=_float("VISION_TEMPERATURE", 0.0) if os.environ.get("VISION_TEMPERATURE") not in (None, "") else None,
        vision_timeout_seconds=_float("VISION_TIMEOUT_SECONDS", 60.0) if os.environ.get("VISION_TIMEOUT_SECONDS") not in (None, "") else None,
        default_width=_int("DEFAULT_WIDTH", 1920),
        default_height=_int("DEFAULT_HEIGHT", 1080),
        default_min_score=_float("DEFAULT_MIN_SCORE", 6.0),
    )
