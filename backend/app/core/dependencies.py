"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session as _get_db_session
from app.agents.checkpointer import get_global_checkpointer
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Database Dependency
# ============================================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in _get_db_session():
        yield session


# ============================================================================
# User Authentication
# ============================================================================

async def get_current_user_id(
    x_user_id: int = Header(default=1, alias="X-User-ID"),
) -> str:
    """Get current user ID from header.
    
    For MVP, we use a simple header-based auth.
    In production, replace with proper JWT/OAuth validation.
    
    Returns UUID string formatted from integer ID (e.g., 1 -> 00000000-0000-0000-0000-000000000001)
    """
    if x_user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
        )
    # Convert integer to UUID format (pad with zeros)
    uuid_str = f"{x_user_id:032x}"  # Convert to 32-char hex string
    # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    return f"{uuid_str[:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"


# ============================================================================
# Checkpointer Dependency
# ============================================================================

def get_checkpointer():
    """Get the global LangGraph checkpointer."""
    return get_global_checkpointer()


# ============================================================================
# Trace ID
# ============================================================================

async def get_trace_id(
    x_trace_id: str | None = Header(None, alias="X-Trace-ID"),
) -> str:
    """Get or generate trace ID for request tracking."""
    if x_trace_id:
        return x_trace_id
    
    # Generate new trace ID if not provided
    import uuid
    return str(uuid.uuid4())
