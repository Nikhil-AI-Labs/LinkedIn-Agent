"""Action/approval endpoint schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SelectDraftRequest(BaseModel):
    """Request to select a draft variant."""
    
    thread_id: str
    selected_draft_id: int | None = None
    user_edited_content: str | None = Field(None, max_length=5000)
    
    @model_validator(mode="after")
    def validate_one_choice(self):
        """Ensure either draft selection or custom content."""
        if self.selected_draft_id is None and not self.user_edited_content:
            raise ValueError("Either selected_draft_id or user_edited_content is required")
        return self


class SelectDraftResponse(BaseModel):
    """Response from draft selection."""
    
    status: Literal["awaiting_final_approval", "error"]
    thread_id: str
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class FinalApproveDraftRequest(BaseModel):
    """Request to final approve/reject draft."""
    
    thread_id: str
    approved: bool


class FinalApproveDraftResponse(BaseModel):
    """Response from final approval."""
    
    status: Literal["posted", "rejected", "error"]
    thread_id: str
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class ApproveEngagementRequest(BaseModel):
    """Request to approve/edit an engagement action."""
    
    thread_id: str
    action_index: int = Field(ge=0)
    edited_comment: str | None = Field(None, max_length=5000)


class ApproveEngagementResponse(BaseModel):
    """Response from engagement approval."""
    
    status: Literal["completed", "error"]
    action_id: int
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class SkipActionRequest(BaseModel):
    """Request to skip an action."""
    
    thread_id: str | None = None
    reason: str | None = Field(None, max_length=500)


class SkipActionResponse(BaseModel):
    """Response from skip action."""
    
    status: Literal["skipped", "error"]
    action_id: int
    trace_id: str


class PendingItem(BaseModel):
    """A pending action item."""
    
    id: int
    type: Literal["draft", "engagement"]
    thread_id: str
    status: str
    created_at: str
    data: dict[str, Any]


class PendingActionsResponse(BaseModel):
    """Response from /pending endpoint."""
    
    status: str = "success"
    trace_id: str
    items: list[PendingItem]
    total_count: int
