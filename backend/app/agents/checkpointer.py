"""PostgreSQL checkpointer for LangGraph state persistence.

LangGraph's PostgresSaver creates and manages its own checkpoint tables.
DO NOT create duplicate checkpoint models in our schema.
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_checkpointer() -> AsyncPostgresSaver:
    """Get or create AsyncPostgresSaver for graph state persistence.
    
    The AsyncPostgresSaver handles its own table creation and management.
    It creates these tables automatically:
    - checkpoints
    - checkpoint_blobs
    - checkpoint_writes
    
    Do not create these tables manually in Alembic.
    """
    # AsyncPostgresSaver uses psycopg (not asyncpg)
    # Convert database_url from postgresql+asyncpg:// to postgresql://
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # CRITICAL: Keep the context manager alive to maintain connection pool
    # Store it globally so it doesn't get garbage collected
    global _checkpointer_context
    
    # Create the context manager
    _checkpointer_context = AsyncPostgresSaver.from_conn_string(db_url)
    
    # Enter the context manager to get the actual checkpointer instance
    checkpointer = await _checkpointer_context.__aenter__()
    
    # Setup creates the necessary tables
    await checkpointer.setup()
    
    logger.info("postgres_checkpointer_initialized", url=db_url.split("@")[1])
    
    return checkpointer


# Singleton instances
_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_context = None  # Keep context manager alive


async def init_checkpointer() -> None:
    """Initialize the global checkpointer singleton."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = await get_checkpointer()
        logger.info("global_checkpointer_initialized")


def get_global_checkpointer() -> AsyncPostgresSaver:
    """Get the global checkpointer singleton.
    
    Raises ValueError if not initialized.
    Call init_checkpointer() first, typically in app startup.
    """
    if _checkpointer is None:
        raise ValueError(
            "Checkpointer not initialized. Call init_checkpointer() first."
        )
    return _checkpointer
