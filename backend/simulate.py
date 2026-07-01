import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.agents.content_creation_agent import build_content_creation_graph, start_content_creation, resume_content_creation
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

async def main():
    pool = AsyncConnectionPool("postgresql://postgres:postgres123@localhost:5432/linkedin_agent")
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres123@localhost:5432/linkedin_agent")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as db:
        thread_id = "test_simulate_001"
        print("Starting content creation...")
        state = await start_content_creation(
            user_id=1,
            thread_id=thread_id,
            intent="create_post",
            user_input="Make a post about AI.",
            messages=[],
            db=db,
            checkpointer=checkpointer
        )
        print("Status after start:", state.get("status"))
        
        print("\nSelecting draft...")
        state2 = await resume_content_creation(
            thread_id=thread_id,
            approved=True,
            selected_draft_id=1,
            user_edited_content=None,
            db=db,
            checkpointer=checkpointer
        )
        print("Status after select:", state2.get("status"))
        print("Final content after select:", state2.get("final_content")[:20] if state2.get("final_content") else None)
        
        print("\nApproving draft...")
        state3 = await resume_content_creation(
            thread_id=thread_id,
            approved=True,
            db=db,
            checkpointer=checkpointer
        )
        print("Status after approve:", state3.get("status"))
        print("Error after approve:", state3.get("error"))

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
