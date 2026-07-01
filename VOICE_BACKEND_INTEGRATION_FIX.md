# Voice Backend Integration Fix

## Problem
The Gemini Live voice feature was connecting **directly from frontend to Gemini API**, completely bypassing the backend. This means:

1. ❌ No LangGraph agent processing
2. ❌ No LinkedIn operations can be triggered
3. ❌ No conversation history in database
4. ❌ Backend logs show no voice activity

## Root Cause
Your frontend (`gemini-live.ts`) connects directly to:
```
wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent
```

This is why backend logs only show health checks and pending actions - the voice conversation never goes through the backend.

## Solution Architecture

### New Flow
```
Frontend → Backend WebSocket → LangGraph Agent → (Gemini remains direct for audio)
                                      ↓
                              LinkedIn Operations
                              Database Storage
                              Agent Logic
```

### What I Created

#### 1. Backend WebSocket Endpoint
**File**: `backend/app/api/v1/routes/voice_live.py`
- WebSocket endpoint at `/api/v1/voice/live`
- Receives transcripts from frontend
- Processes through LangGraph `ChatService`
- Sends agent actions back to frontend

**Key Features**:
- `handle_user_transcript()` - Accumulates user speech
- `handle_ai_transcript()` - Accumulates AI responses
- `handle_turn_complete()` - Triggers LangGraph agent processing
- Sends notifications when LinkedIn actions are pending

#### 2. Updated Backend Configuration
**File**: `backend/app/core/config.py`
- Added `gemini_api_key` setting
- Added to required secrets validation

**File**: `backend/app/main.py`
- Registered `voice_live.router`

**File**: `.env`
- Added `GEMINI_API_KEY=YOUR_KEY_HERE`

## What You Need to Do

### Step 1: Add Gemini API Key to Backend
Edit `.env` file and replace:
```bash
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

With the actual Gemini API key you're using in the frontend.

### Step 2: Update Frontend Service
The frontend needs to connect to **both** WebSockets:
1. Gemini API (for audio/transcription) - keeps working as-is
2. Backend WebSocket (for agent processing) - NEW

**Changes needed in** `frontend/src/services/gemini-live.ts`:

```typescript
// Add backend WebSocket connection
private backendSocket: WebSocket | null = null;
private backendWsUrl = "ws://localhost:8000/api/v1/voice/live";

// In connect() method, after Gemini connection:
async connect(): Promise<void> {
  // ... existing Gemini connection code ...
  
  // Connect to backend
  await this.connectToBackend();
}

// New method to connect to backend
private async connectToBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = `${this.backendWsUrl}?user_id=${this.userId}&thread_id=${this.threadId}`;
    this.backendSocket = new WebSocket(url);

    this.backendSocket.onopen = () => {
      console.log("[Backend] Connected");
      this.backendSocket?.send(JSON.stringify({
        type: "setup",
        userId: this.userId,
        threadId: this.threadId,
      }));
      resolve();
    };

    this.backendSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle agent actions, notifications, etc.
      console.log("[Backend]", data);
    };

    this.backendSocket.onerror = (error) => {
      reject(new Error("Backend connection failed"));
    };
  });
}

// In handleGeminiMessage, send transcripts to backend:
if (serverContent.inputTranscription?.text) {
  this.userInputBuffer += serverContent.inputTranscription.text;
  this.callbacks.onUserTranscript?.(this.userInputBuffer);
  
  // Send to backend
  this.backendSocket?.send(JSON.stringify({
    type: "user_transcript",
    text: serverContent.inputTranscription.text,
  }));
}

if (serverContent.outputTranscription?.text) {
  this.aiResponseBuffer += serverContent.outputTranscription.text;
  this.callbacks.onAiTranscript?.(this.aiResponseBuffer);
  
  // Send to backend
  this.backendSocket?.send(JSON.stringify({
    type: "ai_transcript",
    text: serverContent.outputTranscription.text,
  }));
}

// On turn complete, notify backend for agent processing
if (serverContent.turnComplete) {
  this.backendSocket?.send(JSON.stringify({
    type: "turn_complete",
    userText: this.userInputBuffer,
    aiText: this.aiResponseBuffer,
  }));
  // ... rest of turn complete logic ...
}
```

### Step 3: Test
1. Restart backend: `python backend/app/main.py`
2. Click phone button in frontend
3. Backend logs should now show:
   ```
   voice_live_connection_accepted
   voice_live_setup_received
   voice_live_user_transcript
   voice_live_turn_complete
   ```

### Step 4: Verify Agent Integration
- Speak a command like "create a LinkedIn post about AI"
- Backend should process through LangGraph agent
- Check for `agent_action_required` messages in browser console
- Pending actions should appear in dashboard

## Benefits After Fix
✅ Voice conversations processed by LangGraph agent
✅ LinkedIn operations can be triggered via voice
✅ Conversation history stored in database
✅ Backend logs show voice activity
✅ Intent classification works
✅ Approval workflow integrates with voice

## Next Steps
After implementing the frontend changes:
1. Test voice → agent → LinkedIn post creation flow
2. Verify approvals dashboard shows voice-initiated actions
3. Check database for chat_message records from voice
4. Monitor backend logs for agent processing events

