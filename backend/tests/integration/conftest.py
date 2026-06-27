"""Integration test fixtures and configuration.

Provides real database and checkpointer instances for integration testing.
"""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from langgraph.checkpoint.postgres import PostgresSaver

from app.db.base import Base
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine.
    
    Uses a separate test database to avoid polluting production data.
    """
    # Use separate test database
    test_db_url = settings.DATABASE_URL.replace("linkedin_agent", "linkedin_agent_test")
    
    engine = create_async_engine(test_db_url, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup - drop all tables after test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session.
    
    Each test gets a fresh session that rolls back after the test.
    """
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
def real_checkpointer():
    """Create real PostgresSaver for integration tests.
    
    This checkpointer uses a separate test database and persists state
    across graph executions to prove interrupt/resume functionality.
    """
    # Convert asyncpg URL to psycopg format for PostgresSaver
    test_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://"
    ).replace("linkedin_agent", "linkedin_agent_test")
    
    checkpointer = PostgresSaver.from_conn_string(test_db_url)
    checkpointer.setup()
    
    yield checkpointer
    
    # Note: cleanup of checkpoint tables is handled by dropping the test database


@pytest.fixture
async def test_user(test_db_session):
    """Create a test user for integration tests."""
    from app.db.models import User
    
    user = User(
        email="test@example.com",
        hashed_password="not_a_real_hash",
        linkedin_member_id="test_member_123",
        is_active=True,
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user
