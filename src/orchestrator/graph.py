"""LangGraph state schema and graph definition."""

from pathlib import Path
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

from ..models import SessionStatus
from ..models.session import ActionCommand, AnalysisLog, PlaySession, WindowRegion
from ..utils.logging import get_logger


class GameState(TypedDict):
    """LangGraph state for the game analysis system.

    This state is shared across all nodes in the graph and
    accumulates data throughout the play session.
    """

    # Session management
    session: PlaySession
    status: SessionStatus

    # Current step info
    current_step: int
    max_steps: int

    # Visual input (set by Observe node)
    current_screenshot: Optional[bytes]
    current_video: Optional[bytes]
    post_action_screenshot: Optional[bytes]
    reaction_video: Optional[bytes]

    # Action output (set by Think node)
    pending_action: Optional[ActionCommand]
    action_result: Optional[Any]

    # Game state detection
    game_over: bool
    level_complete: bool

    # Round tracking for multi-round play
    current_round: int
    min_rounds: int
    round_scores: list[int]  # Score per round

    # Analysis results (accumulated by analysis agents)
    analysis_log: Annotated[list[AnalysisLog], add_messages]

    # Memory modules (accumulated over session)
    mechanics_state: dict[str, Any]
    ui_flow_graph: dict[str, Any]
    art_style_state: dict[str, Any]

    # Control flags
    should_continue: bool
    error: Optional[str]


def create_initial_state(session: PlaySession, min_rounds: int = 3) -> GameState:
    """Create initial state for a new game session.

    Args:
        session: The PlaySession configuration
        min_rounds: Minimum number of rounds to play before stopping

    Returns:
        Initial GameState
    """
    return GameState(
        session=session,
        status=SessionStatus.PENDING,
        current_step=0,
        max_steps=session.config.max_steps,
        current_screenshot=None,
        current_video=None,
        post_action_screenshot=None,
        reaction_video=None,
        pending_action=None,
        action_result=None,
        game_over=False,
        level_complete=False,
        current_round=1,
        min_rounds=min_rounds,
        round_scores=[],
        analysis_log=[],
        mechanics_state={},
        ui_flow_graph={"nodes": [], "edges": []},
        art_style_state={"color_palette": [], "style_tags": []},
        should_continue=True,
        error=None,
    )


def build_game_graph() -> StateGraph:
    """Build the LangGraph state machine for game analysis.

    The graph follows this flow:
    1. OBSERVE: Capture screen/video
    2. THINK: Player-Agent decides action
    3. ACT: Execute the action
    4. RECORD: Capture reaction
    5. ANALYZE: Run analysis agents in parallel
    6. UPDATE: Update memory modules
    7. CHECK: Continue or end

    Returns:
        Configured StateGraph
    """
    # Import nodes here to avoid circular imports
    from .nodes import (
        observe_node,
        think_node,
        act_node,
        record_node,
        analyze_node,
        update_memory_node,
        check_continue_node,
    )

    # Create graph with state schema
    graph = StateGraph(GameState)

    # Add nodes
    graph.add_node("observe", observe_node)
    graph.add_node("think", think_node)
    graph.add_node("act", act_node)
    graph.add_node("record", record_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("update_memory", update_memory_node)
    graph.add_node("check_continue", check_continue_node)

    # Define edges (linear flow with conditional end)
    graph.add_edge("observe", "think")
    graph.add_edge("think", "act")
    graph.add_edge("act", "record")
    graph.add_edge("record", "analyze")
    graph.add_edge("analyze", "update_memory")
    graph.add_edge("update_memory", "check_continue")

    # Conditional edge: continue loop or end
    graph.add_conditional_edges(
        "check_continue",
        lambda state: "observe" if state["should_continue"] else "__end__",
        {
            "observe": "observe",
            "__end__": "__end__",
        },
    )

    # Set entry point
    graph.set_entry_point("observe")

    return graph


def run_game_session(
    session: PlaySession,
    on_step: Optional[callable] = None,
    min_rounds: int = 3,
) -> GameState:
    """Run a complete game analysis session.

    Args:
        session: PlaySession configuration.
        on_step: Optional callback called after each step with (step, state).
        min_rounds: Minimum number of rounds to play before stopping.

    Returns:
        Final GameState after session completes.
    """
    from .nodes import init_session_resources, cleanup_session_resources

    logger = get_logger()
    logger.info(f"Starting game session: {session.id} (min rounds: {min_rounds})")

    # Initialize session resources
    init_session_resources(
        region=session.config.window_region,
        session_id=session.id,
        output_dir=session.config.output_dir,
    )

    try:
        # Build and compile the graph
        graph = build_game_graph()
        compiled = graph.compile()

        # Create initial state with min_rounds
        state = create_initial_state(session, min_rounds=min_rounds)

        # Calculate recursion limit based on max_steps
        # Each game step has 7 nodes, add buffer for safety
        recursion_limit = (session.config.max_steps + 10) * 7

        # Run the graph with increased recursion limit
        final_state = None
        for step_state in compiled.stream(
            state,
            {"recursion_limit": recursion_limit},
        ):
            # Get the actual state from the step output
            if isinstance(step_state, dict):
                for node_name, node_state in step_state.items():
                    final_state = node_state

                    # Call step callback if provided
                    if on_step and "current_step" in node_state:
                        on_step(node_state["current_step"], node_state)

        logger.info(f"Session completed: {final_state.get('status', 'unknown')}")
        return final_state or state

    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        return create_initial_state(session)

    except Exception as e:
        logger.error(f"Session failed: {e}")
        state = create_initial_state(session)
        state["error"] = str(e)
        state["status"] = SessionStatus.FAILED
        return state

    finally:
        cleanup_session_resources()


def run_single_step(
    state: GameState,
    graph: Optional[StateGraph] = None,
) -> GameState:
    """Run a single step of the game loop.

    Useful for debugging and testing individual steps.

    Args:
        state: Current GameState.
        graph: Optional pre-built graph (created if not provided).

    Returns:
        Updated GameState after one complete loop.
    """
    from .nodes import (
        observe_node,
        think_node,
        act_node,
        record_node,
        analyze_node,
        update_memory_node,
        check_continue_node,
    )

    # Run nodes sequentially
    state = observe_node(state)
    state = think_node(state)
    state = act_node(state)
    state = record_node(state)
    state = analyze_node(state)
    state = update_memory_node(state)
    state = check_continue_node(state)

    return state


class SessionRunner:
    """High-level session runner with progress tracking.

    Provides a convenient interface for running game sessions
    with callbacks and progress reporting.
    """

    def __init__(self, session: PlaySession) -> None:
        """Initialize session runner.

        Args:
            session: PlaySession configuration.
        """
        self.session = session
        self.logger = get_logger()
        self._callbacks: list[callable] = []
        self._state: Optional[GameState] = None

    def add_callback(self, callback: callable) -> None:
        """Add a step callback.

        Args:
            callback: Function called with (step, state) after each step.
        """
        self._callbacks.append(callback)

    def run(self) -> GameState:
        """Run the session.

        Returns:
            Final GameState.
        """
        def combined_callback(step: int, state: GameState) -> None:
            self._state = state
            for callback in self._callbacks:
                callback(step, state)

        return run_game_session(self.session, on_step=combined_callback)

    @property
    def state(self) -> Optional[GameState]:
        """Get current state (updated during run)."""
        return self._state


__all__ = [
    "GameState",
    "create_initial_state",
    "build_game_graph",
    "run_game_session",
    "run_single_step",
    "SessionRunner",
]
