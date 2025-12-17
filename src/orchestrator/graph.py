"""LangGraph state schema and graph definition."""

from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

from ..models import SessionStatus
from ..models.session import ActionCommand, AnalysisLog, PlaySession


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

    # Action output (set by Think node)
    pending_action: Optional[ActionCommand]

    # Analysis results (accumulated by analysis agents)
    analysis_log: Annotated[list[AnalysisLog], add_messages]

    # Memory modules (accumulated over session)
    mechanics_state: dict[str, Any]
    ui_flow_graph: dict[str, Any]
    art_style_state: dict[str, Any]

    # Control flags
    should_continue: bool
    error: Optional[str]


def create_initial_state(session: PlaySession) -> GameState:
    """Create initial state for a new game session.

    Args:
        session: The PlaySession configuration

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
        pending_action=None,
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


__all__ = [
    "GameState",
    "create_initial_state",
    "build_game_graph",
]
