"""LangGraph node implementations for the game analysis system.

Full implementations for Phase 3 (US1) - Automated Game Play.
"""

import time
from pathlib import Path
from typing import Any

from langsmith import traceable

from ..agents.player import GameStatus, PlayerAgent
from ..analysis.jump_analyzer import JumpAnalysis, JumpAnalyzer
from ..capture.screen import ScreenCapture
from ..capture.video import VideoSynthesizer
from ..control.input import InputController
from ..memory.jump_memory import JumpMemory
from ..memory.play_log import PlayLog
from ..models import ActionResult, ActionType, SessionStatus
from ..models.session import WindowRegion
from ..utils.logging import get_logger, log_step

# Initialize logger
_logger = get_logger()

# Singleton instances (initialized per session)
_capture: ScreenCapture | None = None
_video_synth: VideoSynthesizer | None = None
_input_controller: InputController | None = None
_player_agent: PlayerAgent | None = None
_play_log: PlayLog | None = None
_jump_memory: JumpMemory | None = None
_jump_analyzer: JumpAnalyzer | None = None

# Track last hold action for learning (with distance info)
_last_hold_action: dict | None = None

# Track last jump analysis for passing to AI
_last_jump_analysis: JumpAnalysis | None = None


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
    global _capture, _video_synth, _input_controller, _player_agent, _play_log, _jump_memory, _jump_analyzer, _last_hold_action, _last_jump_analysis

    _logger.info(f"Initializing session resources for {session_id}")

    _capture = ScreenCapture(region=region)
    _video_synth = VideoSynthesizer(region=region, fps=15.0)
    _input_controller = InputController(region)
    _player_agent = PlayerAgent()
    _play_log = PlayLog(session_id=session_id, output_dir=output_dir)

    # Initialize jump analyzer for distance detection
    _jump_analyzer = JumpAnalyzer(
        screen_width=region.width,
        screen_height=region.height,
        debug=True,  # Save debug images
    )

    # Initialize jump memory with screen dimensions
    # Uses persistent file to learn across sessions
    jump_memory_file = output_dir / "jump_memory.json"
    _jump_memory = JumpMemory(
        screen_width=region.width,
        screen_height=region.height,
        memory_file=jump_memory_file,
    )
    _last_hold_action = None
    _last_jump_analysis = None

    if len(_jump_memory) > 0:
        stats = _jump_memory.get_statistics()
        _logger.info(
            f"Loaded {stats['total_jumps']} jump experiences "
            f"(success rate: {stats['success_rate']:.1%})"
        )


def cleanup_session_resources() -> None:
    """Cleanup session resources."""
    global _capture, _video_synth, _input_controller, _player_agent, _play_log, _jump_memory, _last_hold_action, _last_jump_analysis

    # Close any OpenCV windows
    import cv2
    cv2.destroyAllWindows()

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

    if _jump_memory:
        try:
            _jump_memory.save()
            stats = _jump_memory.get_statistics()
            _logger.info(
                f"Jump memory saved: {stats['total_jumps']} experiences, "
                f"success rate: {stats['success_rate']:.1%}"
            )
        except Exception as e:
            _logger.error(f"Failed to save jump memory: {e}")
        _jump_memory = None

    _last_hold_action = None
    _last_jump_analysis = None


@traceable(name="observe_node", run_type="chain")
def observe_node(state: dict[str, Any]) -> dict[str, Any]:
    """Observe node: Capture screen/video from the game window.

    This node captures the current game state as visual input
    for the Player-Agent to analyze. Also runs OpenCV distance
    analysis to detect jump distance.
    """
    global _last_jump_analysis

    step = state.get("current_step", 0)
    log_step(step, "Observing game screen...")

    new_state = state.copy()

    try:
        if _capture is None:
            raise RuntimeError("Screen capture not initialized")

        # Capture screenshot
        screenshot = _capture.capture()
        new_state["current_screenshot"] = screenshot

        # Analyze jump distance using OpenCV
        if _jump_analyzer and screenshot:
            analysis = _jump_analyzer.analyze(screenshot)
            if analysis:
                _last_jump_analysis = analysis
                log_step(
                    step,
                    f"Jump analysis: {analysis.distance_pixels:.0f}px {analysis.direction}, "
                    f"player=({analysis.player_x},{analysis.player_y}), "
                    f"target=({analysis.target_x},{analysis.target_y})"
                )
                # Save and display debug image if available
                if analysis.debug_image is not None:
                    # Save to file
                    if _play_log and _play_log.output_dir:
                        debug_path = str(_play_log.output_dir / f"jump_debug_{step:03d}.png")
                        _jump_analyzer.save_debug_image(analysis, debug_path)

                    # Display using imshow
                    import cv2
                    cv2.imshow("Jump Distance Detection", analysis.debug_image)
                    cv2.waitKey(1)  # Non-blocking, just refresh the window
            else:
                _last_jump_analysis = None
                log_step(step, "Could not detect jump distance (no platforms found)")

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
    and decide what action to take next. Uses jump memory for
    RAG-based learning, and provides OpenCV-detected distance.
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
        context_parts = []
        if _play_log and len(_play_log) > 0:
            context_parts.append(_play_log.get_context_for_agent(max_entries=5))

        # Add OpenCV-detected jump distance info
        if _last_jump_analysis:
            analysis = _last_jump_analysis
            context_parts.append(
                f"\n=== OpenCV Distance Analysis ===\n"
                f"Detected jump distance: {analysis.distance_pixels:.0f} pixels\n"
                f"Direction: {analysis.direction}\n"
                f"Player position: ({analysis.player_x}, {analysis.player_y})\n"
                f"Target position: ({analysis.target_x}, {analysis.target_y})\n"
                f"Recommended duration: {analysis.get_recommended_duration():.2f}s\n"
                f"Confidence: {analysis.confidence:.0%}\n"
                f"USE THIS DISTANCE TO CALCULATE HOLD DURATION!"
            )

            # If we have jump memory, provide prediction based on similar distances
            if _jump_memory and len(_jump_memory) > 0:
                predicted_duration, confidence = _jump_memory.predict_duration(
                    analysis.distance_pixels
                )
                if confidence > 0:
                    context_parts.append(
                        f"\n=== RAG Prediction ===\n"
                        f"Based on {len(_jump_memory)} past experiences:\n"
                        f"Predicted duration for {analysis.distance_pixels:.0f}px: {predicted_duration:.2f}s\n"
                        f"Prediction confidence: {confidence:.0%}\n"
                        f"Use this as reference for your HOLD duration!"
                    )

        # Add general jump memory stats
        if _jump_memory and len(_jump_memory) > 0:
            stats = _jump_memory.get_statistics()
            context_parts.append(
                f"\n=== Learned Jump Experience ===\n"
                f"Total jumps learned: {stats['total_jumps']}\n"
                f"Success rate: {stats['success_rate']:.1%}\n"
                f"Avg successful duration: {stats['avg_success_duration']:.2f}s\n"
            )

        context = "\n".join(context_parts) if context_parts else None

        # Get action decision from Player-Agent
        action = _player_agent.process(
            screenshot=screenshot,
            video=video,
            step=step,
            context=context,
        )

        # Override AI's hold duration with OpenCV-calculated duration
        if action.action_type == ActionType.HOLD and _last_jump_analysis:
            opencv_duration = _last_jump_analysis.get_recommended_duration()
            if action.duration != opencv_duration:
                log_step(
                    step,
                    f"Overriding AI duration {action.duration:.2f}s → OpenCV {opencv_duration:.2f}s "
                    f"(distance: {_last_jump_analysis.distance_pixels:.0f}px)"
                )
                action.duration = opencv_duration

        new_state["pending_action"] = action
        log_step(
            step,
            f"Decided: {action.action_type.value} - {action.reasoning[:50]}..."
            if len(action.reasoning or "") > 50
            else f"Decided: {action.action_type.value} - {action.reasoning or ''}"
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
    using pydirectinput. Tracks hold actions for learning.
    """
    global _last_hold_action

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

        # Track hold actions for learning (include distance if available)
        if action.action_type == ActionType.HOLD and result == ActionResult.SUCCESS:
            _last_hold_action = {
                "step": step,
                "duration": action.duration,
                "reasoning": action.reasoning,
                "x": action.start_coord.x if action.start_coord else 500,
                "y": action.start_coord.y if action.start_coord else 500,
                "distance_pixels": _last_jump_analysis.distance_pixels if _last_jump_analysis else None,
                "player_pos": (
                    (_last_jump_analysis.player_x, _last_jump_analysis.player_y)
                    if _last_jump_analysis else None
                ),
                "target_pos": (
                    (_last_jump_analysis.target_x, _last_jump_analysis.target_y)
                    if _last_jump_analysis else None
                ),
            }
            if _last_jump_analysis:
                log_step(
                    step,
                    f"Hold action tracked: {action.duration:.2f}s for {_last_jump_analysis.distance_pixels:.0f}px"
                )
            else:
                log_step(step, f"Hold action tracked: {action.duration:.2f}s (no distance)")

        if result == ActionResult.SUCCESS:
            log_step(step, "Action executed successfully")
        else:
            log_step(step, "Action failed", level="warning")

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

    This node checks termination conditions and records jump learning.
    Supports multi-round play (clicking "再来一次" to continue).
    """
    global _last_hold_action

    step = state.get("current_step", 0)
    max_steps = state.get("max_steps", 100)
    error = state.get("error")
    game_over = state.get("game_over", False)
    current_round = state.get("current_round", 1)
    min_rounds = state.get("min_rounds", 3)

    new_state = state.copy()
    session_ended = False

    # Record jump learning if there was a hold action
    if _last_hold_action and _jump_memory:
        distance = _last_hold_action.get("distance_pixels")
        duration = _last_hold_action["duration"]

        if game_over:
            # Jump failed - record as failure
            _jump_memory.add_experience(
                distance_pixels=distance,
                hold_duration=duration,
                success=False,
                click_x=_last_hold_action["x"],
                click_y=_last_hold_action["y"],
                reasoning=_last_hold_action["reasoning"],
            )
            if distance:
                log_step(step, f"[LEARN] Jump FAILED: {distance:.0f}px → {duration:.2f}s")
            else:
                log_step(step, f"[LEARN] Jump FAILED: held {duration:.2f}s")
            _last_hold_action = None
        elif not game_over and not state.get("level_complete"):
            # Jump succeeded - record as success
            _jump_memory.add_experience(
                distance_pixels=distance,
                hold_duration=duration,
                success=True,
                click_x=_last_hold_action["x"],
                click_y=_last_hold_action["y"],
                reasoning=_last_hold_action["reasoning"],
            )
            if distance:
                log_step(step, f"[LEARN] Jump SUCCESS: {distance:.0f}px → {duration:.2f}s")
            else:
                log_step(step, f"[LEARN] Jump SUCCESS: held {duration:.2f}s")
            _last_hold_action = None

    # Check termination conditions
    if error:
        log_step(step, f"Ending due to error: {error}", level="error")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.FAILED
        session_ended = True

    elif step >= max_steps:
        log_step(step, f"Max steps ({max_steps}) reached, ending session")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.COMPLETED
        session_ended = True

    elif game_over:
        # Check if we should continue to next round
        if current_round < min_rounds:
            # Continue playing - start new round
            log_step(step, f"Round {current_round} ended! Starting round {current_round + 1}/{min_rounds}...")
            new_state["game_over"] = False  # Reset game over flag
            new_state["current_round"] = current_round + 1
            new_state["should_continue"] = True
            new_state["status"] = SessionStatus.RUNNING
            # The next think_node will see game over screen and click "再来一次"
        else:
            # Played enough rounds, end session
            log_step(step, f"Completed {current_round} rounds, ending session")
            new_state["should_continue"] = False
            new_state["status"] = SessionStatus.COMPLETED
            session_ended = True

    elif state.get("level_complete"):
        log_step(step, "Level complete, ending session")
        new_state["should_continue"] = False
        new_state["status"] = SessionStatus.COMPLETED
        session_ended = True

    else:
        new_state["should_continue"] = True
        new_state["status"] = SessionStatus.RUNNING

    # Log session summary periodically
    if step > 0 and step % 10 == 0:
        _log_session_summary(step)

    # Generate experience summary when session ends
    if session_ended:
        if _play_log:
            _generate_and_log_experience(state)
        if _jump_memory:
            _log_jump_learning_summary()

    return new_state


def _log_jump_learning_summary() -> None:
    """Log jump learning summary at session end."""
    if _jump_memory is None:
        return

    stats = _jump_memory.get_statistics()
    if stats["total_jumps"] == 0:
        return

    print("\n" + "=" * 60)
    print("跳跃学习统计 (Jump Learning Stats)")
    print("=" * 60)
    print(f"总跳跃次数: {stats['total_jumps']}")
    print(f"成功次数: {stats['successful_jumps']}")
    print(f"失败次数: {stats['failed_jumps']}")
    print(f"成功率: {stats['success_rate']:.1%}")
    print(f"平均成功按压时间: {stats['avg_success_duration']:.2f}s")
    print()

    # Show distance-based analysis if available
    if "distance_analysis" in stats and stats["distance_analysis"]:
        print("距离分析 (Distance Analysis):")
        for bucket, data in stats["distance_analysis"].items():
            if data["total"] > 0:
                print(f"  {bucket}: {data['success_rate']:.0%} ({data['success']}/{data['total']}) avg {data['avg_duration']:.2f}s")
        print()

    print("按压时间分析 (Duration Analysis):")
    for bucket, data in stats["duration_analysis"].items():
        if data["total"] > 0:
            print(f"  {bucket}: {data['success_rate']:.0%} ({data['success']}/{data['total']})")
    print("=" * 60)


def _generate_and_log_experience(state: dict[str, Any]) -> None:
    """Generate and log experience summary after session ends.

    Args:
        state: Final game state.
    """
    if _play_log is None:
        return

    try:
        # Generate and print experience report
        report = _play_log.format_experience_report()
        print("\n" + report)

        # Save experience summary to file
        exp_summary = _play_log.generate_experience_summary()

        # Add game state info
        exp_summary["game_over"] = state.get("game_over", False)
        exp_summary["level_complete"] = state.get("level_complete", False)
        exp_summary["final_step"] = state.get("current_step", 0)

        # Save to file
        if _play_log.output_dir:
            import json
            exp_path = _play_log.output_dir / f"experience_{_play_log.session_id}.json"
            exp_path.write_text(json.dumps(exp_summary, indent=2, ensure_ascii=False))
            _logger.info(f"Experience summary saved to: {exp_path}")

    except Exception as e:
        _logger.error(f"Failed to generate experience summary: {e}")


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
