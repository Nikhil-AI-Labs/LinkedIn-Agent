"""Voyager client for LinkedIn READ operations using unofficial linkedin-api.

This client uses the linkedin-api library (Voyager API) for read-only operations.
Voyager is LinkedIn's internal API used by their mobile and web apps.

Features:
- Read user posts and profile posts
- Read comments and reactions
- Validate profiles
- Runs in executor (sync library wrapped for async)
- Retry logic with exponential backoff

Limitations:
- Unofficial API (may break if LinkedIn changes internal API)
- Requires LinkedIn username and encrypted password
- Read-only (no posting capabilities)
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from linkedin_api import Linkedin
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.core.crypto import decrypt_text
from app.core.logging import get_logger
from app.services.linkedin.base import (
    LinkedInClient,
    LinkedInComment,
    LinkedInPost,
    LinkedInProfile,
    LinkedInResult,
)

logger = get_logger(__name__)

# Thread pool for running sync linkedin-api in async context
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="voyager_")


class VoyagerClient(LinkedInClient):
    """Voyager client for LinkedIn READ operations."""

    def __init__(self):
        """Initialize Voyager client."""
        self._client: Optional[Linkedin] = None
        self._authenticated = False

    def _get_client(self) -> Linkedin:
        """Get or create authenticated Voyager client (sync operation)."""
        if self._client is None:
            if not settings.linkedin_username:
                raise ValueError("LINKEDIN_USERNAME is required for Voyager client")
            if not settings.linkedin_password_encrypted:
                raise ValueError(
                    "LINKEDIN_PASSWORD_ENCRYPTED is required for Voyager client"
                )

            # Decrypt password
            password = decrypt_text(settings.linkedin_password_encrypted)

            # Authenticate with linkedin-api
            logger.info(
                "Authenticating with Voyager API",
                username=settings.linkedin_username,
            )
            self._client = Linkedin(settings.linkedin_username, password)
            self._authenticated = True
            logger.info("Voyager authentication successful")

        return self._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _get_user_posts_sync(
        self, user_id: str, limit: int
    ) -> list[dict]:
        """Fetch user posts (sync, runs in executor)."""
        client = self._get_client()
        # linkedin-api uses profile URN, not member ID
        # Extract numeric ID from urn:li:member:123456789
        numeric_id = user_id.split(":")[-1] if ":" in user_id else user_id
        posts = client.get_profile_posts(numeric_id, post_count=limit)
        return posts

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _get_profile_posts_sync(
        self, member_id: str, limit: int
    ) -> list[dict]:
        """Fetch profile posts (sync, runs in executor)."""
        client = self._get_client()
        numeric_id = member_id.split(":")[-1] if ":" in member_id else member_id
        posts = client.get_profile_posts(numeric_id, post_count=limit)
        return posts

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _get_post_comments_sync(self, post_id: str) -> list[dict]:
        """Fetch post comments (sync, runs in executor)."""
        client = self._get_client()
        # Extract activity ID from URN
        activity_id = post_id.split(":")[-1] if ":" in post_id else post_id
        comments = client.get_post_comments(activity_id, comment_count=100)
        return comments

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _get_post_reactions_sync(self, post_id: str) -> dict:
        """Fetch post reactions (sync, runs in executor)."""
        client = self._get_client()
        activity_id = post_id.split(":")[-1] if ":" in post_id else post_id
        reactions = client.get_post_reactions(activity_id)
        return reactions

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def _validate_profile_sync(self, profile_url: str) -> dict:
        """Validate profile (sync, runs in executor)."""
        client = self._get_client()
        # Extract public ID from URL
        # Example: https://www.linkedin.com/in/johndoe/ -> johndoe
        public_id = profile_url.rstrip("/").split("/")[-1]
        profile = client.get_profile(public_id)
        return profile

    def _parse_post(self, raw_post: dict) -> LinkedInPost:
        """Parse raw Voyager post data into LinkedInPost model."""
        # Voyager API returns complex nested structure
        # This is a simplified parser - adjust based on actual response
        post_id = raw_post.get("urn", "")
        
        # Extract author info
        actor = raw_post.get("actor", {})
        author_name = actor.get("name", {}).get("text", "Unknown")
        author_urn = actor.get("urn", "")
        
        # Extract content
        commentary = raw_post.get("commentary", {})
        content = commentary.get("text", {}).get("text", "")
        
        # Extract URL
        share_url = raw_post.get("permalink", "")
        
        # Extract timestamp
        created_time = raw_post.get("actor", {}).get("subDescription", {}).get("text", "")
        created_at = datetime.utcnow()  # Default to now, parse if available
        
        # Extract engagement metrics
        social_counts = raw_post.get("socialDetail", {}).get("totalSocialActivityCounts", {})
        likes_count = social_counts.get("numLikes", 0)
        comments_count = social_counts.get("numComments", 0)
        shares_count = social_counts.get("numShares", 0)
        
        # Extract hashtags
        hashtags = []
        if "hashtags" in commentary:
            hashtags = [tag.get("text", "") for tag in commentary.get("hashtags", [])]
        
        return LinkedInPost(
            post_id=post_id,
            author_name=author_name,
            author_member_id=author_urn,
            author_profile_url=None,  # Not always available in Voyager
            content=content,
            url=share_url,
            created_at=created_at,
            likes_count=likes_count,
            comments_count=comments_count,
            shares_count=shares_count,
            hashtags=hashtags,
        )

    def _parse_comment(self, raw_comment: dict, post_id: str) -> LinkedInComment:
        """Parse raw Voyager comment data into LinkedInComment model."""
        comment_id = raw_comment.get("urn", "")
        
        # Extract author
        actor = raw_comment.get("commenter", {})
        author_name = actor.get("name", "Unknown")
        author_urn = actor.get("urn", "")
        
        # Extract content
        message = raw_comment.get("message", {})
        text = message.get("text", "")
        
        # Extract timestamp
        created_at = datetime.utcnow()  # Default
        if "createdTime" in raw_comment:
            # Convert from milliseconds timestamp
            created_at = datetime.fromtimestamp(raw_comment["createdTime"] / 1000)
        
        # Extract likes
        likes_count = raw_comment.get("likeCount", 0)
        
        # Build comment URL
        url = f"https://www.linkedin.com/feed/update/{post_id}?commentUrn={comment_id}"
        
        return LinkedInComment(
            comment_id=comment_id,
            post_id=post_id,
            author_name=author_name,
            author_member_id=author_urn,
            text=text,
            created_at=created_at,
            likes_count=likes_count,
            url=url,
        )

    def _parse_profile(self, raw_profile: dict, profile_url: str) -> LinkedInProfile:
        """Parse raw Voyager profile data into LinkedInProfile model."""
        # Extract URN
        member_urn = raw_profile.get("entityUrn", "")
        
        # Extract name
        first_name = raw_profile.get("firstName", "")
        last_name = raw_profile.get("lastName", "")
        full_name = f"{first_name} {last_name}".strip()
        
        # Extract headline and location
        headline = raw_profile.get("headline", "")
        location_name = raw_profile.get("locationName", "")
        
        # Extract connections
        connections_count = raw_profile.get("connectionsCount", 0)
        follower_count = raw_profile.get("followersCount", 0)
        
        # Extract profile picture
        profile_picture_url = None
        if "profilePicture" in raw_profile:
            pic_data = raw_profile["profilePicture"]
            if "displayImage" in pic_data:
                profile_picture_url = pic_data["displayImage"]
        
        # Extract about
        about = raw_profile.get("summary", "")
        
        return LinkedInProfile(
            member_id=member_urn,
            profile_url=profile_url,
            full_name=full_name,
            headline=headline,
            location=location_name,
            connections_count=connections_count,
            follower_count=follower_count,
            profile_picture_url=profile_picture_url,
            about=about,
        )

    async def get_user_posts(
        self,
        user_id: str,
        limit: int = 10,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch user's recent posts."""
        logger.info(
            "Fetching user posts via Voyager",
            user_id=user_id,
            limit=limit,
            trace_id=trace_id,
        )

        try:
            # Run sync operation in executor
            loop = asyncio.get_event_loop()
            raw_posts = await loop.run_in_executor(
                _executor, self._get_user_posts_sync, user_id, limit
            )

            # Parse posts
            posts = [self._parse_post(raw_post) for raw_post in raw_posts]

            logger.info(
                "Successfully fetched user posts",
                user_id=user_id,
                count=len(posts),
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=posts, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to fetch user posts",
                user_id=user_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to fetch user posts: {str(e)}",
                error_code="VOYAGER_USER_POSTS_FAILED",
                trace_id=trace_id,
            )

    async def get_profile_posts(
        self,
        member_id: str,
        limit: int = 5,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch posts from a specific profile."""
        logger.info(
            "Fetching profile posts via Voyager",
            member_id=member_id,
            limit=limit,
            trace_id=trace_id,
        )

        try:
            loop = asyncio.get_event_loop()
            raw_posts = await loop.run_in_executor(
                _executor, self._get_profile_posts_sync, member_id, limit
            )

            posts = [self._parse_post(raw_post) for raw_post in raw_posts]

            logger.info(
                "Successfully fetched profile posts",
                member_id=member_id,
                count=len(posts),
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=posts, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to fetch profile posts",
                member_id=member_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to fetch profile posts: {str(e)}",
                error_code="VOYAGER_PROFILE_POSTS_FAILED",
                trace_id=trace_id,
            )

    async def get_post_comments(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch comments on a post."""
        logger.info(
            "Fetching post comments via Voyager",
            post_id=post_id,
            trace_id=trace_id,
        )

        try:
            loop = asyncio.get_event_loop()
            raw_comments = await loop.run_in_executor(
                _executor, self._get_post_comments_sync, post_id
            )

            comments = [
                self._parse_comment(raw_comment, post_id)
                for raw_comment in raw_comments
            ]

            logger.info(
                "Successfully fetched post comments",
                post_id=post_id,
                count=len(comments),
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=comments, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to fetch post comments",
                post_id=post_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to fetch post comments: {str(e)}",
                error_code="VOYAGER_COMMENTS_FAILED",
                trace_id=trace_id,
            )

    async def get_post_reactions(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch reactions on a post."""
        logger.info(
            "Fetching post reactions via Voyager",
            post_id=post_id,
            trace_id=trace_id,
        )

        try:
            loop = asyncio.get_event_loop()
            reactions = await loop.run_in_executor(
                _executor, self._get_post_reactions_sync, post_id
            )

            logger.info(
                "Successfully fetched post reactions",
                post_id=post_id,
                total=sum(reactions.values()) if isinstance(reactions, dict) else 0,
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=reactions, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to fetch post reactions",
                post_id=post_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to fetch post reactions: {str(e)}",
                error_code="VOYAGER_REACTIONS_FAILED",
                trace_id=trace_id,
            )

    async def validate_profile(
        self,
        profile_url: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Validate and fetch profile information."""
        logger.info(
            "Validating profile via Voyager",
            profile_url=profile_url,
            trace_id=trace_id,
        )

        try:
            loop = asyncio.get_event_loop()
            raw_profile = await loop.run_in_executor(
                _executor, self._validate_profile_sync, profile_url
            )

            profile = self._parse_profile(raw_profile, profile_url)

            logger.info(
                "Successfully validated profile",
                profile_url=profile_url,
                member_id=profile.member_id,
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=profile, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to validate profile",
                profile_url=profile_url,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to validate profile: {str(e)}",
                error_code="VOYAGER_PROFILE_VALIDATION_FAILED",
                trace_id=trace_id,
            )
