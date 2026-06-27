"""LinkedIn Manager - Routes requests based on AUTH_MODE with automatic fallback.

This manager provides a unified interface for LinkedIn operations:
- Routes based on AUTH_MODE (oauth vs browser)
- Implements automatic fallback (Kimi → Playwright for writes)
- Propagates trace_id for observability
- Logs all routing decisions

Routing Logic:
==============

AUTH_MODE=oauth:
- Uses OAuthClient for all operations
- Returns "not implemented" errors (OAuth not available to most projects)

AUTH_MODE=browser:
- READ operations: VoyagerClient (linkedin-api)
- WRITE operations: 
  * Primary: KimiBridgePoster (reuses browser session)
  * Fallback: PlaywrightPoster (if Kimi fails)

Architecture:
=============
┌─────────────────────┐
│  LinkedInManager    │
│  (Router)           │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐    ┌───▼────┐
│ OAuth │    │Browser │
│Client │    │ Mode   │
└───┬───┘    └───┬────┘
    │            │
    │       ┌────┴─────┐
    │       │          │
    │   ┌───▼────┐ ┌──▼────────┐
    │   │Voyager │ │Kimi→      │
    │   │(read)  │ │Playwright │
    │   └────────┘ │(write)    │
    │              └───────────┘
    └─────────────────┘
"""

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.linkedin.base import (
    LinkedInClient,
    LinkedInPoster,
    LinkedInResult,
    ReactionType,
)
from app.services.linkedin.browser_poster import KimiBridgePoster, PlaywrightPoster
from app.services.linkedin.oauth_client import OAuthClient
from app.services.linkedin.voyager_client import VoyagerClient

logger = get_logger(__name__)


class LinkedInManager:
    """LinkedIn manager that routes operations based on AUTH_MODE.
    
    Usage:
        manager = LinkedInManager()
        
        # Read operations
        result = await manager.get_user_posts(user_id="123", limit=10)
        
        # Write operations
        result = await manager.create_post(user_id="123", content="Hello LinkedIn!")
    """

    def __init__(self):
        """Initialize LinkedIn manager with appropriate clients."""
        self.auth_mode = settings.auth_mode
        
        logger.info(
            "Initializing LinkedInManager",
            auth_mode=self.auth_mode,
            browser_provider=settings.browser_provider if self.auth_mode == "browser" else None,
        )

        # Initialize clients based on auth mode
        if self.auth_mode == "oauth":
            # OAuth mode (not implemented - will return errors)
            self._read_client: LinkedInClient = OAuthClient()
            self._write_client: LinkedInPoster = OAuthClient()
            self._write_fallback: Optional[LinkedInPoster] = None
            
            logger.warning(
                "OAuth mode selected but not implemented",
                note="OAuth requires LinkedIn app approval with w_member_social scope",
                recommendation="Use browser mode with Voyager + Playwright",
            )

        elif self.auth_mode == "browser":
            # Browser mode
            self._read_client: LinkedInClient = VoyagerClient()
            
            # Primary: Kimi WebBridge, Fallback: Playwright
            if settings.browser_provider == "kimi_webbridge":
                self._write_client: LinkedInPoster = KimiBridgePoster()
                self._write_fallback: Optional[LinkedInPoster] = PlaywrightPoster()
                logger.info(
                    "Browser mode: Kimi WebBridge (primary) + Playwright (fallback)",
                    note="Kimi reuses browser session - safer and easier",
                )
            else:  # playwright
                self._write_client: LinkedInPoster = PlaywrightPoster()
                self._write_fallback: Optional[LinkedInPoster] = None
                logger.warning(
                    "Browser mode: Playwright only (no fallback)",
                    warning="LinkedIn actively detects Playwright. Consider Kimi WebBridge.",
                )

        else:
            raise ValueError(
                f"Invalid AUTH_MODE: {self.auth_mode}. Must be 'oauth' or 'browser'"
            )

    async def _write_with_fallback(
        self,
        operation: str,
        primary_method: callable,
        fallback_method: Optional[callable],
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> LinkedInResult:
        """Execute write operation with automatic fallback.
        
        Args:
            operation: Operation name for logging
            primary_method: Primary write method to try
            fallback_method: Fallback method if primary fails
            trace_id: Trace ID for observability
            **kwargs: Arguments to pass to methods
            
        Returns:
            LinkedInResult from primary or fallback
        """
        logger.info(
            f"Executing {operation}",
            auth_mode=self.auth_mode,
            has_fallback=fallback_method is not None,
            trace_id=trace_id,
        )

        # Try primary method
        result = await primary_method(**kwargs, trace_id=trace_id)

        # If primary succeeded or no fallback available, return
        if result.success or fallback_method is None:
            if result.success:
                logger.info(
                    f"{operation} succeeded with primary method",
                    trace_id=trace_id,
                )
            else:
                logger.error(
                    f"{operation} failed and no fallback available",
                    error=result.error,
                    trace_id=trace_id,
                )
            return result

        # Try fallback
        logger.warning(
            f"{operation} failed with primary, trying fallback",
            primary_error=result.error,
            trace_id=trace_id,
        )

        fallback_result = await fallback_method(**kwargs, trace_id=trace_id)

        if fallback_result.success:
            logger.info(
                f"{operation} succeeded with fallback method",
                trace_id=trace_id,
            )
        else:
            logger.error(
                f"{operation} failed with both primary and fallback",
                primary_error=result.error,
                fallback_error=fallback_result.error,
                trace_id=trace_id,
            )

        return fallback_result

    # ========================================================================
    # READ Operations (Delegated to read_client)
    # ========================================================================

    async def get_user_posts(
        self,
        user_id: str,
        limit: int = 10,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch user's recent posts.
        
        Args:
            user_id: User's LinkedIn member ID
            limit: Maximum number of posts to fetch
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with list[LinkedInPost] in data field
        """
        logger.info(
            "Fetching user posts",
            user_id=user_id,
            limit=limit,
            client=type(self._read_client).__name__,
            trace_id=trace_id,
        )
        return await self._read_client.get_user_posts(user_id, limit, trace_id)

    async def get_profile_posts(
        self,
        member_id: str,
        limit: int = 5,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch posts from a specific profile.
        
        Args:
            member_id: LinkedIn member ID (urn format)
            limit: Maximum number of posts to fetch
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with list[LinkedInPost] in data field
        """
        logger.info(
            "Fetching profile posts",
            member_id=member_id,
            limit=limit,
            client=type(self._read_client).__name__,
            trace_id=trace_id,
        )
        return await self._read_client.get_profile_posts(member_id, limit, trace_id)

    async def get_post_comments(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch comments on a post.
        
        Args:
            post_id: Post ID (urn format)
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with list[LinkedInComment] in data field
        """
        logger.info(
            "Fetching post comments",
            post_id=post_id,
            client=type(self._read_client).__name__,
            trace_id=trace_id,
        )
        return await self._read_client.get_post_comments(post_id, trace_id)

    async def get_post_reactions(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch reactions on a post.
        
        Args:
            post_id: Post ID (urn format)
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with dict of reaction counts in data field
        """
        logger.info(
            "Fetching post reactions",
            post_id=post_id,
            client=type(self._read_client).__name__,
            trace_id=trace_id,
        )
        return await self._read_client.get_post_reactions(post_id, trace_id)

    async def validate_profile(
        self,
        profile_url: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Validate and fetch profile information.
        
        Args:
            profile_url: LinkedIn profile URL
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with LinkedInProfile in data field
        """
        logger.info(
            "Validating profile",
            profile_url=profile_url,
            client=type(self._read_client).__name__,
            trace_id=trace_id,
        )
        return await self._read_client.validate_profile(profile_url, trace_id)

    # ========================================================================
    # WRITE Operations (Delegated to write_client with fallback)
    # ========================================================================

    async def create_post(
        self,
        content: str,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create a new LinkedIn post.
        
        Args:
            content: Post text content
            user_id: User's LinkedIn member ID (optional, uses session user if not provided)
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with post URL in data field
        """
        return await self._write_with_fallback(
            operation="create_post",
            primary_method=self._write_client.create_post,
            fallback_method=self._write_fallback.create_post if self._write_fallback else None,
            trace_id=trace_id,
            user_id=user_id,
            content=content,
        )

    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on a LinkedIn post.
        
        Args:
            post_id: Post ID (urn format or URL)
            content: Comment text content
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with comment URL in data field
        """
        return await self._write_with_fallback(
            operation="create_comment",
            primary_method=self._write_client.create_comment,
            fallback_method=self._write_fallback.create_comment if self._write_fallback else None,
            trace_id=trace_id,
            post_id=post_id,
            content=content,
        )

    async def add_reaction(
        self,
        post_id: str,
        reaction_type: ReactionType,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """React to a LinkedIn post.
        
        Args:
            post_id: Post ID (urn format)
            reaction_type: Type of reaction (like, celebrate, etc.)
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with success boolean in data field
        """
        return await self._write_with_fallback(
            operation="add_reaction",
            primary_method=self._write_client.add_reaction,
            fallback_method=self._write_fallback.add_reaction if self._write_fallback else None,
            trace_id=trace_id,
            post_id=post_id,
            reaction_type=reaction_type,
        )

    async def validate_session(
        self, trace_id: Optional[str] = None
    ) -> LinkedInResult:
        """Validate LinkedIn session is active.
        
        Args:
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with validation status
        """
        logger.info(
            "Validating session",
            client=type(self._write_client).__name__,
            trace_id=trace_id,
        )
        return await self._write_client.validate_session(trace_id)
