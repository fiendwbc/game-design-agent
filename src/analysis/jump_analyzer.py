"""OpenCV-based distance analyzer for Jump Jump game.

Analyzes screenshots to detect platforms and calculate jump distances.
Optimized for the WeChat Jump Jump (跳一跳) game.

Algorithm:
1. Player detection: Color thresholding for dark purple (RGB 50-60, 50-60, 90-100)
2. Target detection: Top-down scanning for first non-background pixel
"""

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from ..utils.logging import get_logger


@dataclass
class JumpAnalysis:
    """Result of jump distance analysis."""

    # Player position (center-bottom of player character)
    player_x: int
    player_y: int

    # Target platform center (landing spot)
    target_x: int
    target_y: int

    # Calculated distance in pixels
    distance_pixels: float

    # Direction: 'left' or 'right'
    direction: str

    # Confidence score (0-1)
    confidence: float

    # Debug image (optional)
    debug_image: np.ndarray | None = None

    @property
    def distance_normalized(self) -> float:
        """Get distance normalized to screen width."""
        return self.distance_pixels

    def get_recommended_duration(self) -> float:
        """Get recommended hold duration based on distance.

        Returns:
            Recommended duration in seconds.
        """
        # Empirical formula for Jump Jump:
        # ~1.35ms per pixel seems to work well
        duration = self.distance_pixels * 0.00135
        return max(0.2, min(2.5, duration))


class JumpAnalyzer:
    """Analyzes Jump Jump screenshots to detect platforms and distances.

    Uses precise color-based detection:
    - Player: Dark purple color (RGB 50-60, 50-60, 90-100)
    - Target: Top-down scanning for first non-background pixel
    """

    # Player color range (BGR format for OpenCV)
    # RGB (50-60, 50-60, 90-100) -> BGR (90-100, 50-60, 50-60)
    PLAYER_COLOR_LOW = np.array([50, 45, 45])
    PLAYER_COLOR_HIGH = np.array([110, 70, 70])

    # Alternative: broader range for different lighting
    PLAYER_COLOR_LOW_ALT = np.array([40, 30, 30])
    PLAYER_COLOR_HIGH_ALT = np.array([130, 90, 90])

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        debug: bool = False,
    ) -> None:
        """Initialize analyzer."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug = debug
        self._logger = get_logger()

    def analyze(self, screenshot: bytes) -> JumpAnalysis | None:
        """Analyze screenshot to detect jump distance."""
        try:
            img = self._bytes_to_cv2(screenshot)
            if img is None:
                return None

            h, w = img.shape[:2]

            # Step 1: Find player position using color thresholding
            player_pos = self._find_player_by_color(img, h, w)
            if player_pos is None:
                self._logger.debug("Could not find player")
                return None

            player_x, player_y = player_pos

            # Step 2: Find target by scanning for non-background pixels
            target_pos = self._find_target_by_scan(img, h, w, player_x, player_y)
            if target_pos is None:
                self._logger.debug("Could not find target")
                return None

            target_x, target_y = target_pos

            # Calculate distance
            distance = np.sqrt((target_x - player_x) ** 2 + (target_y - player_y) ** 2)
            direction = "right" if target_x > player_x else "left"

            # Create debug image
            debug_img = None
            if self.debug:
                debug_img = self._create_debug_image(
                    img, player_pos, target_pos, distance
                )

            analysis = JumpAnalysis(
                player_x=player_x,
                player_y=player_y,
                target_x=target_x,
                target_y=target_y,
                distance_pixels=distance,
                direction=direction,
                confidence=0.9,
                debug_image=debug_img,
            )

            self._logger.debug(
                f"Jump analysis: player=({player_x},{player_y}), "
                f"target=({target_x},{target_y}), distance={distance:.0f}px"
            )

            return analysis

        except Exception as e:
            self._logger.error(f"Jump analysis failed: {e}")
            return None

    def _bytes_to_cv2(self, screenshot: bytes) -> np.ndarray | None:
        """Convert PNG bytes to OpenCV image (BGR)."""
        try:
            pil_image = Image.open(io.BytesIO(screenshot))
            rgb_array = np.array(pil_image.convert("RGB"))
            bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
            return bgr_array
        except Exception as e:
            self._logger.error(f"Failed to convert screenshot: {e}")
            return None

    def _find_player_by_color(
        self, img: np.ndarray, h: int, w: int
    ) -> tuple[int, int] | None:
        """Find player using color thresholding.

        The player chess piece has a fixed dark purple color:
        RGB approximately (50-60, 50-60, 90-100)

        Args:
            img: BGR image
            h: Image height
            w: Image width

        Returns:
            (x, y) of player bottom-center, or None
        """
        # Create mask for player color (BGR)
        mask = cv2.inRange(img, self.PLAYER_COLOR_LOW, self.PLAYER_COLOR_HIGH)

        # If not enough pixels found, try alternative range
        if np.sum(mask > 0) < 100:
            mask = cv2.inRange(img, self.PLAYER_COLOR_LOW_ALT, self.PLAYER_COLOR_HIGH_ALT)

        # Focus on middle vertical area (1/3 to 2/3 of screen height)
        roi_top = int(h * 0.3)
        roi_bottom = int(h * 0.7)
        mask[:roi_top, :] = 0
        mask[roi_bottom:, :] = 0

        # Find all matching pixels
        points = np.where(mask > 0)
        if len(points[0]) < 50:
            return None

        # Get the bottom-most points (player's base)
        y_coords = points[0]
        x_coords = points[1]

        # Find the bottom of the player (max y value)
        max_y = np.max(y_coords)

        # Get all points near the bottom (within 10 pixels)
        bottom_mask = y_coords >= (max_y - 10)
        bottom_x = x_coords[bottom_mask]

        if len(bottom_x) == 0:
            return None

        # Player center X is the average of bottom points
        center_x = int(np.mean(bottom_x))
        # Player base Y is the bottom-most point
        base_y = int(max_y)

        return (center_x, base_y)

    def _find_target_by_scan(
        self,
        img: np.ndarray,
        h: int,
        w: int,
        player_x: int,
        player_y: int,
    ) -> tuple[int, int] | None:
        """Find target platform by scanning for non-background pixels.

        Scans from top to bottom to find the first non-background pixel,
        which is the top of a platform. The target is the platform that
        is horizontally separated from the player.

        Args:
            img: BGR image
            h: Image height
            w: Image width
            player_x: Player X position
            player_y: Player Y position

        Returns:
            (x, y) of target center, or None
        """
        # Get background color from a safe area (middle-top region)
        bg_sample = img[int(h * 0.2):int(h * 0.25), int(w * 0.4):int(w * 0.6)]
        bg_color = np.mean(bg_sample, axis=(0, 1)).astype(np.uint8)

        # Scan parameters - start from where platforms typically appear
        # Player is at around 0.6h, platforms start appearing around 0.3-0.35h
        scan_start_y = int(h * 0.32)  # Skip UI elements at top
        scan_end_y = int(h * 0.55)    # Target platform top is above player level
        color_threshold = 20

        # Define exclusion zone around player (current platform area)
        # Exclude a wider horizontal band around the player
        player_exclude_left = player_x - int(w * 0.2)
        player_exclude_right = player_x + int(w * 0.2)

        # Find the target platform by scanning horizontally
        # Look for the first non-background object that is NOT near the player
        target_info = None

        y = scan_start_y
        while y < scan_end_y and target_info is None:
            row = img[y, :]
            diff = np.abs(row.astype(np.int16) - bg_color.astype(np.int16))
            diff_sum = np.sum(diff, axis=1)
            is_object = diff_sum > color_threshold * 3

            # Mask out the player's platform area
            is_object[max(0, player_exclude_left):min(w, player_exclude_right)] = False

            # Find contiguous segments
            segments = self._find_segments(is_object)

            for seg_start, seg_end in segments:
                seg_width = seg_end - seg_start
                if seg_width < 80:  # Target platform should be reasonably wide
                    continue

                seg_center_x = (seg_start + seg_end) // 2

                # This is likely the target platform top
                # Analyze it to find the center
                target_info = self._analyze_platform(
                    img, y, seg_start, seg_end, bg_color, color_threshold, h
                )
                if target_info:
                    break

            y += 3  # Step down

        if target_info is None:
            return None

        return (target_info["center_x"], target_info["center_y"])

    def _find_segments(self, is_object: np.ndarray) -> list[tuple[int, int]]:
        """Find contiguous True segments in a boolean array."""
        segments = []
        in_segment = False
        start = 0

        for i, val in enumerate(is_object):
            if val and not in_segment:
                in_segment = True
                start = i
            elif not val and in_segment:
                in_segment = False
                segments.append((start, i))

        if in_segment:
            segments.append((start, len(is_object)))

        return segments

    def _analyze_platform(
        self,
        img: np.ndarray,
        top_y: int,
        left_x: int,
        right_x: int,
        bg_color: np.ndarray,
        threshold: int,
        h: int,
    ) -> dict | None:
        """Analyze a platform to find its center.

        Scans down from the top to find the widest point and center.
        """
        max_width = right_x - left_x
        widest_y = top_y
        widest_left = left_x
        widest_right = right_x

        # Scan down to find widest point
        y = top_y
        scan_limit = min(top_y + 200, int(h * 0.85))

        while y < scan_limit:
            row = img[y, :]
            diff = np.abs(row.astype(np.int16) - bg_color.astype(np.int16))
            diff_sum = np.sum(diff, axis=1)
            is_object = diff_sum > threshold * 3

            # Find the segment containing our platform
            segments = self._find_segments(is_object)

            # Find segment closest to our platform center
            expected_center = (left_x + right_x) // 2
            best_seg = None
            best_dist = float("inf")

            for seg_start, seg_end in segments:
                seg_center = (seg_start + seg_end) // 2
                dist = abs(seg_center - expected_center)
                if dist < best_dist and dist < 100:
                    best_dist = dist
                    best_seg = (seg_start, seg_end)

            if best_seg is None:
                break  # Platform ended

            seg_width = best_seg[1] - best_seg[0]
            if seg_width > max_width:
                max_width = seg_width
                widest_y = y
                widest_left = best_seg[0]
                widest_right = best_seg[1]

            y += 3

        # Platform center is at the widest point
        center_x = (widest_left + widest_right) // 2

        # For Jump Jump, the landing spot is usually slightly above the widest point
        # Approximately at 1/3 from top to widest
        center_y = top_y + (widest_y - top_y) // 3

        return {
            "center_x": center_x,
            "center_y": center_y,
            "top_y": top_y,
            "left": widest_left,
            "right": widest_right,
            "width": max_width,
        }

    def _create_debug_image(
        self,
        img: np.ndarray,
        player_pos: tuple[int, int],
        target_pos: tuple[int, int],
        distance: float,
    ) -> np.ndarray:
        """Create debug visualization image."""
        debug = img.copy()
        player_x, player_y = player_pos
        target_x, target_y = target_pos

        # Draw player position (green circle and crosshair)
        cv2.circle(debug, player_pos, 15, (0, 255, 0), 3)
        cv2.circle(debug, player_pos, 5, (0, 255, 0), -1)
        cv2.line(debug, (player_x - 20, player_y), (player_x + 20, player_y), (0, 255, 0), 2)
        cv2.line(debug, (player_x, player_y - 20), (player_x, player_y + 20), (0, 255, 0), 2)
        cv2.putText(
            debug, "Player", (player_x - 35, player_y + 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )

        # Draw target position (red circle and crosshair)
        cv2.circle(debug, target_pos, 15, (0, 0, 255), 3)
        cv2.circle(debug, target_pos, 5, (0, 0, 255), -1)
        cv2.line(debug, (target_x - 20, target_y), (target_x + 20, target_y), (0, 0, 255), 2)
        cv2.line(debug, (target_x, target_y - 20), (target_x, target_y + 20), (0, 0, 255), 2)
        cv2.putText(
            debug, "Target", (target_x - 35, target_y - 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
        )

        # Draw line between player and target
        cv2.line(debug, player_pos, target_pos, (255, 0, 0), 3)

        # Draw distance text at midpoint with background
        mid_x = (player_x + target_x) // 2
        mid_y = (player_y + target_y) // 2

        text = f"{distance:.0f}px"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        cv2.rectangle(
            debug,
            (mid_x - text_w // 2 - 8, mid_y - text_h - 12),
            (mid_x + text_w // 2 + 8, mid_y + 8),
            (255, 255, 255),
            -1
        )
        cv2.rectangle(
            debug,
            (mid_x - text_w // 2 - 8, mid_y - text_h - 12),
            (mid_x + text_w // 2 + 8, mid_y + 8),
            (255, 0, 0),
            2
        )
        cv2.putText(
            debug, text,
            (mid_x - text_w // 2, mid_y),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2
        )

        # Draw info panel in corner
        duration = distance * 0.00135
        info_lines = [
            f"Distance: {distance:.0f}px",
            f"Hold: {duration:.2f}s",
            f"Direction: {'Right' if target_x > player_x else 'Left'}",
        ]

        y_offset = 30
        for line in info_lines:
            cv2.putText(
                debug, line,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2
            )
            y_offset += 30

        return debug

    def save_debug_image(self, analysis: JumpAnalysis, path: str) -> None:
        """Save debug image to file."""
        if analysis.debug_image is not None:
            cv2.imwrite(path, analysis.debug_image)


def analyze_jump_distance(
    screenshot: bytes,
    screen_width: int,
    screen_height: int,
) -> JumpAnalysis | None:
    """Convenience function to analyze jump distance."""
    analyzer = JumpAnalyzer(screen_width, screen_height, debug=True)
    return analyzer.analyze(screenshot)


__all__ = [
    "JumpAnalysis",
    "JumpAnalyzer",
    "analyze_jump_distance",
]
