import asyncio
import websockets
import json

async def kimi_handler(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            try:
                data = json.loads(message)
                command = data.get("command")
                
                # Mock responses based on command
                response = {"status": "success", "command": command}
                
                if command == "validate_session":
                    response["data"] = {"valid": True}
                elif command == "create_post":
                    response["data"] = "https://www.linkedin.com/feed/update/urn:li:activity:mock_post"
                elif command == "create_comment":
                    response["data"] = "https://www.linkedin.com/feed/update/urn:li:activity:mock_post?commentUrn=mock_comment"
                elif command == "add_reaction":
                    response["data"] = {"success": True}
                    
                await websocket.send(json.dumps(response))
            except Exception as e:
                await websocket.send(json.dumps({"status": "error", "error": str(e)}))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(kimi_handler, "localhost", 7777):
        print("Mock Kimi WebBridge running on ws://localhost:7777")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
