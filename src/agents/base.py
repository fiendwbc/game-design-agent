"""Base agent class with Gemini integration."""

import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from google import genai
from google.genai import types
from langsmith import traceable
from pydantic import BaseModel

from ..config import get_config
from ..utils.logging import get_logger, log_agent, log_api_call
from ..utils.retry import retry_api_call
from ..utils.tracing import is_tracing_enabled


class AgentResponse(BaseModel):
    """Standard agent response structure."""

    content: str
    raw_response: Optional[dict[str, Any]] = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""


class BaseAgent(ABC):
    """Abstract base class for all AI agents."""

    def __init__(
        self,
        name: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """Initialize the agent.

        Args:
            name: Agent name for logging
            model: Gemini model to use (default from config)
            system_prompt: System prompt for the agent
        """
        self.name = name
        self.logger = get_logger()

        # Get config (don't validate API key during initialization)
        config = get_config(validate_api_key=False)
        self.model = model or config.analyst_model
        self.system_prompt = system_prompt

        # Initialize Gemini client lazily
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """Get Gemini client (lazy initialization)."""
        if self._client is None:
            config = get_config(validate_api_key=True)
            self._client = genai.Client(api_key=config.google_api_key)
        return self._client

    @retry_api_call(max_attempts=3)
    def generate(
        self,
        prompt: str,
        images: Optional[list[bytes]] = None,
        video: Optional[bytes] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Generate a response from the model.

        Args:
            prompt: Text prompt
            images: Optional list of image bytes
            video: Optional video bytes
            json_schema: Optional JSON schema for structured output

        Returns:
            AgentResponse with content and metadata
        """
        # Use the internal method with tracing if enabled
        if is_tracing_enabled():
            return self._generate_traced(prompt, images, video, json_schema)
        else:
            return self._generate_internal(prompt, images, video, json_schema)

    @traceable(name="gemini_generate", run_type="llm")
    def _generate_traced(
        self,
        prompt: str,
        images: Optional[list[bytes]] = None,
        video: Optional[bytes] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Traced version of generate for LangSmith."""
        return self._generate_internal(prompt, images, video, json_schema)

    def _generate_internal(
        self,
        prompt: str,
        images: Optional[list[bytes]] = None,
        video: Optional[bytes] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Internal generate implementation.

        Args:
            prompt: Text prompt
            images: Optional list of image bytes
            video: Optional video bytes
            json_schema: Optional JSON schema for structured output

        Returns:
            AgentResponse with content and metadata
        """
        log_agent(self.name, f"Generating with model {self.model}")

        # Build content parts
        contents: list[Any] = []

        # Add images if provided
        if images:
            for img_bytes in images:
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                )

        # Add video if provided
        if video:
            contents.append(
                types.Part.from_bytes(data=video, mime_type="video/mp4")
            )

        # Add text prompt
        contents.append(prompt)

        # Build config
        gen_config = types.GenerateContentConfig()

        # Add system instruction if set
        if self.system_prompt:
            gen_config.system_instruction = self.system_prompt

        # Add JSON schema for structured output
        if json_schema:
            gen_config.response_mime_type = "application/json"
            gen_config.response_schema = json_schema

        # Generate response
        start_time = time.time()

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=gen_config,
        )

        latency_ms = (time.time() - start_time) * 1000

        # Extract token usage
        tokens_in = 0
        tokens_out = 0
        if response.usage_metadata:
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = response.usage_metadata.candidates_token_count or 0

        log_api_call(self.model, tokens_in, tokens_out, latency_ms)

        return AgentResponse(
            content=response.text or "",
            raw_response=response.to_json_dict() if hasattr(response, "to_json_dict") else None,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
        )

    @abstractmethod
    def process(self, *args: Any, **kwargs: Any) -> Any:
        """Process input and return agent-specific output.

        This method should be implemented by each specific agent.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r})"


class PlayerAgentBase(BaseAgent):
    """Base class for Player-Agent with faster model."""

    def __init__(self, name: str = "Player-Agent", system_prompt: Optional[str] = None):
        config = get_config(validate_api_key=False)
        super().__init__(
            name=name,
            model=config.player_model,  # Use faster model
            system_prompt=system_prompt,
        )


class AnalystAgentBase(BaseAgent):
    """Base class for analysis agents with deeper reasoning model."""

    def __init__(self, name: str, system_prompt: Optional[str] = None):
        config = get_config(validate_api_key=False)
        super().__init__(
            name=name,
            model=config.analyst_model,  # Use deeper reasoning model
            system_prompt=system_prompt,
        )


__all__ = [
    "AgentResponse",
    "BaseAgent",
    "PlayerAgentBase",
    "AnalystAgentBase",
]
