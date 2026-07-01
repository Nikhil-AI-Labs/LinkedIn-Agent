"""WebSocket endpoint for Gemini Live integration using google.genai SDK."""

import asyncio
import base64
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from google.genai import Client
from google.genai.types import (
    LiveConnectConfig,
    GenerationConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
    AudioTranscriptionConfig,
    Blob,
)

from app.core.dependencies import get_db_session, get_checkpointer
from app.core.config import settings
from app.core.logging import get_logger
from app.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice-live"])

# ── LinkedIn AI Agent system prompt ───────────────────────────────────────────
LINKEDIN_SYSTEM_PROMPT = """You are an intelligent LinkedIn AI Agent — a professional voice assistant
that helps users manage their LinkedIn presence, networking, and career growth.

## Your Core Capabilities
- **Content Creation**: Draft LinkedIn posts, articles, and comments that are engaging and professional
- **Networking**: Help analyze connection opportunities, draft outreach messages, and follow-up strategies
- **Engagement Actions**: Review and decide on pending actions like liking posts, commenting, sending connection requests
- **Profile Optimization**: Suggest improvements to profiles, headlines, and summaries
- **Job & Market Intelligence**: Discuss career opportunities, industry trends, and skill gaps

## Your Personality & Tone
- Professional yet conversational — like a sharp career advisor
- Data-driven and strategic in recommendations
- Concise and action-oriented in responses
- Always honest about limitations — never fabricate data or connections

## Pending Actions
When the user asks about pending actions, you can inform them there are LinkedIn actions waiting for their approval (likes, comments, connection requests, shares). Guide them to check the dashboard or ask you to review them.

## Important Rules
- Always maintain professional LinkedIn standards — no spammy or inauthentic content
- Focus on quality over quantity in all engagement
- Respect privacy — never request personal or sensitive data
- Keep voice responses concise and clear — this is a voice interface

You are connected to a live backend that manages LinkedIn automation. Be helpful, strategic, and professional at all times.
"""


class GeminiLiveProxySession:
    """Proxies audio between frontend WebSocket and Gemini Live API."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: str,
        thread_id: str,
        db: AsyncSession,
        checkpointer,
    ):
        self.websocket = websocket
        self.user_id = user_id
        self.thread_id = thread_id
        self.db = db
        self.checkpointer = checkpointer
        self.trace_id = str(uuid.uuid4())
        self.chat_service = ChatService(db=db, checkpointer=checkpointer)
        self.is_connected = False
        self.gemini_session = None
        self.gemini_task = None

    async def start(self):
        """Start the session: connect to Gemini Live and start proxying."""
        self.is_connected = True
        logger.info(
            "voice_live_session_started",
            user_id=self.user_id,
            thread_id=self.thread_id,
            trace_id=self.trace_id,
        )

        try:
            client = Client(api_key=settings.gemini_api_key)

            config = LiveConnectConfig(
                system_instruction=LINKEDIN_SYSTEM_PROMPT,
                generation_config=GenerationConfig(
                    response_modalities=["AUDIO"],
                    speech_config=SpeechConfig(
                        voice_config=VoiceConfig(
                            prebuilt_voice_config=PrebuiltVoiceConfig(
                                voice_name="Puck"
                            )
                        )
                    ),
                ),
                input_audio_transcription=AudioTranscriptionConfig(),
                output_audio_transcription=AudioTranscriptionConfig(),
            )

            # client.aio.live.connect() is an async context manager.
            # `async with` enters it and yields the real session object.
            async with client.aio.live.connect(
                model="models/gemini-2.5-flash-native-audio-latest",
                config=config,
            ) as session:
                self.gemini_session = session

                # Start the Gemini → frontend relay in the background
                self.gemini_task = asyncio.create_task(self._handle_gemini_messages())

                # Block here reading frontend messages until client disconnects
                await self._handle_frontend_messages()

        except Exception as e:
            logger.error(
                "voice_live_session_error",
                error=str(e),
                user_id=self.user_id,
                trace_id=self.trace_id,
            )
            await self._send_error(str(e))
        finally:
            await self.cleanup()

    async def _handle_gemini_messages(self):
        """Receive messages from Gemini Live and forward to frontend.

        KEY: session.receive() is a one-shot async generator — it ends after
        one turn_complete. We wrap it in `while True` so we re-subscribe for
        every subsequent turn, keeping the conversation alive indefinitely.
        """
        try:
            while self.is_connected:
                # Re-call session.receive() for each new turn.
                # This is the correct pattern for multi-turn voice conversations.
                async for message in self.gemini_session.receive():
                    if not self.is_connected:
                        return

                    if message.server_content:
                        content = message.server_content

                        # ── AI audio chunks ──────────────────────────────────
                        # part.inline_data.data is raw Python bytes from the SDK.
                        # JSON cannot serialize bytes → must base64-encode to str.
                        if content.model_turn and content.model_turn.parts:
                            for part in content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    audio_b64 = base64.b64encode(
                                        part.inline_data.data
                                    ).decode("utf-8")
                                    await self.websocket.send_json({
                                        "type": "ai_audio",
                                        "data": audio_b64,
                                        "mime_type": part.inline_data.mime_type or "audio/pcm;rate=24000",
                                    })

                        # ── AI speech transcript ─────────────────────────────
                        if content.output_transcription and content.output_transcription.text:
                            await self.websocket.send_json({
                                "type": "ai_transcript",
                                "text": content.output_transcription.text,
                            })

                        # ── User speech transcript ───────────────────────────
                        if content.input_transcription and content.input_transcription.text:
                            await self.websocket.send_json({
                                "type": "user_transcript",
                                "text": content.input_transcription.text,
                            })

                        # ── Turn complete signal ─────────────────────────────
                        if content.turn_complete:
                            await self.websocket.send_json({"type": "turn_complete"})
                            # After turn_complete the inner `async for` ends.
                            # The outer `while True` loop immediately re-calls
                            # session.receive() to wait for the NEXT turn.
                            break

                    # Tool calls (if any configured in the future)
                    if message.tool_call:
                        logger.info(
                            "voice_live_tool_call_received",
                            user_id=self.user_id,
                            trace_id=self.trace_id,
                        )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                "voice_live_gemini_handler_error",
                error=str(e),
                user_id=self.user_id,
                trace_id=self.trace_id,
            )
            await self._send_error(f"Gemini error: {str(e)}")

    async def _handle_frontend_messages(self):
        """Receive messages from frontend and forward to Gemini Live."""
        try:
            while self.is_connected:
                data = await self.websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "audio_chunk":
                    # The frontend sends base64-encoded 16-bit PCM audio.
                    # The SDK's send_realtime_input expects raw bytes.
                    audio_b64 = data.get("data", "")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        mime_type = data.get("mime_type", "audio/pcm;rate=16000")
                        await self.gemini_session.send_realtime_input(
                            media=Blob(data=audio_bytes, mime_type=mime_type)
                        )

                elif msg_type == "setup":
                    # Session is already set up with the LinkedIn prompt in start().
                    # Just acknowledge so the frontend knows it can begin streaming.
                    await self.websocket.send_json({
                        "type": "setup_complete",
                        "thread_id": self.thread_id,
                    })

                elif msg_type == "disconnect":
                    logger.info(
                        "voice_live_disconnect_requested",
                        user_id=self.user_id,
                        trace_id=self.trace_id,
                    )
                    break

        except WebSocketDisconnect:
            logger.info(
                "voice_live_client_disconnected",
                user_id=self.user_id,
                trace_id=self.trace_id,
            )
        except Exception as e:
            logger.error(
                "voice_live_frontend_handler_error",
                error=str(e),
                user_id=self.user_id,
                trace_id=self.trace_id,
            )

    async def _send_error(self, error: str):
        """Send error to frontend."""
        try:
            await self.websocket.send_json({"type": "error", "error": error})
        except Exception:
            pass

    async def cleanup(self):
        """Cleanup all resources."""
        self.is_connected = False

        if self.gemini_task:
            self.gemini_task.cancel()
            try:
                await self.gemini_task
            except asyncio.CancelledError:
                pass

        # The `async with` block in start() manages the gemini_session lifetime.
        # Do NOT call .close() here — the context manager handles teardown.
        self.gemini_session = None

        logger.info(
            "voice_live_session_cleanup",
            user_id=self.user_id,
            trace_id=self.trace_id,
        )


@router.websocket("/live")
async def voice_live_websocket(
    websocket: WebSocket,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    thread_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    checkpointer=Depends(get_checkpointer),
):
    """WebSocket endpoint for Gemini Live voice proxy.

    The frontend connects here. The backend connects to Gemini Live via
    google.genai SDK and proxies audio bidirectionally for a full
    multi-turn conversation.
    """
    await websocket.accept()

    if not thread_id:
        thread_id = f"voice_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    logger.info(
        "voice_live_connection_accepted",
        user_id=user_id,
        thread_id=thread_id,
    )

    session = GeminiLiveProxySession(
        websocket=websocket,
        user_id=user_id,
        thread_id=thread_id,
        db=db,
        checkpointer=checkpointer,
    )

    await session.start()
