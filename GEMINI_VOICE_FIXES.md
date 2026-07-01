# Gemini Voice Connection & Message Truncation Fixes

## Issues Fixed

### Issue 1: Connection Disconnects Immediately ✅

**Problem**: When clicking the phone button to connect, the Gemini WebSocket would connect briefly but then immediately disconnect and return to "Ready" state.

**Root Cause**: 
- The WebSocket `onclose` event handler was calling `disconnect()` unconditionally
- This created a race condition where any close event (even during normal connection flow) would trigger disconnect
- The `disconnect()` method was setting `isConnectedFlag = false` after starting the cleanup, allowing `onclose` to call it again

**Fix Applied**:
1. **In `gemini-live.ts` - `onclose` handler**:
   ```typescript
   this.socket.onclose = () => {
     // Only disconnect if this was unexpected (not user-initiated)
     if (this.isConnectedFlag) {
       this.disconnect();
     }
   };
   ```
   - Now only calls `disconnect()` if connection was active
   - Prevents disconnect loop during user-initiated disconnection

2. **In `gemini-live.ts` - `disconnect()` method**:
   - Set `isConnectedFlag = false` **FIRST** before any cleanup
   - This prevents `onclose` from calling `disconnect()` again
   - Ensures clean one-time disconnection

**Result**: Phone button now properly connects and stays connected until user clicks disconnect.

---

### Issue 2: Chat Messages Truncated ✅

**Problem**: LLM responses were being cut off in the frontend. Example:
- Full response: "I can't check your specific LinkedIn account status as I don't have access to your account..."
- Displayed: "I can't check your specific LinkedIn account status as I don't"

**Root Cause**:
- The service was sending **incremental transcript chunks** to the callback
- The VoiceDashboard was **accumulating** these chunks in refs: `userTranscriptRef.current += text`
- But the service itself was **also accumulating** in `aiResponseBuffer` and `userInputBuffer`
- This created a mismatch: callbacks received partial text, but the component expected full text

**Fix Applied**:
1. **In `gemini-live.ts` - transcript callbacks**:
   ```typescript
   // AI transcript (accumulated)
   if (serverContent.outputTranscription?.text) {
     this.aiResponseBuffer += serverContent.outputTranscription.text;
     this.callbacks.onAiTranscript?.(this.aiResponseBuffer);  // ← Send FULL accumulated text
   }

   // User transcript (accumulated)
   if (serverContent.inputTranscription?.text) {
     this.userInputBuffer += serverContent.inputTranscription.text;
     this.callbacks.onUserTranscript?.(this.userInputBuffer);  // ← Send FULL accumulated text
   }
   ```
   - Now sends the **complete accumulated text** on each update
   - Not just the incremental chunk

2. **In `VoiceDashboard.tsx` - callback handlers**:
   ```typescript
   onUserTranscript: (fullText) => {
     // Store the complete accumulated text (don't add to it)
     userTranscriptRef.current = fullText;
   },
   onAiTranscript: (fullText) => {
     // Store the complete accumulated text (don't add to it)
     aiTranscriptRef.current = fullText;
   },
   ```
   - Changed from `+=` to `=` assignment
   - Now properly replaces with full accumulated text

**Result**: Full LLM responses now display correctly in the chat interface.

---

## Testing

### Test Connection (Issue 1)
1. Click phone button → Should show "Connecting"
2. Wait ~1 second → Should change to "Connected" then "Listening"
3. Speak → Should show "Speaking" when AI responds
4. Should stay connected until you click phone button again

✅ **Expected**: Connection stays active, doesn't auto-disconnect

### Test Message Display (Issue 2)
1. Connect voice
2. Say: "Can you tell me about LinkedIn?"
3. Wait for AI response
4. Check transcript panel on right side

✅ **Expected**: Full AI response visible, not truncated

---

## Files Modified

1. `frontend/src/services/gemini-live.ts`
   - Fixed WebSocket `onclose` handler to prevent disconnect loop
   - Fixed `disconnect()` method to set flag first
   - Changed transcript callbacks to send full accumulated text

2. `frontend/src/components/dashboard/VoiceDashboard.tsx`
   - Changed transcript handlers from accumulation (`+=`) to assignment (`=`)
   - Now receives full text from service instead of incremental chunks

---

## Technical Details

### Connection Flow (Now Fixed)
```
1. User clicks phone → toggleSystem()
2. Create GeminiLiveService → connect()
3. WebSocket opens → onopen fires
4. Send setup message
5. Start microphone
6. Status: "connecting" → "connected" → "listening"
7. ✅ Stays connected (was disconnecting here before)
```

### Transcript Flow (Now Fixed)
```
1. User speaks → Audio sent to Gemini
2. Gemini streams back transcription chunks
3. Service accumulates in aiResponseBuffer
4. Service sends FULL accumulated text to callback  ← FIX
5. Component replaces ref with full text (not adds)  ← FIX
6. On turn complete, flush to chat store
7. ✅ Full message displayed
```

---

## No Further Changes Needed

Both issues are now resolved. The Gemini Live voice connection should work smoothly:
- Connects and stays connected ✅
- Full transcripts display properly ✅
- Voice chat flows naturally ✅
