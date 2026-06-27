# LinkedIn AI Agent - API Contract v1.0

**Status:** DRAFT - Needs Stabilization  
**Last Updated:** June 25, 2026

This document defines the canonical API contract for all backend endpoints. All route handlers, service methods, and tests MUST conform to this contract.

---

## Common Structures

### Standard Response Envelope
All successful API responses follow this structure:
```typescript
{
  status: "success" | "error" | "pending" | string,
  trace_id: string,           // Request trace ID for debugging
  [endpoint-specific fields]
}
```

### Standard Error Response
```typescript
{
  status: "error",
  error_code: string,          // Machine-readable error code
  message: string,             // Human-readable error message
  details: object | null,      // Additional error context
  trace_id: string
}
```

### Status Codes
- `200 OK` - Success
- `400 Bad Request` - Validation error
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource
- `422 Unprocessable Entity` - Schema validation failure
- `500 Internal Server Error` - Unexpected error

---

## Endpoints

### 1. POST /api/v1/chat

**Purpose:** Process user chat message with intent routing

**Request:**
```typescript
{
  message: string,              // 1-5000 chars, required
  thread_id: string | null,     // Optional conversation thread
  voice_enabled: boolean,       // Default: false
  language: "en" | "hi" | "hinglish"  // Default: "en"
}
```

**Response (200):**
```typescript
{
  intent: string,               // Classified intent
  status: string,               // "success" | "pending" | etc
  thread_id: string | null,     // Conversation thread ID
  trace_id: string,
  message: string | null,       // Assistant response text
  data: {
    [key: string]: any          // Intent-specific data
    voice_audio?: string,       // Base64 audio if voice_enabled
    voice_mime_type?: string,
    voice_error?: string
  }
}
```

**Possible Intents:**
- `create_post` - Start content creation workflow
- `view_pending` - Show pending approvals
- `list_watchlist` - Show watchlist profiles
- `add_watchlist` - Instruction to use monitor/add endpoint
- `remove_watchlist` - Instruction to use monitor/remove endpoint
- `general_query` - General conversation

---

### 2. POST /api/v1/voice/transcribe

**Purpose:** Transcribe audio to text

**Request:**
```typescript
{
  audio_data: string,           // Base64 encoded audio, required
  language: "en" | "hi" | "hinglish"  // Default: "en"
}
```

**Response (200):**
```typescript
{
  text: string,                 // Transcribed text
  language: string,             // Detected/used language
  confidence: number | null     // 0.0-1.0 confidence score
}
```

**Response (500):**
```typescript
{
  status: "error",
  message: string,
  trace_id: string
}
```

---

### 3. POST /api/v1/voice/speak

**Purpose:** Synthesize text to speech

**Request:**
```typescript
{
  text: string,                 // 1-5000 chars, required
  language: "en" | "hi"         // Default: "en"
}
```

**Response (200):**
```typescript
{
  audio_data: string | null,    // Base64 encoded audio
  audio_available: boolean,     // true if synthesis succeeded
  mime_type: string | null,     // "audio/mpeg" or null
  fallback_text: string | null, // Original text if TTS failed
  error: string | null          // Error message if failed
}
```

**Note:** Returns 200 even on TTS failure (graceful degradation)

---

### 4. GET /api/v1/pending

**Purpose:** List all pending items for current user

**Response (200):**
```typescript
{
  status: "success",
  trace_id: string,
  items: Array<{
    id: number,
    type: "draft" | "engagement",
    thread_id: string,
    status: string,
    created_at: string,         // ISO 8601
    data: object                // Type-specific data
  }>,
  total_count: number
}
```

---

### 5. POST /api/v1/drafts/select

**Purpose:** Select a draft variant or provide custom content

**Request:**
```typescript
{
  thread_id: string,            // Required
  selected_draft_id: number | null,  // Variant number (1-3)
  user_edited_content: string | null // Custom content
}
```

**Response (200):**
```typescript
{
  status: string,               // Graph status after selection
  thread_id: string,
  trace_id: string,
  data: {
    final_content: string | null
  }
}
```

---

### 6. POST /api/v1/drafts/approve

**Purpose:** Final approval or rejection of draft before posting

**Request:**
```typescript
{
  thread_id: string,            // Required
  approved: boolean             // Required
}
```

**Response (200):**
```typescript
{
  status: "posted" | "rejected" | "error",
  thread_id: string,
  trace_id: string,
  data: {
    post_id: string | null,     // LinkedIn post ID if posted
    final_content: string | null
  }
}
```

---

### 7. POST /api/v1/approve/{action_id}

**Purpose:** Approve and optionally edit an engagement action

**Path Parameters:**
- `action_id: int` - Pending engagement ID (>= 1)

**Request:**
```typescript
{
  thread_id: string,            // Required
  action_index: number,         // Index in suggested actions (>= 0)
  edited_comment: string | null // Optional edited comment
}
```

**Response (200):**
```typescript
{
  status: "completed" | "error",
  action_id: number,
  trace_id: string,
  data: {
    engagement_result: Array<object>
  }
}
```

**Response (404):**
```typescript
{
  status: "error",
  error_code: "NOT_FOUND",
  message: "PendingEngagement not found: {action_id}",
  trace_id: string
}
```

---

### 8. DELETE /api/v1/skip/{action_id}

**Purpose:** Skip a pending action

**Path Parameters:**
- `action_id: int` - Pending engagement ID (>= 1)

**Request:**
```typescript
{
  thread_id: string | null,     // Optional for graph resume
  reason: string | null         // Optional skip reason
}
```

**Response (200):**
```typescript
{
  status: "skipped",
  action_id: number,
  trace_id: string
}
```

**Response (404):**
```typescript
{
  status: "error",
  error_code: "NOT_FOUND",
  message: "PendingEngagement not found: {action_id}",
  trace_id: string
}
```

---

### 9. POST /api/v1/monitor/add

**Purpose:** Add a LinkedIn profile to watchlist

**Request:**
```typescript
{
  profile_url: string | null,   // LinkedIn profile URL (https://linkedin.com/in/username)
  member_id: string | null,     // Or LinkedIn member ID
  note: string | null           // Optional note about this profile
}
```

**Note:** Must provide either `profile_url` OR `member_id`

**Response (200):**
```typescript
{
  status: "added",
  trace_id: string,
  profile: {
    id: number,                 // Watchlist entry ID
    linkedin_profile_id: string,
    profile_url: string,
    name: string | null,        // Populated after validation
    headline: string | null,
    note: string | null,
    status: "active",
    added_at: string,           // ISO 8601
    last_checked: string | null
  }
}
```

**Response (400):**
```typescript
{
  status: "error",
  error_code: "VALIDATION_ERROR",
  message: "Either profile_url or member_id is required",
  field: "profile_url" | "member_id",
  trace_id: string
}
```

**Response (409):**
```typescript
{
  status: "error",
  error_code: "CONFLICT",
  message: "Profile {profile_id} is already in your watchlist",
  resource: "watchlist",
  trace_id: string
}
```

---

### 10. DELETE /api/v1/monitor/remove/{profile_id}

**Purpose:** Remove a profile from watchlist

**Path Parameters:**
- `profile_id: string` - LinkedIn profile ID (1-100 chars)

**Response (200):**
```typescript
{
  status: "removed",
  trace_id: string,
  profile_id: string
}
```

**Response (404):**
```typescript
{
  status: "error",
  error_code: "NOT_FOUND",
  message: "WatchlistEntry not found: {profile_id}",
  trace_id: string
}
```

---

### 11. GET /api/v1/monitor/list

**Purpose:** List all profiles in watchlist

**Response (200):**
```typescript
{
  status: "success",
  trace_id: string,
  profiles: Array<{
    id: number,
    linkedin_profile_id: string,
    profile_url: string,
    name: string | null,
    headline: string | null,
    note: string | null,
    status: "active",
    added_at: string,           // ISO 8601
    last_checked: string | null
  }>,
  total_count: number
}
```

---

## Authentication & Authorization

**Current:** Simplified for MVP - single user system

**Headers:**
- `X-User-ID: 1` (hardcoded for MVP)
- `X-Trace-ID: <uuid>` (auto-generated if not provided)

**Future:** OAuth2 with JWT tokens

---

## Rate Limiting

**Not Yet Implemented**

**Future Requirements:**
- 100 requests/minute per user for chat endpoints
- 10 requests/hour for LinkedIn write operations (post, comment)
- 429 response when exceeded

---

## Versioning

**Current:** v1 (in URL path `/api/v1/...`)

**Breaking Changes:** Will require new version (`/api/v2/...`)

**Non-Breaking Changes:** Can be added to v1

---

## Validation Rules

### String Lengths
- `message`: 1-5000 chars
- `text` (TTS): 1-5000 chars
- `note`: 0-500 chars
- `profile_id`: 1-100 chars

### Enums
- `language`: "en", "hi", "hinglish"
- `voice language` (TTS): "en", "hi"

### IDs
- `action_id`: integer >= 1
- `selected_draft_id`: integer 1-3 or null
- `action_index`: integer >= 0

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| VALIDATION_ERROR | 400 | Request validation failed |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Duplicate resource |
| INVALID_STATE | 409 | Invalid workflow state |
| INTERNAL_ERROR | 500 | Unexpected server error |

---

## Implementation Checklist

- [ ] Create `backend/app/schemas/responses.py` with canonical response models
- [ ] Update all route handlers to use response models
- [ ] Update all service methods to return dict matching response models
- [ ] Update all tests to assert against this contract
- [ ] Generate OpenAPI spec from this contract
- [ ] Add response validation middleware

---

## Change Log

### 2026-06-25
- Initial contract definition
- Identified schema drift between services and tests
- Marked as DRAFT pending stabilization

---

**Next Steps:**
1. Review and approve contract
2. Implement response models in code
3. Fix all 17 failing tests against this contract
4. Mark as STABLE v1.0
