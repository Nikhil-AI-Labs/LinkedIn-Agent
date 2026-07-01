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
    config = {'configurable': {'thread_id': 'content_00000000-0000-0000-0000-000000000001_run_280db3a22f57449b'}}
    state = await graph.aget_state(config)
    print('Status:', state.values.get('status'))
    print('Error:', state.values.get('error'))
    print('Approved:', state.values.get('approved'))
    print('Post ID:', state.values.get('post_id'))
    if state.values.get('error'):
        print('Full state:')
        pprint.pprint({k: v for k, v in state.values.items() if k in ['status','error','approved','final_content','post_id','draft_id']})

if __name__ == '__main__':
    asyncio.run(main())
