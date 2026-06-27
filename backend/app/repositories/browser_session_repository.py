"""Browser session repository for tracking browser connection state."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.browser_session import BrowserSession
from app.core.enums import BrowserSessionStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrowserSessionRepository:
    """Repository for BrowserSession model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create_or_update(
        self,
        user_id: UUID,
        provider: str,
        session_data_encrypted: str,
        status: str = BrowserSessionStatus.CONNECTED.value,
    ) -> BrowserSession:
        """Create or update browser session for user.

        Args:
            user_id: User UUID
            provider: Browser provider (kimi_webbridge, playwright)
            session_data_encrypted: Encrypted session cookies/storage
            status: Session status

        Returns:
            BrowserSession instance
        """
        # Try to find existing session for this user and provider
        existing = await self.get_by_user_and_provider(user_id, provider)

        if existing:
            # Update existing
            existing.session_data_encrypted = session_data_encrypted
            existing.status = status
            await self.session.flush()
            logger.info(
                "Browser session updated",
                user_id=str(user_id),
                provider=provider,
                status=status,
            )
            return existing
        else:
            # Create new
            browser_session = BrowserSession(
                user_id=user_id,
                provider=provider,
                session_data_encrypted=session_data_encrypted,
                status=status,
            )
            self.session.add(browser_session)
            await self.session.flush()
            logger.info(
                "Browser session created",
                user_id=str(user_id),
                provider=provider,
                status=status,
            )
            return browser_session

    async def get_by_id(self, session_id: UUID) -> BrowserSession | None:
        """Get browser session by ID.

        Args:
            session_id: Session UUID

        Returns:
            BrowserSession instance or None
        """
        result = await self.session.execute(
            select(BrowserSession).where(BrowserSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_provider(
        self, user_id: UUID, provider: str
    ) -> BrowserSession | None:
        """Get browser session by user and provider.

        Args:
            user_id: User UUID
            provider: Browser provider name

        Returns:
            BrowserSession instance or None
        """
        result = await self.session.execute(
            select(BrowserSession).where(
                BrowserSession.user_id == user_id, BrowserSession.provider == provider
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, session_id: UUID, status: str, error_message: str | None = None
    ) -> BrowserSession:
        """Update browser session status.

        Args:
            session_id: Session UUID
            status: New status
            error_message: Optional error message

        Returns:
            Updated BrowserSession instance

        Raises:
            ValueError: If session not found
        """
        browser_session = await self.get_by_id(session_id)
        if not browser_session:
            raise ValueError(f"Browser session not found: {session_id}")

        old_status = browser_session.status
        browser_session.status = status
        if error_message:
            browser_session.last_error = error_message

        await self.session.flush()

        logger.info(
            "Browser session status updated",
            session_id=str(session_id),
            old_status=old_status,
            new_status=status,
        )

        return browser_session

    async def delete(self, session_id: UUID) -> bool:
        """Delete browser session.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        browser_session = await self.get_by_id(session_id)
        if browser_session:
            await self.session.delete(browser_session)
            await self.session.flush()
            logger.info("Browser session deleted", session_id=str(session_id))
            return True
        return False
