"""Session and action models for game analysis."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

from pydantic import BaseModel, Field

from . import ActionResult, ActionType, LogLevel, PlayStrategy, SessionStatus


class WindowRegion(BaseModel):
    """Window region definition for screen capture."""

    x: int = Field(..., ge=0, description="Top-left X coordinate")
    y: int = Field(..., ge=0, description="Top-left Y coordinate")
    width: int = Field(..., gt=0, description="Region width in pixels")
    height: int = Field(..., gt=0, description="Region height in pixels")

    def to_tuple(self) -> tuple[int, int, int, int]:
        """Convert to mss-compatible tuple (left, top, width, height)."""
        return (self.x, self.y, self.width, self.height)


class SessionConfig(BaseModel):
    """Configuration for a play session."""

    window_region: WindowRegion
    max_steps: int = Field(default=100, ge=1, le=1000, description="Maximum steps per session")
    strategy: PlayStrategy = Field(default=PlayStrategy.EXPLORATION)
    output_dir: Path = Field(default=Path("./output"))
    log_level: LogLevel = Field(default=LogLevel.DETAILED)
    video_segment_duration: float = Field(
        default=3.0, ge=2.0, le=5.0, description="Video segment duration in seconds"
    )

    class Config:
        arbitrary_types_allowed = True


class NormalizedCoordinate(BaseModel):
    """Normalized coordinate (0-1000 range for resolution independence)."""

    x: int = Field(..., ge=0, le=1000, description="X coordinate (0-1000)")
    y: int = Field(..., ge=0, le=1000, description="Y coordinate (0-1000)")

    def to_screen_coords(self, region: WindowRegion) -> tuple[int, int]:
        """Convert normalized coords to actual screen coordinates."""
        screen_x = region.x + int((self.x / 1000) * region.width)
        screen_y = region.y + int((self.y / 1000) * region.height)
        return (screen_x, screen_y)


class ActionCommand(BaseModel):
    """A single game action command."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step: int = Field(..., ge=0, description="Step number in session")
    action_type: ActionType
    start_coord: Optional[NormalizedCoordinate] = Field(
        default=None, description="Start coordinate for click/hold/drag"
    )
    end_coord: Optional[NormalizedCoordinate] = Field(
        default=None, description="End coordinate for drag operations"
    )
    duration: float = Field(
        default=0.1, ge=0, le=10.0, description="Action duration in seconds (for hold action)"
    )
    key: Optional[str] = Field(
        default=None, description="Keyboard key for press action"
    )
    wait_time: Optional[float] = Field(
        default=None, ge=0.1, le=10.0, description="Wait duration for wait action"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    result: Optional[ActionResult] = None
    reasoning: Optional[str] = Field(default=None, description="AI reasoning for this action")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnalysisLog(BaseModel):
    """Timestamped observation log entry."""

    step: int = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    observation: str = Field(..., min_length=1, description="Observation description")
    screenshot_path: Optional[Path] = None
    video_segment_path: Optional[Path] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class PlaySession(BaseModel):
    """A complete game play session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: SessionConfig
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = Field(default=SessionStatus.PENDING)
    current_step: int = Field(default=0, ge=0)
    action_log: list[ActionCommand] = Field(default_factory=list)
    analysis_log: list[AnalysisLog] = Field(default_factory=list)

    def start(self) -> None:
        """Start the session."""
        self.start_time = datetime.now()
        self.status = SessionStatus.RUNNING

    def pause(self) -> None:
        """Pause the session."""
        self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        """Resume the session."""
        self.status = SessionStatus.RUNNING

    def complete(self) -> None:
        """Mark session as completed."""
        self.end_time = datetime.now()
        self.status = SessionStatus.COMPLETED

    def fail(self) -> None:
        """Mark session as failed."""
        self.end_time = datetime.now()
        self.status = SessionStatus.FAILED

    def cancel(self) -> None:
        """Cancel the session."""
        self.end_time = datetime.now()
        self.status = SessionStatus.CANCELLED

    def add_action(self, action: ActionCommand) -> None:
        """Add an action to the log."""
        self.action_log.append(action)
        self.current_step = action.step

    def add_observation(self, observation: AnalysisLog) -> None:
        """Add an observation to the log."""
        self.analysis_log.append(observation)

    def is_step_limit_reached(self) -> bool:
        """Check if max steps reached."""
        return self.current_step >= self.config.max_steps

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat()}


__all__ = [
    "WindowRegion",
    "SessionConfig",
    "NormalizedCoordinate",
    "ActionCommand",
    "AnalysisLog",
    "PlaySession",
]
