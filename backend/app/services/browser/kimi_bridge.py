"""Kimi WebBridge controller for LinkedIn automation.

This controller interfaces with Kimi WebBridge to control the user's
existing browser session. This is the PRIMARY and RECOMMENDED method
for personal use since it:
- Reuses existing authenticated session (no credentials needed)
- Lower detection risk (real browser, no automation markers)
- No session management complexity
"""

import asyncio
import json
import uuid
import websockets
from typing import Any, Optional, Dict
from app.core.logging import get_logger
from app.services.browser.browser_controller import BrowserController

logger = get_logger(__name__)

class KimiBridgeServer:
    """Python-native WebSocket server for Kimi WebBridge extension."""
    _instance = None
    
    def __init__(self, port: int = 10086):
        self.port = port
        self.client_ws = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._server = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        async with self._lock:
            if self._server is not None:
                logger.debug("KimiBridgeServer already running, skipping start")
                return
            
            logger.info(f"Starting KimiBridgeServer on ws://127.0.0.1:{self.port}/ws")
            
            try:
                # websockets.serve supports the path argument if needed, but we can accept any path
                self._server = await websockets.serve(self._handler, "127.0.0.1", self.port)
                logger.info(f"✅ KimiBridgeServer successfully started on port {self.port}")
            except OSError as e:
                if e.errno == 10048:  # Windows: Address already in use
                    logger.warning(f"Port {self.port} already in use - server may already be running from another instance")
                    # Mark as started to prevent further attempts
                    self._server = "already_running"
                else:
                    raise

    async def _handler(self, websocket): # Removed path since websockets 10+ handles paths differently, and we just want to accept the connection
        if self.client_ws is not None:
            logger.warning("Another client tried to connect. Refusing.")
            await websocket.close(code=4000, reason="Already connected")
            return
            
        logger.info("✅ Kimi WebBridge extension connected!")
        self.client_ws = websocket
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    if msg_type == "hello":
                        logger.info(f"Extension handshake received. Version: {data.get('payload', {}).get('extensionVersion')}")
                        await websocket.send(json.dumps({"type": "hello_ack"}))
                    elif msg_type == "tool_result":
                        req_id = data.get("responseToRequestId")
                        if req_id in self.pending_requests:
                            if "error" in data.get("payload", {}):
                                self.pending_requests[req_id].set_exception(Exception(data["payload"]["error"]))
                            else:
                                self.pending_requests[req_id].set_result(data.get("payload", {}).get("data", {}))
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        finally:
            logger.warning("Kimi WebBridge extension disconnected")
            self.client_ws = None
            # Reject all pending requests
            for fut in self.pending_requests.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("Extension disconnected"))
            self.pending_requests.clear()

    async def execute_tool(self, name: str, args: dict, timeout: float = 30.0) -> Any:
        """Send a tool call to the extension and wait for the result."""
        if self.client_ws is None:
            raise ConnectionError("Kimi WebBridge extension is not connected! Ensure Chrome is open and the extension is connected to ws://127.0.0.1:10086/ws")
            
        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_requests[req_id] = fut
        
        payload = {
            "type": "tool_call",
            "requestId": req_id,
            "payload": {
                "name": name,
                "args": args
            }
        }
        
        logger.debug(f"Executing tool {name} with args {args}")
        try:
            await self.client_ws.send(json.dumps(payload))
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            fut.cancel()
            raise TimeoutError(f"Tool {name} timed out after {timeout}s")
        finally:
            self.pending_requests.pop(req_id, None)

# Keep the stub class around so imports don't break, but it won't be used
class KimiBridgeController(BrowserController):
    def __init__(self, bridge_url: str = "ws://localhost:7777") -> None:
        self.bridge_url = bridge_url
        self.connected = False
        self.user_id = None
    async def connect(self, user_id: uuid.UUID) -> dict[str, Any]:
        return {"status": "stub"}
    async def disconnect(self) -> None:
        pass
    async def is_authenticated(self) -> bool:
        return True
    async def create_post(self, content: str, trace_id: str) -> dict[str, str]:
        return {}
    async def post_comment(self, post_url: str, comment_text: str, trace_id: str) -> dict[str, str]:
        return {}
    async def react_to_post(self, post_url: str, reaction_type: str, trace_id: str) -> dict[str, str]:
        return {}
    async def get_profile_posts(self, profile_url: str, limit: int, trace_id: str) -> list[dict[str, Any]]:
        return []
    async def get_post_comments(self, post_url: str, trace_id: str) -> list[dict[str, Any]]:
        return []
    async def get_my_posts(self, limit: int, trace_id: str) -> list[dict[str, Any]]:
        return []
    async def validate_profile_url(self, profile_url: str, trace_id: str) -> bool:
        return True

