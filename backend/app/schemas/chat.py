"""Chat endpoint schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request to /chat endpoint."""
    
    message: str = Field(min_length=1, max_length=5000)
    thread_id: str | None = None
    voice_enabled: bool = False
    language: Literal["en", "hi", "hinglish"] = "en"


class DraftData(BaseModel):
    """Draft variant data."""
    
    variant_number: int
    content: str
    score: float | None = None
    word_count: int | None = None


class ChatResponse(BaseModel):
    """Response from /chat endpoint."""
    
    intent: str
    status: str = "success"  # Default status
    thread_id: str | None = None  # Optional thread ID
    trace_id: str = ""  # Will be set by endpoint
    message: str | None = None  # Assistant message
    data: dict[str, Any] = Field(default_factory=dict)


class VoiceTranscribeRequest(BaseModel):
    """Request to /voice/transcribe endpoint."""
    
    audio_data: str  # Base64 encoded audio
    language: Literal["en", "hi", "hinglish"] = "en"


class VoiceTranscribeResponse(BaseModel):
    """Response from /voice/transcribe endpoint."""
    
    text: str  # Changed from 'transcript' to match implementation
    language: str
    confidence: float | None = None


class VoiceSpeakRequest(BaseModel):
    """Request to /voice/speak endpoint."""
    
    text: str = Field(min_length=1, max_length=5000)
    language: Literal["en", "hi"] = "en"


class VoiceSpeakResponse(BaseModel):
    """Response from /voice/speak endpoint."""
    
    audio_data: str | None = None  # Base64 encoded audio (nullable for fallback)
    audio_available: bool
    mime_type: str | None = None
    fallback_text: str | None = None
    error: str | None = None
