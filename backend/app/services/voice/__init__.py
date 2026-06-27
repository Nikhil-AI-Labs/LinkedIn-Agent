"""Voice services package.

Provides speech-to-text and text-to-speech capabilities using Sarvam AI.
"""

from app.services.voice.models import (
    VoiceLanguage,
    TranscriptionResult,
    TTSResult,
    StreamingSession,
)
from app.services.voice.errors import (
    VoiceError,
    AudioValidationError,
    STTProviderError,
    TTSProviderError,
    StreamingSessionError,
    UnsupportedLanguageError,
    AudioTooLargeError,
    UnsupportedAudioFormatError,
    TextTooLongError,
)
from app.services.voice.language import (
    normalize_language,
    get_stt_params,
    get_tts_params,
    detect_language_from_text,
)
from app.services.voice.audio_utils import (
    validate_audio_upload,
    guess_audio_extension,
    save_temp_audio,
    cleanup_temp_audio,
)
from app.services.voice.stt_client import (
    SarvamSTTClient,
    StreamingTranscriptionSession,
)
from app.services.voice.tts_client import SarvamTTSClient
from app.services.voice.voice_manager import (
    VoiceManager,
    get_voice_manager,
)

__all__ = [
    # Models
    "VoiceLanguage",
    "TranscriptionResult",
    "TTSResult",
    "StreamingSession",
    
    # Errors
    "VoiceError",
    "AudioValidationError",
    "STTProviderError",
    "TTSProviderError",
    "StreamingSessionError",
    "UnsupportedLanguageError",
    "AudioTooLargeError",
    "UnsupportedAudioFormatError",
    "TextTooLongError",
    
    # Language utilities
    "normalize_language",
    "get_stt_params",
    "get_tts_params",
    "detect_language_from_text",
    
    # Audio utilities
    "validate_audio_upload",
    "guess_audio_extension",
    "save_temp_audio",
    "cleanup_temp_audio",
    
    # Clients
    "SarvamSTTClient",
    "SarvamTTSClient",
    "StreamingTranscriptionSession",
    
    # Manager
    "VoiceManager",
    "get_voice_manager",
]
