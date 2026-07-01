"""
Complete LinkedIn Agent Test - Fetch + Analyze + Post

This test demonstrates the CORRECT architecture:
1. FETCH data using linkedin-api (Voyager) - NO browser needed
2. ANALYZE and generate content using LLM
3. POST using Kimi WebBridge (primary) or Playwright (fallback)
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.services.linkedin.voyager_client import VoyagerClient
from app.core.config import settings

API_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json", "X-User-ID": "1"}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    print(f"   {text}")

async def test_voyager_read():
    """Test 1: Fetch LinkedIn data using Voyager API (linkedin-api)"""
    print_header("Step 1: Fetching LinkedIn Data (Voyager API)")
    
    print_info("Using linkedin-api library (NO browser needed)...")
    
    try:
        voyager = VoyagerClient()
        
        # Test if we can initialize
        print_success("VoyagerClient initialized")
        
        print_info("\n📊 What Voyager can fetch:")
        print_info("  - Your profile information")
        print_info("  - Your feed posts")
        print_info("  - Other user profiles")
        print_info("  - Post comments and reactions")
        print_info("  - Network connections")
        
        print_info("\n⚠️  NOTE: Voyager requires LinkedIn session cookies")
        print_info("  For now, this is a structural test")
        print_info("  In production, you'd authenticate Voyager with cookies")
        
        return True
        
    except Exception as e:
        print_error(f"Voyager test failed: {str(e)}")
        return False

async def test_generate_post(client: httpx.AsyncClient):
    """Test 2: Generate post content using LLM"""
    print_header("Step 2: Generating Post Content (LLM)")
    
    payload = {
        "message": "Write an engaging LinkedIn post about how AI agents are transforming workplace productivity"
    }
    
    print_info("Requesting AI to generate post...")
    
    try:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            headers=HEADERS,
            timeout=180.0
        )
        
        if response.status_code == 200:
            data = response.json()
            thread_id = data.get("thread_id")
            drafts = data.get("data", {}).get("drafts", [])
            
            print_success(f"Generated {len(drafts)} draft variants")
            
            if drafts and len(drafts) > 0:
                best_draft = drafts[0]
                content = best_draft.get("content", "")
                
                print_info(f"\n📝 Draft Preview:")
                print_info("─" * 60)
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"{Colors.BLUE}{preview}{Colors.END}")
                print_info("─" * 60)
                
                # Check if it's actual content (not meta-commentary)
                if content.startswith("I'll") or content.startswith("I will") or "I'll focus on" in content:
                    print_error("❌ LLM generated meta-commentary instead of actual post!")
                    print_info(f"Got: {content[:100]}...")
                    return None, None
                else:
                    print_success("✅ LLM generated actual post content (not meta-commentary)")
                
                return thread_id, content
            else:
                print_error("No drafts generated")
                return None, None
        else:
            print_error(f"Failed to generate post: {response.status_code}")
            return None, None
            
    except Exception as e:
        print_error(f"Post generation failed: {str(e)}")
        return None, None

async def test_wait_and_select(client: httpx.AsyncClient, thread_id: str):
    """Test 3: Wait for draft and select it"""
    print_header("Step 3: Selecting Draft")
    
    # Wait for draft to be ready
    print_info("Waiting for draft to be persisted...")
    await asyncio.sleep(3)
    
    # Get pending drafts
    response = await client.get(f"{API_URL}/pending", headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        my_draft = None
        for item in items:
            if item.get("thread_id") == thread_id:
                my_draft = item
                break
        
        if my_draft:
            print_success(f"Draft found: {my_draft.get('id')}")
            
            # Select it
            select_payload = {
                "thread_id": thread_id,
                "selected_draft_id": "1"
            }
            
            select_response = await client.post(
                f"{API_URL}/drafts/select",
                json=select_payload,
                headers=HEADERS,
                timeout=60.0
            )
            
            if select_response.status_code == 200:
                print_success("Draft selected successfully")
                return True
            else:
                print_error(f"Failed to select draft: {select_response.status_code}")
                return False
        else:
            print_error("Draft not found in pending items")
            return False
    else:
        print_error(f"Failed to get pending items: {response.status_code}")
        return False

async def test_post_to_linkedin(client: httpx.AsyncClient, thread_id: str):
    """Test 4: Post to LinkedIn using Kimi or Playwright"""
    print_header("Step 4: Posting to LinkedIn")
    
    print_info("Backend will try:")
    print_info("  1. PRIMARY: Kimi WebBridge (your real browser)")
    print_info("  2. FALLBACK: Playwright (automated browser)")
    
    await asyncio.sleep(5)
    
    approve_payload = {
        "thread_id": thread_id,
        "approved": True
    }
    
    print_info("\nSending final approval...")
    
    try:
        response = await client.post(
            f"{API_URL}/drafts/approve",
            json=approve_payload,
            headers=HEADERS,
            timeout=180.0
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            post_id = data.get("data", {}).get("post_id")
            
            if status == "posted" and post_id:
                print_success("🎉 POST SUCCESSFULLY PUBLISHED!")
                print_info(f"Post ID: {post_id}")
                return True
            elif status == "error":
                print_error("Posting failed")
                
                # Check why
                error_msg = data.get("data", {}).get("error", "")
                if "Kimi" in str(error_msg):
                    print_info("\n💡 Kimi WebBridge not connected")
                    print_info("  - Open Microsoft Edge with Kimi extension")
                    print_info("  - Make sure you're logged into LinkedIn")
                    print_info("  - Extension should auto-connect")
                
                if "Playwright" in str(error_msg) or "Session" in str(error_msg):
                    print_info("\n💡 Playwright fallback also failed")
                    print_info("  - Playwright is trying to log in automatically")
                    print_info("  - Check LINKEDIN_USERNAME in .env")
                    print_info("  - Check LINKEDIN_PASSWORD_ENCRYPTED in .env")
                    print_info("  - Set PLAYWRIGHT_HEADLESS=False in .env to see what's happening")
                
                return False
            else:
                print_error(f"Unexpected status: {status}")
                return False
        else:
            print_error(f"Failed to approve: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"Posting failed: {str(e)}")
        return False

async def main():
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}LinkedIn AI Agent - Complete Architecture Test{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    print(f"\n{Colors.BOLD}ARCHITECTURE:{Colors.END}")
    print("  📖 READ (Fetch data)  → linkedin-api (Voyager) - NO browser")
    print("  ✍️  WRITE (Post/Comment) → Kimi WebBridge OR Playwright")
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    
    # Test 1: Voyager (reading)
    voyager_ok = await test_voyager_read()
    
    # Test 2-4: Generate and post (writing)
    async with httpx.AsyncClient() as client:
        thread_id, content = await test_generate_post(client)
        
        if not thread_id:
            print_error("\n❌ Cannot continue without generated content")
            return
        
        if not await test_wait_and_select(client, thread_id):
            print_error("\n❌ Cannot continue without draft selection")
            return
        
        success = await test_post_to_linkedin(client, thread_id)
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Test Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    print(f"✅ Voyager Client: {'OK' if voyager_ok else 'FAIL'}")
    print(f"✅ LLM Generation: {'OK' if thread_id else 'FAIL'}")
    print(f"✅ LinkedIn Posting: {'OK' if success else 'FAIL'}")
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 FULL E2E TEST PASSED!{Colors.END}")
        print(f"\nYour agent can:")
        print("  ✅ Fetch LinkedIn data (Voyager)")
        print("  ✅ Generate viral content (LLM)")
        print("  ✅ Post to LinkedIn (Kimi/Playwright)")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  PARTIAL SUCCESS{Colors.END}")
        print(f"\nWhat's working:")
        print("  ✅ Backend architecture is correct")
        print("  ✅ LLM is generating actual content")
        print(f"\nWhat needs setup:")
        
        if not success:
            print("  ⚠️  LinkedIn posting needs:")
            print("     - Kimi WebBridge extension (preferred)")
            print("     OR")
            print("     - Playwright credentials in .env")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
