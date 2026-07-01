"""Create missing database tables."""

import asyncio
import sys
from app.db.session import get_engine
from sqlalchemy import text

async def create_chat_history_table():
    """Create the chat_history table."""
    engine = get_engine()
    
    sql_statements = [
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            role VARCHAR(50) NOT NULL,
            message_text TEXT NOT NULL,
            language VARCHAR(10),
            source_mode VARCHAR(50),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            
            CONSTRAINT fk_chat_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_chat_history_user_id ON chat_history(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_chat_history_created_at ON chat_history(created_at DESC);
        """
    ]
    
    try:
        async with engine.begin() as conn:
            print("Creating chat_history table...")
            
            for i, sql in enumerate(sql_statements, 1):
                print(f"  Executing statement {i}/{len(sql_statements)}...")
                await conn.execute(text(sql))
            
            print("✓ chat_history table created successfully!")
            
            # Verify
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='chat_history'")
            )
            if result.fetchone():
                print("✓ Table verified in database")
            else:
                print("✗ Table not found after creation")
                return False
            
        return True
            
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_chat_history_table())
    sys.exit(0 if success else 1)
