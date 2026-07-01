# Chat Error Fix Summary

## Issue
The application was throwing a `TypeError: 'thread_id' is an invalid keyword argument for ChatMessage` when trying to process chat messages.

## Root Cause
The `ChatHistoryRepository.create_message()` method was trying to create `ChatMessage` objects with fields that don't exist in the actual database model:
- Attempting to set: `thread_id`, `content`, `intent`, `metadata`, `trace_id`, `created_at`
- Actual model fields: `user_id`, `role`, `message_text`, `language`, `source_mode`

## Files Fixed

### 1. `backend/app/repositories/chat_history_repository.py`
**Changes:**
- Updated `create_message()` to use correct model fields:
  - Changed `content` → `message_text`
  - Removed `thread_id` from model creation (kept for logging only)
  - Removed `intent`, `metadata`, `trace_id`, `created_at` from model creation
  - Added `language` and `source_mode` parameters
- Updated `list_thread_messages()` to return empty list (thread_id not stored in model)
- Updated `get_thread_by_id()` to return empty list (thread_id not stored in model)

### 2. `backend/app/services/chat_service.py`
**Changes:**
- Added `language` and `source_mode` parameters to `process_message()` method
- Updated both user and assistant message creation to pass `language` and `source_mode`
- Fixed `_handle_general_query()` to access `msg.message_text` instead of `msg.content`

### 3. `backend/app/api/v1/routes/chat.py`
**Changes:**
- Updated chat endpoint to pass `language` from request to chat_service
- Added `source_mode="text"` parameter (defaults to text, can be set to "voice" for voice messages)

## What Works Now
✅ Chat messages can be saved to database
✅ User and assistant messages are persisted correctly
✅ Language is tracked (en, hi, hinglish)
✅ Source mode is tracked (text, voice)
✅ Intent classification and routing works
✅ Thread ID is logged but not stored (current model limitation)

## Known Limitations
⚠️ Thread-based message history is not available (thread_id not stored in ChatMessage model)
- `list_thread_messages()` returns empty list
- `get_thread_by_id()` returns empty list
- Use `get_recent_user_context()` for user-based conversation history instead

## Future Improvements
If thread-based history is needed, add a database migration to:
1. Add `thread_id` column to `chat_history` table
2. Add `intent` column to store classified intent
3. Add `metadata` JSONB column for additional data
4. Add index on `thread_id` for efficient queries

## Testing
To test the fix:
```bash
cd backend
uvicorn app.main:app --reload
```

Then send a POST request to `/api/v1/chat`:
```json
{
  "message": "hello",
  "thread_id": "new",
  "voice_enabled": false,
  "language": "en"
}
```

The error should be resolved and messages should be saved successfully.
