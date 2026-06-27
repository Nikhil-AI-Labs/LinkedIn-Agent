"""Action approval and management endpoints."""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.actions import (
    SelectDraftRequest,
    FinalApproveDraftRequest,
    ApproveEngagementRequest,
    SkipActionRequest,
)
from app.schemas.responses import (
    PendingActionsResponse,
    SelectDraftResponse,
    FinalApproveDraftResponse,
    ApproveEngagementResponse,
    SkipActionResponse,
)
from app.services.action_service import ActionService
from app.core.dependencies import get_db_session, get_current_user_id, get_trace_id, get_checkpointer
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["actions"])


@router.get("/pending", response_model=PendingActionsResponse)
async def get_pending_actions(
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> PendingActionsResponse:
    """Get all pending actions for the current user.
    
    Returns both pending drafts and pending engagement actions.
    """
    logger.info("get_pending_actions_request", user_id=user_id, trace_id=trace_id)
    
    action_service = ActionService(db=db, checkpointer=None)  # No checkpointer needed for read
    
    response_data = await action_service.get_pending_items(
        user_id=user_id,
        trace_id=trace_id,
    )
    
    return PendingActionsResponse(**response_data)


@router.post("/drafts/select", response_model=SelectDraftResponse)
async def select_draft(
    request: SelectDraftRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    checkpointer = Depends(get_checkpointer),
) -> SelectDraftResponse:
    """Select a draft variant or provide custom edited content.
    
    This resumes the content creation graph from the draft selection interrupt point.
    """
    logger.info(
        "select_draft_request",
        user_id=user_id,
        thread_id=request.thread_id,
        selected_draft_id=request.selected_draft_id,
        has_custom_content=request.user_edited_content is not None,
        trace_id=trace_id,
    )
    
    action_service = ActionService(db=db, checkpointer=checkpointer)
    
    response_data = await action_service.select_draft(
        thread_id=request.thread_id,
        selected_draft_id=request.selected_draft_id,
        user_edited_content=request.user_edited_content,
        trace_id=trace_id,
    )
    
    return SelectDraftResponse(**response_data)


@router.post("/drafts/approve", response_model=FinalApproveDraftResponse)
async def final_approve_draft(
    request: FinalApproveDraftRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    checkpointer = Depends(get_checkpointer),
) -> FinalApproveDraftResponse:
    """Final approval or rejection of a draft before posting.
    
    This resumes the content creation graph from the final approval interrupt point.
    """
    logger.info(
        "final_approve_draft_request",
        user_id=user_id,
        thread_id=request.thread_id,
        approved=request.approved,
        trace_id=trace_id,
    )
    
    action_service = ActionService(db=db, checkpointer=checkpointer)
    
    response_data = await action_service.final_approve_draft(
        thread_id=request.thread_id,
        approved=request.approved,
        trace_id=trace_id,
    )
    
    return FinalApproveDraftResponse(**response_data)


@router.post("/approve/{action_id}", response_model=ApproveEngagementResponse)
async def approve_engagement(
    action_id: int = Path(..., ge=1),
    request: ApproveEngagementRequest = ...,
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    checkpointer = Depends(get_checkpointer),
) -> ApproveEngagementResponse:
    """Approve and optionally edit an engagement action.
    
    This resumes the monitoring graph from the approval interrupt point.
    """
    logger.info(
        "approve_engagement_request",
        user_id=user_id,
        action_id=action_id,
        thread_id=request.thread_id,
        action_index=request.action_index,
        has_edit=request.edited_comment is not None,
        trace_id=trace_id,
    )
    
    action_service = ActionService(db=db, checkpointer=checkpointer)
    
    response_data = await action_service.approve_engagement(
        action_id=action_id,
        thread_id=request.thread_id,
        action_index=request.action_index,
        edited_comment=request.edited_comment,
        trace_id=trace_id,
    )
    
    return ApproveEngagementResponse(**response_data)


@router.delete("/skip/{action_id}", response_model=SkipActionResponse)
async def skip_action(
    action_id: int = Path(..., ge=1),
    request: SkipActionRequest = ...,
    db: AsyncSession = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    checkpointer = Depends(get_checkpointer),
) -> SkipActionResponse:
    """Skip a pending action.
    
    Optionally resumes the monitoring graph with rejection.
    """
    logger.info(
        "skip_action_request",
        user_id=user_id,
        action_id=action_id,
        thread_id=request.thread_id,
        reason=request.reason,
        trace_id=trace_id,
    )
    
    action_service = ActionService(db=db, checkpointer=checkpointer)
    
    response_data = await action_service.skip_action(
        action_id=action_id,
        thread_id=request.thread_id,
        reason=request.reason,
        trace_id=trace_id,
    )
    
    return SkipActionResponse(**response_data)
