"""Voice service manager facade.

Orchestrates STT and TTS operations with graceful degradation.
"""

from pathlib import Path

from app.services.voice.models import (
    TranscriptionResult,
    TTSResult,
    VoiceLanguage,
)
from app.services.voice.stt_client import SarvamSTTClient
from app.services.voice.tts_client import SarvamTTSClient
from app.services.voice.audio_utils import (
    validate_audio_upload,
    save_temp_audio,
    cleanup_temp_audio,
    validate_audio_duration,
)
from app.services.voice.errors import (
    VoiceError,
    STTProviderError,
    TTSProviderError,
)
from app.services.voice.language import (
    normalize_language,
    detect_language_from_text,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoiceManager:
    """Voice service manager with STT and TTS capabilities.
    
    Provides graceful degradation: if TTS fails, returns fallback response.
    """
    
    def __init__(
        self,
        stt_client: SarvamSTTClient | None = None,
        tts_client: SarvamTTSClient | None = None,
    ):
        """Initialize voice manager.
        
        Args:
            stt_client: Optional STT client (creates default if None)
            tts_client: Optional TTS client (creates default if None)
        """
        self.stt_client = stt_client or SarvamSTTClient()
        self.tts_client = tts_client or SarvamTTSClient()
        
        logger.info("voice_manager_initialized")
    
    async def transcribe_file(
        self,
        audio_bytes: bytes,
        content_type: str,
        filename: str,
        language: VoiceLanguage | str,
        trace_id: str,
    ) -> TranscriptionResult:
        """Transcribe audio file to text.
        
        Args:
            audio_bytes: Audio file bytes
            content_type: MIME type
            filename: Original filename
            language: Voice language
            trace_id: Trace ID for logging
            
        Returns:
            TranscriptionResult with transcript
            
        Raises:
            AudioValidationError: If audio validation fails
            STTProviderError: If transcription fails
        """
        logger.info(
            "voice_transcribe_starting",
            filename=filename,
            content_type=content_type,
            size_bytes=len(audio_bytes),
            language=language,
            trace_id=trace_id,
        )
        
        # Validate audio file
        validate_audio_upload(filename, content_type, len(audio_bytes))
        
        # Save to temporary file
        temp_path = await save_temp_audio(audio_bytes, content_type)
        
        try:
            # Validate audio duration (30 second limit)
            validate_audio_duration(temp_path)
            
            # Transcribe
            result = await self.stt_client.transcribe_file(
                audio_path=temp_path,
                language=language,
                trace_id=trace_id,
            )
            
            logger.info(
                "voice_transcribe_success",
                text_length=len(result.text),
                trace_id=trace_id,
            )
            
            return result
            
        finally:
            # Always cleanup temp file
            cleanup_temp_audio(temp_path)
    
    async def synthesize_text(
        self,
        text: str,
        language: VoiceLanguage | str | None = None,
        speaker: str | None = None,
        trace_id: str | None = None,
        enable_chunking: bool = True,
    ) -> dict[str, any]:
        """Synthesize text to speech with graceful degradation.
        
        Args:
            text: Text to synthesize
            language: Voice language (auto-detects if None)
            speaker: Optional speaker override
            trace_id: Optional trace ID for logging
            enable_chunking: Whether to chunk long text
            
        Returns:
            Dict with:
            - audio_available: bool
            - audio_base64: str | None
            - mime_type: str | None
            - fallback_text: str | None (if TTS failed)
            - error: str | None (if TTS failed)
        """
        logger.info(
            "voice_synthesize_starting",
            text_length=len(text),
            language=language,
            trace_id=trace_id,
        )
        
        # Auto-detect language if not provided
        if language is None:
            language = detect_language_from_text(text)
            logger.info(
                "voice_language_detected",
                detected_language=language.value,
                trace_id=trace_id,
            )
        
        try:
            # Normalize language
            language_enum = normalize_language(language)
            
            # Check if chunking needed
            from app.services.voice.tts_client import MAX_TTS_TEXT_LENGTH
            
            if len(text) > MAX_TTS_TEXT_LENGTH and enable_chunking:
                # Synthesize with chunking
                logger.info(
                    "voice_using_chunked_synthesis",
                    text_length=len(text),
                    trace_id=trace_id,
                )
                
                results = await self.tts_client.synthesize_chunked(
                    text=text,
                    language=language_enum,
                    speaker=speaker,
                    trace_id=trace_id,
                )
                
                # Concatenate audio chunks (simple concatenation for MVP)
                # Note: Proper audio concatenation would require audio processing
                # For MVP, we just concatenate base64 strings
                combined_audio_base64 = "".join(r.audio_base64 for r in results)
                
                logger.info(
                    "voice_chunked_synthesis_success",
                    num_chunks=len(results),
                    trace_id=trace_id,
                )
                
                return {
                    "audio_available": True,
                    "audio_base64": combined_audio_base64,
                    "mime_type": "audio/mpeg",
                    "fallback_text": None,
                    "error": None,
                    "language": language_enum.value,
                }
            
            else:
                # Single synthesis
                result = await self.tts_client.synthesize(
                    text=text,
                    language=language_enum,
                    speaker=speaker,
                    trace_id=trace_id,
                )
                
                logger.info(
                    "voice_synthesis_success",
                    audio_size_kb=len(result.audio_bytes) / 1024,
                    trace_id=trace_id,
                )
                
                return {
                    "audio_available": True,
                    "audio_base64": result.audio_base64,
                    "mime_type": result.mime_type,
                    "fallback_text": None,
                    "error": None,
                    "language": language_enum.value,
                }
        
        except TTSProviderError as e:
            # TTS failed - return graceful fallback
            logger.warning(
                "voice_synthesis_failed_using_fallback",
                error=str(e),
                trace_id=trace_id,
            )
            
            return {
                "audio_available": False,
                "audio_base64": None,
                "mime_type": None,
                "fallback_text": text,  # Return original text as fallback
                "error": f"TTS temporarily unavailable: {str(e)}",
                "language": language.value if isinstance(language, VoiceLanguage) else language,
            }
        
        except Exception as e:
            # Unexpected error - return graceful fallback
            logger.error(
                "voice_synthesis_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                trace_id=trace_id,
            )
            
            return {
                "audio_available": False,
                "audio_base64": None,
                "mime_type": None,
                "fallback_text": text,
                "error": f"Unexpected TTS error: {str(e)}",
                "language": language.value if isinstance(language, VoiceLanguage) else language,
            }
    
    async def health_check(self) -> dict[str, any]:
        """Check health of voice services.
        
        Returns:
            Dict with service status
        """
        return {
            "stt_available": self.stt_client is not None,
            "tts_available": self.tts_client is not None,
            "stt_model": self.stt_client.model if self.stt_client else None,
            "tts_model": self.tts_client.model if self.tts_client else None,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_voice_manager_instance: VoiceManager | None = None


def get_voice_manager() -> VoiceManager:
    """Get singleton VoiceManager instance.
    
    Returns:
        VoiceManager instance
    """
    global _voice_manager_instance
    
    if _voice_manager_instance is None:
        _voice_manager_instance = VoiceManager()
        logger.info("voice_manager_singleton_created")
    
    return _voice_manager_instance
