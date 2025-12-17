"""Pydantic data models for the game analysis system."""

from enum import Enum


class SessionStatus(str, Enum):
    """Play session status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlayStrategy(str, Enum):
    """Game play strategy."""

    EXPLORATION = "exploration"  # Explore all UI/mechanics
    COMPLETION = "completion"  # Focus on completing the game


class LogLevel(str, Enum):
    """Logging verbosity level."""

    MINIMAL = "minimal"  # Errors only
    DETAILED = "detailed"  # Per-step decisions and API calls
    DEBUG = "debug"  # Full debug with screenshot/video archive


class ActionType(str, Enum):
    """Type of game action."""

    CLICK = "click"  # Single click
    DRAG = "drag"  # Drag from start to end
    PRESS = "press"  # Press and hold
    WAIT = "wait"  # Wait/observe
    END = "end"  # End session


class ActionResult(str, Enum):
    """Result of an action execution."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


__all__ = [
    "SessionStatus",
    "PlayStrategy",
    "LogLevel",
    "ActionType",
    "ActionResult",
]
