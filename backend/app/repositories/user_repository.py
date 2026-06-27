"""User repository for database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(
        self,
        email: str,
        display_name: str,
        preferred_language: str = "en",
        voice_enabled: bool = False,
    ) -> User:
        """Create a new user.

        Args:
            email: User email (unique)
            display_name: User display name
            preferred_language: Preferred language code
            voice_enabled: Whether voice features are enabled

        Returns:
            Created User instance
        """
        user = User(
            email=email,
            display_name=display_name,
            preferred_language=preferred_language,
            voice_enabled=voice_enabled,
        )
        self.session.add(user)
        await self.session.flush()
        logger.info("User created", user_id=str(user.id), email=email)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update_voice_enabled(self, user_id: UUID, voice_enabled: bool) -> User | None:
        """Update voice_enabled setting for user.

        Args:
            user_id: User UUID
            voice_enabled: New voice enabled status

        Returns:
            Updated User instance or None if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            user.voice_enabled = voice_enabled
            await self.session.flush()
            logger.info(
                "User voice settings updated",
                user_id=str(user_id),
                voice_enabled=voice_enabled,
            )
        return user

    async def update_language(self, user_id: UUID, language: str) -> User | None:
        """Update preferred language for user.

        Args:
            user_id: User UUID
            language: New language code

        Returns:
            Updated User instance or None if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            user.preferred_language = language
            await self.session.flush()
            logger.info(
                "User language updated",
                user_id=str(user_id),
                language=language,
            )
        return user

    async def delete(self, user_id: UUID) -> bool:
        """Delete user and all related data (cascade).

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        user = await self.get_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.flush()
            logger.info("User deleted", user_id=str(user_id))
            return True
        return False
