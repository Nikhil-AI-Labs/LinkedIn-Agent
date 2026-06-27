"""Voice service internal models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VoiceLanguage(str, Enum):
    """Supported voice languages."""
    
    EN = "en"
    HI = "hi"
    HINGLISH = "hinglish"


class TranscriptionMode(str, Enum):
    """Transcription mode."""
    
    REST = "rest"  # Batch/file upload
    WS = "ws"      # Realtime streaming


class TranscriptionResult(BaseModel):
    """Result from speech-to-text transcription."""
    
    text: str
    language: VoiceLanguage
    provider: str = "sarvam"
    model: str
    confidence: float | None = None
    duration_ms: int | None = None
    raw_response: dict[str, Any] | None = Field(None, exclude=True)


class TTSResult(BaseModel):
    """Result from text-to-speech synthesis."""
    
    audio_bytes: bytes | None = Field(None, exclude=True)
    audio_base64: str | None = None
    mime_type: str = "audio/mpeg"
    language: VoiceLanguage
    provider: str = "sarvam"
    model: str
    duration_ms: int | None = None
    raw_response: dict[str, Any] | None = Field(None, exclude=True)


class StreamingSession(BaseModel):
    """Streaming transcription session metadata."""
    
    session_id: str
    language: VoiceLanguage
    mode: TranscriptionMode
    created_at: str
    partial_transcript: str = ""
    is_active: bool = True
