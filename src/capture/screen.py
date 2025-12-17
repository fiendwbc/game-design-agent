"""Screen capture module using mss for high-performance capture.

Provides 30+ FPS screen capture for game analysis.
"""

import io
import time
from dataclasses import dataclass, field
from typing import Generator, Optional

import mss
import mss.tools
import numpy as np
from PIL import Image

from ..models.session import WindowRegion
from ..utils.logging import get_logger


@dataclass
class CaptureMetrics:
    """Metrics for screen capture performance."""

    total_captures: int = 0
    total_time: float = 0.0
    min_fps: float = float("inf")
    max_fps: float = 0.0

    @property
    def avg_fps(self) -> float:
        """Calculate average FPS."""
        if self.total_time == 0:
            return 0.0
        return self.total_captures / self.total_time

    def record(self, capture_time: float) -> None:
        """Record a capture metric."""
        self.total_captures += 1
        self.total_time += capture_time
        fps = 1.0 / capture_time if capture_time > 0 else 0.0
        self.min_fps = min(self.min_fps, fps)
        self.max_fps = max(self.max_fps, fps)


@dataclass
class ScreenCapture:
    """High-performance screen capture using mss.

    Maintains a persistent mss instance for optimal performance.
    Supports region-based capture for focused game window recording.
    """

    region: Optional[WindowRegion] = None
    _sct: mss.mss = field(default_factory=mss.mss, init=False, repr=False)
    metrics: CaptureMetrics = field(default_factory=CaptureMetrics, init=False)

    def __post_init__(self) -> None:
        """Initialize logger."""
        self._logger = get_logger()

    def __enter__(self) -> "ScreenCapture":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup mss instance."""
        self.close()

    def close(self) -> None:
        """Close the mss instance."""
        if self._sct:
            self._sct.close()

    def _get_monitor(self) -> dict:
        """Get the monitor/region configuration for capture.

        Returns:
            Monitor dict for mss capture.
        """
        if self.region:
            return {
                "left": self.region.x,
                "top": self.region.y,
                "width": self.region.width,
                "height": self.region.height,
            }
        # Default to primary monitor
        return self._sct.monitors[1]

    def capture(self) -> bytes:
        """Capture a single screenshot as PNG bytes.

        Returns:
            PNG image bytes.
        """
        start_time = time.perf_counter()

        monitor = self._get_monitor()
        sct_img = self._sct.grab(monitor)

        # Convert to PNG bytes
        png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)

        capture_time = time.perf_counter() - start_time
        self.metrics.record(capture_time)

        return png_bytes

    def capture_as_numpy(self) -> np.ndarray:
        """Capture a single screenshot as numpy array (BGR format).

        Returns:
            NumPy array in BGR format (for OpenCV compatibility).
        """
        start_time = time.perf_counter()

        monitor = self._get_monitor()
        sct_img = self._sct.grab(monitor)

        # Convert to numpy array (BGRA -> BGR)
        img = np.array(sct_img)
        img = img[:, :, :3]  # Remove alpha channel

        capture_time = time.perf_counter() - start_time
        self.metrics.record(capture_time)

        return img

    def capture_as_pil(self) -> Image.Image:
        """Capture a single screenshot as PIL Image.

        Returns:
            PIL Image in RGB format.
        """
        start_time = time.perf_counter()

        monitor = self._get_monitor()
        sct_img = self._sct.grab(monitor)

        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        capture_time = time.perf_counter() - start_time
        self.metrics.record(capture_time)

        return img

    def stream(
        self,
        target_fps: float = 30.0,
        max_frames: Optional[int] = None,
    ) -> Generator[np.ndarray, None, None]:
        """Stream screenshots at target FPS.

        Args:
            target_fps: Target frames per second (default 30).
            max_frames: Maximum frames to capture (None for unlimited).

        Yields:
            NumPy arrays in BGR format.
        """
        frame_interval = 1.0 / target_fps
        frame_count = 0

        while max_frames is None or frame_count < max_frames:
            frame_start = time.perf_counter()

            yield self.capture_as_numpy()
            frame_count += 1

            # Sleep to maintain target FPS
            elapsed = time.perf_counter() - frame_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def set_region(self, region: WindowRegion) -> None:
        """Update the capture region.

        Args:
            region: New WindowRegion to capture.
        """
        self.region = region
        self._logger.debug(
            f"Capture region set to: ({region.x}, {region.y}) "
            f"{region.width}x{region.height}"
        )

    def get_available_monitors(self) -> list[dict]:
        """Get list of available monitors.

        Returns:
            List of monitor configurations.
        """
        return self._sct.monitors


def capture_screenshot(region: Optional[WindowRegion] = None) -> bytes:
    """Convenience function to capture a single screenshot.

    Args:
        region: Optional region to capture.

    Returns:
        PNG image bytes.
    """
    with ScreenCapture(region=region) as cap:
        return cap.capture()


def capture_region(
    x: int,
    y: int,
    width: int,
    height: int,
) -> bytes:
    """Capture a specific region of the screen.

    Args:
        x: Left coordinate.
        y: Top coordinate.
        width: Region width.
        height: Region height.

    Returns:
        PNG image bytes.
    """
    region = WindowRegion(x=x, y=y, width=width, height=height)
    return capture_screenshot(region)


class RegionSelector:
    """Interactive region selection utility.

    Provides methods for selecting game window regions.
    Full implementation for T023.
    """

    def __init__(self) -> None:
        """Initialize region selector."""
        self._logger = get_logger()

    def select_interactive(self) -> Optional[WindowRegion]:
        """Open interactive region selection UI.

        Returns:
            Selected WindowRegion or None if cancelled.
        """
        # Capture full screen for selection
        with ScreenCapture() as cap:
            screenshot = cap.capture_as_pil()

        # For now, return a placeholder region
        # Full interactive selection will use tkinter or similar
        self._logger.info("Interactive selection not fully implemented")
        self._logger.info("Using default region: (100, 100) 800x600")

        return WindowRegion(x=100, y=100, width=800, height=600)

    def select_from_window_title(self, title: str) -> Optional[WindowRegion]:
        """Select region from window title (Windows-specific).

        Args:
            title: Window title to search for.

        Returns:
            WindowRegion of the window or None if not found.
        """
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Find window by title
            hwnd = user32.FindWindowW(None, title)
            if not hwnd:
                self._logger.warning(f"Window not found: {title}")
                return None

            # Get window rect
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

            region = WindowRegion(
                x=rect.left,
                y=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
            )

            self._logger.info(f"Found window '{title}': {region}")
            return region

        except Exception as e:
            self._logger.error(f"Error finding window: {e}")
            return None

    def list_windows(self) -> list[str]:
        """List all visible window titles (Windows-specific).

        Returns:
            List of window titles.
        """
        windows = []

        try:
            import ctypes

            user32 = ctypes.windll.user32

            def enum_callback(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        windows.append(buf.value)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        except Exception as e:
            self._logger.error(f"Error listing windows: {e}")

        return windows


__all__ = [
    "CaptureMetrics",
    "ScreenCapture",
    "capture_screenshot",
    "capture_region",
    "RegionSelector",
]
