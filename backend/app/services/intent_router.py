"""Intent classification service with fallback heuristics.

Routes user messages to appropriate handlers:
- create_post
- view_pending
- add_watchlist
- remove_watchlist
- list_watchlist
- approve_action
- skip_action
- general_query
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from app.services.llm import llm_manager, LLMTask, LLMMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Models
# ============================================================================

IntentType = Literal[
    "create_post",
    "view_pending",
    "add_watchlist",
    "remove_watchlist",
    "list_watchlist",
    "approve_action",
    "skip_action",
    "general_query",
]

LanguageType = Literal["en", "hi", "hinglish"]


class IntentResult(BaseModel):
    """Result of intent classification."""
    
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, str] = Field(default_factory=dict)
    language: LanguageType = "en"
    requires_agent: bool = False


# ============================================================================
# Heuristic Pre-routing
# ============================================================================

def _detect_language(text: str) -> LanguageType:
    """Detect language from text using simple heuristics."""
    # Devanagari script detection
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    
    # English word detection
    english_words = len(re.findall(r'\b[a-zA-Z]{2,}\b', text))
    
    # Mixed = Hinglish
    if devanagari_count > 0 and english_words > 0:
        return "hinglish"
    elif devanagari_count > english_words:
        return "hi"
    else:
        return "en"


def _extract_linkedin_profile(text: str) -> str | None:
    """Extract LinkedIn profile URL or member ID from text."""
    # LinkedIn URL patterns
    url_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)'
    match = re.search(url_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Member ID pattern (if provided directly)
    member_pattern = r'\bmember[_-]?id[:\s]+([a-zA-Z0-9_-]+)'
    match = re.search(member_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def _heuristic_intent(
    text: str,
    action_id: str | None = None,
    approve: bool | None = None,
) -> IntentResult | None:
    """Try to classify intent using heuristics before calling LLM.
    
    Returns IntentResult if confident, None if LLM is needed.
    """
    text_lower = text.lower()
    
    # Direct action approval/skip
    if action_id is not None:
        if approve is True:
            logger.info("heuristic_approve_action", action_id=action_id)
            return IntentResult(
                intent="approve_action",
                confidence=1.0,
                entities={"action_id": action_id},
            )
        elif approve is False:
            logger.info("heuristic_skip_action", action_id=action_id)
            return IntentResult(
                intent="skip_action",
                confidence=1.0,
                entities={"action_id": action_id},
            )
    
    # Watchlist add/remove detection
    profile = _extract_linkedin_profile(text)
    if profile:
        if any(kw in text_lower for kw in ["add", "follow", "watch", "monitor", "track"]):
            logger.info("heuristic_add_watchlist", profile=profile)
            return IntentResult(
                intent="add_watchlist",
                confidence=0.9,
                entities={"profile": profile},
                language=_detect_language(text),
            )
        elif any(kw in text_lower for kw in ["remove", "unfollow", "unwatch", "stop", "delete"]):
            logger.info("heuristic_remove_watchlist", profile=profile)
            return IntentResult(
                intent="remove_watchlist",
                confidence=0.9,
                entities={"profile": profile},
                language=_detect_language(text),
            )
    
    # View pending detection
    if any(kw in text_lower for kw in [
        "pending",
        "waiting",
        "queue",
        "show pending",
        "list pending",
        "what's pending",
    ]):
        logger.info("heuristic_view_pending")
        return IntentResult(
            intent="view_pending",
            confidence=0.85,
            language=_detect_language(text),
        )
    
    # List watchlist detection
    if any(kw in text_lower for kw in [
        "list watchlist",
        "show watchlist",
        "who am i watching",
        "my watchlist",
        "watchlist",
    ]) and "add" not in text_lower and "remove" not in text_lower:
        logger.info("heuristic_list_watchlist")
        return IntentResult(
            intent="list_watchlist",
            confidence=0.85,
            language=_detect_language(text),
        )
    
    # Post creation detection (high confidence keywords)
    if any(kw in text_lower for kw in [
        "write a post",
        "create a post",
        "draft a post",
        "generate a post",
        "compose a post",
        "post about",
    ]):
        logger.info("heuristic_create_post")
        return IntentResult(
            intent="create_post",
            confidence=0.9,
            entities={"topic": text},
            language=_detect_language(text),
            requires_agent=True,
        )
    
    # No confident heuristic match
    return None


# ============================================================================
# LLM-based Classification
# ============================================================================

async def _llm_classify(text: str, trace_id: str) -> IntentResult:
    """Classify intent using fast LLM."""
    system_prompt = """You are an intent classifier for a LinkedIn AI agent.

Classify the user message into exactly ONE of these intents:
- create_post: User wants to create/draft/write a LinkedIn post
- view_pending: User wants to see pending actions/approvals
- add_watchlist: User wants to add someone to watchlist
- remove_watchlist: User wants to remove someone from watchlist
- list_watchlist: User wants to see their watchlist
- general_query: Any other question or conversation

Respond with JSON:
{
  "intent": "<intent>",
  "confidence": <0.0-1.0>,
  "entities": {"key": "value"},
  "language": "en|hi|hinglish"
}

Rules:
- If message contains post/draft/write keywords → create_post
- If message contains pending/queue/waiting keywords → view_pending
- If message contains watchlist + add/follow → add_watchlist
- If message contains watchlist + remove/unfollow → remove_watchlist
- If message asks about watchlist → list_watchlist
- Otherwise → general_query
"""
    
    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=f"Classify this message:\n{text}"),
    ]
    
    try:
        response = await llm_manager.call(
            task=LLMTask.CLASSIFY_INTENT,
            messages=messages,
            temperature=0.2,
            max_tokens=200,
            trace_id=trace_id,
        )
        
        # Parse JSON response
        result_data = json.loads(response.content)
        
        result = IntentResult(
            intent=result_data["intent"],
            confidence=result_data.get("confidence", 0.7),
            entities=result_data.get("entities", {}),
            language=result_data.get("language", "en"),
            requires_agent=result_data["intent"] == "create_post",
        )
        
        logger.info(
            "llm_intent_classified",
            intent=result.intent,
            confidence=result.confidence,
            trace_id=trace_id,
        )
        
        return result
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(
            "llm_classification_failed_using_fallback",
            error=str(e),
            trace_id=trace_id,
        )
        
        # Fallback to general_query
        return IntentResult(
            intent="general_query",
            confidence=0.5,
            language=_detect_language(text),
        )


# ============================================================================
# Public API
# ============================================================================

async def classify_intent(
    text: str,
    trace_id: str,
    action_id: str | None = None,
    approve: bool | None = None,
) -> IntentResult:
    """Classify user intent with fallback heuristics.
    
    Args:
        text: User message text
        trace_id: Trace ID for logging
        action_id: Optional action ID for approval/skip
        approve: Optional approval flag
        
    Returns:
        IntentResult with classified intent
    """
    logger.info(
        "classifying_intent",
        text_length=len(text),
        has_action_id=action_id is not None,
        trace_id=trace_id,
    )
    
    # Try heuristics first
    heuristic_result = _heuristic_intent(text, action_id, approve)
    if heuristic_result:
        logger.info(
            "intent_classified_by_heuristic",
            intent=heuristic_result.intent,
            confidence=heuristic_result.confidence,
            trace_id=trace_id,
        )
        return heuristic_result
    
    # Fall back to LLM
    logger.info("using_llm_for_classification", trace_id=trace_id)
    return await _llm_classify(text, trace_id)
