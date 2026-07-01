# Chat API Critical Fixes - COMPLETED

## Issues Fixed

### 1. Missing Repository Method Error
**Error**: `'PendingEngagementRepository' object has no attribute 'get_user_pending'`

**Root Cause**: The repository method was named `get_pending_for_user` but the services were calling `get_user_pending`

**Files Fixed**:
- `backend/app/services/action_service.py` - Changed `get_user_pending` → `get_pending_for_user`
- `backend/app/services/chat_service.py` - Changed `get_user_pending` → `get_pending_for_user`

### 2. Missing LLMTask Enum Value Error
**Error**: `AttributeError: GENERAL_RESPONSE`

**Root Cause**: The `LLMTask` enum has `GENERAL_QUERY` but the code was using `GENERAL_RESPONSE`

**Files Fixed**:
- `backend/app/services/chat_service.py` - Changed `LLMTask.GENERAL_RESPONSE` → `LLMTask.GENERAL_QUERY`

### 3. Model Field Name Mismatches

**Root Cause**: Services were using wrong field names that don't exist in the database models

**Files Fixed**:

#### action_service.py - PendingEngagement fields:
- ❌ `engagement.trace_id` → ✅ `engagement.graph_run_id`
- ❌ `engagement.status.value` → ✅ `engagement.status` (already a string)
- ❌ `engagement.post_id` → ✅ `engagement.source_post_url`
- ❌ `engagement.engagement_type.value` → ✅ `engagement.action_type`
- ❌ `engagement.suggested_content` → ✅ `engagement.suggested_text`
- ❌ `engagement.priority` → ✅ `engagement.source_type`

#### action_service.py - PostDraft fields:
- ❌ `draft.trace_id` → ✅ `draft.graph_run_id`
- ❌ `draft.status.value` → ✅ `draft.status` (already a string)
- ❌ `draft.brief` → ✅ `draft.idea_input`
- ❌ `draft.variants` → ✅ Combined `draft.draft_text`, `draft.variant_index`, `draft.score`

#### chat_service.py - PendingEngagement fields:
- ❌ `item.post_id` → ✅ `item.source_post_url`
- ❌ `item.engagement_type.value` → ✅ `item.action_type`
- ❌ `item.suggested_content` → ✅ `item.suggested_text`
- ❌ `item.priority` → ✅ `item.source_type`

### 4. Type Conversion Issues

**Root Cause**: Services received user_id as string but were passing it directly to repositories that expect UUID

**Files Fixed**:
- `backend/app/services/action_service.py` - Added UUID conversion: `user_uuid = UUID(user_id)`
- `backend/app/services/chat_service.py` - Added UUID conversion: `user_uuid = UUID(user_id)`

## Testing

### Test the Chat Endpoint

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/chat' \
  -H 'accept: application/json' \
  -H 'X-User-ID: 1' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "hello",
  "thread_id": "new",
  "voice_enabled": false,
  "language": "en"
}'
```

**Expected Result**: 
- ✅ No `AttributeError: get_user_pending`
- ✅ No `AttributeError: GENERAL_RESPONSE`
- ✅ Response with general query intent and LLM-generated message

### Test the Pending Actions Endpoint

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/pending' \
  -H 'accept: application/json' \
  -H 'X-User-ID: 1'
```

**Expected Result**:
- ✅ No `AttributeError: get_user_pending`
- ✅ Returns list of pending items (drafts and engagements) with correct field names

## Correct Database Model Field Names

### PendingEngagement Model
```python
id: UUID
user_id: UUID
graph_run_id: UUID | None
source_type: str  # "comment_reply", "watchlist_post", etc.
source_post_url: str | None
source_post_urn: str | None
target_member_id: str | None
action_type: str  # "like", "celebrate", "support", "insightful", "comment"
suggested_text: str | None  # Suggested comment text if action_type=comment
status: str  # "pending", "approved", "skipped", "posted", "failed"
created_at: datetime
updated_at: datetime
```

### PostDraft Model
```python
id: UUID
user_id: UUID
graph_run_id: UUID | None
idea_input: str  # Original user idea
draft_text: str  # Generated draft text
variant_index: int  # Draft variant number (0, 1, 2)
score: int | None  # Score 0-100 from evaluation
score_breakdown_json: dict | None  # Detailed score breakdown
status: str  # "drafted", "approved", "posted", "failed"
final_text: str | None  # User-edited final text before posting
linkedin_post_url: str | None
linkedin_post_urn: str | None
posted_at: datetime | None
created_at: datetime
updated_at: datetime
```

## Status

✅ **ALL FIXES APPLIED** - The backend server should now handle chat and pending action requests without errors.

## Next Steps

1. Restart the backend server (it will auto-reload if using `--reload` flag)
2. Test both endpoints using the curl commands above
3. If any issues remain, check the server logs for specific errors
