"""LinkedIn connection status and diagnostics endpoint.

GET /api/v1/linkedin/status  — validates VoyagerClient auth and reports
                               the full connection chain status.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/linkedin", tags=["linkedin"])

# Shared executor for the sync linkedin-api call
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="linkedin_status_")


def _test_voyager_connection_sync(username: str, password: str, public_id: str | None) -> dict:
    """Run blocking linkedin-api auth check in a thread.

    We intentionally avoid making Voyager API calls (get_profile, etc.) here
    because LinkedIn aggressively rate-limits them. Creating the Linkedin client
    itself validates the credentials — it makes a GET / request to confirm the
    cookies are valid. That is sufficient to confirm the integration is working.
    """
    try:
        from app.core.crypto import decrypt_text
        from linkedin_api import Linkedin

        real_password = decrypt_text(password)
        # Client creation authenticates and validates cookies with LinkedIn
        Linkedin(username, real_password)

        # Strip trailing numeric ID from public profile IDs like "nikhil-pathak-207737388"
        name_parts = (public_id or username.split("@")[0]).replace("-", " ").split()
        display_name = " ".join(p for p in name_parts if not p.isdigit()).title()
        return {
            "success": True,
            "profile": {
                "name": display_name,
                "headline": "LinkedIn account connected",
                "member_id": public_id or username,
            },
        }
    except Exception as e:
        error_msg = str(e)
        if type(e).__name__ == 'InvalidToken':
            error_msg = "Decryption failed. The ENCRYPTION_KEY does not match the LINKEDIN_PASSWORD_ENCRYPTED. Please re-run encrypt_password.py."
        elif not error_msg:
            error_msg = f"Error: {type(e).__name__}"
        return {"success": False, "error": error_msg}


@router.get("/status")
async def linkedin_status() -> JSONResponse:
    """Check LinkedIn connection health.

    Returns the status of:
    1. Voyager (linkedin-api) — for reading data
    2. Write method (KimiBridge stub → Playwright fallback)
    3. Whether credentials are configured
    """
    trace_id = str(uuid.uuid4())

    auth_mode = settings.auth_mode
    browser_provider = settings.browser_provider if auth_mode == "browser" else None
    has_username = bool(settings.linkedin_username)
    has_password = bool(settings.linkedin_password_encrypted)

    # ── Voyager (read) status ─────────────────────────────────────────────────
    voyager_status: dict = {"connected": False, "profile": None, "error": None}

    if auth_mode == "browser" and has_username and has_password:
        try:
            import functools
            loop = asyncio.get_event_loop()
            fn = functools.partial(
                _test_voyager_connection_sync,
                settings.linkedin_username,
                settings.linkedin_password_encrypted,
                settings.linkedin_public_id,
            )
            result = await loop.run_in_executor(_executor, fn)
            if result["success"]:
                voyager_status["connected"] = True
                voyager_status["profile"] = result["profile"]
                logger.info(
                    "linkedin_voyager_status_ok",
                    name=result["profile"].get("name"),
                    trace_id=trace_id,
                )
            else:
                voyager_status["error"] = result["error"]
                logger.warning(
                    "linkedin_voyager_status_failed",
                    error=result["error"],
                    trace_id=trace_id,
                )
        except Exception as e:
            voyager_status["error"] = str(e)
            logger.error(
                "linkedin_voyager_status_exception",
                error=str(e),
                trace_id=trace_id,
            )
    elif not has_username or not has_password:
        voyager_status["error"] = "LINKEDIN_USERNAME or LINKEDIN_PASSWORD_ENCRYPTED not set in .env"
    else:
        voyager_status["error"] = "AUTH_MODE is not 'browser' — Voyager not applicable"

    # ── Write method status ───────────────────────────────────────────────────
    kimi_ready = False
    kimi_note = "Kimi WebBridge extension is not running at ws://localhost:7777"
    
    try:
        import websockets
        async with websockets.connect("ws://localhost:7777", open_timeout=1.0) as ws:
            kimi_ready = True
            kimi_note = "Kimi WebBridge connected successfully"
    except Exception as e:
        kimi_note = f"Kimi WebBridge disconnected: {type(e).__name__}"

    write_status = {
        "primary": "KimiBridgePoster",
        "primary_ready": kimi_ready,
        "primary_note": kimi_note,
        "fallback": "PlaywrightPoster",
        "fallback_ready": True,
        "fallback_note": "Playwright fallback is implemented and uses LINKEDIN_USERNAME + decrypted password",
    }

    return JSONResponse(
        content={
            "trace_id": trace_id,
            "auth_mode": auth_mode,
            "browser_provider": browser_provider,
            "credentials_configured": has_username and has_password,
            "username": settings.linkedin_username if has_username else None,
            "voyager_read": voyager_status,
            "write_method": write_status,
            "summary": (
                "✅ LinkedIn read (Voyager) connected"
                if voyager_status["connected"]
                else f"❌ LinkedIn read failed: {voyager_status.get('error', 'unknown')}"
            ),
        }
    )
