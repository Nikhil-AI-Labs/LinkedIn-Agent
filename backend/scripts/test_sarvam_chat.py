"""Standalone Sarvam API test script.

Run this before pytest to verify Sarvam integration works.
Usage: python scripts/test_sarvam_chat.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from sarvamai import AsyncSarvamAI
    SDK_TYPE = "native"
except ImportError:
    from openai import AsyncOpenAI
    SDK_TYPE = "openai"

from dotenv import load_dotenv

# Load .env from project root
env_file = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_file)


async def main():
    print("=" * 70)
    print("Sarvam AI Chat API Test")
    print("=" * 70)
    print()

    # Get config from environment
    api_key = os.getenv("SARVAM_API_KEY")
    model = os.getenv("SARVAM_MODEL", "sarvam-30b")

    if not api_key:
        print("❌ ERROR: SARVAM_API_KEY not found in environment")
        sys.exit(1)

    print(f"✓ API Key: {api_key[:10]}...")
    print(f"✓ Model: {model}")
    print(f"✓ SDK Type: {SDK_TYPE}")
    print()

    # Create client
    if SDK_TYPE == "native":
        client = AsyncSarvamAI(
            api_subscription_key=api_key,
            timeout=60.0,
        )
    else:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.sarvam.ai/v1",
            timeout=60.0,
        )

    # Test request
    print("📤 Sending test request...")
    print("   Messages:")
    print("     - system: You are concise.")
    print("     - user: Say hello in one sentence.")
    print()

    try:
        response = await client.chat.completions(
            model=model,
            messages=[
                {"role": "system", "content": "You are concise."},
                {"role": "user", "content": "Say hello in one sentence."},
            ],
            temperature=0.2,
            max_tokens=50,
        )

        print("✅ SUCCESS!")
        print()
        print("📥 Response:")
        
        # Debug: Print full response
        print(f"   Raw response type: {type(response)}")
        print(f"   Raw response: {response}")
        print()
        
        # Handle different response structures
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            print(f"   Choice type: {type(choice)}")
            print(f"   Choice: {choice}")
            if hasattr(choice, 'message'):
                message = choice.message
                print(f"   Message: {message}")
                # Check for reasoning_content first (sarvam-105b reasoning model)
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    content = message.reasoning_content
                    print(f"   Using reasoning_content (reasoning model)")
                elif message.content:
                    content = message.content
                    print(f"   Using content (standard model)")
                else:
                    content = ""
            else:
                content = str(choice)
        else:
            content = str(response)
        
        print(f"   Content: {content if content else '(empty response)'}")
        print(f"   Model: {response.model if hasattr(response, 'model') else model}")
        if hasattr(response, 'usage') and response.usage:
            print(f"   Tokens: {response.usage.prompt_tokens} in, {response.usage.completion_tokens} out")
        print()
        
        if not content:
            print("⚠️  WARNING: Response content is empty!")
            print("   This may indicate an issue with the model or prompt.")
            print("   Try using a different model like sarvam-30b.")
            print()
        
        print("=" * 70)
        print("🎉 Sarvam API integration working correctly!")
        print("=" * 70)

    except Exception as e:
        print("❌ FAILED!")
        print()
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Try to get response body
        if hasattr(e, "response") and e.response is not None:
            try:
                print()
                print("Response body:")
                print(e.response.text)
            except Exception:
                pass
        
        print()
        print("=" * 70)
        print("Troubleshooting:")
        print("1. Check if SARVAM_API_KEY is valid")
        print("2. Check if SARVAM_MODEL is correct (try 'sarvam-30b' or 'sarvam-105b')")
        print("3. Install Sarvam SDK: pip install sarvamai")
        print("4. Check Sarvam API docs: https://docs.sarvam.ai")
        print("=" * 70)
        sys.exit(1)
    finally:
        if hasattr(client, 'close'):
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
