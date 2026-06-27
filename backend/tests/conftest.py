"""Shared pytest configuration and fixtures.

Configuration:
- TestClient with raise_server_exceptions=False for error testing
- Proper dependency override cleanup
- Async test support
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client with proper exception handling.
    
    CRITICAL: raise_server_exceptions=False allows testing HTTP 500 responses.
    Without this, TestClient re-raises exceptions instead of returning 500 response.
    
    Reference: https://www.starlette.io/testclient/
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Automatically clean up FastAPI dependency overrides after each test.
    
    CRITICAL: Without this, dependency overrides leak between tests,
    causing unpredictable test failures.
    
    autouse=True means this runs for EVERY test automatically.
    """
    yield
    app.dependency_overrides.clear()


# ============================================================================
# Integration Test Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (slow, require real database)"
    )
    config.addinivalue_line(
        "markers",
        "manual: Manual tests (require human oversight, e.g. real LinkedIn API)"
    )
