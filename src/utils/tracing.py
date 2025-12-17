"""LangSmith tracing utilities for observability.

Provides decorators and context managers for tracing
LLM calls and game session operations.
"""

import functools
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Generator, Optional, TypeVar

from langsmith import Client, traceable
from langsmith.run_trees import RunTree

from ..config import get_config


# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Global client instance
_client: Optional[Client] = None


def get_langsmith_client() -> Optional[Client]:
    """Get or create LangSmith client.

    Returns:
        LangSmith Client if tracing is enabled, None otherwise.
    """
    global _client

    config = get_config(validate_api_key=False)

    if not config.langsmith_tracing:
        return None

    if not config.langsmith_api_key:
        return None

    if _client is None:
        _client = Client(
            api_key=config.langsmith_api_key,
            api_url=config.langsmith_endpoint,
        )

    return _client


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled.

    Returns:
        True if tracing is enabled and configured.
    """
    config = get_config(validate_api_key=False)
    return config.langsmith_tracing and bool(config.langsmith_api_key)


@contextmanager
def trace_session(
    session_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[Optional[RunTree], None, None]:
    """Context manager for tracing an entire game session.

    Args:
        session_id: Unique session identifier.
        metadata: Optional metadata to attach to the trace.

    Yields:
        RunTree for the session, or None if tracing is disabled.

    Example:
        with trace_session("session-123") as run:
            # Game session code here
            pass
    """
    if not is_tracing_enabled():
        yield None
        return

    config = get_config(validate_api_key=False)

    extra = {
        "session_id": session_id,
        "start_time": datetime.now().isoformat(),
        **(metadata or {}),
    }

    try:
        # Note: RunTree context manager handles trace submission
        with RunTree(
            name="game_session",
            run_type="chain",
            project_name=config.langsmith_project,
            extra=extra,
        ) as rt:
            yield rt
    except Exception as e:
        # Don't let tracing errors break the application
        print(f"LangSmith tracing error: {e}")
        yield None


@contextmanager
def trace_step(
    step: int,
    action_type: str,
    parent_run: Optional[RunTree] = None,
) -> Generator[Optional[RunTree], None, None]:
    """Context manager for tracing a single game step.

    Args:
        step: Step number.
        action_type: Type of action being performed.
        parent_run: Optional parent RunTree for nesting.

    Yields:
        RunTree for the step, or None if tracing is disabled.
    """
    if not is_tracing_enabled():
        yield None
        return

    config = get_config(validate_api_key=False)

    try:
        with RunTree(
            name=f"step_{step}",
            run_type="chain",
            project_name=config.langsmith_project,
            parent_run=parent_run,
            extra={
                "step": step,
                "action_type": action_type,
            },
        ) as rt:
            yield rt
    except Exception as e:
        print(f"LangSmith step tracing error: {e}")
        yield None


def trace_llm_call(
    name: str = "llm_call",
    run_type: str = "llm",
    metadata: Optional[dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator for tracing LLM calls.

    Args:
        name: Name for the trace.
        run_type: Type of run (llm, chain, tool, etc.).
        metadata: Optional metadata to attach.

    Returns:
        Decorated function.

    Example:
        @trace_llm_call(name="player_decision")
        def make_decision(screenshot: bytes) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use langsmith's traceable
            traced_func = traceable(
                name=name,
                run_type=run_type,
                metadata=metadata,
            )(func)
            return traced_func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def trace_agent(
    agent_name: str,
    model: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator for tracing agent operations.

    Args:
        agent_name: Name of the agent.
        model: Optional model name.

    Returns:
        Decorated function.

    Example:
        @trace_agent("Player-Agent", model="gemini-2.0-flash")
        def process(self, screenshot: bytes) -> ActionCommand:
            ...
    """
    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            traced_func = traceable(
                name=f"{agent_name}.{func.__name__}",
                run_type="chain",
                metadata={
                    "agent": agent_name,
                    "model": model,
                },
            )(func)
            return traced_func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def trace_node(node_name: str) -> Callable[[F], F]:
    """Decorator for tracing orchestrator nodes.

    Args:
        node_name: Name of the node.

    Returns:
        Decorated function.

    Example:
        @trace_node("observe")
        def observe_node(state: dict) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            traced_func = traceable(
                name=node_name,
                run_type="chain",
                metadata={"node": node_name},
            )(func)
            return traced_func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def log_to_langsmith(
    run_name: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    run_type: str = "chain",
    error: Optional[str] = None,
) -> None:
    """Manually log a run to LangSmith.

    Args:
        run_name: Name for the run.
        inputs: Input data.
        outputs: Output data.
        run_type: Type of run.
        error: Optional error message.
    """
    client = get_langsmith_client()
    if client is None:
        return

    config = get_config(validate_api_key=False)

    try:
        client.create_run(
            name=run_name,
            run_type=run_type,
            inputs=inputs,
            outputs=outputs,
            error=error,
            project_name=config.langsmith_project,
        )
    except Exception as e:
        print(f"Failed to log to LangSmith: {e}")


__all__ = [
    "get_langsmith_client",
    "is_tracing_enabled",
    "trace_session",
    "trace_step",
    "trace_llm_call",
    "trace_agent",
    "trace_node",
    "log_to_langsmith",
]
