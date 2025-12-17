"""Capture module for screen and video recording."""

from .screen import (
    CaptureMetrics,
    ScreenCapture,
    capture_screenshot,
    capture_region,
    RegionSelector,
)
from .video import (
    VideoSegment,
    VideoSynthesizer,
    create_video_segment,
    frames_from_video,
    video_info,
)

__all__ = [
    # Screen capture
    "CaptureMetrics",
    "ScreenCapture",
    "capture_screenshot",
    "capture_region",
    "RegionSelector",
    # Video synthesis
    "VideoSegment",
    "VideoSynthesizer",
    "create_video_segment",
    "frames_from_video",
    "video_info",
]
