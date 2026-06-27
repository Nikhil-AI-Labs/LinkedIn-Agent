"""Test that everything is configured correctly."""

import asyncio
import sys

from app.core.config import settings
from app.db.session import init_db, close_db
from app.core.crypto import encrypt_text, decrypt_text


async def main():
    print("=" * 70)
    print("LinkedIn AI Agent - Setup Verification")
    print("=" * 70)
    print()

    # Test configuration
    print("✓ Testing configuration...")
    print(f"  Auth mode: {settings.auth_mode}")
    
    if settings.auth_mode == "oauth":
        print(f"  OAuth mode: Checking credentials...")
        if not settings.linkedin_client_id or not settings.linkedin_client_secret:
            print("  ✗ OAuth mode requires LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET")
            sys.exit(1)
        print(f"  ✓ OAuth credentials present")
        print(f"  Client ID: {settings.linkedin_client_id[:10]}...")
        print(f"  Redirect URI: {settings.linkedin_redirect_uri}")
    elif settings.auth_mode == "browser":
        print(f"  Browser provider: {settings.browser_provider}")
        print(f"  LinkedIn username: {settings.linkedin_username or '(not set - Kimi will reuse session)'}")
        
        if settings.browser_provider == "kimi_webbridge":
            print("  ✓ Kimi WebBridge mode - will reuse existing browser session")
            if settings.linkedin_username:
                print("  ℹ Username set but not needed for Kimi (will be used as fallback)")
        elif settings.browser_provider == "playwright":
            if not settings.linkedin_username:
                print("  ✗ Playwright mode requires LINKEDIN_USERNAME and LINKEDIN_PASSWORD_ENCRYPTED")
                sys.exit(1)
            if not settings.linkedin_password_encrypted:
                print("  ✗ Playwright mode requires LINKEDIN_PASSWORD_ENCRYPTED")
                print("  Run: python backend/scripts/encrypt_password.py")
                sys.exit(1)
            print("  ✓ Playwright credentials present")
            print("  ⚠ Warning: Playwright has high LinkedIn detection risk. Consider Kimi WebBridge.")
        else:
            print(f"  ✗ Unknown browser provider: {settings.browser_provider}")
            sys.exit(1)
    else:
        print(f"  ✗ Invalid auth mode: {settings.auth_mode}")
        print("  Valid options: 'oauth' or 'browser'")
        sys.exit(1)
    
    print(f"  Database URL: {settings.database_url.split('@')[0]}@...")

    # Test encryption
    print("\n✓ Testing encryption...")
    test_text = "secret-token-12345"
    encrypted = encrypt_text(test_text)
    decrypted = decrypt_text(encrypted)
    assert decrypted == test_text, "Encryption roundtrip failed"
    print("  Encryption working correctly")

    # Test database connection
    print("\n✓ Testing database connection...")
    try:
        await init_db()
        print("  Database connected successfully")
        await close_db()
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        print("\n" + "=" * 70)
        print("Setup incomplete. Fix database connection and try again.")
        print("=" * 70)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🎉 All systems ready! Phase 2 complete.")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run migrations: alembic upgrade head")
    print("3. Test LLM Manager: pytest tests/test_llm_manager.py -v")
    print()


if __name__ == "__main__":
    asyncio.run(main())
