"""Logging utilities with 3-level verbosity support."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from ..models import LogLevel


# Rich console for pretty output
console = Console()

# Logger instance
_logger: Optional[logging.Logger] = None


def setup_logging(level: LogLevel = LogLevel.DETAILED, name: str = "game-analyzer") -> logging.Logger:
    """Setup logging with Rich handler.

    Args:
        level: Logging verbosity level (minimal/detailed/debug)
        name: Logger name

    Returns:
        Configured logger instance
    """
    global _logger

    # Map LogLevel to Python logging level
    level_map = {
        LogLevel.MINIMAL: logging.ERROR,
        LogLevel.DETAILED: logging.INFO,
        LogLevel.DEBUG: logging.DEBUG,
    }

    python_level = level_map.get(level, logging.INFO)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(python_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create Rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=level == LogLevel.DEBUG,
        rich_tracebacks=True,
        tracebacks_show_locals=level == LogLevel.DEBUG,
    )
    rich_handler.setLevel(python_level)

    # Format based on level
    if level == LogLevel.DEBUG:
        fmt = "%(message)s [%(name)s:%(funcName)s:%(lineno)d]"
    else:
        fmt = "%(message)s"

    rich_handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(rich_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def log_step(step: int, message: str, level: str = "info") -> None:
    """Log a step-related message with step prefix.

    Args:
        step: Current step number
        message: Log message
        level: Log level (debug/info/warning/error)
    """
    logger = get_logger()
    formatted = f"[Step {step:03d}] {message}"

    log_func = getattr(logger, level, logger.info)
    log_func(formatted)


def log_agent(agent_name: str, message: str, level: str = "info") -> None:
    """Log an agent-related message.

    Args:
        agent_name: Name of the agent
        message: Log message
        level: Log level (debug/info/warning/error)
    """
    logger = get_logger()
    formatted = f"[{agent_name}] {message}"

    log_func = getattr(logger, level, logger.info)
    log_func(formatted)


def log_api_call(model: str, tokens_in: int, tokens_out: int, latency_ms: float) -> None:
    """Log an API call with metrics (only in detailed/debug mode).

    Args:
        model: Model name
        tokens_in: Input token count
        tokens_out: Output token count
        latency_ms: Latency in milliseconds
    """
    logger = get_logger()
    logger.info(
        f"[API] {model}: {tokens_in} in / {tokens_out} out, {latency_ms:.0f}ms"
    )


def log_file_saved(path: str, file_type: str = "file") -> None:
    """Log a file save operation (only in debug mode).

    Args:
        path: File path
        file_type: Type of file (screenshot/video/document)
    """
    logger = get_logger()
    logger.debug(f"[Save] {file_type}: {path}")


__all__ = [
    "console",
    "setup_logging",
    "get_logger",
    "log_step",
    "log_agent",
    "log_api_call",
    "log_file_saved",
]
