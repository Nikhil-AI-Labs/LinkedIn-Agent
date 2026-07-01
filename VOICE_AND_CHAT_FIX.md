# Voice and Chat Issues - Analysis & Fix

## Issues Identified

### Issue 1: Voice Transcription - Audio Too Long
**Problem**: The Sarvam STT API rejects audio longer than 30 seconds, returning a 500 error.

**Root Cause**: 
- ffprobe is NOT installed on your system
- Duration validation cannot run without ffprobe
- Audio is sent to API and fails there

**Fix Applied**:
- Updated error handling in `/voice/transcribe` endpoint
- Now detects "duration exceeds" errors from API
- Returns HTTP 400 with clear message: "Audio duration exceeds the maximum limit of 30 seconds. Please record a shorter audio clip."

**Solution for You**:
1. **Option A (Recommended)**: Record shorter voice messages (under 30 seconds)
2. **Option B**: Install ffprobe to get early validation:
   ```powershell
   # Install using Chocolatey
   choco install ffmpeg
   
   # OR download from: https://www.gyan.dev/ffmpeg/builds/
   # Extract and add to PATH
   ```

### Issue 2: Chat Response Slow/Not Responding
**From Your Logs**: I don't see any `/chat` endpoint calls completing successfully in the logs you provided. I only see:
- `/voice/transcribe` calls (failing due to duration)
- `/api/v1/pending` calls (working fine - 200 OK)
- `/api/v1/monitor/list` calls (working fine - 200 OK)

**This suggests**: The voice transcription is failing, so the chat never gets the transcribed text to process.

## How the Voice-to-Chat Flow Works

1. User records audio → Frontend sends to `/voice/transcribe`
2. Audio transcribed to text → Returns text to frontend
3. Frontend sends text to `/chat` endpoint → Gets AI response
4. If voice_enabled=true, response is synthesized to speech

**Your Flow is Breaking at Step 1** because audio is too long (>30 seconds).

## Testing & Verification

### Test 1: Voice Transcription (SHORT audio)
Record audio **UNDER 30 seconds** and try again:
- Expected: Should transcribe successfully
- Expected Status: 200 OK

### Test 2: Voice Transcription (LONG audio)  
Record audio **OVER 30 seconds**:
- Expected Error: "Audio duration exceeds the maximum limit of 30 seconds"
- Expected Status: 400 Bad Request (NOT 500 anymore)

### Test 3: Text Chat (Bypass Voice)
Try sending a text message directly (not voice):
1. Open frontend
2. Type "Hello" in text box
3. Send

Expected Flow in Logs:
```
chat_request_received → 
intent_classified → 
handling_general_query → 
groq_request/sarvam_request → 
chat response returned
```

## Current Status

✅ **FIXED**: Error handling for audio duration - now returns 400 instead of 500
✅ **WORKING**: `/pending` endpoint
✅ **WORKING**: `/monitor/list` endpoint  
⚠️ **ISSUE**: Voice transcription fails because audio is too long
❓ **UNKNOWN**: Text chat (not tested in provided logs)

## Next Steps

1. **Test with SHORT voice message** (under 30 seconds)
2. **Test with TEXT message** (bypass voice entirely)
3. If text chat also slow/not responding, check:
   - Groq API key validity
   - Sarvam API key validity
   - Network connectivity
   - API rate limits

## Important Notes

- The 30-second limit is a **Sarvam API limitation**, not our bug
- We cannot change this limit (it's their API rule)
- **Your audio clips are longer than 30 seconds** - that's why they fail
- Try recording shorter messages or typing text instead
