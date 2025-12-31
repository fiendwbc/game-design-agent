"""Input controller module using pydirectinput.

Provides game input control with coordinate normalization.
"""

import time
from dataclasses import dataclass
from typing import Optional, Tuple

import pydirectinput

from ..models import ActionType, ActionResult
from ..models.session import (
    ActionCommand,
    NormalizedCoordinate,
    WindowRegion,
)
from ..utils.logging import get_logger


# Normalized coordinate range (0-1000)
NORMALIZED_MAX = 1000


@dataclass
class CoordinateNormalizer:
    """Converts normalized coordinates (0-1000) to screen coordinates.

    The normalized coordinate system uses a 0-1000 range for both X and Y,
    allowing resolution-independent input specification.
    """

    region: WindowRegion

    def to_screen(self, coord: NormalizedCoordinate) -> Tuple[int, int]:
        """Convert normalized coordinate to screen coordinate.

        Args:
            coord: NormalizedCoordinate with x, y in 0-1000 range.

        Returns:
            Tuple of (screen_x, screen_y).
        """
        # Scale normalized coords to region size
        x = self.region.x + int(coord.x * self.region.width / NORMALIZED_MAX)
        y = self.region.y + int(coord.y * self.region.height / NORMALIZED_MAX)

        return (x, y)

    def from_screen(self, screen_x: int, screen_y: int) -> NormalizedCoordinate:
        """Convert screen coordinate to normalized coordinate.

        Args:
            screen_x: Screen X coordinate.
            screen_y: Screen Y coordinate.

        Returns:
            NormalizedCoordinate with x, y in 0-1000 range.
        """
        # Convert screen coords to normalized
        x = int((screen_x - self.region.x) * NORMALIZED_MAX / self.region.width)
        y = int((screen_y - self.region.y) * NORMALIZED_MAX / self.region.height)

        # Clamp to valid range
        x = max(0, min(NORMALIZED_MAX, x))
        y = max(0, min(NORMALIZED_MAX, y))

        return NormalizedCoordinate(x=x, y=y)

    def is_in_region(self, screen_x: int, screen_y: int) -> bool:
        """Check if screen coordinate is within the region.

        Args:
            screen_x: Screen X coordinate.
            screen_y: Screen Y coordinate.

        Returns:
            True if coordinate is within region.
        """
        return (
            self.region.x <= screen_x < self.region.x + self.region.width
            and self.region.y <= screen_y < self.region.y + self.region.height
        )


class InputController:
    """Game input controller using pydirectinput.

    Handles all input operations with coordinate normalization
    and safety features.
    """

    def __init__(
        self,
        region: WindowRegion,
        click_delay: float = 0.05,
        key_delay: float = 0.05,
        drag_duration: float = 0.3,
    ) -> None:
        """Initialize input controller.

        Args:
            region: Window region for coordinate normalization.
            click_delay: Delay after click in seconds.
            key_delay: Delay between key presses in seconds.
            drag_duration: Duration of drag operation in seconds.
        """
        self.region = region
        self.normalizer = CoordinateNormalizer(region)
        self.click_delay = click_delay
        self.key_delay = key_delay
        self.drag_duration = drag_duration
        self._logger = get_logger()

        # Configure pydirectinput
        pydirectinput.PAUSE = 0.0  # We handle delays ourselves
        pydirectinput.FAILSAFE = True  # Enable fail-safe (move to corner to abort)

    def execute_action(self, action: ActionCommand) -> ActionResult:
        """Execute an action command.

        Args:
            action: ActionCommand to execute.

        Returns:
            ActionResult indicating success or failure.
        """
        try:
            match action.action_type:
                case ActionType.CLICK:
                    return self._execute_click(action)
                case ActionType.HOLD:
                    return self._execute_hold(action)
                case ActionType.DRAG:
                    return self._execute_drag(action)
                case ActionType.PRESS:
                    return self._execute_press(action)
                case ActionType.WAIT:
                    return self._execute_wait(action)
                case _:
                    self._logger.error(f"Unknown action type: {action.action_type}")
                    return ActionResult.FAILED

        except Exception as e:
            self._logger.error(f"Action execution failed: {e}")
            return ActionResult.FAILED

    def _execute_click(self, action: ActionCommand) -> ActionResult:
        """Execute a click action.

        Args:
            action: ActionCommand with click details.

        Returns:
            ActionResult.
        """
        if not action.start_coord:
            self._logger.error("Click action missing start_coord")
            return ActionResult.FAILED

        screen_x, screen_y = self.normalizer.to_screen(action.start_coord)

        self._logger.debug(
            f"Click at normalized ({action.start_coord.x}, {action.start_coord.y}) "
            f"-> screen ({screen_x}, {screen_y})"
        )

        # Move and click
        pydirectinput.moveTo(screen_x, screen_y)
        pydirectinput.click()
        time.sleep(self.click_delay)

        return ActionResult.SUCCESS

    def _execute_hold(self, action: ActionCommand) -> ActionResult:
        """Execute a hold/long press action.

        Used for games like Jump Jump where press duration controls jump distance.

        Args:
            action: ActionCommand with hold details.
                - start_coord: Position to hold at
                - duration: How long to hold in seconds

        Returns:
            ActionResult.
        """
        if not action.start_coord:
            self._logger.error("Hold action missing start_coord")
            return ActionResult.FAILED

        screen_x, screen_y = self.normalizer.to_screen(action.start_coord)
        hold_duration = action.duration if action.duration else 0.5

        self._logger.debug(
            f"Hold at normalized ({action.start_coord.x}, {action.start_coord.y}) "
            f"-> screen ({screen_x}, {screen_y}) for {hold_duration:.3f}s"
        )

        # Move to position
        pydirectinput.moveTo(screen_x, screen_y)

        # Press and hold
        pydirectinput.mouseDown()
        time.sleep(hold_duration)
        pydirectinput.mouseUp()

        time.sleep(self.click_delay)
        return ActionResult.SUCCESS

    def _execute_drag(self, action: ActionCommand) -> ActionResult:
        """Execute a drag action.

        Args:
            action: ActionCommand with drag details.

        Returns:
            ActionResult.
        """
        if not action.start_coord or not action.end_coord:
            self._logger.error("Drag action missing start_coord or end_coord")
            return ActionResult.FAILED

        start_x, start_y = self.normalizer.to_screen(action.start_coord)
        end_x, end_y = self.normalizer.to_screen(action.end_coord)

        self._logger.debug(
            f"Drag from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        )

        # Perform drag
        pydirectinput.moveTo(start_x, start_y)
        pydirectinput.mouseDown()

        # Smooth drag movement
        steps = max(10, int(self.drag_duration * 60))  # 60 steps per second
        for i in range(1, steps + 1):
            t = i / steps
            x = int(start_x + (end_x - start_x) * t)
            y = int(start_y + (end_y - start_y) * t)
            pydirectinput.moveTo(x, y)
            time.sleep(self.drag_duration / steps)

        pydirectinput.mouseUp()
        time.sleep(self.click_delay)

        return ActionResult.SUCCESS

    def _execute_press(self, action: ActionCommand) -> ActionResult:
        """Execute a key press action.

        Args:
            action: ActionCommand with key details.

        Returns:
            ActionResult.
        """
        if not action.key:
            self._logger.error("Press action missing key")
            return ActionResult.FAILED

        self._logger.debug(f"Press key: {action.key}")

        # Handle special keys and key combinations
        key = action.key.lower()

        if "+" in key:
            # Key combination (e.g., "ctrl+c")
            keys = key.split("+")
            for k in keys[:-1]:
                pydirectinput.keyDown(k.strip())
            pydirectinput.press(keys[-1].strip())
            for k in reversed(keys[:-1]):
                pydirectinput.keyUp(k.strip())
        else:
            pydirectinput.press(key)

        time.sleep(self.key_delay)
        return ActionResult.SUCCESS

    def _execute_wait(self, action: ActionCommand) -> ActionResult:
        """Execute a wait action.

        Args:
            action: ActionCommand with wait details.

        Returns:
            ActionResult.
        """
        wait_time = action.wait_time or 1.0
        self._logger.debug(f"Wait for {wait_time}s")
        time.sleep(wait_time)
        return ActionResult.SUCCESS

    def click(self, x: int, y: int) -> ActionResult:
        """Click at normalized coordinates.

        Args:
            x: Normalized X coordinate (0-1000).
            y: Normalized Y coordinate (0-1000).

        Returns:
            ActionResult.
        """
        action = ActionCommand(
            step=0,
            action_type=ActionType.CLICK,
            start_coord=NormalizedCoordinate(x=x, y=y),
            reasoning="Direct click",
        )
        return self.execute_action(action)

    def hold(self, x: int, y: int, duration: float = 0.5) -> ActionResult:
        """Hold/long press at normalized coordinates.

        Used for games like Jump Jump where press duration controls jump distance.

        Args:
            x: Normalized X coordinate (0-1000).
            y: Normalized Y coordinate (0-1000).
            duration: Hold duration in seconds (default 0.5).

        Returns:
            ActionResult.
        """
        action = ActionCommand(
            step=0,
            action_type=ActionType.HOLD,
            start_coord=NormalizedCoordinate(x=x, y=y),
            duration=duration,
            reasoning="Direct hold",
        )
        return self.execute_action(action)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> ActionResult:
        """Drag from start to end normalized coordinates.

        Args:
            start_x: Start X coordinate (0-1000).
            start_y: Start Y coordinate (0-1000).
            end_x: End X coordinate (0-1000).
            end_y: End Y coordinate (0-1000).

        Returns:
            ActionResult.
        """
        action = ActionCommand(
            step=0,
            action_type=ActionType.DRAG,
            start_coord=NormalizedCoordinate(x=start_x, y=start_y),
            end_coord=NormalizedCoordinate(x=end_x, y=end_y),
            reasoning="Direct drag",
        )
        return self.execute_action(action)

    def press_key(self, key: str) -> ActionResult:
        """Press a key.

        Args:
            key: Key to press (e.g., "space", "enter", "ctrl+c").

        Returns:
            ActionResult.
        """
        action = ActionCommand(
            step=0,
            action_type=ActionType.PRESS,
            key=key,
            reasoning="Direct key press",
        )
        return self.execute_action(action)

    def type_text(self, text: str) -> ActionResult:
        """Type a string of text.

        Args:
            text: Text to type.

        Returns:
            ActionResult.
        """
        self._logger.debug(f"Typing: {text[:20]}..." if len(text) > 20 else f"Typing: {text}")

        for char in text:
            pydirectinput.press(char)
            time.sleep(self.key_delay)

        return ActionResult.SUCCESS

    def wait(self, seconds: float) -> ActionResult:
        """Wait for specified time.

        Args:
            seconds: Time to wait in seconds.

        Returns:
            ActionResult.
        """
        action = ActionCommand(
            step=0,
            action_type=ActionType.WAIT,
            wait_time=seconds,
            reasoning="Direct wait",
        )
        return self.execute_action(action)

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position in screen coordinates.

        Returns:
            Tuple of (screen_x, screen_y).
        """
        return pydirectinput.position()

    def get_normalized_mouse_position(self) -> NormalizedCoordinate:
        """Get current mouse position as normalized coordinate.

        Returns:
            NormalizedCoordinate.
        """
        screen_x, screen_y = self.get_mouse_position()
        return self.normalizer.from_screen(screen_x, screen_y)


# Convenience functions for quick usage
def click(
    region: WindowRegion,
    x: int,
    y: int,
) -> ActionResult:
    """Click at normalized coordinates.

    Args:
        region: Window region for normalization.
        x: Normalized X coordinate (0-1000).
        y: Normalized Y coordinate (0-1000).

    Returns:
        ActionResult.
    """
    controller = InputController(region)
    return controller.click(x, y)


def hold(
    region: WindowRegion,
    x: int,
    y: int,
    duration: float = 0.5,
) -> ActionResult:
    """Hold/long press at normalized coordinates.

    Used for games like Jump Jump where press duration controls jump distance.

    Args:
        region: Window region for normalization.
        x: Normalized X coordinate (0-1000).
        y: Normalized Y coordinate (0-1000).
        duration: Hold duration in seconds (default 0.5).

    Returns:
        ActionResult.
    """
    controller = InputController(region)
    return controller.hold(x, y, duration)


def drag(
    region: WindowRegion,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
) -> ActionResult:
    """Drag from start to end normalized coordinates.

    Args:
        region: Window region for normalization.
        start_x: Start X coordinate (0-1000).
        start_y: Start Y coordinate (0-1000).
        end_x: End X coordinate (0-1000).
        end_y: End Y coordinate (0-1000).

    Returns:
        ActionResult.
    """
    controller = InputController(region)
    return controller.drag(start_x, start_y, end_x, end_y)


def press_key(region: WindowRegion, key: str) -> ActionResult:
    """Press a key.

    Args:
        region: Window region (used for controller initialization).
        key: Key to press.

    Returns:
        ActionResult.
    """
    controller = InputController(region)
    return controller.press_key(key)


def type_text(region: WindowRegion, text: str) -> ActionResult:
    """Type text.

    Args:
        region: Window region (used for controller initialization).
        text: Text to type.

    Returns:
        ActionResult.
    """
    controller = InputController(region)
    return controller.type_text(text)


__all__ = [
    "NORMALIZED_MAX",
    "CoordinateNormalizer",
    "InputController",
    "click",
    "hold",
    "drag",
    "press_key",
    "type_text",
]
