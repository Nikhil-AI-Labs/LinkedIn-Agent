"""Canonical API response models.

ALL endpoints MUST return these models. No ad-hoc dicts allowed.
This is the single source of truth for API responses.

Reference: backend/docs/API_CONTRACT.md
"""

from typing import Any
from pydantic import BaseModel, Field


# ============================================================================
# Base Response
# ============================================================================

class BaseResponse(BaseModel):
    """Base response model for all endpoints."""
    
    status: str
    trace_id: str


# ============================================================================
# Chat Endpoints
# ============================================================================

class ChatResponse(BaseResponse):
    """Response from POST /api/v1/chat endpoint.
    
    Contract: API_CONTRACT.md § 1
    """
    
    intent: str
    thread_id: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class VoiceTranscribeResponse(BaseModel):
    """Response from POST /api/v1/voice/transcribe endpoint.
    
    Contract: API_CONTRACT.md § 2
    """
    
    text: str
    language: str
    confidence: float | None = None


class VoiceSpeakResponse(BaseModel):
    """Response from POST /api/v1/voice/speak endpoint.
    
    Contract: API_CONTRACT.md § 3
    """
    
    audio_data: str | None = None
    audio_available: bool
    mime_type: str | None = None
    fallback_text: str | None = None
    error: str | None = None


# ============================================================================
# Action/Approval Endpoints
# ============================================================================

class PendingItem(BaseModel):
    """Single pending item in list."""
    
    id: str  # UUID as string
    type: str  # "draft" | "engagement"
    thread_id: str | None  # Can be None if not yet assigned
    status: str
    created_at: str  # ISO 8601
    data: dict[str, Any]


class PendingActionsResponse(BaseResponse):
    """Response from GET /api/v1/pending endpoint.
    
    Contract: API_CONTRACT.md § 4
    """
    
    items: list[PendingItem]
    total_count: int


class SelectDraftResponse(BaseResponse):
    """Response from POST /api/v1/drafts/select endpoint.
    
    Contract: API_CONTRACT.md § 5
    """
    
    thread_id: str
    data: dict[str, Any]


class FinalApproveDraftResponse(BaseResponse):
    """Response from POST /api/v1/drafts/approve endpoint.
    
    Contract: API_CONTRACT.md § 6
    """
    
    thread_id: str
    data: dict[str, Any]


class ApproveEngagementResponse(BaseResponse):
    """Response from POST /api/v1/approve/{action_id} endpoint.
    
    Contract: API_CONTRACT.md § 7
    """
    
    action_id: int
    data: dict[str, Any]


class SkipActionResponse(BaseResponse):
    """Response from DELETE /api/v1/skip/{action_id} endpoint.
    
    Contract: API_CONTRACT.md § 8
    """
    
    action_id: int


# ============================================================================
# Watchlist Endpoints
# ============================================================================

class WatchlistProfile(BaseModel):
    """Watchlist profile data structure."""
    
    id: int
    linkedin_profile_id: str
    profile_url: str
    name: str | None = None
    headline: str | None = None
    note: str | None = None
    status: str = "active"
    added_at: str  # ISO 8601
    last_checked: str | None = None


class AddWatchlistResponse(BaseResponse):
    """Response from POST /api/v1/monitor/add endpoint.
    
    Contract: API_CONTRACT.md § 9
    """
    
    profile: WatchlistProfile


class RemoveWatchlistResponse(BaseResponse):
    """Response from DELETE /api/v1/monitor/remove/{profile_id} endpoint.
    
    Contract: API_CONTRACT.md § 10
    """
    
    profile_id: str


class ListWatchlistResponse(BaseResponse):
    """Response from GET /api/v1/monitor/list endpoint.
    
    Contract: API_CONTRACT.md § 11
    """
    
    profiles: list[WatchlistProfile]
    total_count: int


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response for all endpoints.
    
    Contract: API_CONTRACT.md § Common Structures
    """
    
    status: str = "error"
    error_code: str
    message: str
    details: dict[str, Any] | None = None
    trace_id: str
