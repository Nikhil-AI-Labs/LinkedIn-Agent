"""Abstract base for all LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    trace_id: str | None = None


@dataclass
class LLMMessage:
    """Message in LLM conversation."""

    role: str  # "system", "user", "assistant"
    content: str


class BaseLLMClient(ABC):
    """All LLM clients implement this interface."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        trace_id: str | None = None,
    ) -> LLMResponse:
        """Run a chat completion."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the client can reach the API."""
        ...
