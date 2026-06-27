"""Shared type definitions for LangGraph agents."""

from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from pydantic import BaseModel, Field


class GraphStatus(str, Enum):
    """Graph execution status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InterruptReason(str, Enum):
    """Reason for graph interruption."""
    
    DRAFT_SELECTION = "draft_selection"
    FINAL_APPROVAL = "final_approval"
    ENGAGEMENT_APPROVAL = "engagement_approval"
    USER_EDIT = "user_edit"


# ============================================================================
# Content Creation Agent State
# ============================================================================

class ContentCreationState(TypedDict, total=False):
    """State for content creation workflow.
    
    total=False allows optional fields while maintaining type safety.
    """
    
    # Identity and tracing
    user_id: int
    thread_id: str
    trace_id: str
    run_id: str | None
    
    # Input
    intent: str  # "create_post"
    user_input: str  # Original user request
    messages: list[dict[str, str]]  # Conversation history
    
    # Content generation
    brief: dict[str, Any] | None  # Structured brief from parse
    drafts: list[dict[str, Any]] | None  # Generated draft variants
    scores: dict[str, float] | None  # Draft scores
    
    # Selection and editing
    selected_draft_id: int | None
    user_edited_content: str | None
    final_content: str | None
    
    # Persistence
    draft_id: int | None  # ID in posts_drafted table
    
    # Approval state
    approval_required: bool
    approved: bool | None
    
    # Result
    post_id: str | None  # LinkedIn post ID
    status: str  # "pending", "posted", "failed"
    error: str | None
    
    # Metadata
    created_at: datetime | None
    updated_at: datetime | None


# ============================================================================
# Monitoring Agent State
# ============================================================================

class MonitoringState(TypedDict, total=False):
    """State for monitoring/engagement workflow."""
    
    # Identity and tracing
    user_id: int
    thread_id: str
    trace_id: str
    run_id: str | None
    
    # Input
    intent: str  # "monitor_engagement"
    watchlist_profile_ids: list[str] | None
    
    # Fetched data
    user_posts: list[dict[str, Any]] | None  # User's own posts
    user_engagement: list[dict[str, Any]] | None  # Comments/reactions on user's posts
    watchlist_posts: list[dict[str, Any]] | None  # Posts from watched profiles
    
    # Classification
    classified_items: list[dict[str, Any]] | None
    
    # Suggestions
    suggested_actions: list[dict[str, Any]] | None
    
    # Selection
    selected_action_id: int | None
    user_edited_comment: str | None
    
    # Persistence
    pending_action_ids: list[int] | None  # IDs in pending_engagements table
    
    # Approval state
    approval_required: bool
    approved: bool | None
    
    # Result
    posted_actions: list[dict[str, Any]] | None
    status: str
    error: str | None
    
    # Metadata
    created_at: datetime | None
    updated_at: datetime | None


# ============================================================================
# Graph Metadata Models (for audit/tracking)
# ============================================================================

class GraphRunMetadata(BaseModel):
    """Metadata for a graph execution run."""
    
    run_id: str
    user_id: int
    thread_id: str
    trace_id: str
    agent_type: str  # "content_creation" | "monitoring"
    status: GraphStatus
    interrupt_reason: InterruptReason | None = None
    node_name: str | None = None  # Current/interrupted node
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class InterruptContext(BaseModel):
    """Context saved when graph is interrupted for approval."""
    
    run_id: str
    user_id: int
    thread_id: str
    interrupt_reason: InterruptReason
    node_name: str
    referenced_entity_id: int | None = None  # draft_id or pending_action_id
    referenced_entity_type: str | None = None  # "draft" | "pending_engagement"
    data: dict[str, Any] = Field(default_factory=dict)  # Arbitrary context data
    created_at: datetime = Field(default_factory=datetime.utcnow)
