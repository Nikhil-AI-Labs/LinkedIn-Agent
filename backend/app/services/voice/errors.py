"""Voice service errors."""


class VoiceError(Exception):
    """Base voice service error."""
    pass


class AudioValidationError(VoiceError):
    """Audio file validation error."""
    pass


class STTProviderError(VoiceError):
    """Speech-to-text provider error."""
    pass


class TTSProviderError(VoiceError):
    """Text-to-speech provider error."""
    pass


class StreamingSessionError(VoiceError):
    """Streaming session error."""
    pass


class UnsupportedLanguageError(VoiceError):
    """Unsupported language error."""
    pass


class AudioTooLargeError(AudioValidationError):
    """Audio file too large."""
    pass


class UnsupportedAudioFormatError(AudioValidationError):
    """Unsupported audio format."""
    pass


class TextTooLongError(VoiceError):
    """Text too long for synthesis."""
    pass
