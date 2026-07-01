import asyncio
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from app.services.linkedin.browser_poster import KimiBridgePoster

async def main():
    poster = KimiBridgePoster()
    print("Testing Kimi WebBridge connection...")
    result = await poster.validate_session(trace_id="test_trace")
    print("Validate session result:", result.success, result.data, result.error)
    if result.success:
        print("Creating mock post...")
        post_result = await poster.create_post(
            user_id="test",
            content="Testing Kimi WebBridge from the backend script! This is a test post.",
            trace_id="test_trace"
        )
        print("Create post result:", post_result.success, post_result.data, post_result.error)

if __name__ == '__main__':
    asyncio.run(main())
