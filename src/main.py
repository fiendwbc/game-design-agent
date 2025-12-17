"""CLI entry point for the game analysis system."""

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .config import get_config, reset_config
from .models import LogLevel, PlayStrategy, SessionStatus
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
    window_title: Optional[str] = typer.Option(
        None,
        "--window",
        "-w",
        help="Find region by window title",
    ),
    list_windows: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all visible windows",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Open interactive region selection",
    ),
) -> None:
    """Select game window region for capture.

    Use --list to see available windows, --window to select by title,
    or --interactive for visual selection.
    """
    from .capture.screen import RegionSelector

    selector = RegionSelector()

    if list_windows:
        # List all visible windows
        windows = selector.list_windows()
        if windows:
            table = Table(title="Visible Windows")
            table.add_column("#", style="dim")
            table.add_column("Window Title", style="cyan")
            for i, title in enumerate(windows, 1):
                table.add_row(str(i), title)
            console.print(table)
        else:
            console.print("[yellow]No visible windows found[/yellow]")
        return

    region = None

    if window_title:
        # Select by window title
        console.print(f"Searching for window: [cyan]{window_title}[/cyan]")
        region = selector.select_from_window_title(window_title)
        if region:
            console.print(f"[green]Found window![/green]")
        else:
            console.print(f"[red]Window not found[/red]")
            raise typer.Exit(1)

    elif interactive:
        # Interactive selection
        console.print("[yellow]Interactive selection starting...[/yellow]")
        region = selector.select_interactive()

    else:
        # Show help for manual configuration
        console.print(Panel(
            "[yellow]No selection method specified.[/yellow]\n\n"
            "Options:\n"
            "  --list / -l        List available windows\n"
            "  --window / -w      Select by window title\n"
            "  --interactive / -i Open visual selection\n\n"
            "Or manually specify in config.json:\n"
            '{\n'
            '  "window_region": {"x": 100, "y": 100, "width": 800, "height": 600}\n'
            '}',
            title="Select Region",
        ))
        return

    if region:
        # Display selected region
        table = Table(title="Selected Region")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("X", str(region.x))
        table.add_row("Y", str(region.y))
        table.add_row("Width", str(region.width))
        table.add_row("Height", str(region.height))
        console.print(table)

        # Save to config file
        config_data = {
            "window_region": {
                "x": region.x,
                "y": region.y,
                "width": region.width,
                "height": region.height,
            }
        }

        # Merge with existing config if exists
        if save.exists():
            try:
                existing = json.loads(save.read_text())
                existing.update(config_data)
                config_data = existing
            except Exception:
                pass

        save.write_text(json.dumps(config_data, indent=2))
        console.print(f"[green]Saved to {save}[/green]")


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
    region_width: int = typer.Option(800, "--width", "-W", help="Window region width"),
    region_height: int = typer.Option(600, "--height", "-H", help="Window region height"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Show configuration without running",
    ),
) -> None:
    """Run a game analysis session.

    Starts automated gameplay on the specified window region,
    analyzes the game, and generates design documents.
    """
    from .orchestrator.graph import run_game_session

    # Setup logging
    setup_logging(level=log_level)
    logger = get_logger()

    # Load config from file if provided
    if config_file and config_file.exists():
        try:
            file_config = json.loads(config_file.read_text())
            if "window_region" in file_config:
                wr = file_config["window_region"]
                region_x = wr.get("x", region_x)
                region_y = wr.get("y", region_y)
                region_width = wr.get("width", region_width)
                region_height = wr.get("height", region_height)
            if "max_steps" in file_config:
                max_steps = file_config["max_steps"]
            if "strategy" in file_config:
                strategy = PlayStrategy(file_config["strategy"])
            console.print(f"[green]Loaded config from {config_file}[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")

    # Create window region
    window_region = WindowRegion(
        x=region_x,
        y=region_y,
        width=region_width,
        height=region_height,
    )

    # Create session config
    session_config = SessionConfig(
        window_region=window_region,
        max_steps=max_steps,
        strategy=strategy,
        output_dir=output_dir,
        log_level=log_level,
    )

    # Show configuration
    config_table = Table(title="Session Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_row("Region", f"({region_x}, {region_y}) {region_width}x{region_height}")
    config_table.add_row("Strategy", strategy.value)
    config_table.add_row("Max Steps", str(max_steps))
    config_table.add_row("Output", str(output_dir))
    config_table.add_row("Log Level", log_level.value)
    console.print(config_table)

    if dry_run:
        console.print("\n[yellow]Dry run - not starting session[/yellow]")
        return

    # Create session
    session = PlaySession(config=session_config)
    logger.info(f"Created session: {session.id}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run with progress display
    console.print("\n[bold]Starting game analysis session...[/bold]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]Playing game (max {max_steps} steps)",
            total=max_steps,
        )

        def on_step(step: int, state: dict[str, Any]) -> None:
            """Update progress on each step."""
            action = state.get("pending_action")
            action_desc = action.action_type.value if action else "waiting"
            progress.update(
                task,
                completed=step,
                description=f"[cyan]Step {step}: {action_desc}",
            )

        try:
            final_state = run_game_session(session, on_step=on_step)

            # Show results
            console.print()
            status = final_state.get("status", SessionStatus.COMPLETED)

            if status == SessionStatus.COMPLETED:
                console.print(Panel(
                    f"[green]Session completed successfully![/green]\n\n"
                    f"Steps: {final_state.get('current_step', 0)}\n"
                    f"Output: {output_dir}",
                    title="Session Complete",
                ))
            elif status == SessionStatus.FAILED:
                error = final_state.get("error", "Unknown error")
                console.print(Panel(
                    f"[red]Session failed![/red]\n\n"
                    f"Error: {error}",
                    title="Session Failed",
                ))
            else:
                console.print(Panel(
                    f"[yellow]Session ended[/yellow]\n\n"
                    f"Status: {status.value}\n"
                    f"Steps: {final_state.get('current_step', 0)}",
                    title="Session Ended",
                ))

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted by user[/yellow]")
            raise typer.Exit(130)


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

    Reads the play log and analysis data from a session directory
    and exports in the specified format.
    """
    from .memory.play_log import PlayLog

    if not session_dir.exists():
        console.print(f"[red]Session directory not found: {session_dir}[/red]")
        raise typer.Exit(1)

    # Find play log file
    log_files = list(session_dir.glob("play_log_*.json"))
    if not log_files:
        console.print(f"[red]No play log found in {session_dir}[/red]")
        raise typer.Exit(1)

    # Load play log
    play_log = PlayLog.load(log_files[0])
    summary = play_log.summarize()

    if format == "json":
        result = play_log.to_json()
    elif format == "markdown":
        # Generate markdown report
        lines = [
            f"# Game Analysis Report",
            f"",
            f"**Session ID**: {play_log.session_id}",
            f"**Total Actions**: {summary['total_actions']}",
            f"**Duration**: {summary['duration_seconds']:.1f}s",
            f"",
            f"## Action Summary",
            f"",
        ]

        for action_type, count in summary["by_type"].items():
            lines.append(f"- {action_type}: {count}")

        lines.extend([
            f"",
            f"## Results",
            f"",
        ])

        for result_type, count in summary["by_result"].items():
            lines.append(f"- {result_type}: {count}")

        lines.extend([
            f"",
            f"## Action Log",
            f"",
            f"| Step | Action | Coordinates | Result |",
            f"|------|--------|-------------|--------|",
        ])

        for entry in play_log._entries:
            coords = f"({entry.start_x}, {entry.start_y})" if entry.start_x else "-"
            lines.append(
                f"| {entry.step} | {entry.action_type.value} | {coords} | {entry.result.value} |"
            )

        result = "\n".join(lines)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(result)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(result)


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

    # Check dependencies
    dep_table = Table(title="Dependencies")
    dep_table.add_column("Package", style="cyan")
    dep_table.add_column("Status", style="green")

    deps = [
        ("mss", "mss"),
        ("opencv-python", "cv2"),
        ("pydirectinput", "pydirectinput"),
        ("google-genai", "google.genai"),
        ("langgraph", "langgraph"),
        ("rich", "rich"),
        ("typer", "typer"),
    ]

    for name, module in deps:
        try:
            __import__(module)
            dep_table.add_row(name, "[green]✓ Installed[/green]")
        except ImportError:
            dep_table.add_row(name, "[red]✗ Missing[/red]")

    console.print(dep_table)


@app.command()
def test_capture(
    region_x: int = typer.Option(100, "--x", help="Region X coordinate"),
    region_y: int = typer.Option(100, "--y", help="Region Y coordinate"),
    region_width: int = typer.Option(800, "--width", "-W", help="Region width"),
    region_height: int = typer.Option(600, "--height", "-H", help="Region height"),
    output: Path = typer.Option(
        Path("./test_capture.png"),
        "--output",
        "-o",
        help="Output file path",
    ),
) -> None:
    """Test screen capture with the specified region.

    Captures a single screenshot and saves it to verify
    the capture region is correct.
    """
    from .capture.screen import capture_region

    console.print(f"Capturing region: ({region_x}, {region_y}) {region_width}x{region_height}")

    try:
        screenshot = capture_region(region_x, region_y, region_width, region_height)
        output.write_bytes(screenshot)
        console.print(f"[green]Screenshot saved to {output}[/green]")
        console.print(f"Size: {len(screenshot) / 1024:.1f} KB")
    except Exception as e:
        console.print(f"[red]Capture failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
