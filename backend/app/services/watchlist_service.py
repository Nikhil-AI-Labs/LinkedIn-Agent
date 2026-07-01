"""Watchlist service orchestration layer."""

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import HttpUrl

from app.repositories.watchlist_repository import WatchlistRepository
from app.core.logging import get_logger
from app.core.errors import ConflictError, NotFoundError, ValidationError

logger = get_logger(__name__)


class WatchlistService:
    """Service for managing watchlist operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.watchlist_repo = WatchlistRepository(db)
    
    def _normalize_profile_id(
        self,
        profile_url: HttpUrl | None,
        member_id: str | None,
    ) -> str:
        """Normalize profile URL or member ID to canonical profile ID.
        
        Args:
            profile_url: LinkedIn profile URL
            member_id: LinkedIn member ID
            
        Returns:
            Normalized profile ID
            
        Raises:
            ValidationError: If neither provided or invalid format
        """
        if profile_url:
            # Extract profile ID from URL
            # https://www.linkedin.com/in/username or https://linkedin.com/in/username
            url_str = str(profile_url)
            match = re.search(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', url_str, re.IGNORECASE)
            if match:
                return match.group(1)
            else:
                raise ValidationError(
                    "Invalid LinkedIn profile URL format",
                    field="profile_url",
                )
        elif member_id:
            # Validate member ID format
            if not re.match(r'^[a-zA-Z0-9_-]+$', member_id):
                raise ValidationError(
                    "Invalid member ID format",
                    field="member_id",
                )
            return member_id
        else:
            raise ValidationError("Either profile_url or member_id is required")
    
    async def add_profile(
        self,
        user_id: int,
        profile_url: HttpUrl | None,
        member_id: str | None,
        note: str | None,
        trace_id: str,
    ) -> dict[str, Any]:
        """Add a profile to user's watchlist.
        
        Args:
            user_id: User ID
            profile_url: LinkedIn profile URL
            member_id: LinkedIn member ID
            note: Optional note about this profile
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status and profile data
            
        Raises:
            ConflictError: If profile already in watchlist
            ValidationError: If invalid input
        """
        # Normalize profile ID
        profile_id = self._normalize_profile_id(profile_url, member_id)
        
        logger.info(
            "adding_profile_to_watchlist",
            user_id=user_id,
            profile_id=profile_id,
            trace_id=trace_id,
        )
        
        # Check if already exists
        existing = await self.watchlist_repo.get_by_profile_id(user_id, profile_id)
        if existing:
            logger.warning(
                "profile_already_in_watchlist",
                user_id=user_id,
                profile_id=profile_id,
                trace_id=trace_id,
            )
            raise ConflictError(
                f"Profile {profile_id} is already in your watchlist",
                resource="watchlist",
            )
        
        # TODO: Validate profile exists via LinkedIn Voyager client
        # For now, we'll create the entry with "active" status
        
        # Create watchlist entry
        entry = await self.watchlist_repo.create(
            user_id=user_id,
            linkedin_profile_id=profile_id,
            note=note,
        )
        
        logger.info(
            "profile_added_to_watchlist",
            user_id=user_id,
            profile_id=profile_id,
            entry_id=entry.id,
            trace_id=trace_id,
        )
        
        return {
            "status": "added",
            "trace_id": trace_id,
            "profile": {
                "id": entry.id,
                "linkedin_profile_id": entry.linkedin_profile_id,
                "profile_url": f"https://linkedin.com/in/{profile_id}",
                "name": None,  # Will be populated after validation
                "headline": None,
                "note": entry.note,
                "status": "active",
                "added_at": entry.added_at.isoformat(),
                "last_checked": None,
            },
        }
    
    async def remove_profile(
        self,
        user_id: int,
        profile_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """Remove a profile from user's watchlist.
        
        Args:
            user_id: User ID
            profile_id: LinkedIn profile ID to remove
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with status
            
        Raises:
            NotFoundError: If profile not in watchlist
        """
        logger.info(
            "removing_profile_from_watchlist",
            user_id=user_id,
            profile_id=profile_id,
            trace_id=trace_id,
        )
        
        # Check if exists
        existing = await self.watchlist_repo.get_by_profile_id(user_id, profile_id)
        if not existing:
            raise NotFoundError("WatchlistEntry", profile_id)
        
        # Delete entry
        await self.watchlist_repo.delete(existing.id)
        
        logger.info(
            "profile_removed_from_watchlist",
            user_id=user_id,
            profile_id=profile_id,
            trace_id=trace_id,
        )
        
        return {
            "status": "removed",
            "trace_id": trace_id,
            "profile_id": profile_id,
        }
    
    async def list_profiles(
        self,
        user_id: int,
        trace_id: str,
    ) -> dict[str, Any]:
        """List all profiles in user's watchlist.
        
        Args:
            user_id: User ID
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with profiles list
        """
        logger.info(
            "listing_watchlist_profiles",
            user_id=user_id,
            trace_id=trace_id,
        )
        
        # Get all watchlist entries
        entries = await self.watchlist_repo.get_for_user(user_id)
        
        profiles = [
            {
                "id": entry.id,
                "linkedin_profile_id": entry.linkedin_profile_id,
                "profile_url": f"https://linkedin.com/in/{entry.linkedin_profile_id}",
                "name": None,  # Will be populated after LinkedIn fetch
                "headline": None,
                "note": entry.note,
                "status": "active",
                "added_at": entry.added_at.isoformat(),
                "last_checked": None,
            }
            for entry in entries
        ]
        
        logger.info(
            "watchlist_profiles_retrieved",
            user_id=user_id,
            total_count=len(profiles),
            trace_id=trace_id,
        )
        
        return {
            "status": "success",
            "trace_id": trace_id,
            "profiles": profiles,
            "total_count": len(profiles),
        }
