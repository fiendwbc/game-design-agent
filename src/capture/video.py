"""Video segment synthesis module using OpenCV.

Synthesizes video segments from captured frames for AI analysis.
"""

import io
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np

from ..models.session import WindowRegion
from ..utils.logging import get_logger
from .screen import ScreenCapture


@dataclass
class VideoSegment:
    """Represents a captured video segment."""

    data: bytes
    duration: float
    frame_count: int
    fps: float
    width: int
    height: int
    timestamp: float = field(default_factory=time.time)

    @property
    def size_mb(self) -> float:
        """Get size in megabytes."""
        return len(self.data) / (1024 * 1024)


class VideoSynthesizer:
    """Synthesizes video segments from screen captures.

    Uses OpenCV to combine frames into video segments
    suitable for Gemini multimodal analysis.
    """

    def __init__(
        self,
        region: Optional[WindowRegion] = None,
        fps: float = 15.0,
        codec: str = "mp4v",
    ) -> None:
        """Initialize video synthesizer.

        Args:
            region: Optional capture region.
            fps: Frames per second for output video.
            codec: FourCC codec for video encoding.
        """
        self.region = region
        self.fps = fps
        self.codec = codec
        self._logger = get_logger()
        self._capture: Optional[ScreenCapture] = None

    def __enter__(self) -> "VideoSynthesizer":
        """Context manager entry."""
        self._capture = ScreenCapture(region=self.region)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._capture:
            self._capture.close()
            self._capture = None

    def _ensure_capture(self) -> ScreenCapture:
        """Ensure capture instance exists."""
        if self._capture is None:
            self._capture = ScreenCapture(region=self.region)
        return self._capture

    def record_segment(
        self,
        duration: float = 3.0,
        max_size_mb: float = 10.0,
    ) -> VideoSegment:
        """Record a video segment of specified duration.

        Args:
            duration: Duration in seconds (default 3.0).
            max_size_mb: Maximum file size in MB (default 10.0).

        Returns:
            VideoSegment with recorded data.
        """
        capture = self._ensure_capture()
        frames: list[np.ndarray] = []
        frame_interval = 1.0 / self.fps
        target_frames = int(duration * self.fps)

        self._logger.debug(
            f"Recording {duration}s segment at {self.fps} FPS "
            f"({target_frames} frames)"
        )

        start_time = time.perf_counter()

        for _ in range(target_frames):
            frame_start = time.perf_counter()

            frame = capture.capture_as_numpy()
            frames.append(frame)

            # Maintain frame rate
            elapsed = time.perf_counter() - frame_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        actual_duration = time.perf_counter() - start_time

        # Synthesize video from frames
        video_bytes = self._synthesize_video(frames)

        # Check size and reduce quality if needed
        size_mb = len(video_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            self._logger.warning(
                f"Video size {size_mb:.1f}MB exceeds limit {max_size_mb}MB, "
                "reducing quality"
            )
            video_bytes = self._synthesize_video(frames, quality=50)

        return VideoSegment(
            data=video_bytes,
            duration=actual_duration,
            frame_count=len(frames),
            fps=self.fps,
            width=frames[0].shape[1] if frames else 0,
            height=frames[0].shape[0] if frames else 0,
        )

    def _synthesize_video(
        self,
        frames: list[np.ndarray],
        quality: int = 80,
    ) -> bytes:
        """Synthesize video from frames.

        Args:
            frames: List of BGR numpy arrays.
            quality: Video quality (0-100).

        Returns:
            Video file bytes.
        """
        if not frames:
            return b""

        height, width = frames[0].shape[:2]

        # Create temporary file for video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*self.codec)
            writer = cv2.VideoWriter(
                tmp_path,
                fourcc,
                self.fps,
                (width, height),
            )

            if not writer.isOpened():
                # Fallback to different codec
                self._logger.warning(
                    f"Codec {self.codec} failed, trying XVID"
                )
                fourcc = cv2.VideoWriter_fourcc(*"XVID")
                tmp_path = tmp_path.replace(".mp4", ".avi")
                writer = cv2.VideoWriter(
                    tmp_path,
                    fourcc,
                    self.fps,
                    (width, height),
                )

            # Write frames
            for frame in frames:
                writer.write(frame)

            writer.release()

            # Read video bytes
            with open(tmp_path, "rb") as f:
                video_bytes = f.read()

            return video_bytes

        finally:
            # Cleanup temp file
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

    def capture_frames(
        self,
        count: int,
        interval: float = 0.1,
    ) -> list[np.ndarray]:
        """Capture multiple frames at regular intervals.

        Args:
            count: Number of frames to capture.
            interval: Time between frames in seconds.

        Returns:
            List of BGR numpy arrays.
        """
        capture = self._ensure_capture()
        frames = []

        for _ in range(count):
            frame_start = time.perf_counter()
            frames.append(capture.capture_as_numpy())

            elapsed = time.perf_counter() - frame_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        return frames

    def frames_to_video(self, frames: list[np.ndarray]) -> bytes:
        """Convert existing frames to video.

        Args:
            frames: List of BGR numpy arrays.

        Returns:
            Video file bytes.
        """
        return self._synthesize_video(frames)

    def stream_segments(
        self,
        segment_duration: float = 3.0,
        max_segments: Optional[int] = None,
    ) -> Generator[VideoSegment, None, None]:
        """Stream continuous video segments.

        Args:
            segment_duration: Duration per segment in seconds.
            max_segments: Maximum segments to record (None for unlimited).

        Yields:
            VideoSegment objects.
        """
        segment_count = 0

        while max_segments is None or segment_count < max_segments:
            yield self.record_segment(duration=segment_duration)
            segment_count += 1

    def set_region(self, region: WindowRegion) -> None:
        """Update the capture region.

        Args:
            region: New WindowRegion to capture.
        """
        self.region = region
        if self._capture:
            self._capture.set_region(region)


def create_video_segment(
    region: Optional[WindowRegion] = None,
    duration: float = 3.0,
    fps: float = 15.0,
) -> VideoSegment:
    """Convenience function to create a single video segment.

    Args:
        region: Optional capture region.
        duration: Duration in seconds.
        fps: Frames per second.

    Returns:
        VideoSegment with recorded data.
    """
    with VideoSynthesizer(region=region, fps=fps) as synth:
        return synth.record_segment(duration=duration)


def frames_from_video(video_path: str) -> list[np.ndarray]:
    """Extract frames from an existing video file.

    Args:
        video_path: Path to video file.

    Returns:
        List of BGR numpy arrays.
    """
    frames = []
    cap = cv2.VideoCapture(video_path)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
    finally:
        cap.release()

    return frames


def video_info(video_path: str) -> dict:
    """Get information about a video file.

    Args:
        video_path: Path to video file.

    Returns:
        Dict with video info (fps, frame_count, width, height, duration).
    """
    cap = cv2.VideoCapture(video_path)

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration,
        }
    finally:
        cap.release()


__all__ = [
    "VideoSegment",
    "VideoSynthesizer",
    "create_video_segment",
    "frames_from_video",
    "video_info",
]
