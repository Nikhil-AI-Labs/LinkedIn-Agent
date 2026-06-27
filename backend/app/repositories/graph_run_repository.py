"""Graph run repository for tracking LangGraph workflow executions."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.graph_run import GraphRun
from app.core.enums import GraphStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class GraphRunRepository:
    """Repository for GraphRun model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        thread_id: UUID,
        workflow_type: str,
        input_data_json: dict | None = None,
    ) -> GraphRun:
        """Create a new graph run.

        Args:
            user_id: User UUID
            thread_id: LangGraph thread ID (UUID)
            workflow_type: Workflow type (content_creation, monitoring, etc.)
            input_data_json: Optional input data passed to workflow

        Returns:
            Created GraphRun instance
        """
        run = GraphRun(
            user_id=user_id,
            thread_id=thread_id,
            workflow_type=workflow_type,
            input_data_json=input_data_json,
            status=GraphStatus.RUNNING.value,
        )
        self.session.add(run)
        await self.session.flush()
        logger.info(
            "Graph run created",
            run_id=str(run.id),
            thread_id=str(thread_id),
            workflow_type=workflow_type,
            status=run.status,
        )
        return run

    async def get_by_id(self, run_id: UUID) -> GraphRun | None:
        """Get graph run by ID.

        Args:
            run_id: Run UUID

        Returns:
            GraphRun instance or None
        """
        result = await self.session.execute(select(GraphRun).where(GraphRun.id == run_id))
        return result.scalar_one_or_none()

    async def get_by_thread_id(self, thread_id: UUID) -> GraphRun | None:
        """Get graph run by thread ID.

        Args:
            thread_id: LangGraph thread UUID

        Returns:
            GraphRun instance or None
        """
        result = await self.session.execute(
            select(GraphRun).where(GraphRun.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(
        self, user_id: UUID, workflow_type: str | None = None, limit: int = 20
    ) -> list[GraphRun]:
        """Get graph runs for user, optionally filtered by workflow type.

        Args:
            user_id: User UUID
            workflow_type: Optional workflow type filter
            limit: Maximum number of runs to return

        Returns:
            List of GraphRun instances ordered by started_at desc
        """
        query = select(GraphRun).where(GraphRun.user_id == user_id)

        if workflow_type:
            query = query.where(GraphRun.workflow_type == workflow_type)

        query = query.order_by(GraphRun.started_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_running_for_user(self, user_id: UUID) -> list[GraphRun]:
        """Get currently running graph runs for user.

        Args:
            user_id: User UUID

        Returns:
            List of running GraphRun instances
        """
        result = await self.session.execute(
            select(GraphRun)
            .where(
                GraphRun.user_id == user_id,
                GraphRun.status.in_(
                    [GraphStatus.RUNNING.value, GraphStatus.WAITING_HUMAN.value]
                ),
            )
            .order_by(GraphRun.started_at)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        run_id: UUID,
        new_status: str,
        output_data_json: dict | None = None,
        error_message: str | None = None,
    ) -> GraphRun:
        """Update graph run status.

        Args:
            run_id: Run UUID
            new_status: New status value
            output_data_json: Optional output data from workflow
            error_message: Optional error message if failed

        Returns:
            Updated GraphRun instance

        Raises:
            ValueError: If run not found
        """
        run = await self.get_by_id(run_id)
        if not run:
            raise ValueError(f"Graph run not found: {run_id}")

        old_status = run.status
        run.status = new_status

        # Update completed_at for terminal states
        if new_status in [
            GraphStatus.COMPLETED.value,
            GraphStatus.FAILED.value,
            GraphStatus.CANCELLED.value,
        ]:
            run.completed_at = datetime.now(timezone.utc)

        if output_data_json is not None:
            run.output_data_json = output_data_json

        if error_message is not None:
            run.error_message = error_message

        await self.session.flush()

        logger.info(
            "Graph run status updated",
            run_id=str(run_id),
            thread_id=str(run.thread_id),
            old_status=old_status,
            new_status=new_status,
        )

        return run

    async def delete(self, run_id: UUID) -> bool:
        """Delete graph run.

        Args:
            run_id: Run UUID

        Returns:
            True if deleted, False if not found
        """
        run = await self.get_by_id(run_id)
        if run:
            await self.session.delete(run)
            await self.session.flush()
            logger.info("Graph run deleted", run_id=str(run_id))
            return True
        return False
