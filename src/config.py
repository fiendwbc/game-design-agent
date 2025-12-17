"""Configuration management with .env support."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from .models import LogLevel, PlayStrategy


# Load .env file
load_dotenv()


class AppConfig(BaseModel):
    """Application configuration loaded from environment."""

    # API Keys
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""),
        description="Google Gemini API key",
    )

    # Logging
    log_level: LogLevel = Field(
        default_factory=lambda: LogLevel(os.getenv("LOG_LEVEL", "detailed")),
        description="Logging verbosity level",
    )

    # Output
    output_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./output")),
        description="Output directory for generated documents",
    )

    # Session defaults
    max_steps: int = Field(
        default_factory=lambda: int(os.getenv("MAX_STEPS", "100")),
        ge=1,
        le=1000,
        description="Default maximum steps per session",
    )
    play_strategy: PlayStrategy = Field(
        default_factory=lambda: PlayStrategy(os.getenv("PLAY_STRATEGY", "exploration")),
        description="Default play strategy",
    )
    video_segment_duration: float = Field(
        default_factory=lambda: float(os.getenv("VIDEO_SEGMENT_DURATION", "3.0")),
        ge=2.0,
        le=5.0,
        description="Video segment duration in seconds",
    )

    # Model configuration
    player_model: str = Field(
        default="gemini-2.0-flash",
        description="Model for Player-Agent (fast responses)",
    )
    analyst_model: str = Field(
        default="gemini-3-pro-preview",
        description="Model for analysis agents (deep reasoning)",
    )

    @field_validator("google_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is set."""
        if not v:
            raise ValueError(
                "GOOGLE_API_KEY is required. Set it in .env or environment variables."
            )
        return v

    @field_validator("output_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Ensure output_dir is a Path."""
        return Path(v) if isinstance(v, str) else v

    def ensure_output_dir(self) -> Path:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    class Config:
        arbitrary_types_allowed = True


# Singleton config instance
_config: Optional[AppConfig] = None


def get_config(validate_api_key: bool = True) -> AppConfig:
    """Get application configuration singleton.

    Args:
        validate_api_key: If True, validate that API key is set.
                         Set to False for CLI help commands.
    """
    global _config
    if _config is None:
        if validate_api_key:
            _config = AppConfig()
        else:
            # Create config without validation for help commands
            _config = AppConfig.model_construct(
                google_api_key=os.getenv("GOOGLE_API_KEY", ""),
                log_level=LogLevel(os.getenv("LOG_LEVEL", "detailed")),
                output_dir=Path(os.getenv("OUTPUT_DIR", "./output")),
                max_steps=int(os.getenv("MAX_STEPS", "100")),
                play_strategy=PlayStrategy(os.getenv("PLAY_STRATEGY", "exploration")),
                video_segment_duration=float(os.getenv("VIDEO_SEGMENT_DURATION", "3.0")),
                player_model="gemini-2.0-flash",
                analyst_model="gemini-3-pro-preview",
            )
    return _config


def reset_config() -> None:
    """Reset config singleton (useful for testing)."""
    global _config
    _config = None


__all__ = ["AppConfig", "get_config", "reset_config"]
