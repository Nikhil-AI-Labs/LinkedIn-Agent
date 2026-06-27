"""Browser-based posters for LinkedIn WRITE operations.

This module provides two browser automation implementations:
1. KimiBridgePoster: Primary method, reuses existing browser session via Kimi WebBridge
2. PlaywrightPoster: Fallback method, uses Playwright with stealth mode

Both implementations support:
- Creating posts
- Commenting on posts
- Adding reactions
- Session validation
- Human-like delays (2-7s random)
- Retry logic with exponential backoff
"""

import asyncio
import random
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
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
    LinkedInPoster,
    LinkedInResult,
    ReactionType,
)

logger = get_logger(__name__)


# ============================================================================
# Kimi WebBridge Poster (Primary)
# ============================================================================


class KimiBridgePoster(LinkedInPoster):
    """Kimi WebBridge poster for LinkedIn WRITE operations.
    
    This is a STUB implementation. Kimi WebBridge requires:
    1. Running Kimi browser with WebBridge extension
    2. WebSocket connection to bridge server
    3. Custom command protocol for LinkedIn automation
    
    Implementation TODO:
    - WebSocket client connection
    - Command protocol (create_post, create_comment, add_reaction)
    - Session validation via bridge
    - Error handling and retry logic
    """

    def __init__(self):
        """Initialize Kimi WebBridge poster."""
        self._bridge_connected = False
        logger.warning(
            "KimiBridgePoster initialized but not yet implemented",
            note="This is a stub. Implement WebSocket bridge connection for production.",
        )

    async def validate_session(self, trace_id: Optional[str] = None) -> LinkedInResult:
        """Validate LinkedIn session via Kimi WebBridge."""
        return LinkedInResult.fail(
            error="KimiBridgePoster not yet implemented. "
            "Requires WebSocket connection to Kimi WebBridge extension. "
            "Use PlaywrightPoster as fallback or implement Kimi integration.",
            error_code="KIMI_NOT_IMPLEMENTED",
            trace_id=trace_id,
        )

    async def create_post(
        self,
        user_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create LinkedIn post via Kimi WebBridge."""
        return LinkedInResult.fail(
            error="KimiBridgePoster.create_post not yet implemented. "
            "Requires WebSocket bridge to send create_post command to Kimi browser.",
            error_code="KIMI_NOT_IMPLEMENTED",
            trace_id=trace_id,
        )

    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on LinkedIn post via Kimi WebBridge."""
        return LinkedInResult.fail(
            error="KimiBridgePoster.create_comment not yet implemented. "
            "Requires WebSocket bridge to send create_comment command to Kimi browser.",
            error_code="KIMI_NOT_IMPLEMENTED",
            trace_id=trace_id,
        )

    async def add_reaction(
        self,
        post_id: str,
        reaction_type: ReactionType,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """React to LinkedIn post via Kimi WebBridge."""
        return LinkedInResult.fail(
            error="KimiBridgePoster.add_reaction not yet implemented. "
            "Requires WebSocket bridge to send add_reaction command to Kimi browser.",
            error_code="KIMI_NOT_IMPLEMENTED",
            trace_id=trace_id,
        )


# ============================================================================
# Playwright Poster (Fallback)
# ============================================================================


class PlaywrightPoster(LinkedInPoster):
    """Playwright poster for LinkedIn WRITE operations.
    
    Uses Playwright browser automation with:
    - playwright-stealth for anti-detection
    - Human-like delays (2-7s random)
    - Retry logic (2 attempts with exponential backoff)
    - Session validation before operations
    
    WARNING: LinkedIn actively detects browser automation.
    Use this as a last resort. Kimi WebBridge is safer.
    """

    def __init__(self):
        """Initialize Playwright poster."""
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._authenticated = False

    async def _human_delay(self):
        """Add random human-like delay (2-7 seconds)."""
        delay = random.uniform(2.0, 7.0)
        logger.debug("Human-like delay", duration_seconds=delay)
        await asyncio.sleep(delay)

    async def _init_browser(self) -> Page:
        """Initialize Playwright browser with stealth mode."""
        if self._page is not None and not self._page.is_closed():
            return self._page

        logger.info("Initializing Playwright browser with stealth mode")

        playwright = await async_playwright().start()
        
        # Launch browser with stealth arguments
        self._browser = await playwright.chromium.launch(
            headless=False,  # LinkedIn detects headless mode
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
            ],
        )

        # Create context with realistic user agent
        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )

        # Apply playwright-stealth
        try:
            from playwright_stealth import stealth_async
            self._page = await context.new_page()
            await stealth_async(self._page)
            logger.info("Playwright stealth mode applied")
        except ImportError:
            logger.warning(
                "playwright-stealth not available, using basic stealth",
                warning="Install playwright-stealth for better anti-detection",
            )
            self._page = await context.new_page()
            # Basic stealth: override navigator.webdriver
            await self._page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

        return self._page

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError, ConnectionError)),
    )
    async def _login(self, page: Page) -> bool:
        """Login to LinkedIn using credentials."""
        if not settings.linkedin_username or not settings.linkedin_password_encrypted:
            raise ValueError(
                "LINKEDIN_USERNAME and LINKEDIN_PASSWORD_ENCRYPTED required for Playwright"
            )

        logger.info("Logging in to LinkedIn", username=settings.linkedin_username)

        # Navigate to LinkedIn login
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        await self._human_delay()

        # Fill username
        await page.fill('input[name="session_key"]', settings.linkedin_username)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Fill password
        password = decrypt_text(settings.linkedin_password_encrypted)
        await page.fill('input[name="session_password"]', password)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Click sign in
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Check if login successful (look for feed or profile)
        try:
            await page.wait_for_selector('div[role="main"]', timeout=10000)
            logger.info("LinkedIn login successful")
            self._authenticated = True
            return True
        except PlaywrightTimeoutError:
            logger.error("LinkedIn login failed - could not find main feed")
            return False

    async def validate_session(self, trace_id: Optional[str] = None) -> LinkedInResult:
        """Validate LinkedIn session is active."""
        logger.info("Validating LinkedIn session", trace_id=trace_id)

        try:
            page = await self._init_browser()

            # Try to navigate to feed
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Check if we're on login page (session expired)
            current_url = page.url
            if "login" in current_url:
                logger.warning("Session expired, re-authenticating")
                success = await self._login(page)
                if not success:
                    return LinkedInResult.fail(
                        error="Failed to authenticate with LinkedIn",
                        error_code="PLAYWRIGHT_AUTH_FAILED",
                        trace_id=trace_id,
                    )

            # Check for feed presence
            try:
                await page.wait_for_selector('div[role="main"]', timeout=5000)
                logger.info("LinkedIn session valid", trace_id=trace_id)
                return LinkedInResult.ok(data={"valid": True}, trace_id=trace_id)
            except PlaywrightTimeoutError:
                return LinkedInResult.fail(
                    error="LinkedIn session validation failed - could not find feed",
                    error_code="PLAYWRIGHT_SESSION_INVALID",
                    trace_id=trace_id,
                )

        except Exception as e:
            logger.error(
                "Session validation error",
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Session validation failed: {str(e)}",
                error_code="PLAYWRIGHT_SESSION_ERROR",
                trace_id=trace_id,
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError,)),
    )
    async def create_post(
        self,
        user_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create LinkedIn post via Playwright."""
        logger.info(
            "Creating LinkedIn post via Playwright",
            user_id=user_id,
            content_length=len(content),
            trace_id=trace_id,
        )

        try:
            # Validate session first
            validation = await self.validate_session(trace_id)
            if not validation.success:
                return validation

            page = self._page
            await self._human_delay()

            # Navigate to feed
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Click "Start a post" button
            await page.click('button[aria-label*="Start a post"]')
            await asyncio.sleep(random.uniform(1, 2))

            # Wait for editor
            await page.wait_for_selector('div[role="textbox"]', timeout=5000)
            await asyncio.sleep(1)

            # Type content with human-like typing
            editor = await page.query_selector('div[role="textbox"]')
            await editor.click()
            await asyncio.sleep(0.5)
            
            # Type character by character with random delays
            for char in content:
                await editor.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await self._human_delay()

            # Click Post button
            await page.click('button[aria-label="Post"]')
            await page.wait_for_load_state("networkidle", timeout=15000)

            logger.info(
                "LinkedIn post created successfully",
                user_id=user_id,
                trace_id=trace_id,
            )

            # Try to get post URL from feed
            post_url = "https://www.linkedin.com/feed/"  # Fallback
            return LinkedInResult.ok(data=post_url, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to create LinkedIn post",
                user_id=user_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to create post: {str(e)}",
                error_code="PLAYWRIGHT_CREATE_POST_FAILED",
                trace_id=trace_id,
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError,)),
    )
    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on LinkedIn post via Playwright."""
        logger.info(
            "Creating LinkedIn comment via Playwright",
            post_id=post_id,
            content_length=len(content),
            trace_id=trace_id,
        )

        try:
            validation = await self.validate_session(trace_id)
            if not validation.success:
                return validation

            page = self._page
            await self._human_delay()

            # Navigate to post (construct URL from post_id)
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
            await page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Click comment button/field
            await page.click('button[aria-label*="Comment"]')
            await asyncio.sleep(random.uniform(1, 2))

            # Wait for comment editor
            await page.wait_for_selector('div[role="textbox"]', timeout=5000)
            await asyncio.sleep(1)

            # Type comment
            editor = await page.query_selector('div[role="textbox"]')
            await editor.click()
            await asyncio.sleep(0.5)
            
            for char in content:
                await editor.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await self._human_delay()

            # Click Post comment button
            await page.click('button[aria-label*="Post comment"]')
            await page.wait_for_load_state("networkidle", timeout=10000)

            logger.info(
                "LinkedIn comment created successfully",
                post_id=post_id,
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data=post_url, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to create LinkedIn comment",
                post_id=post_id,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to create comment: {str(e)}",
                error_code="PLAYWRIGHT_CREATE_COMMENT_FAILED",
                trace_id=trace_id,
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=10),
        retry=retry_if_exception_type((PlaywrightTimeoutError,)),
    )
    async def add_reaction(
        self,
        post_id: str,
        reaction_type: ReactionType,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """React to LinkedIn post via Playwright."""
        logger.info(
            "Adding LinkedIn reaction via Playwright",
            post_id=post_id,
            reaction_type=reaction_type,
            trace_id=trace_id,
        )

        try:
            validation = await self.validate_session(trace_id)
            if not validation.success:
                return validation

            page = self._page
            await self._human_delay()

            # Navigate to post
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
            await page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Click reaction button (Like button)
            if reaction_type == ReactionType.LIKE:
                await page.click('button[aria-label*="Like"]')
            else:
                # For other reactions, hold Like button to show reaction picker
                like_button = await page.query_selector('button[aria-label*="Like"]')
                await like_button.hover()
                await asyncio.sleep(0.5)
                
                # Click specific reaction
                reaction_map = {
                    ReactionType.CELEBRATE: "Celebrate",
                    ReactionType.SUPPORT: "Support",
                    ReactionType.LOVE: "Love",
                    ReactionType.INSIGHTFUL: "Insightful",
                    ReactionType.FUNNY: "Funny",
                }
                reaction_label = reaction_map.get(reaction_type, "Like")
                await page.click(f'button[aria-label*="{reaction_label}"]')

            await asyncio.sleep(1)

            logger.info(
                "LinkedIn reaction added successfully",
                post_id=post_id,
                reaction_type=reaction_type,
                trace_id=trace_id,
            )

            return LinkedInResult.ok(data={"success": True}, trace_id=trace_id)

        except Exception as e:
            logger.error(
                "Failed to add LinkedIn reaction",
                post_id=post_id,
                reaction_type=reaction_type,
                error=str(e),
                trace_id=trace_id,
            )
            return LinkedInResult.fail(
                error=f"Failed to add reaction: {str(e)}",
                error_code="PLAYWRIGHT_ADD_REACTION_FAILED",
                trace_id=trace_id,
            )

    async def close(self):
        """Close browser and cleanup resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
            logger.info("Playwright browser closed")
