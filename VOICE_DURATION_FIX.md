# Voice Transcription Duration Fix

## Problem
The Sarvam STT API has a 30-second limit for audio files. When users tried to transcribe audio longer than 30 seconds, they received a 500 Internal Server Error with the message:

```
Audio duration exceeds the maximum limit of 30 seconds. 
Please use the batch API for longer audio files.
```

## Solution Implemented

### 1. Added Audio Duration Validation (`audio_utils.py`)
- Added `MAX_AUDIO_DURATION_SECONDS = 30` constant
- Implemented `get_audio_duration()` function using ffprobe to detect audio duration
- Implemented `validate_audio_duration()` to check if audio exceeds 30 seconds
- Raises `AudioValidationError` with user-friendly message if duration exceeds limit

### 2. Updated Voice Manager (`voice_manager.py`)
- Added duration validation in `transcribe_file()` method
- Validation happens after saving temp file but before calling STT API
- Imported `validate_audio_duration` from audio_utils

### 3. Improved Error Handling (`chat.py`)
- Updated `/voice/transcribe` endpoint to catch `AudioValidationError`
- Returns HTTP 400 (Bad Request) for validation errors instead of 500
- Returns HTTP 500 only for unexpected errors
- Provides clear error messages to users

## User Experience

**Before:**
- 500 Internal Server Error
- Cryptic API error message

**After:**
- 400 Bad Request (appropriate status code)
- Clear message: "Audio duration (X.Xs) exceeds the maximum limit of 30 seconds. Please record a shorter audio clip."

## Technical Details

### Duration Detection
- Uses `ffprobe` (from FFmpeg) to detect audio duration
- If ffprobe is not available, validation is skipped and API handles it
- Graceful degradation ensures the feature works even without ffprobe

### Files Modified
1. `backend/app/services/voice/audio_utils.py` - Added duration validation functions
2. `backend/app/services/voice/voice_manager.py` - Integrated duration check
3. `backend/app/api/v1/routes/chat.py` - Improved error handling

## Testing

To test:
1. Record audio shorter than 30 seconds - should work fine
2. Record audio longer than 30 seconds - should get clear error message
3. Verify HTTP status code is 400 (not 500) for duration errors

## Notes

- The fix validates duration client-side before sending to API (better UX)
- Falls back to API validation if ffprobe is unavailable
- User gets immediate feedback instead of waiting for API call to fail
