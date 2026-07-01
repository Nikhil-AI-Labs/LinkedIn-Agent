"""Action/approval endpoint request schemas.

This file contains ONLY request models for action/approval endpoints.
Response models are in app.schemas.responses module.
"""

from pydantic import BaseModel, Field, model_validator


class SelectDraftRequest(BaseModel):
    """Request to select a draft variant."""
    
    thread_id: str
    selected_draft_id: str | None = None  # Can be variant number or draft ID
    user_edited_content: str | None = Field(None, max_length=5000)
    
    @model_validator(mode="after")
    def validate_one_choice(self):
        """Ensure either draft selection or custom content."""
        if self.selected_draft_id is None and not self.user_edited_content:
            raise ValueError("Either selected_draft_id or user_edited_content is required")
        return self


class FinalApproveDraftRequest(BaseModel):
    """Request to final approve/reject draft."""
    
    thread_id: str
    approved: bool


class ApproveEngagementRequest(BaseModel):
    """Request to approve/edit an engagement action."""
    
    thread_id: str
    action_index: int = Field(ge=0)
    edited_comment: str | None = Field(None, max_length=5000)


class SkipActionRequest(BaseModel):
    """Request to skip an action."""
    
    thread_id: str | None = None
    reason: str | None = Field(None, max_length=500)
