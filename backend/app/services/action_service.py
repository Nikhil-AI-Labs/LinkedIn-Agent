"""Action/approval service orchestration layer."""

from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

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
        checkpointer: AsyncPostgresSaver,
    ):
        self.db = db
        self.checkpointer = checkpointer
        self.draft_repo = DraftRepository(db)
        self.pending_repo = PendingEngagementRepository(db)
    
    async def get_pending_items(
        self,
        user_id: str,
        trace_id: str,
    ) -> dict:
        """Get all pending items for user.
        
        Args:
            user_id: User ID (UUID string)
            trace_id: Trace ID for logging
            
        Returns:
            Dict with pending items list
        """
        from uuid import UUID
        
        user_uuid = UUID(user_id)
        logger.info("fetching_pending_items", user_id=user_id, trace_id=trace_id)
        
        # Get pending drafts
        pending_drafts = await self.draft_repo.get_user_drafts_by_status(
            user_id=user_uuid,
            status="pending",
        )
        
        # Get pending engagements
        pending_engagements = await self.pending_repo.get_pending_for_user(user_uuid)
        
        items = []
        
        # Add drafts
        for draft in pending_drafts:
            items.append({
                "id": str(draft.id),
                "type": "draft",
                "thread_id": str(draft.graph_run_id) if draft.graph_run_id else None,
                "status": draft.status,
                "created_at": draft.created_at.isoformat(),
                "data": {
                    "idea_input": draft.idea_input,
                    "draft_text": draft.draft_text,
                    "variant_index": draft.variant_index,
                    "score": draft.score,
                },
            })
        
        # Add engagements
        for engagement in pending_engagements:
            items.append({
                "id": str(engagement.id),
                "type": "engagement",
                "thread_id": str(engagement.graph_run_id) if engagement.graph_run_id else None,
                "status": engagement.status,
                "created_at": engagement.created_at.isoformat(),
                "data": {
                    "source_post_url": engagement.source_post_url,
                    "action_type": engagement.action_type,
                    "suggested_text": engagement.suggested_text,
                    "source_type": engagement.source_type,
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
        selected_draft_id: str | None,  # Now accepts string
        user_edited_content: str | None,
        trace_id: str,
    ) -> dict:
        """Select a draft variant and resume content creation agent.
        
        Args:
            thread_id: Thread ID
            selected_draft_id: Selected draft variant number or ID (as string)
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
            # Parse draft ID - extract variant number from frontend ID like "draft-1782659708840"
            variant_number = None
            if selected_draft_id:
                # Try to extract variant number from the string
                # Frontend sends IDs like "draft-{timestamp}" where timestamp encodes variant
                if selected_draft_id.startswith("draft-"):
                    # Extract timestamp and convert to variant (1, 2, or 3)
                    try:
                        timestamp_str = selected_draft_id.split("-")[1]
                        # Use last digit to determine variant (1-3)
                        variant_number = (int(timestamp_str) % 3) + 1
                    except (IndexError, ValueError):
                        variant_number = 1  # Default to first variant
                else:
                    # Direct variant number
                    try:
                        variant_number = int(selected_draft_id)
                    except ValueError:
                        variant_number = 1  # Default to first variant
            
            # Resume content creation agent with user selection
            final_state = await resume_content_creation(
                thread_id=thread_id,
                approved=True,  # User is approving draft selection step
                selected_draft_id=variant_number,
                user_edited_content=user_edited_content,
                db=self.db,
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
                db=self.db,
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
