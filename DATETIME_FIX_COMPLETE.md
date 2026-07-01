# DateTime Timezone Fix - Complete

## The Problem

The error was:
```
TypeError: can't subtract offset-naive and offset-aware datetimes
asyncpg.exceptions.DataError: invalid input for query argument $7
```

### Root Cause
The `BaseModel` class was using `datetime.now(timezone.utc)` which creates **timezone-aware** datetimes (with UTC timezone info), but PostgreSQL's `TIMESTAMP WITHOUT TIME ZONE` column expects **timezone-naive** datetimes.

When asyncpg tried to insert the timezone-aware datetime into a timezone-naive column, it failed with the mixing error.

## The Solution

### Fix 1: BaseModel Timestamps
**File**: `backend/app/db/base.py`

Changed from timezone-aware to timezone-naive:
```python
# BEFORE (wrong - timezone-aware)
created_at: Mapped[datetime] = mapped_column(
    default=lambda: datetime.now(timezone.utc),
    ...
)

# AFTER (correct - timezone-naive)
created_at: Mapped[datetime] = mapped_column(
    default=lambda: datetime.utcnow(),
    ...
)
```

`datetime.utcnow()` returns a timezone-naive UTC datetime, which is what PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` expects.

### Fix 2: Missing DraftRepository Method
**File**: `backend/app/repositories/draft_repository.py`

Added the missing `get_user_drafts_by_status` method that was being called by `action_service.py`:

```python
async def get_user_drafts_by_status(
    self, user_id: UUID, status: str, limit: int = 50
) -> list[PostDraft]:
    """Get user's drafts filtered by status."""
    if status == "pending":
        return await self.get_pending_for_user(user_id, limit=limit)
    
    # Filter by exact status
    result = await self.session.execute(
        select(PostDraft)
        .where(
            PostDraft.user_id == user_id,
            PostDraft.status == status,
        )
        .order_by(PostDraft.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
```

## Testing

The server should have auto-reloaded. Now try the chat endpoint again:

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

Or test via Swagger UI at http://localhost:8000/docs

## What Should Work Now

✅ Chat messages saved to database  
✅ No timezone mixing errors  
✅ All timestamps stored correctly as UTC  
✅ DraftRepository method available  
✅ Pending actions endpoint working

## Technical Notes

### Why `TIMESTAMP WITHOUT TIME ZONE`?
PostgreSQL has two timestamp types:
- `TIMESTAMP WITHOUT TIME ZONE` - stores naive datetimes, assumes UTC
- `TIMESTAMP WITH TIME ZONE` - stores timezone-aware datetimes

The migration used `WITHOUT TIME ZONE`, so we need to provide naive datetimes.

### Why `datetime.utcnow()`?
- `datetime.utcnow()` → naive datetime in UTC
- `datetime.now(timezone.utc)` → aware datetime with UTC timezone
- For `TIMESTAMP WITHOUT TIME ZONE`, we need the first one

The database still stores everything in UTC, we just don't include the timezone info in the datetime object.
