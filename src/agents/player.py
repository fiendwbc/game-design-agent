"""Player-Agent implementation for automated game playing.

Uses gemini-2.0-flash for fast visual analysis and action decisions.
"""

import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..models import ActionType
from ..models.session import ActionCommand, NormalizedCoordinate
from ..utils.logging import get_logger
from .base import AgentResponse, PlayerAgentBase


class GameStatus(str, Enum):
    """Detected game status."""

    PLAYING = "playing"
    GAME_OVER = "game_over"
    LEVEL_COMPLETE = "level_complete"
    MENU = "menu"
    LOADING = "loading"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class PlayerDecision(BaseModel):
    """Structured response from Player-Agent."""

    action_type: ActionType
    x: Optional[int] = Field(None, ge=0, le=1000)
    y: Optional[int] = Field(None, ge=0, le=1000)
    end_x: Optional[int] = Field(None, ge=0, le=1000)
    end_y: Optional[int] = Field(None, ge=0, le=1000)
    duration: Optional[float] = Field(None, ge=0.1, le=5.0, description="Hold duration in seconds")
    key: Optional[str] = None
    wait_time: Optional[float] = Field(None, ge=0.1, le=10.0)
    reasoning: str
    game_status: GameStatus = GameStatus.PLAYING
    confidence: float = Field(0.8, ge=0.0, le=1.0)


# JSON schema for structured output
PLAYER_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string",
            "enum": ["click", "hold", "drag", "press", "wait"],
        },
        "x": {"type": "integer", "minimum": 0, "maximum": 1000},
        "y": {"type": "integer", "minimum": 0, "maximum": 1000},
        "end_x": {"type": "integer", "minimum": 0, "maximum": 1000},
        "end_y": {"type": "integer", "minimum": 0, "maximum": 1000},
        "duration": {"type": "number", "minimum": 0.1, "maximum": 5.0},
        "key": {"type": "string"},
        "wait_time": {"type": "number", "minimum": 0.1, "maximum": 10.0},
        "reasoning": {"type": "string"},
        "game_status": {
            "type": "string",
            "enum": ["playing", "game_over", "level_complete", "menu", "loading", "paused", "unknown"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["action_type", "reasoning", "game_status", "confidence"],
}


# System prompt for Player-Agent
PLAYER_SYSTEM_PROMPT = """You are a Player-Agent for automated game playing.

Your role is to analyze visual game input (screenshots or video) and decide the next action to take.

## Coordinate System
- Use normalized coordinates (0-1000) where:
  - (0, 0) = top-left corner
  - (1000, 1000) = bottom-right corner
  - (500, 500) = center of screen

## Available Actions
1. **click**: Click at a specific position (x, y)
2. **hold**: Long press at position (x, y) with duration (0.1-5.0 seconds)
   - IMPORTANT: Use this for games where press duration matters (e.g., "Jump Jump/跳一跳")
   - The longer you hold, the stronger/further the action (jump distance, power, etc.)
   - Estimate distance between objects and adjust duration accordingly:
     * Short distance: 0.2-0.5 seconds
     * Medium distance: 0.5-1.0 seconds
     * Long distance: 1.0-2.0 seconds
     * Very long distance: 2.0-3.0 seconds
3. **drag**: Drag from (x, y) to (end_x, end_y)
4. **press**: Press a keyboard key (e.g., "space", "enter", "up", "down")
5. **wait**: Wait for a specified time (0.1-10 seconds)

## Decision Process
1. Analyze the current game state from the visual input
2. Identify interactive elements (buttons, characters, objects)
3. Determine the game status (playing, game_over, menu, etc.)
4. Choose the most appropriate action
5. For "hold" actions, carefully estimate the required duration based on visual distance
6. Provide clear reasoning for your choice

## Game Status Detection
- **playing**: Normal gameplay in progress
- **game_over**: Game has ended (loss state)
- **level_complete**: Level/stage completed (win state)
- **menu**: In a menu screen
- **loading**: Loading screen
- **paused**: Game is paused
- **unknown**: Cannot determine state

## IMPORTANT: Game Over Handling
When you detect a game over screen (game_status = "game_over"):
- Look for a "再来一次" (Play Again) or similar restart button
- CLICK on that button to restart the game
- Report game_status as "game_over" but action_type as "click"
- This allows the system to continue playing multiple rounds

## Strategy Guidelines
- Prioritize progression over exploration when playing
- Click on obvious interactive elements (buttons, collectibles)
- Use **hold** for games requiring timed/charged actions (jumping games, power meters)
- Use keyboard controls for movement when applicable
- Wait when transitions or animations are occurring
- Avoid clicking on non-interactive UI elements

## Jump Jump (跳一跳) Specific Tips
- The character jumps based on how long you press
- Look at the distance between current platform and target platform
- Hold longer for farther platforms, shorter for closer ones
- Aim for the center of the target platform for bonus points
- The position you click/hold doesn't matter, only the duration

## Learning from Experience (IMPORTANT!)
If "Learned Jump Experience" context is provided:
- USE the learned success rate and average duration as your baseline
- If success rate is HIGH (>70%), trust the learned durations
- If success rate is LOW (<50%), experiment with different durations
- Adjust based on past failures:
  * If similar distances failed with short holds → try longer
  * If similar distances failed with long holds → try shorter
- The system learns from EVERY jump - your choices improve the model!

Always respond with a valid JSON object matching the required schema.
"""


class PlayerAgent(PlayerAgentBase):
    """Player-Agent for automated game playing.

    Uses visual analysis to decide game actions in real-time.
    """

    def __init__(self) -> None:
        """Initialize Player-Agent."""
        super().__init__(
            name="Player-Agent",
            system_prompt=PLAYER_SYSTEM_PROMPT,
        )
        self._logger = get_logger()

    def process(
        self,
        screenshot: Optional[bytes] = None,
        video: Optional[bytes] = None,
        step: int = 0,
        context: Optional[str] = None,
    ) -> ActionCommand:
        """Process visual input and decide next action.

        Args:
            screenshot: Current game screenshot (PNG bytes).
            video: Recent gameplay video (MP4 bytes).
            step: Current step number.
            context: Optional additional context about the game.

        Returns:
            ActionCommand to execute.
        """
        if screenshot is None and video is None:
            self._logger.warning("No visual input provided, returning wait action")
            return self._create_wait_action(step, "No visual input available")

        # Build prompt
        prompt = self._build_prompt(step, context)

        # Generate response
        images = [screenshot] if screenshot else None
        response = self.generate(
            prompt=prompt,
            images=images,
            video=video,
            json_schema=PLAYER_DECISION_SCHEMA,
        )

        # Parse decision
        decision = self._parse_decision(response)
        action = self._decision_to_action(decision, step)

        self._logger.debug(
            f"Step {step}: {decision.action_type.value} "
            f"(status={decision.game_status.value}, confidence={decision.confidence:.2f})"
        )

        return action

    def _build_prompt(self, step: int, context: Optional[str]) -> str:
        """Build the prompt for the model.

        Args:
            step: Current step number.
            context: Optional additional context.

        Returns:
            Formatted prompt string.
        """
        prompt = f"""Analyze this game screen and decide the next action.

Step: {step}
"""

        if context:
            prompt += f"\nContext: {context}\n"

        prompt += """
Based on what you see:
1. What is the current game status?
2. What interactive elements are visible?
3. What action should be taken next?

Respond with a JSON object specifying the action to take.
"""
        return prompt

    def _parse_decision(self, response: AgentResponse) -> PlayerDecision:
        """Parse the model response into a PlayerDecision.

        Args:
            response: AgentResponse from the model.

        Returns:
            Parsed PlayerDecision.
        """
        try:
            data = json.loads(response.content)
            return PlayerDecision(**data)
        except (json.JSONDecodeError, ValueError) as e:
            self._logger.warning(f"Failed to parse decision: {e}")
            # Return default wait action on parse failure
            return PlayerDecision(
                action_type=ActionType.WAIT,
                wait_time=1.0,
                reasoning=f"Parse error: {e}",
                game_status=GameStatus.UNKNOWN,
                confidence=0.0,
            )

    def _decision_to_action(
        self,
        decision: PlayerDecision,
        step: int,
    ) -> ActionCommand:
        """Convert PlayerDecision to ActionCommand.

        Args:
            decision: Parsed PlayerDecision.
            step: Current step number.

        Returns:
            ActionCommand ready for execution.
        """
        start_coord = None
        end_coord = None

        if decision.x is not None and decision.y is not None:
            start_coord = NormalizedCoordinate(x=decision.x, y=decision.y)

        if decision.end_x is not None and decision.end_y is not None:
            end_coord = NormalizedCoordinate(x=decision.end_x, y=decision.end_y)

        # Set duration for HOLD actions
        duration = 0.1  # default
        if decision.action_type == ActionType.HOLD and decision.duration is not None:
            duration = decision.duration

        return ActionCommand(
            step=step,
            action_type=decision.action_type,
            start_coord=start_coord,
            end_coord=end_coord,
            duration=duration,
            key=decision.key,
            wait_time=decision.wait_time,
            reasoning=decision.reasoning,
        )

    def _create_wait_action(self, step: int, reason: str) -> ActionCommand:
        """Create a default wait action.

        Args:
            step: Current step number.
            reason: Reason for waiting.

        Returns:
            Wait ActionCommand.
        """
        return ActionCommand(
            step=step,
            action_type=ActionType.WAIT,
            wait_time=1.0,
            reasoning=reason,
        )

    def detect_game_status(
        self,
        screenshot: Optional[bytes] = None,
        video: Optional[bytes] = None,
    ) -> GameStatus:
        """Detect the current game status.

        Args:
            screenshot: Current game screenshot.
            video: Recent gameplay video.

        Returns:
            Detected GameStatus.
        """
        if screenshot is None and video is None:
            return GameStatus.UNKNOWN

        prompt = """Analyze this game screen and determine the game status.

Possible statuses:
- playing: Normal gameplay in progress
- game_over: Game has ended (loss state, "Game Over" screen)
- level_complete: Level completed (win state, victory screen)
- menu: In a menu or settings screen
- loading: Loading screen
- paused: Game is paused
- unknown: Cannot determine state

What is the current game status? Respond with a JSON object.
"""

        images = [screenshot] if screenshot else None
        response = self.generate(
            prompt=prompt,
            images=images,
            video=video,
            json_schema=PLAYER_DECISION_SCHEMA,
        )

        try:
            data = json.loads(response.content)
            return GameStatus(data.get("game_status", "unknown"))
        except (json.JSONDecodeError, ValueError):
            return GameStatus.UNKNOWN

    def is_game_over(
        self,
        screenshot: Optional[bytes] = None,
        video: Optional[bytes] = None,
    ) -> bool:
        """Check if the game is over.

        Args:
            screenshot: Current game screenshot.
            video: Recent gameplay video.

        Returns:
            True if game is over (either win or loss).
        """
        status = self.detect_game_status(screenshot, video)
        return status in (GameStatus.GAME_OVER, GameStatus.LEVEL_COMPLETE)

    def is_in_menu(
        self,
        screenshot: Optional[bytes] = None,
        video: Optional[bytes] = None,
    ) -> bool:
        """Check if currently in a menu.

        Args:
            screenshot: Current game screenshot.
            video: Recent gameplay video.

        Returns:
            True if in menu.
        """
        status = self.detect_game_status(screenshot, video)
        return status == GameStatus.MENU


__all__ = [
    "GameStatus",
    "PlayerDecision",
    "PlayerAgent",
    "PLAYER_SYSTEM_PROMPT",
    "PLAYER_DECISION_SCHEMA",
]
