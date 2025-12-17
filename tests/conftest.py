"""Pytest configuration and fixtures."""

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.config import reset_config
from src.models import ActionType, ActionResult, LogLevel, PlayStrategy, SessionStatus
from src.models.session import (
    ActionCommand,
    AnalysisLog,
    NormalizedCoordinate,
    PlaySession,
    SessionConfig,
    WindowRegion,
)


# Set test environment
os.environ.setdefault("GOOGLE_API_KEY", "test-api-key-for-testing")
os.environ.setdefault("LOG_LEVEL", "minimal")


@pytest.fixture(autouse=True)
def reset_config_fixture() -> Generator[None, None, None]:
    """Reset config singleton before each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def sample_window_region() -> WindowRegion:
    """Sample window region for testing."""
    return WindowRegion(x=100, y=100, width=800, height=600)


@pytest.fixture
def sample_session_config(sample_window_region: WindowRegion, tmp_path: Path) -> SessionConfig:
    """Sample session configuration for testing."""
    return SessionConfig(
        window_region=sample_window_region,
        max_steps=50,
        strategy=PlayStrategy.EXPLORATION,
        output_dir=tmp_path / "output",
        log_level=LogLevel.MINIMAL,
        video_segment_duration=3.0,
    )


@pytest.fixture
def sample_session(sample_session_config: SessionConfig) -> PlaySession:
    """Sample play session for testing."""
    return PlaySession(config=sample_session_config)


@pytest.fixture
def sample_coordinate() -> NormalizedCoordinate:
    """Sample normalized coordinate."""
    return NormalizedCoordinate(x=500, y=500)


@pytest.fixture
def sample_action(sample_coordinate: NormalizedCoordinate) -> ActionCommand:
    """Sample action command for testing."""
    return ActionCommand(
        step=1,
        action_type=ActionType.CLICK,
        start_coord=sample_coordinate,
        reasoning="Test click action",
    )


@pytest.fixture
def sample_drag_action() -> ActionCommand:
    """Sample drag action for testing."""
    return ActionCommand(
        step=2,
        action_type=ActionType.DRAG,
        start_coord=NormalizedCoordinate(x=100, y=100),
        end_coord=NormalizedCoordinate(x=900, y=900),
        reasoning="Test drag action",
    )


@pytest.fixture
def sample_press_action() -> ActionCommand:
    """Sample key press action for testing."""
    return ActionCommand(
        step=3,
        action_type=ActionType.PRESS,
        key="space",
        reasoning="Test press action",
    )


@pytest.fixture
def sample_wait_action() -> ActionCommand:
    """Sample wait action for testing."""
    return ActionCommand(
        step=4,
        action_type=ActionType.WAIT,
        wait_time=1.0,
        reasoning="Test wait action",
    )


@pytest.fixture
def sample_analysis_log() -> AnalysisLog:
    """Sample analysis log entry for testing."""
    return AnalysisLog(
        step=1,
        observation="Player clicked on start button, game transitioned to level select",
    )


@pytest.fixture
def mock_gemini_response() -> dict:
    """Mock Gemini API response."""
    return {
        "text": '{"action_type": "click", "x": 500, "y": 300, "reasoning": "Click start button", "game_status": "playing", "confidence": 0.9}',
        "usage_metadata": {
            "prompt_token_count": 100,
            "candidates_token_count": 50,
        },
    }


@pytest.fixture
def mock_gemini_client(mock_gemini_response: dict) -> Generator[MagicMock, None, None]:
    """Mock Gemini client for testing without API calls."""
    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup response
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response["text"]
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_client.models.generate_content.return_value = mock_response

        yield mock_client


@pytest.fixture
def sample_screenshot() -> bytes:
    """Sample screenshot bytes (1x1 PNG) for testing."""
    # Minimal valid PNG (1x1 red pixel)
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
        0x8D, 0xB5, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
        0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ])


@pytest.fixture
def sample_video() -> bytes:
    """Sample video bytes placeholder for testing."""
    # Just a placeholder - actual video testing would use real files
    return b"MOCK_VIDEO_DATA"


@pytest.fixture
def mock_screen_capture(sample_screenshot: bytes) -> Generator[MagicMock, None, None]:
    """Mock screen capture for testing without actual screen access."""
    with patch("src.capture.screen.mss.mss") as mock_mss:
        mock_sct = MagicMock()
        mock_mss.return_value = mock_sct

        # Mock screenshot result
        mock_img = MagicMock()
        mock_img.rgb = b"\xff\x00\x00"  # Red pixel
        mock_img.size = (1, 1)
        mock_img.bgra = b"\x00\x00\xff\xff"  # BGRA format
        mock_sct.grab.return_value = mock_img
        mock_sct.monitors = [
            {},  # All monitors
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # Primary
        ]

        yield mock_sct


@pytest.fixture
def mock_input_controller() -> Generator[MagicMock, None, None]:
    """Mock input controller for testing without actual input."""
    with patch("pydirectinput.moveTo") as mock_move, \
         patch("pydirectinput.click") as mock_click, \
         patch("pydirectinput.mouseDown") as mock_down, \
         patch("pydirectinput.mouseUp") as mock_up, \
         patch("pydirectinput.press") as mock_press, \
         patch("pydirectinput.keyDown") as mock_key_down, \
         patch("pydirectinput.keyUp") as mock_key_up, \
         patch("pydirectinput.position") as mock_pos:

        mock_pos.return_value = (500, 500)

        yield {
            "moveTo": mock_move,
            "click": mock_click,
            "mouseDown": mock_down,
            "mouseUp": mock_up,
            "press": mock_press,
            "keyDown": mock_key_down,
            "keyUp": mock_key_up,
            "position": mock_pos,
        }


@pytest.fixture
def sample_game_state(sample_session: PlaySession) -> dict:
    """Sample game state for testing orchestrator nodes."""
    return {
        "session": sample_session,
        "status": SessionStatus.RUNNING,
        "current_step": 0,
        "max_steps": 50,
        "current_screenshot": None,
        "current_video": None,
        "post_action_screenshot": None,
        "reaction_video": None,
        "pending_action": None,
        "action_result": None,
        "game_over": False,
        "level_complete": False,
        "analysis_log": [],
        "mechanics_state": {},
        "ui_flow_graph": {"nodes": [], "edges": []},
        "art_style_state": {"color_palette": [], "style_tags": []},
        "should_continue": True,
        "error": None,
    }


# Markers for different test categories
def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "contract: mark test as contract test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring real API access"
    )
    config.addinivalue_line(
        "markers", "requires_display: mark test as requiring display access"
    )
