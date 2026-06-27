"""Language normalization for voice providers."""

from app.services.voice.models import VoiceLanguage
from app.services.voice.errors import UnsupportedLanguageError


# Language mapping for Sarvam AI
# Sarvam expects locale-style codes and supports codemixing
LANGUAGE_MAP = {
    VoiceLanguage.EN: {
        "tts_lang": "en-IN",
        "stt_lang": "en-IN",
        "tts_speaker": "meera",  # Default English speaker
        "codemix": False,
    },
    VoiceLanguage.HI: {
        "tts_lang": "hi-IN",
        "stt_lang": "hi-IN",
        "tts_speaker": "arvind",  # Default Hindi speaker
        "codemix": False,
    },
    VoiceLanguage.HINGLISH: {
        "tts_lang": "hi-IN",  # Use Hindi for Hinglish
        "stt_lang": "hi-IN",
        "tts_speaker": "arvind",
        "codemix": True,  # Enable codemixing
    },
}


def normalize_language(language: VoiceLanguage | str) -> VoiceLanguage:
    """Normalize language string to VoiceLanguage enum.
    
    Args:
        language: Language code string or enum
        
    Returns:
        VoiceLanguage enum
        
    Raises:
        UnsupportedLanguageError: If language not supported
    """
    if isinstance(language, VoiceLanguage):
        return language
    
    try:
        return VoiceLanguage(language.lower())
    except ValueError:
        raise UnsupportedLanguageError(f"Unsupported language: {language}")


def get_stt_params(language: VoiceLanguage) -> dict[str, str]:
    """Get STT parameters for Sarvam API.
    
    Args:
        language: Voice language
        
    Returns:
        Dict with STT parameters
    """
    lang_config = LANGUAGE_MAP.get(language)
    if not lang_config:
        raise UnsupportedLanguageError(f"Language not configured: {language}")
    
    params = {
        "language_code": lang_config["stt_lang"],
    }
    
    if lang_config["codemix"]:
        params["enable_codemixing"] = "true"
    
    return params


def get_tts_params(
    language: VoiceLanguage,
    speaker: str | None = None,
) -> dict[str, str]:
    """Get TTS parameters for Sarvam API.
    
    Args:
        language: Voice language
        speaker: Optional speaker override
        
    Returns:
        Dict with TTS parameters
    """
    lang_config = LANGUAGE_MAP.get(language)
    if not lang_config:
        raise UnsupportedLanguageError(f"Language not configured: {language}")
    
    params = {
        "language_code": lang_config["tts_lang"],
        "speaker": speaker or lang_config["tts_speaker"],
    }
    
    return params


def detect_language_from_text(text: str) -> VoiceLanguage:
    """Detect language from text using simple heuristics.
    
    Args:
        text: Text to analyze
        
    Returns:
        Detected VoiceLanguage
    """
    import re
    
    # Count Devanagari characters
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    
    # Count ASCII letters
    ascii_count = len(re.findall(r'[a-zA-Z]', text))
    
    # Hinglish if mixed
    if devanagari_count > 0 and ascii_count > 0:
        return VoiceLanguage.HINGLISH
    
    # Hindi if mostly Devanagari
    if devanagari_count > ascii_count:
        return VoiceLanguage.HI
    
    # Default to English
    return VoiceLanguage.EN
