"""Audio file validation and utilities."""

import tempfile
import subprocess
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

# Maximum audio duration for Sarvam STT (30 seconds)
MAX_AUDIO_DURATION_SECONDS = 30


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


def get_audio_duration(audio_path: Path) -> float | None:
    """Get audio duration in seconds using ffprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds, or None if unable to determine
    """
    try:
        # Try using ffprobe if available
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            logger.debug(
                "audio_duration_detected",
                path=str(audio_path),
                duration_seconds=duration,
            )
            return duration
            
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        logger.debug(
            "audio_duration_detection_failed",
            path=str(audio_path),
            error=str(e),
            note="ffprobe not available or failed - duration check skipped",
        )
    
    return None


def validate_audio_duration(audio_path: Path) -> None:
    """Validate that audio duration is within limits.
    
    Args:
        audio_path: Path to audio file
        
    Raises:
        AudioValidationError: If audio exceeds maximum duration
        
    Note:
        If ffprobe not available, falls back to file-size heuristic
        (webm voice recordings ~3KB/s, so >200KB likely exceeds 30s).
    """
    duration = get_audio_duration(audio_path)
    
    if duration is not None:
        # ffprobe worked — use exact duration
        if duration > MAX_AUDIO_DURATION_SECONDS:
            logger.warning(
                "audio_duration_exceeds_limit",
                path=str(audio_path),
                duration_seconds=duration,
                max_duration_seconds=MAX_AUDIO_DURATION_SECONDS,
            )
            raise AudioValidationError(
                f"Audio duration ({duration:.1f}s) exceeds the maximum limit of "
                f"{MAX_AUDIO_DURATION_SECONDS} seconds. Please record a shorter audio clip."
            )
        logger.info(
            "audio_duration_validated",
            path=str(audio_path),
            duration_seconds=duration,
        )
        return
    
    # ffprobe not available — use file-size heuristic
    file_size = audio_path.stat().st_size
    # Browser MediaRecorder default bitrate varies (Chrome ~128kbps, Firefox ~96kbps).
    # At 128 kbps: 25s = 400KB.  At 64 kbps: 25s = 200KB.
    # We configure frontend to 16 kbps (50KB/25s), but fallback must be generous.
    # Threshold: 600KB allows ~37s at 128kbps — well above our 25s timer.
    estimated_max_bytes = 600 * 1024  # 600 KB
    
    if file_size > estimated_max_bytes:
        # Use 8KB/s (64 kbps) as a realistic browser-default estimate
        estimated_duration = file_size / (8 * 1024)
        logger.warning(
            "audio_duration_heuristic_exceeds_limit",
            path=str(audio_path),
            size_bytes=file_size,
            estimated_duration_seconds=estimated_duration,
            note="ffprobe not available - using file-size heuristic (64kbps assumption)",
        )
        raise AudioValidationError(
            f"Audio file too large ({file_size / 1024:.0f}KB). Estimated duration "
            f"exceeds the {MAX_AUDIO_DURATION_SECONDS}-second limit. Please record a shorter audio clip."
        )
    
    logger.info(
        "audio_duration_heuristic_passed",
        path=str(audio_path),
        size_bytes=file_size,
        note="ffprobe not available - file size within limit",
    )
