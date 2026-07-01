"""
Test Kimi WebBridge Connection

This script tests if the Kimi WebBridge extension is properly connected.
"""

import asyncio
import websockets
import json
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_kimi_connection():
    """Test connection to Kimi WebBridge server."""
    
    print("🔍 Testing Kimi WebBridge Connection...")
    print("=" * 60)
    
    # Check if server is running
    print("\n1. Checking if backend server is running on port 10086...")
    
    try:
        async with websockets.connect(
            "ws://127.0.0.1:10086/ws"
        ) as websocket:
            print("   ✅ Connected to ws://127.0.0.1:10086/ws")
            
            # Send hello message
            print("\n2. Sending hello message...")
            hello_msg = {
                "type": "hello",
                "payload": {
                    "clientType": "test_script",
                    "version": "1.0.0"
                }
            }
            await websocket.send(json.dumps(hello_msg))
            print("   ✅ Hello message sent")
            
            # Wait for response
            print("\n3. Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f"   ✅ Received response: {data.get('type')}")
                
                if data.get('type') == 'hello_ack':
                    print("\n" + "=" * 60)
                    print("🎉 SUCCESS! Kimi WebBridge is properly connected!")
                    print("=" * 60)
                    return True
                else:
                    print(f"\n⚠️  Unexpected response type: {data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print("\n❌ Timeout waiting for response")
                print("   Extension may not be connected or responding")
                return False
                
    except ConnectionRefusedError:
        print("   ❌ Connection refused - Backend server not running")
        print("\n💡 Solution:")
        print("   Start backend: cd backend && uvicorn app.main:app --reload")
        return False
        
    except asyncio.TimeoutError:
        print("   ❌ Connection timeout")
        print("\n💡 Solution:")
        print("   1. Ensure backend server is running")
        print("   2. Check if port 10086 is open")
        return False
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

async def main():
    print("\n🔧 Kimi WebBridge Connection Test")
    print("=" * 60)
    print("\nPrerequisites:")
    print("  1. Backend server running (uvicorn app.main:app)")
    print("  2. Kimi WebBridge extension installed in browser")
    print("  3. Browser open with LinkedIn logged in")
    print("  4. Extension connected to ws://127.0.0.1:10086/ws")
    print("=" * 60)
    
    result = await test_kimi_connection()
    
    if not result:
        print("\n" + "=" * 60)
        print("❌ Connection Failed")
        print("=" * 60)
        print("\n📋 Troubleshooting Steps:")
        print("\n1. Check if backend is running:")
        print("   curl http://localhost:8000/health")
        print("\n2. Open Microsoft Edge/Chrome and go to:")
        print("   - Extensions page")
        print("   - Find 'Kimi WebBridge'")
        print("   - Check if it's enabled")
        print("\n3. Open browser console (F12) and look for:")
        print("   - 'Connected to ws://127.0.0.1:10086/ws'")
        print("   - Any connection errors")
        print("\n4. Make sure you're logged into LinkedIn in the browser")
        print("\n5. Try refreshing the LinkedIn page")
        print("=" * 60)
    
    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
