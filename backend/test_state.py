import asyncio
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy.ext.asyncio import create_async_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.agents.content_creation_agent import build_content_creation_graph
from app.core.config import settings

async def main():
    engine = create_async_engine(str(settings.database_url).replace('postgresql://', 'postgresql+asyncpg://'))
    
    async with AsyncPostgresSaver.from_conn_string(str(settings.database_url).replace('postgresql://', 'postgresql+asyncpg://')) as checkpointer:
        graph = build_content_creation_graph(checkpointer, None)
        config = {'configurable': {'thread_id': 'content_00000000-0000-0000-0000-000000000001_run_26581964c8704f52'}}
        state = await graph.aget_state(config)
        print('Final State:')
        import pprint
        pprint.pprint(state.values)

if __name__ == '__main__':
    asyncio.run(main())
