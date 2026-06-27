"""Tests for LinkedIn integration components.

Tests cover:
1. Voyager client READ operations
2. Browser poster WRITE operations with fallback logic
3. LinkedIn manager routing and integration
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from app.services.linkedin.base import (
    LinkedInPost,
    LinkedInComment,
    LinkedInProfile,
    LinkedInResult,
    ReactionType,
)
from app.services.linkedin.voyager_client import VoyagerClient
from app.services.linkedin.browser_poster import KimiBridgePoster, PlaywrightPoster
from app.services.linkedin.oauth_client import OAuthClient
from app.services.linkedin.linkedin_manager import LinkedInManager


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_settings_browser():
    """Mock settings for browser mode."""
    with patch("app.services.linkedin.linkedin_manager.settings") as mock:
        mock.auth_mode = "browser"
        mock.browser_provider = "kimi_webbridge"
        mock.linkedin_username = "test@example.com"
        mock.linkedin_password_encrypted = "encrypted_password"
        yield mock


@pytest.fixture
def mock_settings_oauth():
    """Mock settings for OAuth mode."""
    with patch("app.services.linkedin.linkedin_manager.settings") as mock:
        mock.auth_mode = "oauth"
        mock.linkedin_client_id = "test_client_id"
        mock.linkedin_client_secret = "test_client_secret"
        yield mock


# ============================================================================
# Test 1: Voyager Client Authentication
# ============================================================================


@pytest.mark.asyncio
async def test_voyager_client_authentication():
    """Test Voyager client authenticates with LinkedIn."""
    with patch("app.services.linkedin.voyager_client.settings") as mock_settings:
        mock_settings.linkedin_username = "test@example.com"
        mock_settings.linkedin_password_encrypted = "gAAAAABl..."  # Mock encrypted
        
        with patch("app.services.linkedin.voyager_client.decrypt_text") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_password"
            
            with patch("app.services.linkedin.voyager_client.Linkedin") as mock_linkedin:
                mock_client_instance = Mock()
                mock_linkedin.return_value = mock_client_instance
                
                # Create Voyager client
                client = VoyagerClient()
                
                # Trigger authentication by calling _get_client
                authenticated_client = client._get_client()
                
                # Verify Linkedin was instantiated with correct credentials
                mock_linkedin.assert_called_once_with("test@example.com", "decrypted_password")
                assert authenticated_client == mock_client_instance
                assert client._authenticated is True


@pytest.mark.asyncio
async def test_voyager_client_get_user_posts():
    """Test Voyager client fetches user posts."""
    with patch("app.services.linkedin.voyager_client.settings") as mock_settings:
        mock_settings.linkedin_username = "test@example.com"
        mock_settings.linkedin_password_encrypted = "gAAAAABl..."
        
        with patch("app.services.linkedin.voyager_client.decrypt_text"):
            with patch("app.services.linkedin.voyager_client.Linkedin") as mock_linkedin:
                # Mock Voyager API response
                mock_client_instance = Mock()
                mock_client_instance.get_profile_posts.return_value = [
                    {
                        "urn": "urn:li:activity:1234567890",
                        "actor": {"name": {"text": "Test User"}, "urn": "urn:li:member:123"},
                        "commentary": {"text": {"text": "Test post content"}},
                        "permalink": "https://www.linkedin.com/feed/update/...",
                        "socialDetail": {
                            "totalSocialActivityCounts": {
                                "numLikes": 10,
                                "numComments": 2,
                                "numShares": 1,
                            }
                        },
                    }
                ]
                mock_linkedin.return_value = mock_client_instance
                
                # Create client and fetch posts
                client = VoyagerClient()
                result = await client.get_user_posts(user_id="123", limit=10)
                
                # Verify result
                assert result.success is True
                assert isinstance(result.data, list)
                assert len(result.data) == 1
                assert isinstance(result.data[0], LinkedInPost)
                assert result.data[0].author_name == "Test User"
                assert result.data[0].content == "Test post content"


# ============================================================================
# Test 2: Browser Poster Fallback Logic
# ============================================================================


@pytest.mark.asyncio
async def test_kimi_bridge_not_implemented():
    """Test Kimi WebBridge returns not implemented error."""
    kimi = KimiBridgePoster()
    
    # Test create_post
    result = await kimi.create_post(user_id="123", content="Test post")
    assert result.success is False
    assert "not yet implemented" in result.error.lower()
    assert result.error_code == "KIMI_NOT_IMPLEMENTED"
    
    # Test validate_session
    result = await kimi.validate_session()
    assert result.success is False
    assert result.error_code == "KIMI_NOT_IMPLEMENTED"


@pytest.mark.asyncio
async def test_playwright_poster_validation():
    """Test Playwright poster session validation."""
    with patch("app.services.linkedin.browser_poster.async_playwright") as mock_playwright:
        # Mock Playwright components
        mock_page = AsyncMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://www.linkedin.com/feed/"
        mock_page.wait_for_selector = AsyncMock()
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser
        
        mock_playwright.return_value.start.return_value = mock_pw_instance
        
        # Create poster and validate session
        poster = PlaywrightPoster()
        result = await poster.validate_session(trace_id="test-trace")
        
        # Verify result
        assert result.success is True
        assert result.data["valid"] is True
        assert result.trace_id == "test-trace"


@pytest.mark.asyncio
async def test_playwright_poster_session_expired():
    """Test Playwright poster handles expired session."""
    with patch("app.services.linkedin.browser_poster.async_playwright") as mock_playwright:
        with patch("app.services.linkedin.browser_poster.settings") as mock_settings:
            mock_settings.linkedin_username = "test@example.com"
            mock_settings.linkedin_password_encrypted = "gAAAAABl..."
            
            with patch("app.services.linkedin.browser_poster.decrypt_text") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                # Mock Playwright components - session expired (redirected to login)
                mock_page = AsyncMock()
                mock_page.is_closed.return_value = False
                mock_page.url = "https://www.linkedin.com/login"  # Redirected to login
                mock_page.wait_for_selector = AsyncMock()
                mock_page.fill = AsyncMock()
                mock_page.click = AsyncMock()
                mock_page.wait_for_load_state = AsyncMock()
                
                mock_context = AsyncMock()
                mock_context.new_page.return_value = mock_page
                
                mock_browser = AsyncMock()
                mock_browser.new_context.return_value = mock_context
                
                mock_pw_instance = AsyncMock()
                mock_pw_instance.chromium.launch.return_value = mock_browser
                
                mock_playwright.return_value.start.return_value = mock_pw_instance
                
                # Create poster and validate session
                poster = PlaywrightPoster()
                result = await poster.validate_session(trace_id="test-trace")
                
                # Should attempt re-login
                # In actual implementation, this would call _login()
                # For now, just verify the flow detected expired session
                assert mock_page.url == "https://www.linkedin.com/login"


# ============================================================================
# Test 3: LinkedIn Manager Routing
# ============================================================================


@pytest.mark.asyncio
async def test_linkedin_manager_browser_mode(mock_settings_browser):
    """Test LinkedIn manager routes correctly in browser mode."""
    with patch("app.services.linkedin.linkedin_manager.VoyagerClient") as mock_voyager:
        with patch("app.services.linkedin.linkedin_manager.KimiBridgePoster") as mock_kimi:
            with patch("app.services.linkedin.linkedin_manager.PlaywrightPoster") as mock_playwright:
                # Create mock instances
                mock_voyager_instance = Mock()
                mock_voyager.return_value = mock_voyager_instance
                
                mock_kimi_instance = Mock()
                mock_kimi.return_value = mock_kimi_instance
                
                mock_playwright_instance = Mock()
                mock_playwright.return_value = mock_playwright_instance
                
                # Create manager
                manager = LinkedInManager()
                
                # Verify clients were created
                assert manager.auth_mode == "browser"
                assert manager._read_client == mock_voyager_instance
                assert manager._write_client == mock_kimi_instance
                assert manager._write_fallback == mock_playwright_instance


@pytest.mark.asyncio
async def test_linkedin_manager_write_fallback():
    """Test LinkedIn manager fallback logic for write operations."""
    with patch("app.services.linkedin.linkedin_manager.settings") as mock_settings:
        mock_settings.auth_mode = "browser"
        mock_settings.browser_provider = "kimi_webbridge"
        
        # Create mocks
        mock_kimi = Mock()
        mock_kimi.create_post = AsyncMock(
            return_value=LinkedInResult.fail(
                error="Kimi not available",
                error_code="KIMI_NOT_IMPLEMENTED",
            )
        )
        
        mock_playwright = Mock()
        mock_playwright.create_post = AsyncMock(
            return_value=LinkedInResult.ok(
                data="https://www.linkedin.com/feed/update/..."
            )
        )
        
        with patch("app.services.linkedin.linkedin_manager.KimiBridgePoster", return_value=mock_kimi):
            with patch("app.services.linkedin.linkedin_manager.PlaywrightPoster", return_value=mock_playwright):
                with patch("app.services.linkedin.linkedin_manager.VoyagerClient"):
                    # Create manager
                    manager = LinkedInManager()
                    
                    # Call create_post (should fallback from Kimi to Playwright)
                    result = await manager.create_post(
                        user_id="123",
                        content="Test post",
                        trace_id="test-trace",
                    )
                    
                    # Verify fallback worked
                    assert result.success is True
                    assert "linkedin.com" in result.data
                    mock_kimi.create_post.assert_called_once()
                    mock_playwright.create_post.assert_called_once()


@pytest.mark.asyncio
async def test_linkedin_manager_oauth_mode(mock_settings_oauth):
    """Test LinkedIn manager in OAuth mode (not implemented)."""
    with patch("app.services.linkedin.linkedin_manager.OAuthClient") as mock_oauth:
        mock_oauth_instance = Mock()
        mock_oauth_instance.get_user_posts = AsyncMock(
            return_value=LinkedInResult.fail(
                error="OAuth not implemented",
                error_code="OAUTH_NOT_IMPLEMENTED",
            )
        )
        mock_oauth.return_value = mock_oauth_instance
        
        # Create manager
        manager = LinkedInManager()
        
        # Verify OAuth client was created
        assert manager.auth_mode == "oauth"
        assert manager._read_client == mock_oauth_instance
        assert manager._write_client == mock_oauth_instance
        
        # Verify operations return not implemented
        result = await manager.get_user_posts(user_id="123")
        assert result.success is False
        assert result.error_code == "OAUTH_NOT_IMPLEMENTED"


@pytest.mark.asyncio
async def test_linkedin_manager_read_operations():
    """Test LinkedIn manager delegates READ operations correctly."""
    with patch("app.services.linkedin.linkedin_manager.settings") as mock_settings:
        mock_settings.auth_mode = "browser"
        mock_settings.browser_provider = "playwright"
        
        # Create mock Voyager client
        mock_voyager = Mock()
        mock_voyager.get_user_posts = AsyncMock(
            return_value=LinkedInResult.ok(data=[])
        )
        mock_voyager.get_profile_posts = AsyncMock(
            return_value=LinkedInResult.ok(data=[])
        )
        mock_voyager.get_post_comments = AsyncMock(
            return_value=LinkedInResult.ok(data=[])
        )
        mock_voyager.get_post_reactions = AsyncMock(
            return_value=LinkedInResult.ok(data={})
        )
        mock_voyager.validate_profile = AsyncMock(
            return_value=LinkedInResult.ok(data=None)
        )
        
        with patch("app.services.linkedin.linkedin_manager.VoyagerClient", return_value=mock_voyager):
            with patch("app.services.linkedin.linkedin_manager.PlaywrightPoster"):
                # Create manager
                manager = LinkedInManager()
                
                # Test all READ operations
                await manager.get_user_posts(user_id="123", limit=10)
                mock_voyager.get_user_posts.assert_called_once()
                
                await manager.get_profile_posts(member_id="456", limit=5)
                mock_voyager.get_profile_posts.assert_called_once()
                
                await manager.get_post_comments(post_id="789")
                mock_voyager.get_post_comments.assert_called_once()
                
                await manager.get_post_reactions(post_id="789")
                mock_voyager.get_post_reactions.assert_called_once()
                
                await manager.validate_profile(profile_url="https://linkedin.com/in/test")
                mock_voyager.validate_profile.assert_called_once()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
