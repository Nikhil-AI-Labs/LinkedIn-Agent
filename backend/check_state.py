import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import json
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def main():
    pool = AsyncConnectionPool("postgresql://postgres:postgres123@localhost:5432/linkedin_agent")
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    
    from app.agents.content_creation_agent import build_content_creation_graph
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres123@localhost:5432/linkedin_agent")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as db:
        graph = build_content_creation_graph(checkpointer, db)
        config = {"configurable": {"thread_id": "content_00000000-0000-0000-0000-000000000001_run_97d322c444114e89"}}
        state = await graph.aget_state(config)
        
        history = []
        async for state_snapshot in graph.aget_state_history(config):
            history.append(state_snapshot)
        
        print(f"Total snapshots: {len(history)}")
        for i, snap in enumerate(reversed(history)):
            print(f"--- Snapshot {i} ---")
            print("Next:", snap.next)
            print("State:", snap.values.get("status"), "| final_content:", snap.values.get("final_content")[:20] if snap.values.get("final_content") else None)
            print("Error:", snap.values.get("error"))
        
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
