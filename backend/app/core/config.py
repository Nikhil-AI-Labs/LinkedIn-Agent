"""Application configuration with startup validation."""

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger()

# Deterministic path to project root (3 levels up from this file)
BASE_DIR = Path(__file__).resolve().parents[3]  # backend/app/core/config.py -> project root
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable validation."""

    # Application
    app_name: str = "LinkedIn AI Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Authentication Mode
    auth_mode: Literal["oauth", "browser"] = "browser"  # Default to browser for personal use
    browser_provider: Literal["kimi_webbridge", "playwright"] = "kimi_webbridge"

    # Database
    database_url: str

    # LLM APIs
    sarvam_api_key: str
    sarvam_model: str = "sarvam-105b"
    sarvam_stt_model: str = "saarika:v2.5"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_language: str = "hi-IN"
    sarvam_tts_speaker: str = "roopa"
    
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    
    gemini_api_key: str
    
    # Voice Service Configuration
    voice_max_upload_mb: int = 15
    voice_max_tts_chars: int = 1800

    # Security
    encryption_key: str
    jwt_secret: str

    # LinkedIn OAuth App Credentials (for official API - if approved)
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_redirect_uri: str = "http://localhost:8000/api/v1/auth/linkedin/callback"

    # LinkedIn Browser Fallback (optional - only for Playwright emergency login)
    # Kimi WebBridge reuses your existing session - credentials not needed
    # IMPORTANT: LINKEDIN_PASSWORD_ENCRYPTED should be encrypted using encrypt_password.py script
    linkedin_username: str | None = None
    linkedin_password_encrypted: str | None = None
    linkedin_public_id: str | None = None  # e.g. "nikhil-pathak-207737388" from linkedin.com/in/<ID>
    playwright_headless: bool = True  # Set to False to solve captchas/2FA interactively

    # Observability
    langsmith_api_key: str | None = None
    langchain_project: str = "linkedin-ai-agent"
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def validate_settings(settings: Settings) -> None:
    """Validate required settings based on auth mode and fail fast."""

    missing_secrets: list[str] = []

    # Always required base secrets
    required_base = [
        "database_url",
        "sarvam_api_key",
        "groq_api_key",
        "gemini_api_key",
        "encryption_key",
        "jwt_secret",
    ]

    for key in required_base:
        value = getattr(settings, key)
        if not value:
            missing_secrets.append(key.upper())

    # Validate auth_mode
    if settings.auth_mode not in ["oauth", "browser"]:
        logger.error(
            "Invalid AUTH_MODE",
            auth_mode=settings.auth_mode,
            valid_modes=["oauth", "browser"],
        )
        sys.exit(1)

    # OAuth mode specific
    if settings.auth_mode == "oauth":
        if not settings.linkedin_client_id or not settings.linkedin_client_secret:
            logger.error(
                "OAuth mode requires LinkedIn app credentials",
                message="Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET. "
                "Get these from LinkedIn Developer Portal after app approval. "
                "Note: Most personal projects cannot get w_member_social scope needed for posting.",
            )
            sys.exit(1)
        logger.info(
            "OAuth mode enabled",
            note="Requires approved LinkedIn app with w_member_social scope for posting",
        )

    # Browser mode specific
    elif settings.auth_mode == "browser":
        # Validate browser provider
        if settings.browser_provider not in ["kimi_webbridge", "playwright"]:
            logger.error(
                "Invalid BROWSER_PROVIDER",
                browser_provider=settings.browser_provider,
                valid_providers=["kimi_webbridge", "playwright"],
            )
            sys.exit(1)

        if settings.browser_provider == "kimi_webbridge":
            logger.info(
                "Kimi WebBridge mode enabled (recommended for personal use)",
                note="Reuses your existing browser session - no credentials needed",
            )
        elif settings.browser_provider == "playwright":
            logger.warning(
                "Playwright browser automation enabled",
                warning="This uses unofficial methods and may break. Kimi WebBridge is recommended. "
                "LinkedIn actively detects automation - use at your own risk.",
            )
            # Credentials optional for Playwright - can reuse session cookies
            if not settings.linkedin_username or not settings.linkedin_password_encrypted:
                logger.info(
                    "No LinkedIn credentials provided - will attempt session reuse",
                    note="Set LINKEDIN_USERNAME and LINKEDIN_PASSWORD_ENCRYPTED for fresh login fallback",
                )

    # Fail if missing secrets
    if missing_secrets:
        logger.error(
            "Missing required secrets",
            missing_secrets=", ".join(missing_secrets),
            message="Please set all required environment variables in .env file",
        )
        sys.exit(1)

    logger.info(
        "All required secrets validated",
        auth_mode=settings.auth_mode,
        browser_provider=(
            settings.browser_provider if settings.auth_mode == "browser" else None
        ),
        observability_enabled=settings.langchain_tracing_v2,
    )


# Create settings instance
settings = Settings()

# Validate on import
validate_settings(settings)
# trigger reload 2
