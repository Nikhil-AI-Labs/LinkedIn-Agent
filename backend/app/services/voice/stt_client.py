"""Sarvam speech-to-text client."""

import httpx
from pathlib import Path
from typing import Any

from app.services.voice.models import (
    TranscriptionResult,
    VoiceLanguage,
)
from app.services.voice.language import (
    normalize_language,
    get_stt_params,
)
from app.services.voice.errors import (
    STTProviderError,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SarvamSTTClient:
    """Sarvam AI speech-to-text client.
    
    Uses Sarvam's REST API for batch transcription.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        """Initialize STT client.
        
        Args:
            api_key: Sarvam API key (defaults to settings)
            model: STT model (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.sarvam_api_key
        self.model = model or settings.sarvam_stt_model
        self.timeout = timeout
        
        self.base_url = "https://api.sarvam.ai"
        self.endpoint = f"{self.base_url}/speech-to-text"
        
        logger.info(
            "sarvam_stt_client_initialized",
            model=self.model,
            timeout=self.timeout,
        )
    
    async def transcribe_file(
        self,
        audio_path: Path,
        language: VoiceLanguage | str,
        trace_id: str,
    ) -> TranscriptionResult:
        """Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            language: Voice language
            trace_id: Trace ID for logging
            
        Returns:
            TranscriptionResult with transcript
            
        Raises:
            STTProviderError: If transcription fails
        """
        language_enum = normalize_language(language)
        stt_params = get_stt_params(language_enum)
        
        logger.info(
            "stt_transcribe_starting",
            audio_path=str(audio_path),
            language=language_enum.value,
            model=self.model,
            trace_id=trace_id,
        )
        
        try:
            # Prepare multipart form data
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (audio_path.name, audio_file, 'audio/mpeg'),
                }
                
                data = {
                    'model': self.model,
                    'language_code': stt_params['language_code'],
                }
                
                # Add codemixing if needed
                if 'enable_codemixing' in stt_params:
                    data['enable_codemixing'] = stt_params['enable_codemixing']
                
                headers = {
                    'api-subscription-key': self.api_key,
                }
                
                # Make API request
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.endpoint,
                        files=files,
                        data=data,
                        headers=headers,
                    )
                    
                    # Log response for debugging (but not full transcript in sensitive mode)
                    logger.debug(
                        "stt_api_response",
                        status_code=response.status_code,
                        trace_id=trace_id,
                    )
                    
                    if response.status_code != 200:
                        error_detail = response.text[:500]  # Truncate for logging
                        logger.error(
                            "stt_api_error",
                            status_code=response.status_code,
                            error=error_detail,
                            trace_id=trace_id,
                        )
                        raise STTProviderError(
                            f"Sarvam STT API error ({response.status_code}): {error_detail}"
                        )
                    
                    response_data = response.json()
            
            # Parse response
            transcript = response_data.get('transcript', '')
            
            if not transcript:
                logger.warning(
                    "stt_empty_transcript",
                    response_data=response_data,
                    trace_id=trace_id,
                )
                # Return empty but valid result
                transcript = ""
            
            result = TranscriptionResult(
                text=transcript,
                language=language_enum,
                provider="sarvam",
                model=self.model,
                confidence=response_data.get('confidence'),
                duration_ms=response_data.get('duration_ms'),
                raw_response=response_data,
            )
            
            logger.info(
                "stt_transcription_success",
                text_length=len(transcript),
                language=language_enum.value,
                trace_id=trace_id,
            )
            
            return result
            
        except httpx.TimeoutException:
            logger.error(
                "stt_timeout",
                timeout=self.timeout,
                trace_id=trace_id,
            )
            raise STTProviderError(
                f"Sarvam STT request timed out after {self.timeout}s"
            )
        
        except httpx.RequestError as e:
            logger.error(
                "stt_request_error",
                error=str(e),
                trace_id=trace_id,
            )
            raise STTProviderError(f"Sarvam STT request failed: {e}")
        
        except Exception as e:
            logger.error(
                "stt_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                trace_id=trace_id,
            )
            raise STTProviderError(f"Unexpected STT error: {e}")


# ============================================================================
# WebSocket Streaming (Scaffold for Future MVP+)
# ============================================================================

class StreamingTranscriptionSession:
    """WebSocket-based streaming transcription session.
    
    This is a scaffold for future implementation.
    For MVP, we only support batch (REST API) transcription.
    """
    
    def __init__(
        self,
        api_key: str,
        language: VoiceLanguage,
        session_id: str,
    ):
        """Initialize streaming session.
        
        Args:
            api_key: Sarvam API key
            language: Voice language
            session_id: Unique session ID
        """
        self.api_key = api_key
        self.language = language
        self.session_id = session_id
        
        logger.info(
            "streaming_session_scaffold",
            session_id=session_id,
            language=language.value,
            note="WebSocket streaming not yet implemented - use REST for MVP",
        )
    
    async def connect(self) -> None:
        """Connect to Sarvam WebSocket endpoint.
        
        Not implemented in MVP.
        """
        raise NotImplementedError(
            "WebSocket streaming will be implemented in future version. "
            "Use REST API transcription for now."
        )
    
    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send audio chunk for realtime transcription.
        
        Not implemented in MVP.
        """
        raise NotImplementedError("WebSocket streaming not yet implemented")
    
    async def get_partial_transcript(self) -> str:
        """Get partial transcript from ongoing session.
        
        Not implemented in MVP.
        """
        raise NotImplementedError("WebSocket streaming not yet implemented")
    
    async def close(self) -> str:
        """Close session and get final transcript.
        
        Not implemented in MVP.
        """
        raise NotImplementedError("WebSocket streaming not yet implemented")
