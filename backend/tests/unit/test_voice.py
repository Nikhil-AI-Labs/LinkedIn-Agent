"""Voice service tests with mocked Sarvam API."""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from app.services.voice import (
    VoiceManager,
    SarvamSTTClient,
    SarvamTTSClient,
    VoiceLanguage,
    TranscriptionResult,
    TTSResult,
    AudioValidationError,
    AudioTooLargeError,
    UnsupportedAudioFormatError,
    TextTooLongError,
    STTProviderError,
    TTSProviderError,
)
from app.services.voice.audio_utils import (
    validate_audio_upload,
    guess_audio_extension,
    save_temp_audio,
    cleanup_temp_audio,
    SUPPORTED_MIME_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
)
from app.services.voice.language import (
    normalize_language,
    get_stt_params,
    get_tts_params,
    detect_language_from_text,
)


# ============================================================================
# Audio Utilities Tests
# ============================================================================

class TestAudioUtilities:
    """Tests for audio validation and utilities."""
    
    def test_validate_audio_upload_success(self):
        """Test successful audio validation."""
        # Should not raise
        validate_audio_upload(
            filename="test.mp3",
            content_type="audio/mpeg",
            size_bytes=1024 * 1024,  # 1MB
        )
    
    def test_validate_audio_upload_too_large(self):
        """Test validation fails for oversized file."""
        with pytest.raises(AudioTooLargeError):
            validate_audio_upload(
                filename="large.mp3",
                content_type="audio/mpeg",
                size_bytes=MAX_UPLOAD_SIZE_BYTES + 1,
            )
    
    def test_validate_audio_upload_unsupported_format(self):
        """Test validation fails for unsupported format."""
        with pytest.raises(UnsupportedAudioFormatError):
            validate_audio_upload(
                filename="test.flac",
                content_type="audio/flac",
                size_bytes=1024,
            )
    
    def test_guess_audio_extension(self):
        """Test MIME type to extension mapping."""
        assert guess_audio_extension("audio/mpeg") == ".mp3"
        assert guess_audio_extension("audio/wav") == ".wav"
        assert guess_audio_extension("audio/webm") == ".webm"
    
    def test_guess_audio_extension_unsupported(self):
        """Test extension guessing fails for unsupported format."""
        with pytest.raises(UnsupportedAudioFormatError):
            guess_audio_extension("audio/unknown")
    
    @pytest.mark.asyncio
    async def test_save_and_cleanup_temp_audio(self):
        """Test saving and cleaning up temporary audio."""
        audio_data = b"fake audio data"
        
        temp_path = await save_temp_audio(
            file_content=audio_data,
            content_type="audio/mp3",
        )
        
        assert temp_path.exists()
        assert temp_path.suffix == ".mp3"
        
        # Cleanup
        cleanup_temp_audio(temp_path)
        assert not temp_path.exists()


# ============================================================================
# Language Utilities Tests
# ============================================================================

class TestLanguageUtilities:
    """Tests for language normalization and detection."""
    
    def test_normalize_language_enum(self):
        """Test normalizing language enum."""
        result = normalize_language(VoiceLanguage.EN)
        assert result == VoiceLanguage.EN
    
    def test_normalize_language_string(self):
        """Test normalizing language string."""
        assert normalize_language("en") == VoiceLanguage.EN
        assert normalize_language("hi") == VoiceLanguage.HI
        assert normalize_language("hinglish") == VoiceLanguage.HINGLISH
    
    def test_get_stt_params_english(self):
        """Test STT parameters for English."""
        params = get_stt_params(VoiceLanguage.EN)
        assert params["language_code"] == "en-IN"
        assert "enable_codemixing" not in params
    
    def test_get_stt_params_hinglish(self):
        """Test STT parameters for Hinglish."""
        params = get_stt_params(VoiceLanguage.HINGLISH)
        assert params["language_code"] == "hi-IN"
        assert params["enable_codemixing"] == "true"
    
    def test_get_tts_params(self):
        """Test TTS parameters."""
        params = get_tts_params(VoiceLanguage.EN)
        assert params["language_code"] == "en-IN"
        assert "speaker" in params
    
    def test_detect_language_from_text_english(self):
        """Test language detection for English."""
        text = "This is a test message"
        result = detect_language_from_text(text)
        assert result == VoiceLanguage.EN
    
    def test_detect_language_from_text_hindi(self):
        """Test language detection for Hindi."""
        text = "यह एक परीक्षण संदेश है"
        result = detect_language_from_text(text)
        assert result == VoiceLanguage.HI
    
    def test_detect_language_from_text_hinglish(self):
        """Test language detection for Hinglish."""
        text = "Hello यह test है"
        result = detect_language_from_text(text)
        assert result == VoiceLanguage.HINGLISH


# ============================================================================
# STT Client Tests
# ============================================================================

class TestSarvamSTTClient:
    """Tests for Sarvam STT client."""
    
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_transcribe_file_success(self, mock_client_class):
        """Test successful transcription."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcript": "Hello world",
            "confidence": 0.95,
            "duration_ms": 1500,
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Create client and transcribe
        client = SarvamSTTClient(api_key="test-key")
        
        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = await client.transcribe_file(
                audio_path=Path("/fake/path.mp3"),
                language=VoiceLanguage.EN,
                trace_id="test-trace",
            )
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == VoiceLanguage.EN
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_transcribe_file_api_error(self, mock_client_class):
        """Test transcription with API error."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        client = SarvamSTTClient(api_key="test-key")
        
        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            with pytest.raises(STTProviderError):
                await client.transcribe_file(
                    audio_path=Path("/fake/path.mp3"),
                    language=VoiceLanguage.EN,
                    trace_id="test-trace",
                )


# ============================================================================
# TTS Client Tests
# ============================================================================

class TestSarvamTTSClient:
    """Tests for Sarvam TTS client."""
    
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_synthesize_success(self, mock_client_class):
        """Test successful synthesis."""
        # Mock response
        fake_audio_base64 = base64.b64encode(b"fake audio bytes").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audios": [fake_audio_base64],
            "duration_ms": 2000,
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Create client and synthesize
        client = SarvamTTSClient(api_key="test-key")
        result = await client.synthesize(
            text="Hello world",
            language=VoiceLanguage.EN,
            trace_id="test-trace",
        )
        
        assert isinstance(result, TTSResult)
        assert result.audio_base64 == fake_audio_base64
        assert result.language == VoiceLanguage.EN
        assert len(result.audio_bytes) > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_text_too_long(self):
        """Test synthesis fails for text that's too long."""
        client = SarvamTTSClient(api_key="test-key")
        
        long_text = "a" * 2000  # Exceeds MAX_TTS_TEXT_LENGTH
        
        with pytest.raises(TextTooLongError):
            await client.synthesize(
                text=long_text,
                language=VoiceLanguage.EN,
            )
    
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_synthesize_api_error(self, mock_client_class):
        """Test synthesis with API error."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        client = SarvamTTSClient(api_key="test-key")
        
        with pytest.raises(TTSProviderError):
            await client.synthesize(
                text="Hello",
                language=VoiceLanguage.EN,
            )
    
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_synthesize_chunked(self, mock_client_class):
        """Test chunked synthesis for long text."""
        # Mock response
        fake_audio_base64 = base64.b64encode(b"fake audio").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audios": [fake_audio_base64],
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        client = SarvamTTSClient(api_key="test-key")
        
        # Create text longer than chunk size
        long_text = ". ".join(["Sentence"] * 200)  # ~1800 chars
        
        results = await client.synthesize_chunked(
            text=long_text,
            language=VoiceLanguage.EN,
            chunk_size=500,
        )
        
        assert len(results) > 1  # Should be chunked
        assert all(isinstance(r, TTSResult) for r in results)


# ============================================================================
# Voice Manager Tests
# ============================================================================

class TestVoiceManager:
    """Tests for VoiceManager facade."""
    
    @pytest.mark.asyncio
    @patch("app.services.voice.voice_manager.save_temp_audio")
    @patch("app.services.voice.voice_manager.cleanup_temp_audio")
    async def test_transcribe_file_success(
        self,
        mock_cleanup,
        mock_save_temp,
    ):
        """Test successful transcription via manager."""
        # Mock temp file
        mock_temp_path = Path("/tmp/audio.mp3")
        mock_save_temp.return_value = mock_temp_path
        
        # Mock STT client
        mock_stt_client = AsyncMock()
        mock_stt_client.transcribe_file.return_value = TranscriptionResult(
            text="Transcribed text",
            language=VoiceLanguage.EN,
            provider="sarvam",
            model="saarika:v2.5",
        )
        
        # Create manager with mocked client
        manager = VoiceManager(stt_client=mock_stt_client)
        
        result = await manager.transcribe_file(
            audio_bytes=b"fake audio",
            content_type="audio/mp3",
            filename="test.mp3",
            language=VoiceLanguage.EN,
            trace_id="test-trace",
        )
        
        assert result.text == "Transcribed text"
        mock_cleanup.assert_called_once_with(mock_temp_path)
    
    @pytest.mark.asyncio
    async def test_synthesize_text_success(self):
        """Test successful TTS via manager."""
        # Mock TTS client
        fake_audio_base64 = base64.b64encode(b"fake audio").decode()
        mock_tts_client = AsyncMock()
        mock_tts_client.synthesize.return_value = TTSResult(
            audio_bytes=b"fake audio",
            audio_base64=fake_audio_base64,
            mime_type="audio/mpeg",
            language=VoiceLanguage.EN,
            provider="sarvam",
            model="bulbul:v3",
        )
        
        # Create manager with mocked client
        manager = VoiceManager(tts_client=mock_tts_client)
        
        result = await manager.synthesize_text(
            text="Hello world",
            language=VoiceLanguage.EN,
            trace_id="test-trace",
        )
        
        assert result["audio_available"] is True
        assert result["audio_base64"] == fake_audio_base64
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_synthesize_text_with_fallback(self):
        """Test TTS with graceful fallback on error."""
        # Mock TTS client that raises error
        mock_tts_client = AsyncMock()
        mock_tts_client.synthesize.side_effect = TTSProviderError("API down")
        
        # Create manager with mocked client
        manager = VoiceManager(tts_client=mock_tts_client)
        
        result = await manager.synthesize_text(
            text="Hello world",
            language=VoiceLanguage.EN,
            trace_id="test-trace",
        )
        
        # Should return graceful fallback
        assert result["audio_available"] is False
        assert result["audio_base64"] is None
        assert result["fallback_text"] == "Hello world"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_synthesize_text_auto_detect_language(self):
        """Test TTS with automatic language detection."""
        # Mock TTS client
        mock_tts_client = AsyncMock()
        mock_tts_client.synthesize.return_value = TTSResult(
            audio_bytes=b"fake audio",
            audio_base64="fake_base64",
            mime_type="audio/mpeg",
            language=VoiceLanguage.HI,
            provider="sarvam",
            model="bulbul:v3",
        )
        
        manager = VoiceManager(tts_client=mock_tts_client)
        
        # Hindi text without explicit language
        result = await manager.synthesize_text(
            text="नमस्ते",
            language=None,  # Auto-detect
            trace_id="test-trace",
        )
        
        assert result["audio_available"] is True
        # Language should be detected
        assert result["language"] == "hi"
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        manager = VoiceManager()
        
        health = await manager.health_check()
        
        assert "stt_available" in health
        assert "tts_available" in health
        assert health["stt_available"] is True
        assert health["tts_available"] is True
