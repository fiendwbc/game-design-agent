"""Play log memory module for recording gameplay actions.

Stores and retrieves the history of actions taken during a play session.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from ..models import ActionType, ActionResult
from ..models.session import ActionCommand, AnalysisLog
from ..utils.logging import get_logger


class PlayLogEntry(BaseModel):
    """A single entry in the play log."""

    step: int
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: ActionType
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    end_x: Optional[int] = None
    end_y: Optional[int] = None
    duration: Optional[float] = None  # Hold duration in seconds
    key: Optional[str] = None
    wait_time: Optional[float] = None
    reasoning: str
    result: ActionResult = ActionResult.PENDING
    screenshot_path: Optional[str] = None
    video_path: Optional[str] = None
    observation: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PlayLog:
    """Memory module for storing gameplay actions.

    Provides:
    - Action history storage
    - Screenshot/video path linking
    - Observation recording
    - JSON export/import
    """

    def __init__(
        self,
        session_id: str,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Initialize play log.

        Args:
            session_id: Session identifier.
            output_dir: Optional directory for saving logs.
        """
        self.session_id = session_id
        self.output_dir = output_dir
        self._entries: list[PlayLogEntry] = []
        self._logger = get_logger()

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

    def __len__(self) -> int:
        """Return number of entries."""
        return len(self._entries)

    def __getitem__(self, index: int) -> PlayLogEntry:
        """Get entry by index."""
        return self._entries[index]

    def add_action(
        self,
        action: ActionCommand,
        result: ActionResult = ActionResult.PENDING,
        screenshot_path: Optional[str] = None,
        video_path: Optional[str] = None,
    ) -> PlayLogEntry:
        """Add an action to the log.

        Args:
            action: ActionCommand that was executed.
            result: Result of the action.
            screenshot_path: Path to associated screenshot.
            video_path: Path to associated video.

        Returns:
            Created PlayLogEntry.
        """
        entry = PlayLogEntry(
            step=action.step,
            action_type=action.action_type,
            start_x=action.start_coord.x if action.start_coord else None,
            start_y=action.start_coord.y if action.start_coord else None,
            end_x=action.end_coord.x if action.end_coord else None,
            end_y=action.end_coord.y if action.end_coord else None,
            duration=action.duration if action.action_type == ActionType.HOLD else None,
            key=action.key,
            wait_time=action.wait_time,
            reasoning=action.reasoning or "",
            result=result,
            screenshot_path=screenshot_path,
            video_path=video_path,
        )

        self._entries.append(entry)
        self._logger.debug(f"Logged action: step={entry.step}, type={entry.action_type.value}")

        return entry

    def update_result(self, step: int, result: ActionResult) -> bool:
        """Update the result of an action.

        Args:
            step: Step number to update.
            result: New result value.

        Returns:
            True if entry was found and updated.
        """
        for entry in self._entries:
            if entry.step == step:
                entry.result = result
                return True
        return False

    def add_observation(self, step: int, observation: str) -> bool:
        """Add an observation to an existing entry.

        Args:
            step: Step number to update.
            observation: Observation text.

        Returns:
            True if entry was found and updated.
        """
        for entry in self._entries:
            if entry.step == step:
                entry.observation = observation
                return True
        return False

    def get_recent(self, count: int = 5) -> list[PlayLogEntry]:
        """Get the most recent entries.

        Args:
            count: Number of entries to return.

        Returns:
            List of recent entries (newest first).
        """
        return list(reversed(self._entries[-count:]))

    def get_by_type(self, action_type: ActionType) -> list[PlayLogEntry]:
        """Get all entries of a specific action type.

        Args:
            action_type: ActionType to filter by.

        Returns:
            List of matching entries.
        """
        return [e for e in self._entries if e.action_type == action_type]

    def get_successful(self) -> list[PlayLogEntry]:
        """Get all successful actions.

        Returns:
            List of successful entries.
        """
        return [e for e in self._entries if e.result == ActionResult.SUCCESS]

    def get_failed(self) -> list[PlayLogEntry]:
        """Get all failed actions.

        Returns:
            List of failed entries.
        """
        return [e for e in self._entries if e.result == ActionResult.FAILED]

    def summarize(self) -> dict:
        """Generate a summary of the play log.

        Returns:
            Summary dictionary with statistics.
        """
        total = len(self._entries)
        if total == 0:
            return {
                "total_actions": 0,
                "by_type": {},
                "by_result": {},
                "duration_seconds": 0,
            }

        # Count by type
        by_type = {}
        for action_type in ActionType:
            count = len(self.get_by_type(action_type))
            if count > 0:
                by_type[action_type.value] = count

        # Count by result
        by_result = {}
        for result in ActionResult:
            count = len([e for e in self._entries if e.result == result])
            if count > 0:
                by_result[result.value] = count

        # Calculate duration
        if len(self._entries) >= 2:
            duration = (
                self._entries[-1].timestamp - self._entries[0].timestamp
            ).total_seconds()
        else:
            duration = 0

        return {
            "total_actions": total,
            "by_type": by_type,
            "by_result": by_result,
            "duration_seconds": duration,
        }

    def to_analysis_logs(self) -> list[AnalysisLog]:
        """Convert play log to analysis logs.

        Returns:
            List of AnalysisLog entries.
        """
        return [
            AnalysisLog(
                step=entry.step,
                observation=entry.observation or f"{entry.action_type.value} action",
            )
            for entry in self._entries
        ]

    def to_dict(self) -> dict:
        """Convert play log to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "session_id": self.session_id,
            "entries": [entry.model_dump() for entry in self._entries],
            "summary": self.summarize(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert play log to JSON string.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: Optional[Path] = None) -> Path:
        """Save play log to file.

        Args:
            path: Optional path (defaults to output_dir/play_log.json).

        Returns:
            Path where file was saved.
        """
        if path is None:
            if self.output_dir is None:
                raise ValueError("No output directory specified")
            path = self.output_dir / f"play_log_{self.session_id}.json"

        path.write_text(self.to_json())
        self._logger.info(f"Play log saved to: {path}")
        return path

    @classmethod
    def load(cls, path: Path) -> "PlayLog":
        """Load play log from file.

        Args:
            path: Path to JSON file.

        Returns:
            Loaded PlayLog instance.
        """
        data = json.loads(path.read_text())
        log = cls(session_id=data["session_id"])

        for entry_data in data["entries"]:
            # Convert datetime string back to datetime
            if isinstance(entry_data.get("timestamp"), str):
                entry_data["timestamp"] = datetime.fromisoformat(entry_data["timestamp"])
            log._entries.append(PlayLogEntry(**entry_data))

        return log

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def get_context_for_agent(self, max_entries: int = 10) -> str:
        """Generate context string for agent prompts.

        Args:
            max_entries: Maximum entries to include.

        Returns:
            Formatted context string.
        """
        recent = self.get_recent(max_entries)
        if not recent:
            return "No previous actions recorded."

        lines = [f"Recent actions (last {len(recent)}):"]
        for entry in reversed(recent):  # Chronological order
            action_desc = f"Step {entry.step}: {entry.action_type.value}"
            if entry.action_type == ActionType.CLICK and entry.start_x is not None:
                action_desc += f" at ({entry.start_x}, {entry.start_y})"
            elif entry.action_type == ActionType.HOLD and entry.duration is not None:
                action_desc += f" for {entry.duration:.2f}s at ({entry.start_x}, {entry.start_y})"
            elif entry.action_type == ActionType.DRAG:
                action_desc += f" from ({entry.start_x}, {entry.start_y}) to ({entry.end_x}, {entry.end_y})"
            elif entry.action_type == ActionType.PRESS:
                action_desc += f" key '{entry.key}'"
            elif entry.action_type == ActionType.WAIT:
                action_desc += f" for {entry.wait_time}s"

            action_desc += f" [{entry.result.value}]"
            if entry.observation:
                action_desc += f" - {entry.observation}"

            lines.append(f"  {action_desc}")

        return "\n".join(lines)

    def get_hold_actions(self) -> list[PlayLogEntry]:
        """Get all hold actions.

        Returns:
            List of hold action entries.
        """
        return [e for e in self._entries if e.action_type == ActionType.HOLD]

    def analyze_hold_patterns(self) -> dict:
        """Analyze hold action patterns for experience summary.

        Returns:
            Analysis dictionary with hold patterns.
        """
        hold_actions = self.get_hold_actions()
        if not hold_actions:
            return {"total_holds": 0}

        durations = [e.duration for e in hold_actions if e.duration is not None]

        return {
            "total_holds": len(hold_actions),
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "durations": durations,
        }

    def generate_experience_summary(self) -> dict:
        """Generate experience summary after game over.

        Analyzes the play log to extract lessons learned,
        especially useful for games like Jump Jump.

        Returns:
            Experience summary dictionary.
        """
        summary = self.summarize()
        hold_analysis = self.analyze_hold_patterns()

        # Find the last few actions before game over
        last_actions = self.get_recent(5)

        # Analyze what might have gone wrong
        insights = []
        recommendations = []

        # Analyze hold durations
        if hold_analysis["total_holds"] > 0:
            avg_duration = hold_analysis["avg_duration"]
            insights.append(f"执行了 {hold_analysis['total_holds']} 次长按操作")
            insights.append(f"长按时间范围: {hold_analysis['min_duration']:.2f}s - {hold_analysis['max_duration']:.2f}s")
            insights.append(f"平均长按时间: {avg_duration:.2f}s")

            # Check if last action was a hold (likely the failing jump)
            if last_actions and last_actions[0].action_type == ActionType.HOLD:
                last_hold = last_actions[0]
                insights.append(f"最后一次跳跃长按了 {last_hold.duration:.2f}s")

                # Provide recommendations
                if last_hold.duration and last_hold.duration < 0.3:
                    recommendations.append("最后一跳时间太短，可能跳得不够远")
                    recommendations.append("尝试增加长按时间来跳得更远")
                elif last_hold.duration and last_hold.duration > 2.0:
                    recommendations.append("最后一跳时间较长，可能跳过头了")
                    recommendations.append("尝试减少长按时间来控制距离")

        # Analyze overall performance
        total = summary.get("total_actions", 0)
        successful = summary.get("by_result", {}).get("success", 0)
        if total > 0:
            success_rate = successful / total * 100
            insights.append(f"总共执行了 {total} 次操作，成功率 {success_rate:.1f}%")

        # Game duration
        duration = summary.get("duration_seconds", 0)
        if duration > 0:
            insights.append(f"游戏持续了 {duration:.1f} 秒")

        # General recommendations
        if hold_analysis["total_holds"] > 0:
            recommendations.append("观察平台间距，近距离用短按，远距离用长按")
            recommendations.append("建议长按时间: 近(0.2-0.5s), 中(0.5-1.0s), 远(1.0-2.0s)")

        return {
            "session_id": self.session_id,
            "total_steps": total,
            "success_rate": successful / total * 100 if total > 0 else 0,
            "duration_seconds": duration,
            "hold_analysis": hold_analysis,
            "insights": insights,
            "recommendations": recommendations,
            "last_actions": [
                {
                    "step": e.step,
                    "action": e.action_type.value,
                    "duration": e.duration,
                    "reasoning": e.reasoning,
                }
                for e in last_actions
            ],
        }

    def format_experience_report(self) -> str:
        """Generate formatted experience report string.

        Returns:
            Human-readable experience report.
        """
        exp = self.generate_experience_summary()

        lines = [
            "=" * 50,
            "游戏经验总结 (Experience Summary)",
            "=" * 50,
            "",
            "📊 统计数据:",
        ]

        for insight in exp["insights"]:
            lines.append(f"  • {insight}")

        if exp["recommendations"]:
            lines.append("")
            lines.append("💡 改进建议:")
            for rec in exp["recommendations"]:
                lines.append(f"  • {rec}")

        if exp["last_actions"]:
            lines.append("")
            lines.append("📝 最后几步操作:")
            for action in exp["last_actions"]:
                action_str = f"  Step {action['step']}: {action['action']}"
                if action["duration"]:
                    action_str += f" ({action['duration']:.2f}s)"
                if action["reasoning"]:
                    action_str += f" - {action['reasoning'][:30]}..."
                lines.append(action_str)

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


__all__ = [
    "PlayLogEntry",
    "PlayLog",
]
