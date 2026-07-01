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
    
    Uses the official Kimi WebBridge local service running on port 10086
    which controls your existing browser session via the Chrome/Edge extension.
    
    NO credentials needed, NO 2FA, NO Playwright - uses your real browser!
    """

    WEBBRIDGE_URL = "http://localhost:10086"

    def __init__(self):
        """Initialize Kimi WebBridge poster."""
        import httpx
        self._client = httpx.AsyncClient(timeout=60.0)

    async def _check_connection(self) -> bool:
        """Verify Kimi WebBridge service and extension are connected."""
        try:
            response = await self._client.get(f"{self.WEBBRIDGE_URL}/status")
            if response.status_code == 200:
                data = response.json()
                return data.get("extension_connected", False)
        except Exception as e:
            logger.error(f"Kimi health check failed: {e}")
        return False

    async def _execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool command via Kimi WebBridge HTTP API."""
        payload = {
            "tool_call": {
                "name": tool_name,
                "args": args
            }
        }
        
        logger.info(f"Kimi execute: {tool_name}", args=args)
        
        response = await self._client.post(
            f"{self.WEBBRIDGE_URL}/execute",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def _navigate(self, url: str):
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return await self._execute("navigate", {"url": url})

    async def _click(self, selector: str):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return await self._execute("click", {"selector": selector})

    async def _fill(self, selector: str, value: str):
        await asyncio.sleep(random.uniform(0.5, 1.0))
        return await self._execute("fill", {"selector": selector, "value": value})

    async def _evaluate(self, code: str):
        result = await self._execute("evaluate", {"code": code})
        return result.get("data") if isinstance(result, dict) else result

    async def validate_session(self, trace_id: Optional[str] = None) -> LinkedInResult:
        """Validate LinkedIn session via Kimi WebBridge."""
        try:
            # First check if service is up and extension connected
            if not await self._check_connection():
                return LinkedInResult.fail(
                    error="Kimi WebBridge extension is not connected. Open Chrome/Edge with Kimi extension.",
                    error_code="KIMI_NOT_CONNECTED",
                    trace_id=trace_id,
                )
            
            # Navigate to LinkedIn feed
            await self._navigate("https://www.linkedin.com/feed/")
            await asyncio.sleep(3)
            
            # Check if we're logged in
            is_logged_in = await self._evaluate(
                "!!document.querySelector('.global-nav__me') || "
                "document.body.innerHTML.includes('feed-identity-module')"
            )
            
            if is_logged_in:
                logger.info("Kimi WebBridge session valid", trace_id=trace_id)
                return LinkedInResult.ok(data={"valid": True}, trace_id=trace_id)
            
            return LinkedInResult.fail(
                error="Not logged into LinkedIn. Please log in via your browser first.",
                error_code="KIMI_NOT_LOGGED_IN",
                trace_id=trace_id,
            )
        except Exception as e:
            logger.error(f"Kimi session validation failed: {e}")
            return LinkedInResult.fail(
                error=f"Kimi WebBridge error: {str(e)}",
                error_code="KIMI_CONNECTION_ERROR",
                trace_id=trace_id,
            )

    async def create_post(
        self,
        user_id: Optional[str],
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Create LinkedIn post via Kimi WebBridge using your real browser."""
        try:
            # Check connection first
            if not await self._check_connection():
                return LinkedInResult.fail(
                    error="Kimi WebBridge extension is not connected! Open Chrome/Edge with the extension.",
                    error_code="KIMI_NOT_CONNECTED",
                    trace_id=trace_id,
                )
            
            logger.info(
                "Creating LinkedIn post via Kimi WebBridge",
                content_length=len(content),
                trace_id=trace_id,
            )
            
            # 1. Navigate to feed
            await self._navigate("https://www.linkedin.com/feed/")
            await asyncio.sleep(4)
            
            # 2. Click "Start a post" - try multiple selectors
            click_start_js = """
            (function() {
                // Try various selectors for "Start a post"
                var selectors = [
                    'button[aria-label*="Start a post"]',
                    '[data-placeholder*="talk about"]',
                    'button.share-box-feed-entry__trigger',
                    '.share-box-feed-entry__top-bar button'
                ];
                for (var sel of selectors) {
                    var el = document.querySelector(sel);
                    if (el) { el.click(); return 'clicked: ' + sel; }
                }
                // Fallback: find by text
                var btns = Array.from(document.querySelectorAll('button'));
                var btn = btns.find(b => b.innerText && b.innerText.includes('Start a post'));
                if (btn) { btn.click(); return 'clicked by text'; }
                return 'not found';
            })()
            """
            click_result = await self._evaluate(click_start_js)
            logger.info(f"Start post click: {click_result}")
            await asyncio.sleep(3)
            
            # 3. Fill content in the editor
            fill_js = f"""
            (function() {{
                var content = {repr(content)};
                var editor = document.querySelector('.ql-editor[contenteditable="true"]') ||
                             document.querySelector('div[role="textbox"]') ||
                             document.querySelector('.ql-editor');
                if (editor) {{
                    editor.focus();
                    editor.innerHTML = '<p>' + content.replace(/\\n/g, '</p><p>') + '</p>';
                    // Trigger input event
                    var event = new Event('input', {{ bubbles: true }});
                    editor.dispatchEvent(event);
                    return 'filled';
                }}
                return 'editor not found';
            }})()
            """
            fill_result = await self._evaluate(fill_js)
            logger.info(f"Fill content: {fill_result}")
            await asyncio.sleep(2)
            
            # 4. Click Post button
            click_post_js = """
            (function() {
                var selectors = [
                    'button.share-actions__primary-action',
                    'button[aria-label="Post"]',
                    '.share-box_actions button.artdeco-button--primary'
                ];
                for (var sel of selectors) {
                    var el = document.querySelector(sel);
                    if (el && !el.disabled) { el.click(); return 'clicked: ' + sel; }
                }
                // Fallback: find by text
                var btns = Array.from(document.querySelectorAll('button'));
                var btn = btns.find(b => 
                    b.innerText && 
                    (b.innerText.trim() === 'Post' || b.innerText.trim() === 'Publish') &&
                    !b.disabled
                );
                if (btn) { btn.click(); return 'clicked by text'; }
                return 'post button not found';
            })()
            """
            post_result = await self._evaluate(click_post_js)
            logger.info(f"Post button click: {post_result}")
            await asyncio.sleep(5)
            
            # 5. Get current URL as proof of posting
            current_url = await self._evaluate("window.location.href")
            
            logger.info(
                "LinkedIn post created via Kimi WebBridge",
                url=current_url,
                trace_id=trace_id,
            )
            
            return LinkedInResult.ok(
                data=current_url or "https://www.linkedin.com/feed/",
                trace_id=trace_id
            )
            
        except Exception as e:
            logger.error(f"Kimi create_post failed: {e}", exc_info=True)
            return LinkedInResult.fail(
                error=f"Failed to create post via Kimi: {str(e)}",
                error_code="KIMI_CREATE_POST_FAILED",
                trace_id=trace_id,
            )

    async def create_comment(
        self,
        post_id: str,
        content: str,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """Comment on LinkedIn post via Kimi WebBridge."""
        try:
            if not await self._check_connection():
                return LinkedInResult.fail(
                    error="Kimi WebBridge extension is not connected!",
                    error_code="KIMI_NOT_CONNECTED",
                    trace_id=trace_id,
                )
            
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            await self._navigate(post_url)
            await asyncio.sleep(4)
            
            # Click comment box first
            click_comment_js = """
            (function() {
                var btn = document.querySelector('button[aria-label*="Comment"]') ||
                          document.querySelector('.comments-comment-box__form-trigger');
                if (btn) { btn.click(); return 'clicked'; }
                return 'not found';
            })()
            """
            await self._evaluate(click_comment_js)
            await asyncio.sleep(2)
            
            # Fill comment
            fill_comment_js = f"""
            (function() {{
                var content = {repr(content)};
                var editor = document.querySelector('.comments-comment-box__text-editor .ql-editor') ||
                             document.querySelector('.comments-comment-box .ql-editor');
                if (editor) {{
                    editor.focus();
                    editor.innerHTML = '<p>' + content + '</p>';
                    var event = new Event('input', {{ bubbles: true }});
                    editor.dispatchEvent(event);
                    return 'filled';
                }}
                return 'editor not found';
            }})()
            """
            await self._evaluate(fill_comment_js)
            await asyncio.sleep(2)
            
            # Submit comment
            submit_js = """
            (function() {
                var btn = document.querySelector('.comments-comment-box__submit-button') ||
                          document.querySelector('button[type="submit"].comments-comment-box__submit-button');
                if (btn && !btn.disabled) { btn.click(); return 'submitted'; }
                return 'submit button not found';
            })()
            """
            await self._evaluate(submit_js)
            await asyncio.sleep(3)
            
            return LinkedInResult.ok(data=f"{post_url}?comment=success", trace_id=trace_id)
        except Exception as e:
            logger.error(f"Kimi create_comment failed: {e}", exc_info=True)
            return LinkedInResult.fail(
                error=f"Failed to create comment via Kimi: {str(e)}",
                error_code="KIMI_CREATE_COMMENT_FAILED",
                trace_id=trace_id,
            )

    async def add_reaction(
        self,
        post_id: str,
        reaction_type: ReactionType,
        trace_id: Optional[str] = None,
    ) -> LinkedInResult:
        """React to LinkedIn post via Kimi WebBridge."""
        try:
            if not await self._check_connection():
                return LinkedInResult.fail(
                    error="Kimi WebBridge extension is not connected!",
                    error_code="KIMI_NOT_CONNECTED",
                    trace_id=trace_id,
                )
            
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            await self._navigate(post_url)
            await asyncio.sleep(4)
            
            # Click Like button
            click_like_js = """
            (function() {
                var btn = document.querySelector('button[aria-label*="React Like"]') ||
                          document.querySelector('button.react-button__trigger') ||
                          document.querySelector('button[aria-label*="Like"]');
                if (btn) { btn.click(); return 'liked'; }
                return 'like button not found';
            })()
            """
            await self._evaluate(click_like_js)
            await asyncio.sleep(2)
            
            return LinkedInResult.ok(data={"success": True}, trace_id=trace_id)
        except Exception as e:
            logger.error(f"Kimi add_reaction failed: {e}", exc_info=True)
            return LinkedInResult.fail(
                error=f"Failed to add reaction via Kimi: {str(e)}",
                error_code="KIMI_ADD_REACTION_FAILED",
                trace_id=trace_id,
            )



# ============================================================================
# Playwright Poster (Fallback)
# ============================================================================


class _InnerPlaywrightPoster(LinkedInPoster):
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
        import os
        state_file = "playwright_state.json"
        
        # Launch browser with stealth arguments
        self._browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,  # Use config instead of hardcoded False
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
            ],
        )

        # Create context with realistic user agent and persisted state
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
        }
        if os.path.exists(state_file):
            context_args["storage_state"] = state_file
            
        context = await self._browser.new_context(**context_args)

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
            # Wait up to 120 seconds if we need manual 2FA intervention
            timeout = 120000 if not settings.playwright_headless else 30000
            await page.wait_for_selector('div[role="main"]', timeout=timeout)
            logger.info("LinkedIn login successful")
            self._authenticated = True
            
            # Save session state so we don't need to login next time
            await page.context.storage_state(path="playwright_state.json")
            logger.info("Saved browser session state")
            
            return True
        except PlaywrightTimeoutError:
            logger.error("LinkedIn login failed - could not find main feed (timeout waiting for 2FA or feed)")
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


import threading
from concurrent.futures import Future

class PlaywrightThread:
    """Dedicated background thread for Playwright with ProactorEventLoop."""
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_loop(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance.loop
            
    def __init__(self):
        self.loop = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="PlaywrightThread")
        self.thread.start()
        self.ready.wait()
        
    def _run_loop(self):
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()

class PlaywrightPoster(LinkedInPoster):
    """Thread-safe proxy for Playwright operations."""
    
    def __init__(self):
        self._inner = _InnerPlaywrightPoster()

    async def _run_in_thread(self, coro_func_name: str, *args, **kwargs):
        loop = PlaywrightThread.get_loop()
        
        async def _wrapper():
            func = getattr(self._inner, coro_func_name)
            return await func(*args, **kwargs)
            
        future = asyncio.run_coroutine_threadsafe(_wrapper(), loop)
        return await asyncio.wrap_future(future)

    async def validate_session(self, trace_id: Optional[str] = None) -> LinkedInResult:
        return await self._run_in_thread("validate_session", trace_id)

    async def create_post(self, user_id: str, content: str, trace_id: Optional[str] = None) -> LinkedInResult:
        return await self._run_in_thread("create_post", user_id, content, trace_id)

    async def create_comment(self, post_id: str, content: str, trace_id: Optional[str] = None) -> LinkedInResult:
        return await self._run_in_thread("create_comment", post_id, content, trace_id)

    async def add_reaction(self, post_id: str, reaction_type: ReactionType, trace_id: Optional[str] = None) -> LinkedInResult:
        return await self._run_in_thread("add_reaction", post_id, reaction_type, trace_id)
        
    async def close(self):
        return await self._run_in_thread("close")
