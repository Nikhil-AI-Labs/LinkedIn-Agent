"""Watchlist repository."""

from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.models.watchlist_entry import WatchlistEntry
from app.core.logging import get_logger

logger = get_logger(__name__)


class WatchlistRepository:
    """Repository for WatchlistEntry model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def add(
        self,
        user_id: UUID,
        target_member_id: str,
        target_profile_url: str,
        notes: str | None = None,
    ) -> WatchlistEntry:
        """Add a profile to user's watchlist.

        Args:
            user_id: User UUID
            target_member_id: LinkedIn member ID
            target_profile_url: LinkedIn profile URL
            notes: Optional notes about this profile

        Returns:
            Created WatchlistEntry instance

        Raises:
            ValueError: If entry already exists (unique constraint violation)
        """
        entry = WatchlistEntry(
            user_id=user_id,
            target_member_id=target_member_id,
            target_profile_url=target_profile_url,
            notes=notes,
        )

        try:
            self.session.add(entry)
            await self.session.flush()
            logger.info(
                "Watchlist entry added",
                user_id=str(user_id),
                target_member_id=target_member_id,
            )
            return entry
        except IntegrityError as e:
            await self.session.rollback()
            raise ValueError(
                f"Profile {target_member_id} already in watchlist for user {user_id}"
            ) from e

    async def get_by_id(self, entry_id: UUID) -> WatchlistEntry | None:
        """Get watchlist entry by ID.

        Args:
            entry_id: Entry UUID

        Returns:
            WatchlistEntry instance or None
        """
        result = await self.session.execute(
            select(WatchlistEntry).where(WatchlistEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, user_id: UUID) -> list[WatchlistEntry]:
        """Get all watchlist entries for user.

        Args:
            user_id: User UUID

        Returns:
            List of WatchlistEntry instances ordered by created_at desc
        """
        result = await self.session.execute(
            select(WatchlistEntry)
            .where(WatchlistEntry.user_id == user_id)
            .order_by(WatchlistEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_member_id(
        self, user_id: UUID, target_member_id: str
    ) -> WatchlistEntry | None:
        """Get watchlist entry by user and member ID.

        Args:
            user_id: User UUID
            target_member_id: LinkedIn member ID

        Returns:
            WatchlistEntry instance or None
        """
        result = await self.session.execute(
            select(WatchlistEntry).where(
                and_(
                    WatchlistEntry.user_id == user_id,
                    WatchlistEntry.target_member_id == target_member_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def exists(self, user_id: UUID, target_member_id: str) -> bool:
        """Check if profile is in user's watchlist.

        Args:
            user_id: User UUID
            target_member_id: LinkedIn member ID

        Returns:
            True if exists, False otherwise
        """
        entry = await self.get_by_member_id(user_id, target_member_id)
        return entry is not None

    async def remove_by_member_id(self, user_id: UUID, target_member_id: str) -> bool:
        """Remove profile from watchlist by member ID.

        Args:
            user_id: User UUID
            target_member_id: LinkedIn member ID

        Returns:
            True if removed, False if not found
        """
        entry = await self.get_by_member_id(user_id, target_member_id)
        if entry:
            await self.session.delete(entry)
            await self.session.flush()
            logger.info(
                "Watchlist entry removed",
                user_id=str(user_id),
                target_member_id=target_member_id,
            )
            return True
        return False

    async def update_notes(self, entry_id: UUID, notes: str) -> WatchlistEntry | None:
        """Update notes for watchlist entry.

        Args:
            entry_id: Entry UUID
            notes: New notes text

        Returns:
            Updated WatchlistEntry instance or None if not found
        """
        entry = await self.get_by_id(entry_id)
        if entry:
            entry.notes = notes
            await self.session.flush()
            logger.info("Watchlist entry notes updated", entry_id=str(entry_id))
        return entry

    async def count_for_user(self, user_id: UUID) -> int:
        """Count watchlist entries for user.

        Args:
            user_id: User UUID

        Returns:
            Count of watchlist entries
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(WatchlistEntry.id)).where(
                WatchlistEntry.user_id == user_id
            )
        )
        return result.scalar_one()
