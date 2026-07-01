"""Draft repository with status transition validation."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.post_draft import PostDraft
from app.core.enums import DraftStatus, DRAFT_STATUS_TRANSITIONS, validate_status_transition
from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftRepository:
    """Repository for PostDraft model with status transition validation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        graph_run_id: str | None,
        idea_input: str,
        draft_text: str,
        variant_index: int = 0,
        score: int | None = None,
        score_breakdown_json: dict | None = None,
    ) -> PostDraft:
        """Create a new draft.

        Args:
            user_id: User UUID
            graph_run_id: Optional LangGraph thread_id string
            idea_input: Original user idea
            draft_text: Generated draft text
            variant_index: Draft variant number (0, 1, 2)
            score: Optional evaluation score 0-100
            score_breakdown_json: Optional detailed score breakdown

        Returns:
            Created PostDraft instance
        """
        draft = PostDraft(
            user_id=user_id,
            graph_run_id=graph_run_id,
            idea_input=idea_input,
            draft_text=draft_text,
            variant_index=variant_index,
            score=score,
            score_breakdown_json=score_breakdown_json,
            status=DraftStatus.DRAFTED.value,
        )
        self.session.add(draft)
        await self.session.flush()
        logger.info(
            "Draft created",
            draft_id=str(draft.id),
            user_id=str(user_id),
            variant_index=variant_index,
            status=draft.status,
        )
        return draft

    async def get_by_id(self, draft_id: UUID) -> PostDraft | None:
        """Get draft by ID.

        Args:
            draft_id: Draft UUID

        Returns:
            PostDraft instance or None
        """
        result = await self.session.execute(
            select(PostDraft).where(PostDraft.id == draft_id)
        )
        return result.scalar_one_or_none()

    async def get_by_graph_run_id(self, graph_run_id: str) -> list[PostDraft]:
        """Get all drafts for a graph run (typically 2-3 variants).

        Args:
            graph_run_id: LangGraph thread_id string

        Returns:
            List of PostDraft instances
        """
        result = await self.session.execute(
            select(PostDraft)
            .where(PostDraft.graph_run_id == graph_run_id)
            .order_by(PostDraft.score.desc().nulls_last(), PostDraft.variant_index)
        )
        return list(result.scalars().all())

    async def get_pending_for_user(self, user_id: UUID, limit: int = 10) -> list[PostDraft]:
        """Get pending (drafted/approved) drafts for user.

        Args:
            user_id: User UUID
            limit: Maximum number of drafts to return

        Returns:
            List of PostDraft instances
        """
        result = await self.session.execute(
            select(PostDraft)
            .where(
                PostDraft.user_id == user_id,
                PostDraft.status.in_([DraftStatus.DRAFTED.value, DraftStatus.APPROVED.value]),
            )
            .order_by(PostDraft.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_user_drafts_by_status(
        self, user_id: UUID, status: str, limit: int = 50
    ) -> list[PostDraft]:
        """Get user's drafts filtered by status.
        
        This is an alias method for backwards compatibility.
        
        Args:
            user_id: User UUID
            status: Status to filter by (ignored if "pending", uses DRAFTED/APPROVED)
            limit: Maximum number of drafts to return
            
        Returns:
            List of PostDraft instances
        """
        # "pending" maps to DRAFTED and APPROVED statuses
        if status == "pending":
            return await self.get_pending_for_user(user_id, limit=limit)
        
        # Otherwise filter by exact status
        result = await self.session.execute(
            select(PostDraft)
            .where(
                PostDraft.user_id == user_id,
                PostDraft.status == status,
            )
            .order_by(PostDraft.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        draft_id: UUID,
        new_status: str,
        final_text: str | None = None,
        linkedin_post_url: str | None = None,
        linkedin_post_urn: str | None = None,
    ) -> PostDraft:
        """Update draft status with validation.

        Args:
            draft_id: Draft UUID
            new_status: New status value
            final_text: Optional final edited text (for approved status)
            linkedin_post_url: Optional LinkedIn post URL (for posted status)
            linkedin_post_urn: Optional LinkedIn post URN (for posted status)

        Returns:
            Updated PostDraft instance

        Raises:
            ValueError: If status transition is invalid or draft not found
        """
        draft = await self.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")

        # Validate status transition
        if not validate_status_transition(
            draft.status, new_status, DRAFT_STATUS_TRANSITIONS
        ):
            raise ValueError(
                f"Invalid status transition: {draft.status} -> {new_status}. "
                f"Allowed transitions: {DRAFT_STATUS_TRANSITIONS.get(draft.status, [])}"
            )

        # Update status
        old_status = draft.status
        draft.status = new_status

        # Update associated fields based on status
        if new_status == DraftStatus.APPROVED.value and final_text is not None:
            draft.final_text = final_text

        if new_status == DraftStatus.POSTED.value:
            draft.posted_at = datetime.now(timezone.utc)
            if linkedin_post_url:
                draft.linkedin_post_url = linkedin_post_url
            if linkedin_post_urn:
                draft.linkedin_post_urn = linkedin_post_urn

        await self.session.flush()

        logger.info(
            "Draft status updated",
            draft_id=str(draft_id),
            old_status=old_status,
            new_status=new_status,
            has_final_text=final_text is not None,
            has_post_url=linkedin_post_url is not None,
        )

        return draft

    async def update_score(
        self, draft_id: UUID, score: int, score_breakdown_json: dict | None = None
    ) -> PostDraft:
        """Update draft evaluation score.

        Args:
            draft_id: Draft UUID
            score: New score 0-100
            score_breakdown_json: Optional detailed breakdown

        Returns:
            Updated PostDraft instance

        Raises:
            ValueError: If draft not found or score invalid
        """
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")

        draft = await self.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")

        draft.score = score
        if score_breakdown_json is not None:
            draft.score_breakdown_json = score_breakdown_json

        await self.session.flush()

        logger.info(
            "Draft score updated",
            draft_id=str(draft_id),
            score=score,
        )

        return draft

    async def delete(self, draft_id: UUID) -> bool:
        """Delete draft.

        Args:
            draft_id: Draft UUID

        Returns:
            True if deleted, False if not found
        """
        draft = await self.get_by_id(draft_id)
        if draft:
            await self.session.delete(draft)
            await self.session.flush()
            logger.info("Draft deleted", draft_id=str(draft_id))
            return True
        return False
