"""OAuth client stub for LinkedIn official API.

This is a STUB implementation for the official LinkedIn OAuth API.

Why OAuth is not implemented:
1. LinkedIn requires app approval with "Sign In with LinkedIn using OpenID Connect" product
2. Posting requires w_member_social scope, which is NOT available to most personal projects
3. LinkedIn rarely grants w_member_social to individual developers
4. The approval process takes weeks/months and often gets rejected

Alternative approaches:
- Use Voyager API (linkedin-api) for READ operations (implemented)
- Use browser automation (Playwright/Kimi) for WRITE operations (implemented)
- For production apps with LinkedIn partnership, implement OAuth here

Official API docs: https://learn.microsoft.com/en-us/linkedin/
"""

from typing import Optional

from app.core.logging import get_logger
from app.services.linkedin.base import (
    LinkedInClient,
    LinkedInPoster,
    LinkedInResult,
    ReactionType,
)

logger = get_logger(__name__)


class OAuthClient(LinkedInClient, LinkedInPoster):
    """OAuth client stub for LinkedIn official API.
    
    This class implements both LinkedInClient (read) and LinkedInPoster (write)
    interfaces, but all methods return "not implemented" errors.
    
    To implement OAuth:
    1. Get LinkedIn app approved with required scopes
    2. Implement OAuth 2.0 authorization code flow
    3. Store access tokens securely in database (encrypted)
    4. Implement token refresh logic
    5. Implement API endpoints per LinkedIn REST API docs
    """

    def __init__(self):
        """Initialize OAuth client."""
        logger.warning(
            "OAuthClient initialized but not implemented",
            reason="LinkedIn OAuth requires app approval with w_member_social scope",
            note="Most personal projects cannot get this scope approved",
            alternatives="Use VoyagerClient (read) + PlaywrightPoster (write)",
        )

    def _not_implemented_error(
        self, operation: str, trace_id: Optional[str] = None
    ) -> LinkedInResult:
        """Return not implemented error."""
        return LinkedInResult.fail(
            error=f"OAuth {operation} not implemented. "
            "LinkedIn OAuth requires app approval with w_member_social scope, "
            "which is NOT available to most personal projects. "
            "Use VoyagerClient for READ operations and PlaywrightPoster/KimiBridgePoster for WRITE operations.",
            error_code="OAUTH_NOT_IMPLEMENTED",
            trace_id=trace_id,
        )

    # ========================================================================
    # LinkedInClient (READ) Interface
    # ========================================================================

    async def get_user_posts(
        self,
        user_id: str,
        limit: int = 10,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch user's recent posts (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth get_user_posts called but not implemented",
            user_id=user_id,
            trace_id=trace_id,
        )
        return self._not_implemented_error("get_user_posts", trace_id)

    async def get_profile_posts(
        self,
        member_id: str,
        limit: int = 5,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch posts from a specific profile (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth get_profile_posts called but not implemented",
            member_id=member_id,
            trace_id=trace_id,
        )
        return self._not_implemented_error("get_profile_posts", trace_id)

    async def get_post_comments(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch comments on a post (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth get_post_comments called but not implemented",
            post_id=post_id,
            trace_id=trace_id,
        )
        return self._not_implemented_error("get_post_comments", trace_id)

    async def get_post_reactions(
        self,
        post_id: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Fetch reactions on a post (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth get_post_reactions called but not implemented",
            post_id=post_id,
            trace_id=trace_id,
        )
        return self._not_implemented_error("get_post_reactions", trace_id)

    async def validate_profile(
        self,
        profile_url: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Validate and fetch profile information (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth validate_profile called but not implemented",
            profile_url=profile_url,
            trace_id=trace_id,
        )
        return self._not_implemented_error("validate_profile", trace_id)

    # ========================================================================
    # LinkedInPoster (WRITE) Interface
    # ========================================================================

    async def create_post(
        self,
        user_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create a new LinkedIn post (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth create_post called but not implemented",
            user_id=user_id,
            content_length=len(content),
            trace_id=trace_id,
        )
        return self._not_implemented_error("create_post", trace_id)

    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on a LinkedIn post (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth create_comment called but not implemented",
            post_id=post_id,
            content_length=len(content),
            trace_id=trace_id,
        )
        return self._not_implemented_error("create_comment", trace_id)

    async def add_reaction(
        self,
        post_id: str,
        reaction_type: ReactionType,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """React to a LinkedIn post (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth add_reaction called but not implemented",
            post_id=post_id,
            reaction_type=reaction_type,
            trace_id=trace_id,
        )
        return self._not_implemented_error("add_reaction", trace_id)

    async def validate_session(
        self, trace_id: Optional[str] = None
    ) -> LinkedInResult:
        """Validate LinkedIn session (NOT IMPLEMENTED)."""
        logger.warning(
            "OAuth validate_session called but not implemented",
            trace_id=trace_id,
        )
        return self._not_implemented_error("validate_session", trace_id)


# ============================================================================
# OAuth Implementation Guide (For Future Development)
# ============================================================================

"""
OAUTH IMPLEMENTATION GUIDE
==========================

If you get LinkedIn app approval with w_member_social scope, implement:

1. Authorization Flow:
   - Redirect user to LinkedIn OAuth authorize endpoint
   - Handle callback with authorization code
   - Exchange code for access token
   - Store encrypted token in oauth_accounts table

2. Token Management:
   - Implement token refresh (tokens expire after 60 days)
   - Handle token revocation
   - Encrypt tokens using app.core.crypto

3. API Endpoints:

   READ Operations (require r_liteprofile, r_basicprofile scopes):
   - GET /v2/me - Get current user profile
   - GET /v2/ugcPosts - Get user posts
   - GET /v2/socialActions/{shareKey}/comments - Get post comments
   
   WRITE Operations (require w_member_social scope):
   - POST /v2/ugcPosts - Create post
   - POST /v2/socialActions/{shareKey}/comments - Create comment
   - POST /v2/reactions/{entity} - Add reaction

4. Example Implementation:

   ```python
   import httpx
   from app.core.crypto import encrypt_text, decrypt_text
   
   class OAuthClient(LinkedInClient, LinkedInPoster):
       async def _get_access_token(self, user_id: str) -> str:
           # Fetch from oauth_accounts table
           # Decrypt using decrypt_text()
           # Check expiry and refresh if needed
           pass
       
       async def create_post(self, user_id: str, content: str, trace_id: str):
           token = await self._get_access_token(user_id)
           
           async with httpx.AsyncClient() as client:
               response = await client.post(
                   "https://api.linkedin.com/v2/ugcPosts",
                   headers={
                       "Authorization": f"Bearer {token}",
                       "Content-Type": "application/json",
                       "X-Restli-Protocol-Version": "2.0.0",
                   },
                   json={
                       "author": f"urn:li:person:{user_id}",
                       "lifecycleState": "PUBLISHED",
                       "specificContent": {
                           "com.linkedin.ugc.ShareContent": {
                               "shareCommentary": {"text": content},
                               "shareMediaCategory": "NONE",
                           }
                       },
                       "visibility": {
                           "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                       },
                   },
               )
               
               if response.status_code == 201:
                   post_id = response.json()["id"]
                   post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
                   return LinkedInResult.ok(data=post_url, trace_id=trace_id)
               else:
                   return LinkedInResult.fail(
                       error=f"LinkedIn API error: {response.text}",
                       error_code=f"LINKEDIN_API_{response.status_code}",
                       trace_id=trace_id,
                   )
   ```

5. References:
   - OAuth Guide: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication
   - Share API: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/share-api
   - UGC Posts: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
"""
