"""Voice API endpoint integration tests."""

import pytest
import base64
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.voice import (
    TranscriptionResult,
    TTSResult,
    VoiceLanguage,
    TTSProviderError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def override_auth_deps():
    """Override authentication dependencies."""
    from app.core.dependencies import get_current_user_id, get_db_session, get_checkpointer
    
    async def _get_user_id():
        return 1
    
    async def _get_db():
        yield AsyncMock()
    
    async def _get_checkpointer():
        return AsyncMock()
    
    app.dependency_overrides[get_current_user_id] = _get_user_id
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_checkpointer] = _get_checkpointer
    
    yield
    
    app.dependency_overrides.clear()


# ============================================================================
# Voice Transcription Tests
# ============================================================================

class TestVoiceTranscriptionAPI:
    """Tests for /api/v1/voice/transcribe endpoint."""
    
    @patch("app.services.voice.voice_manager.VoiceManager.transcribe_file")
    def test_transcribe_voice_success(
        self,
        mock_transcribe,
        client,
        override_auth_deps,
    ):
        """Test successful voice transcription."""
        # Mock transcription result
        mock_transcribe.return_value = TranscriptionResult(
            text="Transcribed text here",
            language=VoiceLanguage.EN,
            provider="sarvam",
            model="saarika:v2.5",
            confidence=0.95,
        )
        
        # Prepare request
        fake_audio = base64.b64encode(b"fake audio data").decode()
        
        response = client.post(
            "/api/v1/voice/transcribe",
            json={
                "audio_data": fake_audio,
                "language": "en",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Transcribed text here"
        assert data["language"] == "en"
        assert data["confidence"] == 0.95
    
    @patch("app.services.voice.voice_manager.VoiceManager.transcribe_file")
    def test_transcribe_voice_with_hinglish(
        self,
        mock_transcribe,
        client,
        override_auth_deps,
    ):
        """Test transcription with Hinglish language."""
        mock_transcribe.return_value = TranscriptionResult(
            text="Hello यह test है",
            language=VoiceLanguage.HINGLISH,
            provider="sarvam",
            model="saarika:v2.5",
        )
        
        fake_audio = base64.b64encode(b"fake audio").decode()
        
        response = client.post(
            "/api/v1/voice/transcribe",
            json={
                "audio_data": fake_audio,
                "language": "hinglish",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "hinglish"
    
    @patch("app.services.voice.voice_manager.VoiceManager.transcribe_file")
    def test_transcribe_voice_error(
        self,
        mock_transcribe,
        client,
        override_auth_deps,
    ):
        """Test transcription with error."""
        from app.services.voice.errors import STTProviderError
        
        mock_transcribe.side_effect = STTProviderError("API down")
        
        fake_audio = base64.b64encode(b"fake audio").decode()
        
        response = client.post(
            "/api/v1/voice/transcribe",
            json={
                "audio_data": fake_audio,
                "language": "en",
            },
        )
        
        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()
    
    def test_transcribe_voice_missing_audio(
        self,
        client,
        override_auth_deps,
    ):
        """Test transcription with missing audio data."""
        response = client.post(
            "/api/v1/voice/transcribe",
            json={
                "language": "en",
                # Missing audio_data
            },
        )
        
        assert response.status_code == 422  # Validation error


# ============================================================================
# Voice Synthesis Tests
# ============================================================================

class TestVoiceSynthesisAPI:
    """Tests for /api/v1/voice/speak endpoint."""
    
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_synthesize_speech_success(
        self,
        mock_synthesize,
        client,
        override_auth_deps,
    ):
        """Test successful speech synthesis."""
        # Mock synthesis result
        fake_audio_base64 = base64.b64encode(b"fake audio").decode()
        mock_synthesize.return_value = {
            "audio_available": True,
            "audio_base64": fake_audio_base64,
            "mime_type": "audio/mpeg",
            "fallback_text": None,
            "error": None,
            "language": "en",
        }
        
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "text": "Hello world",
                "language": "en",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["audio_available"] is True
        assert data["audio_data"] == fake_audio_base64
        assert data["mime_type"] == "audio/mpeg"
        assert data["error"] is None
    
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_synthesize_speech_with_fallback(
        self,
        mock_synthesize,
        client,
        override_auth_deps,
    ):
        """Test synthesis with graceful fallback."""
        # Mock synthesis failure with fallback
        mock_synthesize.return_value = {
            "audio_available": False,
            "audio_base64": None,
            "mime_type": None,
            "fallback_text": "Hello world",
            "error": "TTS temporarily unavailable",
            "language": "en",
        }
        
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "text": "Hello world",
                "language": "en",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["audio_available"] is False
        assert data["audio_data"] is None
        assert data["fallback_text"] == "Hello world"
        assert "error" in data
    
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_synthesize_speech_exception_handling(
        self,
        mock_synthesize,
        client,
        override_auth_deps,
    ):
        """Test synthesis exception returns graceful fallback."""
        # Mock unexpected exception
        mock_synthesize.side_effect = Exception("Unexpected error")
        
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "text": "Hello world",
                "language": "en",
            },
        )
        
        # Should still return 200 with fallback
        assert response.status_code == 200
        data = response.json()
        assert data["audio_available"] is False
        assert data["fallback_text"] == "Hello world"
        assert "error" in data
    
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_synthesize_speech_hindi(
        self,
        mock_synthesize,
        client,
        override_auth_deps,
    ):
        """Test synthesis with Hindi language."""
        fake_audio_base64 = base64.b64encode(b"fake hindi audio").decode()
        mock_synthesize.return_value = {
            "audio_available": True,
            "audio_base64": fake_audio_base64,
            "mime_type": "audio/mpeg",
            "fallback_text": None,
            "error": None,
            "language": "hi",
        }
        
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "text": "नमस्ते",
                "language": "hi",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["audio_available"] is True
    
    def test_synthesize_speech_missing_text(
        self,
        client,
        override_auth_deps,
    ):
        """Test synthesis with missing text."""
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "language": "en",
                # Missing text
            },
        )
        
        assert response.status_code == 422  # Validation error


# ============================================================================
# Chat with Voice Integration Tests
# ============================================================================

class TestChatWithVoice:
    """Tests for chat endpoint with voice_enabled flag."""
    
    @patch("app.services.chat_service.ChatService.process_message")
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_chat_with_voice_enabled_success(
        self,
        mock_synthesize,
        mock_process_message,
        client,
        override_auth_deps,
    ):
        """Test chat with voice synthesis enabled."""
        # Mock chat response
        mock_process_message.return_value = {
            "message": "Here's your response",
            "intent": "general_query",
            "thread_id": None,
            "requires_approval": False,
            "data": {},
        }
        
        # Mock TTS success
        fake_audio_base64 = base64.b64encode(b"audio").decode()
        mock_synthesize.return_value = {
            "audio_available": True,
            "audio_base64": fake_audio_base64,
            "mime_type": "audio/mpeg",
            "fallback_text": None,
            "error": None,
            "language": "en",
        }
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Tell me something",
                "voice_enabled": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "voice_audio" in data["data"]
        assert data["data"]["voice_audio"] == fake_audio_base64
        assert data["data"]["voice_mime_type"] == "audio/mpeg"
    
    @patch("app.services.chat_service.ChatService.process_message")
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_chat_with_voice_enabled_tts_failure(
        self,
        mock_synthesize,
        mock_process_message,
        client,
        override_auth_deps,
    ):
        """Test chat with voice synthesis failure."""
        # Mock chat response
        mock_process_message.return_value = {
            "message": "Response text",
            "intent": "general_query",
            "thread_id": None,
            "requires_approval": False,
            "data": {},
        }
        
        # Mock TTS failure
        mock_synthesize.return_value = {
            "audio_available": False,
            "audio_base64": None,
            "mime_type": None,
            "fallback_text": "Response text",
            "error": "TTS unavailable",
            "language": "en",
        }
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Tell me something",
                "voice_enabled": True,
            },
        )
        
        # Should still return 200
        assert response.status_code == 200
        data = response.json()
        # Voice error should be in data
        assert "voice_error" in data["data"]
    
    @patch("app.services.chat_service.ChatService.process_message")
    def test_chat_with_voice_disabled(
        self,
        mock_process_message,
        client,
        override_auth_deps,
    ):
        """Test chat with voice disabled."""
        mock_process_message.return_value = {
            "message": "Response",
            "intent": "general_query",
            "thread_id": None,
            "requires_approval": False,
            "data": {},
        }
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Test",
                "voice_enabled": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # No voice data should be present
        assert "voice_audio" not in data["data"]
