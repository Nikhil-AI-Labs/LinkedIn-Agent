"""Audio file validation and utilities."""

import tempfile
from pathlib import Path
from typing import BinaryIO

from app.services.voice.errors import (
    AudioValidationError,
    AudioTooLargeError,
    UnsupportedAudioFormatError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# Supported audio formats
SUPPORTED_MIME_TYPES = {
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/ogg; codecs=opus": ".ogg",
}

# Maximum upload size (15MB as per requirements)
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


def validate_audio_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> None:
    """Validate audio file upload.
    
    Args:
        filename: Original filename
        content_type: MIME type
        size_bytes: File size in bytes
        
    Raises:
        AudioTooLargeError: If file exceeds max size
        UnsupportedAudioFormatError: If format not supported
    """
    # Check file size
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        logger.warning(
            "audio_file_too_large",
            filename=filename,
            size_bytes=size_bytes,
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
        )
        raise AudioTooLargeError(
            f"Audio file too large: {size_bytes / 1024 / 1024:.2f}MB "
            f"(max: {MAX_UPLOAD_SIZE_BYTES / 1024 / 1024}MB)"
        )
    
    # Check MIME type
    if content_type not in SUPPORTED_MIME_TYPES:
        logger.warning(
            "unsupported_audio_format",
            filename=filename,
            content_type=content_type,
            supported_formats=list(SUPPORTED_MIME_TYPES.keys()),
        )
        raise UnsupportedAudioFormatError(
            f"Unsupported audio format: {content_type}. "
            f"Supported: {', '.join(SUPPORTED_MIME_TYPES.keys())}"
        )
    
    logger.info(
        "audio_validation_passed",
        filename=filename,
        content_type=content_type,
        size_mb=f"{size_bytes / 1024 / 1024:.2f}",
    )


def guess_audio_extension(content_type: str) -> str:
    """Get file extension from MIME type.
    
    Args:
        content_type: MIME type
        
    Returns:
        File extension (e.g., ".mp3")
        
    Raises:
        UnsupportedAudioFormatError: If format not recognized
    """
    extension = SUPPORTED_MIME_TYPES.get(content_type)
    if not extension:
        raise UnsupportedAudioFormatError(
            f"Cannot determine extension for: {content_type}"
        )
    
    return extension


async def save_temp_audio(
    file_content: bytes,
    content_type: str,
    prefix: str = "audio_",
) -> Path:
    """Save audio bytes to temporary file.
    
    Args:
        file_content: Audio file bytes
        content_type: MIME type
        prefix: Filename prefix
        
    Returns:
        Path to temporary file
        
    Note:
        Caller is responsible for cleaning up temp file.
    """
    extension = guess_audio_extension(content_type)
    
    # Create temporary file
    temp_fd, temp_path_str = tempfile.mkstemp(
        suffix=extension,
        prefix=prefix,
    )
    
    temp_path = Path(temp_path_str)
    
    try:
        # Write audio data
        with open(temp_fd, 'wb') as f:
            f.write(file_content)
        
        logger.info(
            "audio_saved_to_temp",
            path=str(temp_path),
            size_bytes=len(file_content),
        )
        
        return temp_path
        
    except Exception as e:
        # Clean up on error
        temp_path.unlink(missing_ok=True)
        logger.error(
            "failed_to_save_temp_audio",
            error=str(e),
        )
        raise AudioValidationError(f"Failed to save audio file: {e}")


def cleanup_temp_audio(path: Path) -> None:
    """Delete temporary audio file.
    
    Args:
        path: Path to temporary file
    """
    try:
        if path.exists():
            path.unlink()
            logger.debug("temp_audio_cleaned_up", path=str(path))
    except Exception as e:
        logger.warning(
            "failed_to_cleanup_temp_audio",
            path=str(path),
            error=str(e),
        )


def get_audio_mime_type(extension: str) -> str | None:
    """Get MIME type from file extension.
    
    Args:
        extension: File extension (e.g., ".mp3")
        
    Returns:
        MIME type or None if not found
    """
    extension = extension.lower()
    if not extension.startswith('.'):
        extension = f".{extension}"
    
    for mime_type, ext in SUPPORTED_MIME_TYPES.items():
        if ext == extension:
            return mime_type
    
    return None
