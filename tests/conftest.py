"""Pytest configuration and fixtures."""

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.config import reset_config
from src.models import ActionType, LogLevel, PlayStrategy, SessionStatus
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
        "text": '{"action_type": "click", "x": 500, "y": 300, "reasoning": "Click start button"}',
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
