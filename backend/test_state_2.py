import asyncio
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy.ext.asyncio import create_async_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.agents.content_creation_agent import build_content_creation_graph

async def main():
    db_url = 'postgresql+asyncpg://postgres:postgres123@localhost:5432/linkedin_agent'
    engine = create_async_engine(db_url)
    
    async with AsyncPostgresSaver(engine) as checkpointer:
        graph = build_content_creation_graph(checkpointer, None)
        config = {'configurable': {'thread_id': 'content_00000000-0000-0000-0000-000000000001_run_26581964c8704f52'}}
        state = await graph.aget_state(config)
        print('Final State error:', state.values.get('error'))
        print('Final State status:', state.values.get('status'))

if __name__ == '__main__':
    asyncio.run(main())
