import asyncio
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath('.'))

from app.services.linkedin.browser_poster import PlaywrightPoster
from app.core.config import settings

async def main():
    print("Browser Provider:", settings.browser_provider)
    poster = PlaywrightPoster()
    print("Testing Playwright connection...")
    try:
        result = await poster.validate_session(trace_id="test_trace")
        print("Validate session result:", result.success, result.data, result.error)
    except Exception as e:
        print("Exception:", str(e))

if __name__ == '__main__':
    asyncio.run(main())
