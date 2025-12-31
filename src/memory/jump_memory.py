"""Jump experience memory module with RAG-based learning.

Stores and retrieves jump experiences to learn optimal hold durations
based on visual distance analysis.
"""

import json
import math
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from ..utils.logging import get_logger


class JumpExperience(BaseModel):
    """A single jump experience record."""

    timestamp: datetime = Field(default_factory=datetime.now)

    # Window/screen dimensions for normalization
    screen_width: int
    screen_height: int

    # Visual distance estimation (pixels or normalized)
    distance_pixels: float | None = None  # Estimated pixel distance
    distance_normalized: float | None = None  # Normalized 0-1 based on screen

    # Action details
    hold_duration: float  # How long was held (seconds)
    click_x: int  # Where clicked (normalized 0-1000)
    click_y: int

    # Result
    success: bool  # Whether the jump landed successfully
    landed_center: bool = False  # Bonus: landed on center

    # AI reasoning at the time
    reasoning: str | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JumpMemory:
    """RAG-based memory for learning optimal jump durations.

    Stores jump experiences and retrieves similar ones to help
    predict optimal hold duration for new jumps.
    """

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        memory_file: Path | None = None,
    ) -> None:
        """Initialize jump memory.

        Args:
            screen_width: Game window width in pixels.
            screen_height: Game window height in pixels.
            memory_file: Optional path to persist memory.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.memory_file = memory_file
        self._experiences: list[JumpExperience] = []
        self._logger = get_logger()

        # Load existing memory if file exists
        if memory_file and memory_file.exists():
            self.load(memory_file)

    def __len__(self) -> int:
        return len(self._experiences)

    def add_experience(
        self,
        distance_pixels: float | None,
        hold_duration: float,
        success: bool,
        click_x: int = 500,
        click_y: int = 500,
        landed_center: bool = False,
        reasoning: str | None = None,
    ) -> JumpExperience:
        """Record a new jump experience.

        Args:
            distance_pixels: Estimated distance in pixels.
            hold_duration: How long held in seconds.
            success: Whether jump was successful.
            click_x: Click X coordinate (normalized 0-1000).
            click_y: Click Y coordinate (normalized 0-1000).
            landed_center: Whether landed on center (bonus).
            reasoning: AI reasoning for the jump.

        Returns:
            Created JumpExperience.
        """
        # Calculate normalized distance (0-1 based on screen diagonal)
        distance_normalized = None
        if distance_pixels is not None:
            diagonal = math.sqrt(self.screen_width**2 + self.screen_height**2)
            distance_normalized = distance_pixels / diagonal

        exp = JumpExperience(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            distance_pixels=distance_pixels,
            distance_normalized=distance_normalized,
            hold_duration=hold_duration,
            click_x=click_x,
            click_y=click_y,
            success=success,
            landed_center=landed_center,
            reasoning=reasoning,
        )

        self._experiences.append(exp)
        dist_str = f"{distance_pixels:.0f}px" if distance_pixels is not None else "unknown"
        self._logger.debug(
            f"Recorded jump: dist={dist_str}, "
            f"duration={hold_duration:.2f}s, success={success}"
        )

        # Auto-save if memory file is set
        if self.memory_file:
            self.save()

        return exp

    def get_successful_experiences(self) -> list[JumpExperience]:
        """Get all successful jump experiences."""
        return [e for e in self._experiences if e.success]

    def get_failed_experiences(self) -> list[JumpExperience]:
        """Get all failed jump experiences."""
        return [e for e in self._experiences if not e.success]

    def find_similar(
        self,
        distance_pixels: float,
        tolerance: float = 50.0,
        limit: int = 10,
    ) -> list[JumpExperience]:
        """Find experiences with similar distance (RAG retrieval).

        Args:
            distance_pixels: Target distance in pixels.
            tolerance: Distance tolerance in pixels.
            limit: Maximum results to return.

        Returns:
            List of similar experiences, sorted by distance similarity.
        """
        similar = []

        for exp in self._experiences:
            if exp.distance_pixels is not None:
                diff = abs(exp.distance_pixels - distance_pixels)
                if diff <= tolerance:
                    similar.append((diff, exp))

        # Sort by distance similarity
        similar.sort(key=lambda x: x[0])

        return [exp for _, exp in similar[:limit]]

    def predict_duration(
        self,
        distance_pixels: float,
        tolerance: float = 80.0,
    ) -> tuple[float, float]:
        """Predict optimal hold duration based on past experiences.

        Uses RAG to find similar past jumps and calculate
        the optimal duration based on successful attempts.

        Args:
            distance_pixels: Estimated distance in pixels.
            tolerance: Distance tolerance for finding similar jumps.

        Returns:
            Tuple of (predicted_duration, confidence).
            Confidence is 0-1 based on number of similar experiences.
        """
        similar = self.find_similar(distance_pixels, tolerance)

        if not similar:
            # No similar experiences, use default heuristic
            # Rough estimate: 0.5s per 100 pixels
            default_duration = (distance_pixels / 100) * 0.5
            default_duration = max(0.2, min(3.0, default_duration))
            return (default_duration, 0.0)

        # Separate successful and failed attempts
        successful = [e for e in similar if e.success]
        failed = [e for e in similar if not e.success]

        if not successful:
            # All similar attempts failed, try adjusting
            if failed:
                avg_failed_duration = sum(e.hold_duration for e in failed) / len(failed)
                # If most failed jumps were short, try longer
                # If most failed jumps were long, try shorter
                # Simple heuristic: try 20% different
                adjusted = avg_failed_duration * 1.2
                return (adjusted, 0.3)
            return ((distance_pixels / 100) * 0.5, 0.0)

        # Calculate weighted average of successful durations
        # Weight by how close the distance was
        total_weight = 0.0
        weighted_sum = 0.0

        for exp in successful:
            if exp.distance_pixels is not None:
                # Closer distance = higher weight
                distance_diff = abs(exp.distance_pixels - distance_pixels)
                weight = 1.0 / (1.0 + distance_diff / 50.0)

                # Bonus weight for center landings
                if exp.landed_center:
                    weight *= 1.5

                weighted_sum += exp.hold_duration * weight
                total_weight += weight

        if total_weight > 0:
            predicted = weighted_sum / total_weight
        else:
            predicted = sum(e.hold_duration for e in successful) / len(successful)

        # Calculate confidence based on sample size and success rate
        success_rate = len(successful) / len(similar) if similar else 0
        sample_confidence = min(1.0, len(similar) / 10.0)  # More samples = more confidence
        confidence = success_rate * sample_confidence

        return (predicted, confidence)

    def get_statistics(self) -> dict:
        """Get statistics about learned experiences."""
        total = len(self._experiences)
        if total == 0:
            return {
                "total_jumps": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
            }

        successful = self.get_successful_experiences()
        failed = self.get_failed_experiences()

        all_durations = [e.hold_duration for e in self._experiences]
        success_durations = [e.hold_duration for e in successful]

        # Analyze duration ranges for success
        duration_buckets = {
            "short (0-0.5s)": {"total": 0, "success": 0},
            "medium (0.5-1.0s)": {"total": 0, "success": 0},
            "long (1.0-2.0s)": {"total": 0, "success": 0},
            "very_long (2.0s+)": {"total": 0, "success": 0},
        }

        for exp in self._experiences:
            d = exp.hold_duration
            if d < 0.5:
                bucket = "short (0-0.5s)"
            elif d < 1.0:
                bucket = "medium (0.5-1.0s)"
            elif d < 2.0:
                bucket = "long (1.0-2.0s)"
            else:
                bucket = "very_long (2.0s+)"

            duration_buckets[bucket]["total"] += 1
            if exp.success:
                duration_buckets[bucket]["success"] += 1

        # Calculate success rate per bucket
        for bucket in duration_buckets:
            total_in_bucket = duration_buckets[bucket]["total"]
            if total_in_bucket > 0:
                duration_buckets[bucket]["success_rate"] = (
                    duration_buckets[bucket]["success"] / total_in_bucket
                )
            else:
                duration_buckets[bucket]["success_rate"] = 0.0

        # Analyze distance ranges for success (if distance data available)
        distance_buckets = {
            "close (0-150px)": {"total": 0, "success": 0, "durations": []},
            "medium (150-300px)": {"total": 0, "success": 0, "durations": []},
            "far (300-500px)": {"total": 0, "success": 0, "durations": []},
            "very_far (500px+)": {"total": 0, "success": 0, "durations": []},
        }

        for exp in self._experiences:
            if exp.distance_pixels is not None:
                d = exp.distance_pixels
                if d < 150:
                    bucket = "close (0-150px)"
                elif d < 300:
                    bucket = "medium (150-300px)"
                elif d < 500:
                    bucket = "far (300-500px)"
                else:
                    bucket = "very_far (500px+)"

                distance_buckets[bucket]["total"] += 1
                if exp.success:
                    distance_buckets[bucket]["success"] += 1
                    distance_buckets[bucket]["durations"].append(exp.hold_duration)

        # Calculate success rate and avg duration per distance bucket
        for bucket in distance_buckets:
            total_in_bucket = distance_buckets[bucket]["total"]
            if total_in_bucket > 0:
                distance_buckets[bucket]["success_rate"] = (
                    distance_buckets[bucket]["success"] / total_in_bucket
                )
                durations = distance_buckets[bucket]["durations"]
                distance_buckets[bucket]["avg_duration"] = (
                    sum(durations) / len(durations) if durations else 0.0
                )
            else:
                distance_buckets[bucket]["success_rate"] = 0.0
                distance_buckets[bucket]["avg_duration"] = 0.0
            # Remove durations list from output
            del distance_buckets[bucket]["durations"]

        return {
            "total_jumps": total,
            "successful_jumps": len(successful),
            "failed_jumps": len(failed),
            "success_rate": len(successful) / total,
            "avg_duration": sum(all_durations) / total,
            "avg_success_duration": sum(success_durations) / len(successful) if successful else 0,
            "min_duration": min(all_durations),
            "max_duration": max(all_durations),
            "duration_analysis": duration_buckets,
            "distance_analysis": distance_buckets,
        }

    def get_learning_context(self, distance_pixels: float) -> str:
        """Generate context string for AI agent with learned experience.

        Args:
            distance_pixels: Current estimated distance.

        Returns:
            Context string describing past experiences.
        """
        predicted_duration, confidence = self.predict_duration(distance_pixels)
        similar = self.find_similar(distance_pixels, tolerance=80.0, limit=5)
        stats = self.get_statistics()

        lines = [
            "=== Jump Learning Memory ===",
            f"Total learned jumps: {stats['total_jumps']}",
            f"Overall success rate: {stats['success_rate']:.1%}",
            "",
            f"For estimated distance ~{distance_pixels:.0f}px:",
            f"  Predicted duration: {predicted_duration:.2f}s (confidence: {confidence:.1%})",
        ]

        if similar:
            lines.append(f"  Similar past jumps ({len(similar)} found):")
            for exp in similar[:3]:
                status = "✓" if exp.success else "✗"
                lines.append(
                    f"    {status} dist={exp.distance_pixels:.0f}px, "
                    f"held={exp.hold_duration:.2f}s"
                )

        if stats["total_jumps"] > 5:
            lines.append("")
            lines.append("Duration success rates:")
            for bucket, data in stats["duration_analysis"].items():
                if data["total"] > 0:
                    lines.append(
                        f"  {bucket}: {data['success_rate']:.0%} "
                        f"({data['success']}/{data['total']})"
                    )

        return "\n".join(lines)

    def save(self, path: Path | None = None) -> Path:
        """Save memory to file.

        Args:
            path: Optional path (uses memory_file if not specified).

        Returns:
            Path where saved.
        """
        save_path = path or self.memory_file
        if save_path is None:
            raise ValueError("No save path specified")

        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "experiences": [exp.model_dump() for exp in self._experiences],
            "statistics": self.get_statistics(),
        }

        save_path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        self._logger.info(f"Jump memory saved to: {save_path}")

        return save_path

    def load(self, path: Path) -> None:
        """Load memory from file.

        Args:
            path: Path to load from.
        """
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())

            # Update screen dimensions if different
            if data.get("screen_width"):
                self.screen_width = data["screen_width"]
            if data.get("screen_height"):
                self.screen_height = data["screen_height"]

            # Load experiences
            self._experiences = []
            for exp_data in data.get("experiences", []):
                if isinstance(exp_data.get("timestamp"), str):
                    exp_data["timestamp"] = datetime.fromisoformat(exp_data["timestamp"])
                self._experiences.append(JumpExperience(**exp_data))

            self._logger.info(f"Loaded {len(self._experiences)} jump experiences from: {path}")

        except Exception as e:
            self._logger.error(f"Failed to load jump memory: {e}")

    def clear(self) -> None:
        """Clear all experiences."""
        self._experiences.clear()


__all__ = [
    "JumpExperience",
    "JumpMemory",
]
