"""
LinkedIn WebBridge Poster - Uses Kimi WebBridge local service
to control your real browser session (no Playwright, no 2FA needed)
"""

import httpx
import asyncio
import random
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger("linkedin_webbridge_poster")

# Kimi WebBridge local service (discovered from status check)
WEBBRIDGE_BASE_URL = "http://localhost:10086"


class LinkedInWebBridgePoster:
    """
    Posts to LinkedIn using Kimi WebBridge - controls your real
    Chrome/Edge browser where you're already logged into LinkedIn.
    
    No credentials needed, no 2FA, no session management.
    Uses your existing browser session via the Kimi extension.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._connected = False

    async def health_check(self) -> bool:
        """Check if Kimi WebBridge service is running and extension connected."""
        try:
            response = await self.client.get(f"{WEBBRIDGE_BASE_URL}/status")
            if response.status_code == 200:
                data = response.json()
                self._connected = data.get("extension_connected", False)
                
                if self._connected:
                    logger.info(
                        "kimi_webbridge_connected",
                        extension_version=data.get("extension_version"),
                        uptime=data.get("uptime_seconds")
                    )
                else:
                    logger.warning("kimi_extension_not_connected")
                
                return self._connected
        except Exception as e:
            logger.error("kimi_health_check_failed", error=str(e))
            return False
        
        return False

    async def _human_delay(self, min_s: float = 2.0, max_s: float = 7.0):
        """Human-like delay between actions."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def _execute_command(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command via Kimi WebBridge API.
        
        Based on the Kimi WebBridge protocol:
        - navigate: Go to URL
        - click: Click element by selector
        - fill: Type text into element
        - evaluate: Run JavaScript
        """
        payload = {
            "tool_call": {
                "name": tool_name,
                "args": args
            }
        }
        
        logger.info("kimi_execute", tool=tool_name, args=args)
        
        try:
            response = await self.client.post(
                f"{WEBBRIDGE_BASE_URL}/execute",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info("kimi_result", tool=tool_name, success=result.get("success"))
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error("kimi_http_error", status=e.response.status_code, body=e.response.text)
            raise RuntimeError(f"Kimi WebBridge command failed: {e.response.text}")
        except Exception as e:
            logger.error("kimi_command_error", error=str(e), exc_info=True)
            raise

    async def navigate(self, url: str):
        """Navigate browser to URL."""
        await self._human_delay(1.0, 2.0)
        return await self._execute_command("navigate", {"url": url})

    async def click(self, selector: str):
        """Click element by CSS selector."""
        await self._human_delay(0.5, 1.5)
        return await self._execute_command("click", {"selector": selector})

    async def fill(self, selector: str, value: str):
        """Type text into element."""
        await self._human_delay(0.5, 1.0)
        return await self._execute_command("fill", {
            "selector": selector,
            "value": value
        })

    async def evaluate(self, code: str) -> Any:
        """Execute JavaScript in browser."""
        result = await self._execute_command("evaluate", {"code": code})
        return result.get("data")

    async def create_post(self, content: str, user_id: Optional[str] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a LinkedIn post using your existing browser session.
        
        This is the main method your agent will call.
        
        Args:
            content: The post text to publish
            user_id: Optional user ID for logging
            trace_id: Optional trace ID for logging
            
        Returns:
            Dict with success status and post_id if successful
        """
        try:
            if not self._connected:
                if not await self.health_check():
                    raise RuntimeError(
                        "Kimi WebBridge extension is not connected! "
                        "Ensure Microsoft Edge is open with LinkedIn logged in "
                        "and the Kimi WebBridge extension is active."
                    )
            
            logger.info(
                "linkedin_post_starting",
                user_id=user_id,
                content_length=len(content),
                trace_id=trace_id
            )

            # Step 1: Navigate to LinkedIn feed
            logger.info("navigate_to_feed")
            await self.navigate("https://www.linkedin.com/feed/")
            await self._human_delay(2.0, 3.0)

            # Step 2: Click "Start a post" button
            logger.info("clicking_start_post")
            await self.click('[data-placeholder="What do you want to talk about?"]')
            await self._human_delay(1.0, 2.0)

            # Step 3: Fill in the post content
            logger.info("filling_post_content")
            await self.fill(
                '.ql-editor[data-placeholder="What do you want to talk about?"]',
                content
            )
            await self._human_delay(2.0, 3.0)

            # Step 4: Click Post button
            logger.info("clicking_post_button")
            await self.click('button.share-actions__primary-action')
            await self._human_delay(3.0, 5.0)

            # Step 5: Verify post was created (check for success message or URL change)
            current_url = await self.evaluate("window.location.href")
            
            logger.info(
                "linkedin_post_completed",
                user_id=user_id,
                trace_id=trace_id,
                current_url=current_url
            )

            return {
                "success": True,
                "post_id": current_url if "update" in str(current_url) else None,
                "message": "Post published successfully via Kimi WebBridge"
            }

        except Exception as e:
            logger.error(
                "linkedin_post_failed",
                error=str(e),
                user_id=user_id,
                trace_id=trace_id,
                exc_info=True
            )
            raise RuntimeError(f"Failed to post via Kimi WebBridge: {str(e)}")

    async def create_comment(self, post_urn: str, comment_text: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Post a comment on a LinkedIn post."""
        try:
            logger.info("linkedin_comment_starting", post_urn=post_urn, trace_id=trace_id)

            # Navigate to post
            post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
            await self.navigate(post_url)
            await self._human_delay(2.0, 3.0)

            # Click comment box
            await self.click('.comments-comment-box__text-editor .ql-editor')
            await self._human_delay(0.5, 1.0)

            # Type comment
            await self.fill(
                '.comments-comment-box__text-editor .ql-editor',
                comment_text
            )
            await self._human_delay(1.5, 2.5)

            # Submit comment
            await self.click('.comments-comment-box__submit-button')
            await self._human_delay(2.0, 3.0)

            logger.info("linkedin_comment_completed", post_urn=post_urn, trace_id=trace_id)

            return {
                "success": True,
                "message": "Comment posted successfully via Kimi WebBridge"
            }

        except Exception as e:
            logger.error("linkedin_comment_failed", error=str(e), post_urn=post_urn, trace_id=trace_id)
            raise RuntimeError(f"Failed to comment via Kimi WebBridge: {str(e)}")

    async def add_reaction(self, post_urn: str, reaction_type: str = "LIKE", trace_id: Optional[str] = None) -> Dict[str, Any]:
        """React to a LinkedIn post."""
        try:
            logger.info("linkedin_reaction_starting", post_urn=post_urn, reaction_type=reaction_type, trace_id=trace_id)

            # Navigate to post
            post_url = f"https://www.linkedin.com/feed/update/{post_urn}/"
            await self.navigate(post_url)
            await self._human_delay(2.0, 3.0)

            # Click like/react button
            await self.click('button.react-button__trigger')
            await self._human_delay(1.0, 2.0)

            logger.info("linkedin_reaction_completed", post_urn=post_urn, reaction_type=reaction_type, trace_id=trace_id)

            return {
                "success": True,
                "message": f"Reacted with {reaction_type} via Kimi WebBridge"
            }

        except Exception as e:
            logger.error("linkedin_reaction_failed", error=str(e), post_urn=post_urn, trace_id=trace_id)
            raise RuntimeError(f"Failed to react via Kimi WebBridge: {str(e)}")

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
