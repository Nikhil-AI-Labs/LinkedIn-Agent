import asyncio
import sys
import os
import pprint

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy import select, text
from app.db.session import get_session_maker
from app.db.models.post_draft import PostDraft

async def main():
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(PostDraft).order_by(PostDraft.created_at.desc()).limit(5)
        )
        drafts = result.scalars().all()
        for d in drafts:
            print(f"Draft {d.id} | status={d.status} | created={d.created_at} | graph_run_id={d.graph_run_id}")

if __name__ == '__main__':
    asyncio.run(main())
