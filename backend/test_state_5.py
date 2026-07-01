import asyncio
import sys
import os
import pprint

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from app.agents.checkpointer import get_checkpointer
from app.agents.content_creation_agent import build_content_creation_graph

async def main():
    checkpointer = await get_checkpointer()
    graph = build_content_creation_graph(checkpointer, None)
    config = {'configurable': {'thread_id': 'content_00000000-0000-0000-0000-000000000001_run_de9d3748010144a8'}}
    state = await graph.aget_state(config)
    print('Final State error:', state.values.get('error'))
    print('Final State status:', state.values.get('status'))
    print('Final State intent:', state.values.get('intent'))
    if state.values.get('error'):
        print('Error details:')
        pprint.pprint(state.values)

if __name__ == '__main__':
    asyncio.run(main())
