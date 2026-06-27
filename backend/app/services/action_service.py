"""Action/approval service orchestration layer."""

from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.postgres import PostgresSaver

from app.agents.content_creation_agent import (
    resume_content_creation,
    build_content_creation_graph,
)
from app.agents.monitoring_agent import (
    resume_monitoring,
    build_monitoring_graph,
)
from app.repositories.draft_repository import DraftRepository
from app.repositories.pending_engagement_repository import PendingEngagementRepository
from app.core.logging import get_logger
from app.core.errors import NotFoundError, InvalidStateError

logger = get_logger(__name__)


class ActionService:
    """Service for handling action approvals and skips."""
    
    def __init__(
        self,
        db: AsyncSession,
        checkpointer: PostgresSaver,
    ):
        self.db = db
        self.checkpointer = checkpointer
        self.draft_repo = DraftRepository(db)
        self.pending_repo = PendingEngagementRepository(db)
    
    async def get_pending_items(
        self,
        user_id: int,
        trace_id: str,
    ) -> dict:
        """Get all pending items for user.
        
        Args:
            user_id: User ID
            trace_id: Trace ID for logging
            
        Returns:
            Dict with pending items list
        """
        logger.info("fetching_pending_items", user_id=user_id, trace_id=trace_id)
        
        # Get pending drafts
        pending_drafts = await self.draft_repo.get_user_drafts_by_status(
            user_id=user_id,
            status="pending",
        )
        
        # Get pending engagements
        pending_engagements = await self.pending_repo.get_user_pending(user_id)
        
        items = []
        
        # Add drafts
        for draft in pending_drafts:
            items.append({
                "id": draft.id,
                "type": "draft",
                "thread_id": draft.trace_id,  # Using trace_id as proxy for thread_id
                "status": draft.status.value,
                "created_at": draft.created_at.isoformat(),
                "data": {
                    "brief": draft.brief,
                    "variants": draft.variants,
                },
            })
        
        # Add engagements
        for engagement in pending_engagements:
            items.append({
                "id": engagement.id,
                "type": "engagement",
                "thread_id": engagement.trace_id,
                "status": engagement.status.value,
                "created_at": engagement.created_at.isoformat(),
                "data": {
                    "post_id": engagement.post_id,
                    "engagement_type": engagement.engagement_type.value,
                    "suggested_content": engagement.suggested_content,
                    "priority": engagement.priority,
                },
            })
        
        logger.info(
            "pending_items_retrieved",
            user_id=user_id,
            total_count=len(items),
            trace_id=trace_id,
        )
        
        return {
            "status": "success",
            "trace_id": trace_id,
            "items": items,
            "total_count": len(items),
        }
    
    async def select_draft(
        self,
        thread_id: str,
        selected_draft_id: int | None,
        user_edited_content: str | None,
        trace_id: str,
    ) -> dict:
        """Select a draft variant and resume content creation agent.
        
        Args:
            thread_id: Thread ID
            selected_draft_id: Selected draft variant number
            user_edited_content: User's custom edited content
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status and data
        """
        logger.info(
            "selecting_draft",
            thread_id=thread_id,
            selected_draft_id=selected_draft_id,
            has_custom_content=user_edited_content is not None,
            trace_id=trace_id,
        )
        
        try:
            # Resume content creation agent with user selection
            final_state = await resume_content_creation(
                thread_id=thread_id,
                approved=True,  # User is approving draft selection step
                selected_draft_id=selected_draft_id,
                user_edited_content=user_edited_content,
                checkpointer=self.checkpointer,
            )
            
            status = final_state.get("status", "unknown")
            
            return {
                "status": status,
                "thread_id": thread_id,
                "trace_id": trace_id,
                "data": {
                    "final_content": final_state.get("final_content"),
                },
            }
            
        except Exception as e:
            logger.error(
                "draft_selection_failed",
                thread_id=thread_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise InvalidStateError(
                f"Failed to resume draft selection: {str(e)}",
                current_state="awaiting_selection",
            )
    
    async def final_approve_draft(
        self,
        thread_id: str,
        approved: bool,
        trace_id: str,
    ) -> dict:
        """Final approval/rejection of draft before posting.
        
        Args:
            thread_id: Thread ID
            approved: Whether user approved
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status and data
        """
        logger.info(
            "final_approve_draft",
            thread_id=thread_id,
            approved=approved,
            trace_id=trace_id,
        )
        
        if not approved:
            logger.info("draft_rejected_by_user", thread_id=thread_id, trace_id=trace_id)
            return {
                "status": "rejected",
                "thread_id": thread_id,
                "trace_id": trace_id,
                "data": {"message": "Draft rejected"},
            }
        
        try:
            # Resume content creation agent with final approval
            final_state = await resume_content_creation(
                thread_id=thread_id,
                approved=True,
                checkpointer=self.checkpointer,
            )
            
            status = final_state.get("status", "unknown")
            post_id = final_state.get("post_id")
            
            return {
                "status": "posted" if post_id else "error",
                "thread_id": thread_id,
                "trace_id": trace_id,
                "data": {
                    "post_id": post_id,
                    "final_content": final_state.get("final_content"),
                },
            }
            
        except Exception as e:
            logger.error(
                "final_approval_failed",
                thread_id=thread_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise InvalidStateError(
                f"Failed to finalize approval: {str(e)}",
                current_state="awaiting_final_approval",
            )
    
    async def approve_engagement(
        self,
        action_id: int,
        thread_id: str,
        action_index: int,
        edited_comment: str | None,
        trace_id: str,
    ) -> dict:
        """Approve and optionally edit an engagement action.
        
        Args:
            action_id: Pending engagement ID
            thread_id: Thread ID
            action_index: Index of action in suggested actions list
            edited_comment: User's edited comment (optional)
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status and data
        """
        logger.info(
            "approving_engagement",
            action_id=action_id,
            thread_id=thread_id,
            action_index=action_index,
            has_edit=edited_comment is not None,
            trace_id=trace_id,
        )
        
        # Verify action exists
        engagement = await self.pending_repo.get_by_id(action_id)
        if not engagement:
            raise NotFoundError("PendingEngagement", action_id)
        
        try:
            # Resume monitoring agent with approval
            final_state = await resume_monitoring(
                thread_id=thread_id,
                approved=True,
                selected_action_id=action_index,
                user_edited_comment=edited_comment,
                checkpointer=self.checkpointer,
            )
            
            status = final_state.get("status", "unknown")
            
            return {
                "status": "completed" if status == "engagement_posted" else "error",
                "action_id": action_id,
                "trace_id": trace_id,
                "data": {
                    "engagement_result": final_state.get("posted_actions", []),
                },
            }
            
        except Exception as e:
            logger.error(
                "engagement_approval_failed",
                action_id=action_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise InvalidStateError(
                f"Failed to approve engagement: {str(e)}",
                current_state="awaiting_approval",
            )
    
    async def skip_action(
        self,
        action_id: int,
        thread_id: str | None,
        reason: str | None,
        trace_id: str,
    ) -> dict:
        """Skip a pending action.
        
        Args:
            action_id: Pending engagement ID
            thread_id: Thread ID (optional, for graph resume)
            reason: Reason for skipping (optional)
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status
        """
        logger.info(
            "skipping_action",
            action_id=action_id,
            thread_id=thread_id,
            reason=reason,
            trace_id=trace_id,
        )
        
        # Verify action exists
        engagement = await self.pending_repo.get_by_id(action_id)
        if not engagement:
            raise NotFoundError("PendingEngagement", action_id)
        
        # If thread_id provided, resume graph with rejection
        if thread_id:
            try:
                await resume_monitoring(
                    thread_id=thread_id,
                    approved=False,
                    checkpointer=self.checkpointer,
                )
            except Exception as e:
                logger.warning(
                    "graph_resume_failed_marking_skipped_directly",
                    error=str(e),
                    trace_id=trace_id,
                )
        
        # Mark as skipped in DB
        from app.core.enums import EngagementStatus
        await self.pending_repo.update_status(action_id, EngagementStatus.SKIPPED)
        
        logger.info("action_skipped", action_id=action_id, trace_id=trace_id)
        
        return {
            "status": "skipped",
            "action_id": action_id,
            "trace_id": trace_id,
        }
