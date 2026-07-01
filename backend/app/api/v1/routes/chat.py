"""Chat and voice endpoints."""

import base64
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import (
    ChatRequest,
    VoiceTranscribeRequest,
    VoiceSpeakRequest,
)
from app.schemas.responses import (
    ChatResponse,
    VoiceTranscribeResponse,
    VoiceSpeakResponse,
)
from app.services.chat_service import ChatService
from app.services.voice import get_voice_manager, VoiceLanguage
from app.services.voice.errors import AudioValidationError, STTProviderError
from app.core.dependencies import get_db_session, get_current_user_id, get_trace_id, get_checkpointer
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    checkpointer = Depends(get_checkpointer),
) -> ChatResponse:
    """Process a chat message.
    
    Handles:
    - Intent classification
    - Routing to appropriate handler (create post, view pending, etc.)
    - Message persistence
    - Optional voice synthesis (if voice_enabled=true)
    """
    logger.info(
        "chat_request_received",
        user_id=user_id,
        message_length=len(request.message),
        thread_id=request.thread_id,
        voice_enabled=request.voice_enabled,
        trace_id=trace_id,
    )
    
    # Create chat service
    chat_service = ChatService(db=db, checkpointer=checkpointer)
    
    # Process message
    response_data = await chat_service.process_message(
        user_id=user_id,
        message=request.message,
        thread_id=request.thread_id,
        trace_id=trace_id,
        language=request.language,
        source_mode="text",  # Default to text; voice transcription would set this to "voice"
    )
    
    # If voice enabled and response has message, add TTS
    if request.voice_enabled and response_data.get("message"):
        logger.info("voice_synthesis_requested", trace_id=trace_id)
        
        try:
            voice_manager = get_voice_manager()
            
            # Synthesize response message
            tts_result = await voice_manager.synthesize_text(
                text=response_data["message"],
                language=None,  # Auto-detect
                trace_id=trace_id,
            )
            
            # Add voice data to response
            if tts_result["audio_available"]:
                response_data["data"]["voice_audio"] = tts_result["audio_base64"]
                response_data["data"]["voice_mime_type"] = tts_result["mime_type"]
                logger.info("voice_synthesis_success", trace_id=trace_id)
            else:
                # TTS failed, but we have fallback text
                response_data["data"]["voice_error"] = tts_result.get("error")
                logger.warning(
                    "voice_synthesis_failed",
                    error=tts_result.get("error"),
                    trace_id=trace_id,
                )
        
        except Exception as e:
            # Don't fail the whole request if TTS fails
            logger.error(
                "voice_synthesis_exception",
                error=str(e),
                trace_id=trace_id,
            )
            response_data["data"]["voice_error"] = f"TTS error: {str(e)}"
    
    return ChatResponse(**response_data)


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    request: VoiceTranscribeRequest,
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> VoiceTranscribeResponse:
    """Transcribe audio to text using Sarvam STT."""
    logger.info(
        "voice_transcribe_requested",
        user_id=user_id,
        language=request.language,
        audio_length=len(request.audio_data),
        trace_id=trace_id,
    )
    
    try:
        voice_manager = get_voice_manager()
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_data)
        
        # Transcribe
        result = await voice_manager.transcribe_file(
            audio_bytes=audio_bytes,
            content_type="audio/webm",  # Default, can be enhanced to accept mime type
            filename="audio_upload",
            language=request.language,
            trace_id=trace_id,
        )
        
        return VoiceTranscribeResponse(
            text=result.text,
            language=result.language.value,
            confidence=result.confidence,
        )
    
    except AudioValidationError as e:
        logger.warning(
            "voice_transcribe_validation_error",
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except STTProviderError as e:
        error_msg = str(e).lower()
        
        # Check if it's a duration error from API
        if "duration" in error_msg and ("exceeds" in error_msg or "30" in error_msg or "limit" in error_msg):
            logger.warning(
                "voice_transcribe_duration_exceeded",
                error=str(e),
                trace_id=trace_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio duration exceeds the maximum limit of 30 seconds. Please record a shorter audio clip (under 25 seconds).",
            )
        
        # Other STT errors
        logger.error(
            "voice_transcribe_stt_error",
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription service error: {str(e)}",
        )
    
    except Exception as e:
        logger.error(
            "voice_transcribe_error",
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/voice/speak", response_model=VoiceSpeakResponse)
async def synthesize_speech(
    request: VoiceSpeakRequest,
    user_id: str = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
) -> VoiceSpeakResponse:
    """Synthesize text to speech using Sarvam TTS."""
    logger.info(
        "voice_synthesis_requested",
        user_id=user_id,
        language=request.language,
        text_length=len(request.text),
        trace_id=trace_id,
    )
    
    try:
        voice_manager = get_voice_manager()
        
        # Synthesize
        result = await voice_manager.synthesize_text(
            text=request.text,
            language=request.language,
            speaker=None,  # Can be enhanced to accept speaker parameter
            trace_id=trace_id,
        )
        
        return VoiceSpeakResponse(
            audio_data=result.get("audio_base64"),
            audio_available=result["audio_available"],
            mime_type=result.get("mime_type"),
            fallback_text=result.get("fallback_text"),
            error=result.get("error"),
        )
    
    except Exception as e:
        logger.error(
            "voice_synthesis_error",
            error=str(e),
            trace_id=trace_id,
        )
        # Return graceful fallback
        return VoiceSpeakResponse(
            audio_data=None,
            audio_available=False,
            mime_type=None,
            fallback_text=request.text,
            error=f"Synthesis failed: {str(e)}",
        )
