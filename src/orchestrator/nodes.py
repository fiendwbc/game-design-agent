"""LangGraph node implementations for the game analysis system.

Full implementations for Phase 3 (US1) - Automated Game Play.
"""

import time
from pathlib import Path
from typing import Any, Optional

from langsmith import traceable

from ..agents.player import GameStatus, PlayerAgent
from ..capture.screen import ScreenCapture
from ..capture.video import VideoSynthesizer
from ..control.input import InputController
from ..memory.play_log import PlayLog
from ..models import ActionResult, SessionStatus
from ..models.session import WindowRegion
from ..utils.logging import get_logger, log_step
from ..utils.tracing import is_tracing_enabled


# Initialize logger
_logger = get_logger()

# Singleton instances (initialized per session)
_capture: Optional[ScreenCapture] = None
_video_synth: Optional[VideoSynthesizer] = None
_input_controller: Optional[InputController] = None
_player_agent: Optional[PlayerAgent] = None
_play_log: Optional[PlayLog] = None


def init_session_resources(
    region: WindowRegion,
    session_id: str,
    output_dir: Path,
) -> None:
    """Initialize session resources for the game loop.

    Args:
        region: Window region for capture and input.
        session_id: Session identifier.
        output_dir: Directory for output files.
    """
    global _capture, _video_synth, _input_controller, _player_agent, _play_log

    _logger.info(f"Initializing session resources for {session_id}")

    _capture = ScreenCapture(region=region)
    _video_synth = VideoSynthesizer(region=region, fps=15.0)
    _input_controller = InputController(region)
    _player_agent = PlayerAgent()
    _play_log = PlayLog(session_id=session_id, output_dir=output_dir)


def cleanup_session_resources() -> None:
    """Cleanup session resources."""
    global _capture, _video_synth, _input_controller, _player_agent, _play_log

    if _capture:
        _capture.close()
        _capture = None

    if _video_synth:
        _video_synth = None

    _input_controller = None
    _player_agent = None

    if _play_log:
        try:
            _play_log.save()
        except Exception as e:
            _logger.error(f"Failed to save play log: {e}")
        _play_log = None


@traceable(name="observe_node", run_type="chain")
def observe_node(state: dict[str, Any]) -> dict[str, Any]:
    """Observe node: Capture screen/video from the game window.

    This node captures the current game state as visual input
    for the Player-Agent to analyze.
    """
    step = state.get("current_step", 0)
    log_step(step, "Observing game screen...")

    new_state = state.copy()

    try:
        if _capture is None:
            raise RuntimeError("Screen capture not initialized")

        # Capture screenshot
        screenshot = _capture.capture()
        new_state["current_screenshot"] = screenshot

        # Optionally capture video segment for richer context
        if _video_synth and step % 5 == 0:  # Every 5 steps, capture video
            segment = _video_synth.record_segment(duration=2.0)
            new_state["current_video"] = segment.data
            log_step(step, f"Captured video segment ({segment.size_mb:.1f}MB)")
        else:
            new_state["current_video"] = None

        log_step(step, "Screen captured successfully")

    except Exception as e:
        _logger.error(f"Observe failed: {e}")
        new_state["error"] = str(e)

    return new_state


@traceable(name="think_node", run_type="chain")
def think_node(state: dict[str, Any]) -> dict[str, Any]:
    """Think node: Player-Agent decides the next action.

    This node uses the Player-Agent to analyze the visual input
    and decide what action to take next.
    """
    step = state.get("current_step", 0)
    log_step(step, "Player-Agent thinking...")

    new_state = state.copy()

    try:
        if _player_agent is None:
            raise RuntimeError("Player-Agent not initialized")

        screenshot = state.get("current_screenshot")
        video = state.get("current_video")

        if screenshot is None:
            raise RuntimeError("No screenshot available for decision")

        # Build context from play log
        context = None
        if _play_log and len(_play_log) > 0:
            context = _play_log.get_context_for_agent(max_entries=5)

        # Get action decision from Player-Agent
        action = _player_agent.process(
            screenshot=screenshot,
            video=video,
            step=step,
            context=context,
        )

        new_state["pending_action"] = action
        log_step(
            step,
            f"Decided: {action.action_type.value} - {action.reasoning[:50]}..."
            if len(action.reasoning) > 50
            else f"Decided: {action.action_type.value} - {action.reasoning}"
        )

        # Check for game over
        status = _player_agent.detect_game_status(screenshot=screenshot)
        if status == GameStatus.GAME_OVER:
            log_step(step, "Game over detected!")
            new_state["game_over"] = True
        elif status == GameStatus.LEVEL_COMPLETE:
            log_step(step, "Level complete detected!")
            new_state["level_complete"] = True

    except Exception as e:
        _logger.error(f"Think failed: {e}")
        new_state["error"] = str(e)

    return new_state


@traceable(name="act_node", run_type="chain")
def act_node(state: dict[str, Any]) -> dict[str, Any]:
    """Act node: Execute the pending action.

    This node executes the action decided by the Player-Agent
    using pydirectinput.
    """
    step = state.get("current_step", 0)
    action = state.get("pending_action")

    new_state = state.copy()

    if action is None:
        log_step(step, "No action to execute")
        return new_state

    log_step(step, f"Executing action: {action.action_type.value}")

    try:
        if _input_controller is None:
            raise RuntimeError("Input controller not initialized")

        # Execute the action
        result = _input_controller.execute_action(action)
        new_state["action_result"] = result

        # Log to play log
        if _play_log:
            _play_log.add_action(action, result=result)

        if result == ActionResult.SUCCESS:
            log_step(step, f"Action executed successfully")
        else:
            log_step(step, f"Action failed", level="warning")

    except Exception as e:
        _logger.error(f"Act failed: {e}")
        new_state["error"] = str(e)
        new_state["action_result"] = ActionResult.FAILED

    return new_state


@traceable(name="record_node", run_type="chain")
def record_node(state: dict[str, Any]) -> dict[str, Any]:
    """Record node: Capture the reaction to the action.

    This node records the game's response to the executed action,
    capturing the "effect" of the action.
    """
    step = state.get("current_step", 0)
    log_step(step, "Recording reaction...")

    new_state = state.copy()

    try:
        # Wait briefly for game to respond to action
        time.sleep(0.3)

        # Capture post-action screenshot for comparison
        if _capture:
            post_screenshot = _capture.capture()
            new_state["post_action_screenshot"] = post_screenshot
            log_step(step, "Post-action screenshot captured")

        # Optionally record reaction video
        if _video_synth and state.get("action_result") == ActionResult.SUCCESS:
            # Short recording to capture immediate reaction
            segment = _video_synth.record_segment(duration=1.5)
            new_state["reaction_video"] = segment.data
            log_step(step, f"Reaction video recorded ({segment.size_mb:.1f}MB)")

    except Exception as e:
        _logger.error(f"Record failed: {e}")
        # Non-fatal error, continue

    return new_state


@traceable(name="analyze_node", run_type="chain")
def analyze_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze node: Run analysis agents on the captured data.

    This node runs multiple analysis agents in parallel:
    - Mechanics-Analyst (US2)
    - UI-Agent (US3)
    - Art-Agent (US4)

    Will be fully implemented in Phase 4-6.
    """
    step = state.get("current_step", 0)
    log_step(step, "Running analysis agents...")

    new_state = state.copy()

    # Placeholder: Analysis agents will be added in later phases
    # For now, just pass through
    # Full implementation will:
    # 1. Run Mechanics-Analyst → update mechanics_state
    # 2. Run UI-Agent → update ui_flow_graph
    # 3. Run Art-Agent → update art_style_state
    # All in parallel for efficiency

    return new_state


@traceable(name="update_memory_node", run_type="chain")
def update_memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Update memory node: Persist analysis results.

    This node updates the memory modules with the latest
    analysis results and increments the step counter.
    """
    step = state.get("current_step", 0)
    log_step(step, "Updating memory modules...")

    new_state = state.copy()

    # Update play log with observation if available
    if _play_log:
        action = state.get("pending_action")
        if action:
            # Generate observation from post-action state
            observation = _generate_observation(state)
            _play_log.add_observation(step, observation)

    # Increment step counter
    new_state["current_step"] = step + 1

    return new_state


def _generate_observation(state: dict[str, Any]) -> str:
    """Generate observation text from state.

    Args:
        state: Current game state.

    Returns:
        Observation string.
    """
    action = state.get("pending_action")
    result = state.get("action_result", ActionResult.PENDING)

    parts = []

    if action:
        parts.append(f"Executed {action.action_type.value}")
        if action.reasoning:
            parts.append(f"for: {action.reasoning}")

    parts.append(f"Result: {result.value}")

    if state.get("game_over"):
        parts.append("(Game Over detected)")
    elif state.get("level_complete"):
        parts.append("(Level Complete detected)")

    return " | ".join(parts)


@traceable(name="check_continue_node", run_type="chain")
def check_continue_node(state: dict[str, Any]) -> dict[str, Any]:
    """Check continue node: Decide whether to continue or end.

    This node checks termination conditions:
    - Max steps reached
    - Game over detected
    - Level complete detected
    - User requested stop
    - Error occurred
    """
    step = state.get("current_step", 0)
    max_steps = state.get("max_steps", 100)
    error = state.get("error")

    new_state = state.copy()

    # Check termination conditions
    if error:
        log_step(step, f"Ending due to error: {error}", level="error")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.FAILED

    elif step >= max_steps:
        log_step(step, f"Max steps ({max_steps}) reached, ending session")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.COMPLETED

    elif state.get("game_over"):
        log_step(step, "Game over, ending session")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.COMPLETED

    elif state.get("level_complete"):
        log_step(step, "Level complete, ending session")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.COMPLETED

    else:
        new_state["should_continue"] = True
        new_state["status"] = SessionStatus.RUNNING

    # Log session summary periodically
    if step > 0 and step % 10 == 0:
        _log_session_summary(step)

    return new_state


def _log_session_summary(step: int) -> None:
    """Log a session summary.

    Args:
        step: Current step number.
    """
    if _play_log:
        summary = _play_log.summarize()
        _logger.info(
            f"Session progress: {step} steps, "
            f"{summary['by_result'].get('success', 0)} successful, "
            f"{summary['by_result'].get('failed', 0)} failed"
        )


__all__ = [
    "init_session_resources",
    "cleanup_session_resources",
    "observe_node",
    "think_node",
    "act_node",
    "record_node",
    "analyze_node",
    "update_memory_node",
    "check_continue_node",
]
