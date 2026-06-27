"""Groq client — fast classification LLM."""

import structlog
from groq import AsyncGroq

from app.core.config import settings
from .base import BaseLLMClient, LLMMessage, LLMResponse

log = structlog.get_logger(__name__)

TIMEOUT_SECONDS = 15  # Groq is fast; fail fast if it's slow


class GroqClient(BaseLLMClient):
    """
    Client for Groq (default: llama-3.3-70b-versatile).
    Used for: intent classification, quick parsing, comment classification.
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=TIMEOUT_SECONDS,
        )
        self._model = settings.groq_model

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.3,  # Lower default — classification needs determinism
        max_tokens: int = 512,  # Classification responses are short
        trace_id: str | None = None,
    ) -> LLMResponse:
        log.info(
            "groq_request",
            trace_id=trace_id,
            model=self._model,
            message_count=len(messages),
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""
        usage = response.usage

        log.info(
            "groq_response",
            trace_id=trace_id,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

        return LLMResponse(
            content=content,
            model=self._model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            trace_id=trace_id,
        )

    async def health_check(self) -> bool:
        try:
            await self.complete(
                [LLMMessage(role="user", content="ping")],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
