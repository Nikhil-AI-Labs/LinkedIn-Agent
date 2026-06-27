"""LLM Manager — unified router with retry logic.

This is the ONLY thing agents and services should import for LLM calls.
"""

import asyncio
import uuid
import structlog
from enum import Enum

from .base import BaseLLMClient, LLMMessage, LLMResponse
from .sarvam_client import SarvamClient
from .groq_client import GroqClient

log = structlog.get_logger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0  # doubles each retry: 1s, 2s, 4s


class LLMTask(str, Enum):
    """Task type determines which LLM is used.
    
    PRIMARY tasks → Sarvam-M (reasoning quality)
    FAST tasks → Groq (speed, classification)
    """

    # Primary LLM tasks
    DRAFT_POST = "draft_post"
    EVALUATE_DRAFT = "evaluate_draft"
    GENERATE_COMMENT = "generate_comment"
    GENERAL_QUERY = "general_query"

    # Fast LLM tasks
    CLASSIFY_INTENT = "classify_intent"
    CLASSIFY_ENGAGEMENT = "classify_engagement"
    PARSE_VOICE_INTENT = "parse_voice_intent"


FAST_TASKS = {
    LLMTask.CLASSIFY_INTENT,
    LLMTask.CLASSIFY_ENGAGEMENT,
    LLMTask.PARSE_VOICE_INTENT,
}


class LLMManager:
    """Single entry point for all LLM calls.
    
    Usage:
        manager = LLMManager()
        response = await manager.call(
            task=LLMTask.CLASSIFY_INTENT,
            messages=[LLMMessage(role="user", content="create a post about...")],
        )
    """

    def __init__(self) -> None:
        self._primary = SarvamClient()
        self._fast = GroqClient()

    def _get_client(self, task: LLMTask) -> BaseLLMClient:
        if task in FAST_TASKS:
            return self._fast
        return self._primary

    async def call(
        self,
        task: LLMTask,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        """Call the appropriate LLM for the given task.
        
        Retries up to MAX_RETRIES times with exponential backoff.
        Only retries on transient errors (timeouts, connection errors, 429, 5xx).
        Does not retry on client errors (400, 401, 403, 404).
        Raises RuntimeError if all retries fail.
        """
        trace_id = trace_id or str(uuid.uuid4())
        client = self._get_client(task)
        client_name = client.__class__.__name__

        kwargs: dict = {"trace_id": trace_id}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.info(
                    "llm_call_attempt",
                    task=task.value,
                    client=client_name,
                    attempt=attempt,
                    trace_id=trace_id,
                )

                response = await client.complete(messages, **kwargs)

                log.info(
                    "llm_call_success",
                    task=task.value,
                    client=client_name,
                    attempt=attempt,
                    trace_id=trace_id,
                )

                return response

            except Exception as e:
                last_error = e
                
                # Check if error is retryable
                should_retry = self._is_retryable_error(e)
                
                backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))

                log.warning(
                    "llm_call_failed",
                    task=task.value,
                    client=client_name,
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__,
                    retryable=should_retry,
                    retry_in=backoff if should_retry else None,
                    trace_id=trace_id,
                )

                # Don't retry client errors (400, 401, 403, 404)
                if not should_retry:
                    log.error(
                        "llm_call_non_retryable",
                        task=task.value,
                        client=client_name,
                        error=str(e),
                        trace_id=trace_id,
                    )
                    raise RuntimeError(
                        f"LLM call failed with non-retryable error for task '{task.value}': {e}"
                    )

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)

        log.error(
            "llm_call_exhausted",
            task=task.value,
            client=client_name,
            total_attempts=MAX_RETRIES,
            trace_id=trace_id,
        )

        raise RuntimeError(
            f"LLM call failed after {MAX_RETRIES} attempts for task '{task.value}'. "
            f"Last error: {last_error}"
        )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error should be retried.
        
        Retryable: timeouts, connection errors, 429, 500-599
        Non-retryable: 400, 401, 403, 404 (client errors)
        """
        error_str = str(error).lower()
        
        # Non-retryable HTTP status codes (client errors)
        non_retryable_codes = ["400", "401", "403", "404"]
        for code in non_retryable_codes:
            if code in error_str:
                return False
        
        # Check for specific retryable errors
        retryable_indicators = [
            "timeout",
            "connection",
            "429",  # Rate limit
            "500", "502", "503", "504",  # Server errors
        ]
        
        for indicator in retryable_indicators:
            if indicator in error_str:
                return True
        
        # Default: retry on unknown errors (conservative approach)
        # This catches network errors, DNS failures, etc.
        return True

    async def health_check(self) -> dict[str, bool]:
        """Check both clients. Used in /health endpoint."""
        primary_ok = await self._primary.health_check()
        fast_ok = await self._fast.health_check()
        return {"sarvam_m": primary_ok, "groq": fast_ok}

    async def close(self) -> None:
        await self._primary.close()
        # Groq SDK handles its own cleanup


# Singleton — import this in agents and services
llm_manager = LLMManager()
