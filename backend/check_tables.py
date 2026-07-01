"""Check what tables exist in the database."""

import asyncio
from app.db.session import get_engine
from sqlalchemy import text

async def check_tables():
    """List all tables in the database."""
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        )
        tables = [row[0] for row in result]
        
        if tables:
            print("Existing tables:")
            for table in tables:
                print(f"  - {table}")
        else:
            print("No tables found in the database.")
        
        return tables

if __name__ == "__main__":
    tables = asyncio.run(check_tables())
