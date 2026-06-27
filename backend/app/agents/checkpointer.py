"""PostgreSQL checkpointer for LangGraph state persistence.

LangGraph's PostgresSaver creates and manages its own checkpoint tables.
DO NOT create duplicate checkpoint models in our schema.
"""

from langgraph.checkpoint.postgres import PostgresSaver
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_checkpointer() -> PostgresSaver:
    """Get or create PostgresSaver for graph state persistence.
    
    The PostgresSaver handles its own table creation and management.
    It creates these tables automatically:
    - checkpoints
    - checkpoint_blobs
    - checkpoint_writes
    
    Do not create these tables manually in Alembic.
    """
    # Convert asyncpg URL to psycopg2 format for PostgresSaver
    # asyncpg: postgresql+asyncpg://...
    # psycopg2: postgresql://...
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    checkpointer = PostgresSaver.from_conn_string(db_url)
    
    # Setup creates tables if they don't exist
    checkpointer.setup()
    
    logger.info("postgres_checkpointer_initialized", url=db_url.split("@")[1])
    
    return checkpointer


# Singleton instance
_checkpointer: PostgresSaver | None = None


def init_checkpointer() -> None:
    """Initialize the global checkpointer singleton."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = get_checkpointer()
        logger.info("global_checkpointer_initialized")


def get_global_checkpointer() -> PostgresSaver:
    """Get the global checkpointer singleton.
    
    Raises ValueError if not initialized.
    Call init_checkpointer() first, typically in app startup.
    """
    if _checkpointer is None:
        raise ValueError(
            "Checkpointer not initialized. Call init_checkpointer() first."
        )
    return _checkpointer
