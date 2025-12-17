"""CLI entry point for the game analysis system."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_config, reset_config
from .models import LogLevel, PlayStrategy
from .models.session import PlaySession, SessionConfig, WindowRegion
from .utils.logging import setup_logging, get_logger

# Create Typer app
app = typer.Typer(
    name="game-analyzer",
    help="Multi-Agent Game Analysis System - Automatically play and analyze games",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from . import __version__
        console.print(f"game-analyzer version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Multi-Agent Game Analysis System.

    Automatically play Windows mini-games and generate professional
    game design documents including GDD, numerical analysis, and art reports.
    """
    pass


@app.command()
def select_region(
    save: Path = typer.Option(
        Path("config.json"),
        "--save",
        "-s",
        help="Save configuration to file",
    ),
) -> None:
    """Select game window region interactively.

    Opens an interactive tool to select the game window region
    for screen capture.

    Will be fully implemented in T032 (US1).
    """
    console.print(Panel(
        "[yellow]Interactive region selection not yet implemented.[/yellow]\n\n"
        "For now, manually specify the region in config.json:\n"
        '{\n'
        '  "window_region": {"x": 100, "y": 100, "width": 800, "height": 600}\n'
        '}',
        title="Select Region",
    ))


@app.command()
def run(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    max_steps: int = typer.Option(
        100,
        "--max-steps",
        "-n",
        help="Maximum steps per session (1-1000)",
        min=1,
        max=1000,
    ),
    strategy: PlayStrategy = typer.Option(
        PlayStrategy.EXPLORATION,
        "--strategy",
        "-S",
        help="Play strategy: exploration or completion",
    ),
    output_dir: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory for generated documents",
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.DETAILED,
        "--log-level",
        "-l",
        help="Logging level: minimal, detailed, or debug",
    ),
    region_x: int = typer.Option(100, "--x", help="Window region X coordinate"),
    region_y: int = typer.Option(100, "--y", help="Window region Y coordinate"),
    region_width: int = typer.Option(800, "--width", "-w", help="Window region width"),
    region_height: int = typer.Option(600, "--height", "-h", help="Window region height"),
) -> None:
    """Run a game analysis session.

    Starts automated gameplay on the specified window region,
    analyzes the game, and generates design documents.

    Will be fully implemented in T033-T034 (US1).
    """
    # Setup logging
    setup_logging(level=log_level)
    logger = get_logger()

    # Show configuration
    console.print(Panel(
        f"[bold]Game Analysis Session[/bold]\n\n"
        f"Region: ({region_x}, {region_y}) - {region_width}x{region_height}\n"
        f"Strategy: {strategy.value}\n"
        f"Max Steps: {max_steps}\n"
        f"Output: {output_dir}\n"
        f"Log Level: {log_level.value}",
        title="Configuration",
    ))

    # Create session config
    window_region = WindowRegion(
        x=region_x,
        y=region_y,
        width=region_width,
        height=region_height,
    )

    session_config = SessionConfig(
        window_region=window_region,
        max_steps=max_steps,
        strategy=strategy,
        output_dir=output_dir,
        log_level=log_level,
    )

    # Create session
    session = PlaySession(config=session_config)
    logger.info(f"Created session: {session.id}")

    # Placeholder for actual game loop
    console.print(Panel(
        "[yellow]Game loop not yet implemented.[/yellow]\n\n"
        "The following features will be added in Phase 3 (US1):\n"
        "- Screen capture with mss\n"
        "- Video synthesis with OpenCV\n"
        "- Player-Agent with Gemini\n"
        "- Input control with pydirectinput\n"
        "- LangGraph orchestration",
        title="Run Session",
    ))


@app.command()
def export(
    session_dir: Path = typer.Argument(
        ...,
        help="Session directory containing analysis results",
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Export format: markdown, json, or html",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (default: stdout)",
    ),
) -> None:
    """Export analysis results from a completed session.

    Will be fully implemented in T068 (Phase 9).
    """
    console.print(Panel(
        f"[yellow]Export not yet implemented.[/yellow]\n\n"
        f"Session: {session_dir}\n"
        f"Format: {format}\n"
        f"Output: {output or 'stdout'}",
        title="Export",
    ))


@app.command()
def status() -> None:
    """Show system status and configuration."""
    # Reset config to get fresh values
    reset_config()

    # Try to load config without validation
    config = get_config(validate_api_key=False)

    # Build status table
    table = Table(title="System Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # API Key status
    api_key_status = "[green]Set[/green]" if config.google_api_key else "[red]Not Set[/red]"
    table.add_row("Google API Key", api_key_status)

    table.add_row("Log Level", config.log_level.value)
    table.add_row("Output Directory", str(config.output_dir))
    table.add_row("Default Max Steps", str(config.max_steps))
    table.add_row("Default Strategy", config.play_strategy.value)
    table.add_row("Player Model", config.player_model)
    table.add_row("Analyst Model", config.analyst_model)

    console.print(table)


if __name__ == "__main__":
    app()
