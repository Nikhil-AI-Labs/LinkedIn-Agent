"""Base models and abstract interfaces for LinkedIn integration.

This module defines:
- Pydantic data models for LinkedIn entities (posts, comments, profiles)
- Result wrapper for operations
- Abstract interfaces for clients and posters
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Enums
# ============================================================================


class ReactionType(str, Enum):
    """LinkedIn reaction types."""

    LIKE = "like"
    CELEBRATE = "celebrate"
    SUPPORT = "support"
    LOVE = "love"
    INSIGHTFUL = "insightful"
    FUNNY = "funny"


# ============================================================================
# Data Models
# ============================================================================


class LinkedInProfile(BaseModel):
    """LinkedIn profile information."""

    member_id: str = Field(..., description="LinkedIn member ID (urn format)")
    profile_url: str = Field(..., description="Public profile URL")
    full_name: str = Field(..., description="Member's full name")
    headline: Optional[str] = Field(None, description="Professional headline")
    location: Optional[str] = Field(None, description="Location")
    connections_count: Optional[int] = Field(None, description="Number of connections")
    follower_count: Optional[int] = Field(None, description="Number of followers")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    about: Optional[str] = Field(None, description="About section")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "member_id": "urn:li:member:123456789",
                "profile_url": "https://www.linkedin.com/in/johndoe/",
                "full_name": "John Doe",
                "headline": "Software Engineer at Tech Corp",
                "location": "San Francisco, CA",
                "connections_count": 500,
                "follower_count": 1200,
            }
        }


class LinkedInComment(BaseModel):
    """LinkedIn comment information."""

    comment_id: str = Field(..., description="Comment ID (urn format)")
    post_id: str = Field(..., description="Parent post ID")
    author_name: str = Field(..., description="Comment author's name")
    author_member_id: str = Field(..., description="Author's member ID")
    author_profile_url: Optional[str] = Field(None, description="Author's profile URL")
    text: str = Field(..., description="Comment text content")
    created_at: datetime = Field(..., description="Comment creation timestamp")
    likes_count: int = Field(0, description="Number of likes on comment")
    url: str = Field(..., description="Direct URL to comment")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "comment_id": "urn:li:comment:9876543210",
                "post_id": "urn:li:activity:1234567890",
                "author_name": "Jane Smith",
                "author_member_id": "urn:li:member:987654321",
                "text": "Great insights! Thanks for sharing.",
                "created_at": "2024-01-15T10:30:00Z",
                "likes_count": 5,
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:1234567890?commentUrn=urn%3Ali%3Acomment%3A9876543210",
            }
        }


class LinkedInPost(BaseModel):
    """LinkedIn post information."""

    post_id: str = Field(..., description="Post ID (urn format)")
    author_name: str = Field(..., description="Post author's name")
    author_member_id: str = Field(..., description="Author's member ID")
    author_profile_url: Optional[str] = Field(None, description="Author's profile URL")
    content: str = Field(..., description="Post text content")
    url: str = Field(..., description="Direct URL to post")
    created_at: datetime = Field(..., description="Post creation timestamp")
    
    # Engagement metrics
    likes_count: int = Field(0, description="Number of likes")
    comments_count: int = Field(0, description="Number of comments")
    shares_count: int = Field(0, description="Number of shares")
    
    # Media
    has_image: bool = Field(False, description="Whether post has images")
    has_video: bool = Field(False, description="Whether post has video")
    has_document: bool = Field(False, description="Whether post has document")
    
    # Additional metadata
    is_reshare: bool = Field(False, description="Whether this is a reshared post")
    original_post_id: Optional[str] = Field(None, description="Original post ID if reshared")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags used in post")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "post_id": "urn:li:activity:1234567890",
                "author_name": "John Doe",
                "author_member_id": "urn:li:member:123456789",
                "content": "Excited to share insights on AI automation! #AI #Tech",
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:1234567890/",
                "created_at": "2024-01-15T09:00:00Z",
                "likes_count": 42,
                "comments_count": 8,
                "shares_count": 3,
                "hashtags": ["AI", "Tech"],
            }
        }


class LinkedInResult(BaseModel):
    """Wrapper for LinkedIn operation results."""

    success: bool = Field(..., description="Whether operation succeeded")
    data: Optional[Any] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code for debugging")
    trace_id: Optional[str] = Field(None, description="Trace ID for observability")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"post_url": "https://www.linkedin.com/feed/update/..."},
                "error": None,
                "trace_id": "uuid-trace-id",
            }
        }

    @classmethod
    def ok(cls, data: Any = None, trace_id: Optional[str] = None) -> "LinkedInResult":
        """Create successful result."""
        return cls(success=True, data=data, trace_id=trace_id)

    @classmethod
    def fail(
        cls,
        error: str,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> "LinkedInResult":
        """Create failed result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            trace_id=trace_id,
        )


# ============================================================================
# Abstract Interfaces
# ============================================================================


class LinkedInClient(ABC):
    """Abstract interface for LinkedIn read operations.
    
    Implementations:
    - VoyagerClient: Uses unofficial Voyager API via linkedin-api library
    - OAuthClient: Uses official LinkedIn OAuth API (when approved)
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class LinkedInPoster(ABC):
    """Abstract interface for LinkedIn write operations.
    
    Implementations:
    - KimiBridgePoster: Uses Kimi WebBridge (primary, reuses browser session)
    - PlaywrightPoster: Uses Playwright automation (fallback, requires credentials)
    - OAuthClient: Uses official LinkedIn OAuth API (when approved)
    """

    @abstractmethod
    async def create_post(
        self,
        user_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create a new LinkedIn post.
        
        Args:
            user_id: User's LinkedIn member ID
            content: Post text content
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with post URL in data field
        """
        pass

    @abstractmethod
    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on a LinkedIn post.
        
        Args:
            post_id: Post ID (urn format)
            content: Comment text content
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with comment URL in data field
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def validate_session(self, trace_id: Optional[str] = None) -> LinkedInResult:
        """Validate LinkedIn session is active.
        
        Args:
            trace_id: Trace ID for observability
            
        Returns:
            LinkedInResult with validation status
        """
        pass
