"""Sarvam AI client — primary reasoning LLM."""

import structlog

from app.core.config import settings
from .base import BaseLLMClient, LLMMessage, LLMResponse

log = structlog.get_logger(__name__)

# Import Sarvam SDK - falls back to OpenAI SDK if not available
try:
    from sarvamai import AsyncSarvamAI
    USE_SARVAM_SDK = True
except ImportError:
    from openai import AsyncOpenAI
    USE_SARVAM_SDK = False

SARVAM_BASE_URL = "https://api.sarvam.ai/v1"
TIMEOUT_SECONDS = 60  # Large models need time


class SarvamClient(BaseLLMClient):
    """
    Client for Sarvam AI via native SDK or OpenAI-compatible REST API.
    Used for: post drafting, content evaluation, comment generation.
    """

    def __init__(self) -> None:
        if USE_SARVAM_SDK:
            # Use native Sarvam SDK (preferred)
            self._client = AsyncSarvamAI(
                api_subscription_key=settings.sarvam_api_key,
                timeout=TIMEOUT_SECONDS,
            )
            self._sdk_type = "native"
        else:
            # Fallback to OpenAI SDK
            self._client = AsyncOpenAI(
                api_key=settings.sarvam_api_key,
                base_url=SARVAM_BASE_URL,
                timeout=TIMEOUT_SECONDS,
            )
            self._sdk_type = "openai"
        
        self._model = settings.sarvam_model
        log.info("sarvam_client_initialized", sdk_type=self._sdk_type, model=self._model)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        trace_id: str | None = None,
    ) -> LLMResponse:
        log.info(
            "sarvam_request",
            trace_id=trace_id,
            model=self._model,
            sdk_type=self._sdk_type,
            message_count=len(messages),
        )

        try:
            response = await self._client.chat.completions(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Handle different response structures
            if hasattr(response, 'choices') and len(response.choices) > 0:
                # Native SDK or OpenAI SDK
                choice = response.choices[0]
                if hasattr(choice, 'message'):
                    message = choice.message
                    # sarvam-105b sometimes returns empty content and puts the whole response in reasoning_content
                    if message.content:
                        content = message.content
                    elif hasattr(message, 'reasoning_content') and message.reasoning_content:
                        content = message.reasoning_content
                    else:
                        content = ""
                else:
                    content = str(choice)
            else:
                content = str(response)

            usage = getattr(response, 'usage', None)

            log.info(
                "sarvam_response",
                trace_id=trace_id,
                content_length=len(content),
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
        except Exception as e:
            log.error(
                "sarvam_call_failed",
                trace_id=trace_id,
                sdk_type=self._sdk_type,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Log response body if available for debugging
            if hasattr(e, "response") and e.response is not None:
                try:
                    log.error("sarvam_response_body", body=e.response.text)
                except Exception:
                    pass
            raise

    async def health_check(self) -> bool:
        try:
            await self.complete(
                [LLMMessage(role="user", content="ping")],
                max_tokens=5,
            )
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if hasattr(self._client, 'close'):
            await self._client.close()
