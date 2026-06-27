"""Abstract browser controller interface for LinkedIn automation."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class BrowserController(ABC):
    """Abstract base class for browser-based LinkedIn automation.

    Implementations:
    - KimiBridgeController: Uses Kimi WebBridge to control existing browser
    - PlaywrightController: Uses Playwright for automated browser control
    """

    @abstractmethod
    async def connect(self, user_id: UUID) -> dict[str, Any]:
        """Connect to browser session.

        Args:
            user_id: User UUID to load session for

        Returns:
            Connection info dict with status and session data

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from browser session."""
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check if LinkedIn session is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        pass

    @abstractmethod
    async def create_post(self, content: str, trace_id: str) -> dict[str, str]:
        """Create a LinkedIn post.

        Args:
            content: Post text content
            trace_id: Trace ID for logging

        Returns:
            Dict with post_url and post_urn

        Raises:
            ValueError: If post creation fails
        """
        pass

    @abstractmethod
    async def post_comment(
        self, post_url: str, comment_text: str, trace_id: str
    ) -> dict[str, str]:
        """Post a comment on a LinkedIn post.

        Args:
            post_url: LinkedIn post URL
            comment_text: Comment text
            trace_id: Trace ID for logging

        Returns:
            Dict with comment_url and activity_urn

        Raises:
            ValueError: If comment posting fails
        """
        pass

    @abstractmethod
    async def react_to_post(
        self, post_url: str, reaction_type: str, trace_id: str
    ) -> dict[str, str]:
        """React to a LinkedIn post.

        Args:
            post_url: LinkedIn post URL
            reaction_type: Reaction type (like, celebrate, support, insightful)
            trace_id: Trace ID for logging

        Returns:
            Dict with activity_urn

        Raises:
            ValueError: If reaction fails
        """
        pass

    @abstractmethod
    async def get_profile_posts(
        self, profile_url: str, limit: int, trace_id: str
    ) -> list[dict[str, Any]]:
        """Fetch recent posts from a LinkedIn profile.

        Args:
            profile_url: LinkedIn profile URL
            limit: Maximum number of posts to fetch
            trace_id: Trace ID for logging

        Returns:
            List of post dicts with content, url, timestamp

        Raises:
            ValueError: If fetching fails
        """
        pass

    @abstractmethod
    async def get_post_comments(
        self, post_url: str, trace_id: str
    ) -> list[dict[str, Any]]:
        """Fetch comments on a LinkedIn post.

        Args:
            post_url: LinkedIn post URL
            trace_id: Trace ID for logging

        Returns:
            List of comment dicts with text, author, url

        Raises:
            ValueError: If fetching fails
        """
        pass

    @abstractmethod
    async def get_my_posts(self, limit: int, trace_id: str) -> list[dict[str, Any]]:
        """Fetch user's own recent posts.

        Args:
            limit: Maximum number of posts to fetch
            trace_id: Trace ID for logging

        Returns:
            List of post dicts with content, url, timestamp

        Raises:
            ValueError: If fetching fails
        """
        pass

    @abstractmethod
    async def validate_profile_url(self, profile_url: str, trace_id: str) -> bool:
        """Validate that a LinkedIn profile URL exists.

        Args:
            profile_url: LinkedIn profile URL to validate
            trace_id: Trace ID for logging

        Returns:
            True if profile exists, False otherwise
        """
        pass
