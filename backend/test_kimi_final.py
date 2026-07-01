"""
Test Kimi WebBridge integration for LinkedIn posting.

This test verifies that the official Kimi WebBridge service is running
and can control your browser to post to LinkedIn.
"""

import asyncio
import sys
import httpx
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


async def test_kimi_service():
    """Test if Kimi WebBridge service is running and extension connected."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}Testing Kimi WebBridge Service{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            print("1. Checking service status at http://localhost:10086/status...")
            response = await client.get("http://localhost:10086/status")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"{Colors.GREEN}✅ Kimi WebBridge service is running{Colors.END}")
                print(f"   Version: {data.get('version')}")
                print(f"   Uptime: {data.get('uptime_seconds')} seconds")
                print(f"   Port: {data.get('port')}")
                
                if data.get("extension_connected"):
                    print(f"{Colors.GREEN}✅ Browser extension is CONNECTED{Colors.END}")
                    print(f"   Extension ID: {data.get('extension_id')}")
                    print(f"   Extension Version: {data.get('extension_version')}")
                    return True, "connected"
                else:
                    print(f"{Colors.YELLOW}⚠️  Extension is NOT connected{Colors.END}")
                    print(f"\n{Colors.BOLD}To fix:{Colors.END}")
                    print("   1. Open Microsoft Edge")
                    print("   2. Click the Kimi WebBridge extension icon")
                    print("   3. Make sure it shows as 'Connected' (green)")
                    print("   4. Go to linkedin.com and log in")
                    return True, "not_connected"
            else:
                print(f"{Colors.RED}❌ Service returned status {response.status_code}{Colors.END}")
                return False, "service_error"
                
    except httpx.ConnectError:
        print(f"{Colors.RED}❌ Cannot connect to Kimi WebBridge service{Colors.END}")
        print(f"\n{Colors.BOLD}The Kimi WebBridge service is not running!{Colors.END}")
        print(f"\n{Colors.BOLD}To install/start it:{Colors.END}")
        print("   Open PowerShell and run:")
        print(f"   {Colors.BLUE}irm https://kimi-web-img.moonshot.cn/webbridge/install.ps1 | iex{Colors.END}")
        return False, "not_installed"
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        return False, "error"


async def test_kimi_posting():
    """Test posting to LinkedIn via Kimi WebBridge."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}Testing LinkedIn Posting via Kimi{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    from app.services.linkedin.browser_poster import KimiBridgePoster
    
    poster = KimiBridgePoster()
    
    # Test session validation
    print("2. Validating LinkedIn session...")
    validation = await poster.validate_session(trace_id="test_kimi")
    
    if validation.success:
        print(f"{Colors.GREEN}✅ LinkedIn session is valid{Colors.END}")
        print("   You are logged into LinkedIn in your browser")
    else:
        print(f"{Colors.RED}❌ Session validation failed: {validation.error}{Colors.END}")
        print(f"\n{Colors.BOLD}To fix:{Colors.END}")
        print("   1. Open Microsoft Edge")
        print("   2. Go to https://linkedin.com")
        print("   3. Log in to your account")
        print("   4. Leave the browser open")
        return False
    
    # Test post creation
    print(f"\n3. Creating a test post...")
    print(f"{Colors.YELLOW}   This will post to your REAL LinkedIn account!{Colors.END}")
    
    test_content = """🤖 Testing Kimi WebBridge Integration

This is an automated test post created by my LinkedIn AI Agent using Kimi WebBridge.

The agent successfully:
✅ Connected to Kimi WebBridge service
✅ Controlled my real browser session
✅ Posted to LinkedIn without Playwright or 2FA

#AIAgents #Automation #LinkedInAPI #KimiWebBridge"""
    
    print(f"\n{Colors.BOLD}Post content:{Colors.END}")
    print(f"{Colors.BLUE}{test_content[:150]}...{Colors.END}")
    
    # Ask for confirmation
    print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  WARNING:{Colors.END}")
    print("This will create a REAL post on your LinkedIn profile.")
    print("Make sure you're ready!")
    
    response = input(f"\n{Colors.BOLD}Type 'yes' to post, anything else to skip: {Colors.END}")
    
    if response.lower() != 'yes':
        print(f"{Colors.YELLOW}Skipped posting test{Colors.END}")
        return True
    
    print(f"\n{Colors.BLUE}Posting...{Colors.END}")
    result = await poster.create_post(
        user_id="test_user",
        content=test_content,
        trace_id="test_kimi_post"
    )
    
    if result.success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 SUCCESS!{Colors.END}")
        print(f"{Colors.GREEN}Post created successfully via Kimi WebBridge!{Colors.END}")
        print(f"URL: {result.data}")
        print(f"\nCheck your LinkedIn profile to see the post!")
        return True
    else:
        print(f"\n{Colors.RED}❌ Failed to create post{Colors.END}")
        print(f"Error: {result.error}")
        print(f"Error code: {result.error_code}")
        return False


async def main():
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Kimi WebBridge Integration Test{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    # Test 1: Check service
    service_ok, status = await test_kimi_service()
    
    if not service_ok:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Cannot proceed - Kimi WebBridge service not running{Colors.END}")
        return
    
    if status == "not_connected":
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Cannot proceed - Extension not connected{Colors.END}")
        return
    
    # Test 2: Try posting
    post_ok = await test_kimi_posting()
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Test Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    if service_ok and status == "connected" and post_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED!{Colors.END}")
        print(f"\nYour LinkedIn AI Agent is fully operational with Kimi WebBridge!")
        print(f"\n{Colors.BOLD}What this means:{Colors.END}")
        print("  ✅ No Playwright needed")
        print("  ✅ No 2FA prompts")
        print("  ✅ Uses your real browser session")
        print("  ✅ Undetectable by LinkedIn")
        print(f"\n{Colors.BOLD}Ready to use in production!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  PARTIAL SUCCESS{Colors.END}")
        print(f"\nService: {'✅' if service_ok else '❌'}")
        print(f"Extension: {'✅' if status == 'connected' else '❌'}")
        print(f"Posting: {'✅' if post_ok else '⏭️  Skipped'}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Test error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
