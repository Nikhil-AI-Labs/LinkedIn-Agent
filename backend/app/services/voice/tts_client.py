"""Sarvam text-to-speech client."""

import base64
import httpx
from typing import Any

from app.services.voice.models import (
    TTSResult,
    VoiceLanguage,
)
from app.services.voice.language import (
    normalize_language,
    get_tts_params,
)
from app.services.voice.errors import (
    TTSProviderError,
    TextTooLongError,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Maximum text length for TTS (as per requirements)
MAX_TTS_TEXT_LENGTH = 1800


class SarvamTTSClient:
    """Sarvam AI text-to-speech client.
    
    Uses Sarvam Bulbul v3 model for natural voice synthesis.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize TTS client.
        
        Args:
            api_key: Sarvam API key (defaults to settings)
            model: TTS model (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.sarvam_api_key
        self.model = model or settings.sarvam_tts_model
        self.timeout = timeout
        
        self.base_url = "https://api.sarvam.ai"
        self.endpoint = f"{self.base_url}/text-to-speech"
        
        logger.info(
            "sarvam_tts_client_initialized",
            model=self.model,
            timeout=self.timeout,
        )
    
    async def synthesize(
        self,
        text: str,
        language: VoiceLanguage | str,
        speaker: str | None = None,
        trace_id: str | None = None,
    ) -> TTSResult:
        """Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            language: Voice language
            speaker: Optional speaker override
            trace_id: Optional trace ID for logging
            
        Returns:
            TTSResult with audio data
            
        Raises:
            TextTooLongError: If text exceeds max length
            TTSProviderError: If synthesis fails
        """
        # Validate text length
        if len(text) > MAX_TTS_TEXT_LENGTH:
            logger.warning(
                "tts_text_too_long",
                text_length=len(text),
                max_length=MAX_TTS_TEXT_LENGTH,
                trace_id=trace_id,
            )
            raise TextTooLongError(
                f"Text too long for TTS: {len(text)} chars "
                f"(max: {MAX_TTS_TEXT_LENGTH})"
            )
        
        language_enum = normalize_language(language)
        tts_params = get_tts_params(language_enum, speaker)
        
        logger.info(
            "tts_synthesis_starting",
            text_length=len(text),
            language=language_enum.value,
            speaker=tts_params['speaker'],
            model=self.model,
            trace_id=trace_id,
        )
        
        try:
            # Prepare request payload
            payload = {
                'inputs': [text],
                'target_language_code': tts_params['language_code'],
                'speaker': tts_params['speaker'],
                'model': self.model,
                'enable_preprocessing': True,  # Normalize text before TTS
                'sample_rate': 16000,  # Standard sample rate
            }
            
            headers = {
                'api-subscription-key': self.api_key,
                'Content-Type': 'application/json',
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                )
                
                # Log response for debugging
                logger.debug(
                    "tts_api_response",
                    status_code=response.status_code,
                    trace_id=trace_id,
                )
                
                if response.status_code != 200:
                    error_detail = response.text[:500]  # Truncate for logging
                    logger.error(
                        "tts_api_error",
                        status_code=response.status_code,
                        error=error_detail,
                        trace_id=trace_id,
                    )
                    raise TTSProviderError(
                        f"Sarvam TTS API error ({response.status_code}): {error_detail}"
                    )
                
                response_data = response.json()
            
            # Parse response - Sarvam returns base64-encoded audio
            audio_base64 = response_data.get('audios', [None])[0]
            
            if not audio_base64:
                logger.error(
                    "tts_empty_audio",
                    response_data=response_data,
                    trace_id=trace_id,
                )
                raise TTSProviderError("Sarvam TTS returned empty audio")
            
            # Decode base64 to bytes
            audio_bytes = base64.b64decode(audio_base64)
            
            result = TTSResult(
                audio_bytes=audio_bytes,
                audio_base64=audio_base64,
                mime_type="audio/mpeg",  # Sarvam returns MP3
                language=language_enum,
                provider="sarvam",
                model=self.model,
                duration_ms=response_data.get('duration_ms'),
                raw_response=response_data,
            )
            
            logger.info(
                "tts_synthesis_success",
                audio_size_kb=len(audio_bytes) / 1024,
                language=language_enum.value,
                trace_id=trace_id,
            )
            
            return result
            
        except httpx.TimeoutException:
            logger.error(
                "tts_timeout",
                timeout=self.timeout,
                trace_id=trace_id,
            )
            raise TTSProviderError(
                f"Sarvam TTS request timed out after {self.timeout}s"
            )
        
        except httpx.RequestError as e:
            logger.error(
                "tts_request_error",
                error=str(e),
                trace_id=trace_id,
            )
            raise TTSProviderError(f"Sarvam TTS request failed: {e}")
        
        except Exception as e:
            logger.error(
                "tts_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                trace_id=trace_id,
            )
            raise TTSProviderError(f"Unexpected TTS error: {e}")
    
    async def synthesize_chunked(
        self,
        text: str,
        language: VoiceLanguage | str,
        speaker: str | None = None,
        trace_id: str | None = None,
        chunk_size: int = MAX_TTS_TEXT_LENGTH,
    ) -> list[TTSResult]:
        """Synthesize long text by chunking.
        
        Splits text into chunks and synthesizes each chunk separately.
        Useful for texts longer than MAX_TTS_TEXT_LENGTH.
        
        Args:
            text: Text to synthesize
            language: Voice language
            speaker: Optional speaker override
            trace_id: Optional trace ID for logging
            chunk_size: Maximum chars per chunk
            
        Returns:
            List of TTSResult (one per chunk)
            
        Note:
            Caller is responsible for concatenating audio chunks.
        """
        if len(text) <= chunk_size:
            # No chunking needed
            return [await self.synthesize(text, language, speaker, trace_id)]
        
        # Split text into chunks (simple sentence-aware splitting)
        chunks = []
        current_chunk = ""
        
        sentences = text.split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= chunk_size:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(
            "tts_chunked_synthesis",
            total_length=len(text),
            num_chunks=len(chunks),
            trace_id=trace_id,
        )
        
        # Synthesize each chunk
        results = []
        for i, chunk in enumerate(chunks):
            logger.debug(
                "tts_synthesizing_chunk",
                chunk_index=i,
                chunk_length=len(chunk),
                trace_id=trace_id,
            )
            
            result = await self.synthesize(
                chunk,
                language,
                speaker,
                trace_id,
            )
            results.append(result)
        
        return results
