"""Pending engagement repository with status transition validation."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pending_engagement import PendingEngagement
from app.core.enums import (
    EngagementStatus,
    ENGAGEMENT_STATUS_TRANSITIONS,
    validate_status_transition,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class PendingEngagementRepository:
    """Repository for PendingEngagement model with status transition validation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        graph_run_id: UUID | None,
        action_type: str,
        target_post_url: str,
        suggested_content: str | None = None,
        context_json: dict | None = None,
    ) -> PendingEngagement:
        """Create a new pending engagement action.

        Args:
            user_id: User UUID
            graph_run_id: Optional graph run UUID
            action_type: Action type (like, comment, etc.)
            target_post_url: LinkedIn post URL to engage with
            suggested_content: Optional suggested comment text
            context_json: Optional context about why this was suggested

        Returns:
            Created PendingEngagement instance
        """
        engagement = PendingEngagement(
            user_id=user_id,
            graph_run_id=graph_run_id,
            action_type=action_type,
            target_post_url=target_post_url,
            suggested_content=suggested_content,
            context_json=context_json,
            status=EngagementStatus.PENDING.value,
        )
        self.session.add(engagement)
        await self.session.flush()
        logger.info(
            "Pending engagement created",
            engagement_id=str(engagement.id),
            user_id=str(user_id),
            action_type=action_type,
            status=engagement.status,
        )
        return engagement

    async def get_by_id(self, engagement_id: UUID) -> PendingEngagement | None:
        """Get engagement by ID.

        Args:
            engagement_id: Engagement UUID

        Returns:
            PendingEngagement instance or None
        """
        result = await self.session.execute(
            select(PendingEngagement).where(PendingEngagement.id == engagement_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[PendingEngagement]:
        """Get pending (not yet acted upon) engagements for user.

        Args:
            user_id: User UUID
            limit: Maximum number of engagements to return

        Returns:
            List of PendingEngagement instances ordered by created_at
        """
        result = await self.session.execute(
            select(PendingEngagement)
            .where(
                PendingEngagement.user_id == user_id,
                PendingEngagement.status == EngagementStatus.PENDING.value,
            )
            .order_by(PendingEngagement.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_graph_run_id(self, graph_run_id: UUID) -> list[PendingEngagement]:
        """Get all engagements for a graph run.

        Args:
            graph_run_id: Graph run UUID

        Returns:
            List of PendingEngagement instances
        """
        result = await self.session.execute(
            select(PendingEngagement)
            .where(PendingEngagement.graph_run_id == graph_run_id)
            .order_by(PendingEngagement.created_at)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        engagement_id: UUID,
        new_status: str,
        final_content: str | None = None,
        linkedin_activity_urn: str | None = None,
    ) -> PendingEngagement:
        """Update engagement status with validation.

        Args:
            engagement_id: Engagement UUID
            new_status: New status value
            final_content: Optional final edited content (for approved status)
            linkedin_activity_urn: Optional LinkedIn activity URN (for posted status)

        Returns:
            Updated PendingEngagement instance

        Raises:
            ValueError: If status transition is invalid or engagement not found
        """
        engagement = await self.get_by_id(engagement_id)
        if not engagement:
            raise ValueError(f"Engagement not found: {engagement_id}")

        # Validate status transition
        if not validate_status_transition(
            engagement.status, new_status, ENGAGEMENT_STATUS_TRANSITIONS
        ):
            raise ValueError(
                f"Invalid status transition: {engagement.status} -> {new_status}. "
                f"Allowed transitions: {ENGAGEMENT_STATUS_TRANSITIONS.get(engagement.status, [])}"
            )

        # Update status
        old_status = engagement.status
        engagement.status = new_status

        # Update associated fields based on status
        if new_status == EngagementStatus.APPROVED.value and final_content is not None:
            engagement.final_content = final_content

        if new_status in [
            EngagementStatus.POSTED.value,
            EngagementStatus.SKIPPED.value,
            EngagementStatus.FAILED.value,
        ]:
            engagement.completed_at = datetime.now(timezone.utc)

        if new_status == EngagementStatus.POSTED.value and linkedin_activity_urn:
            engagement.linkedin_activity_urn = linkedin_activity_urn

        await self.session.flush()

        logger.info(
            "Engagement status updated",
            engagement_id=str(engagement_id),
            old_status=old_status,
            new_status=new_status,
            has_final_content=final_content is not None,
            has_activity_urn=linkedin_activity_urn is not None,
        )

        return engagement

    async def delete(self, engagement_id: UUID) -> bool:
        """Delete engagement.

        Args:
            engagement_id: Engagement UUID

        Returns:
            True if deleted, False if not found
        """
        engagement = await self.get_by_id(engagement_id)
        if engagement:
            await self.session.delete(engagement)
            await self.session.flush()
            logger.info("Engagement deleted", engagement_id=str(engagement_id))
            return True
        return False

    async def count_pending_for_user(self, user_id: UUID) -> int:
        """Count pending engagements for user.

        Args:
            user_id: User UUID

        Returns:
            Count of pending engagements
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(PendingEngagement.id)).where(
                PendingEngagement.user_id == user_id,
                PendingEngagement.status == EngagementStatus.PENDING.value,
            )
        )
        return result.scalar_one()
