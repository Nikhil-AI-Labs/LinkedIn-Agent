# Backend Stabilization Action Plan

**Goal:** Transform backend from 60% complete to production-ready  
**Timeline:** 2-3 weeks  
**Current Status:** 8/25 API tests passing (68% failure rate)

---

## Phase 1: API Contract Freeze (Days 1-2)

### ✅ COMPLETED
- [x] Create honest status assessment (`HONEST_BACKEND_STATUS.md`)
- [x] Create API contract document (`backend/docs/API_CONTRACT.md`)
- [x] Fix TestClient configuration (raise_server_exceptions=False)
- [x] Fix mock_user fixture (remove is_active field)

### TODO: Create Canonical Response Models

**File:** `backend/app/schemas/responses.py`

```python
"""Canonical API response models.

All endpoints MUST return these models. No ad-hoc dicts.
"""

from typing import Any
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model for all endpoints."""
    status: str
    trace_id: str


class ChatResponse(BaseResponse):
    """Response from /api/v1/chat endpoint."""
    intent: str
    thread_id: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class PendingItem(BaseModel):
    """Single pending item."""
    id: int
    type: str  # "draft" | "engagement"
    thread_id: str
    status: str
    created_at: str
    data: dict[str, Any]


class PendingActionsResponse(BaseResponse):
    """Response from /api/v1/pending endpoint."""
    items: list[PendingItem]
    total_count: int


class SelectDraftResponse(BaseResponse):
    """Response from /api/v1/drafts/select endpoint."""
    thread_id: str
    data: dict[str, Any]


class FinalApproveDraftResponse(BaseResponse):
    """Response from /api/v1/drafts/approve endpoint."""
    thread_id: str
    data: dict[str, Any]


class ApproveEngagementResponse(BaseResponse):
    """Response from /api/v1/approve/{action_id} endpoint."""
    action_id: int
    data: dict[str, Any]


class SkipActionResponse(BaseResponse):
    """Response from /api/v1/skip/{action_id} endpoint."""
    action_id: int


class WatchlistProfile(BaseModel):
    """Watchlist profile data."""
    id: int
    linkedin_profile_id: str
    profile_url: str
    name: str | None = None
    headline: str | None = None
    note: str | None = None
    status: str = "active"
    added_at: str
    last_checked: str | None = None


class AddWatchlistResponse(BaseResponse):
    """Response from /api/v1/monitor/add endpoint."""
    profile: WatchlistProfile


class RemoveWatchlistResponse(BaseResponse):
    """Response from /api/v1/monitor/remove/{profile_id} endpoint."""
    profile_id: str


class ListWatchlistResponse(BaseResponse):
    """Response from /api/v1/monitor/list endpoint."""
    profiles: list[WatchlistProfile]
    total_count: int
```

**Action:** Create this file and update all route handlers to use these models.

---

## Phase 2: Fix All 17 Failing Tests (Days 3-5)

### Strategy: One Test at a Time

For each failing test:
1. Read actual route handler
2. Read actual service return value
3. Update test mock to match reality
4. Update test assertions to match reality
5. Run ONLY that test
6. Commit fix
7. Move to next test

### Test Fix Checklist

#### Draft Approval Tests (5 failures)

- [ ] `test_select_draft_variant`
  - Mock should return: `{status, thread_id, trace_id, data}`
  - Not: `{message, draft_id, next_step}`

- [ ] `test_select_draft_with_edit`
  - Same fix as above

- [ ] `test_final_approve_draft_approved`
  - Mock should return: `{status: "posted", thread_id, trace_id, data: {post_id, final_content}}`
  - Not: `{message, post_url, completed}`

- [ ] `test_final_approve_draft_rejected`
  - Mock should return: `{status: "rejected", thread_id, trace_id, data: {message}}`
  - Not: `{message, next_step, completed}`

- [ ] `test_idempotency_on_duplicate_selection`
  - Same fix as select_draft

#### Engagement Approval Tests (4 failures)

- [ ] `test_approve_engagement_no_edit`
  - Mock should return: `{status: "completed", action_id, trace_id, data}`
  - Not: `{message, action_id, completed}`

- [ ] `test_approve_engagement_with_edit`
  - Same fix as above

- [ ] `test_skip_action`
  - Mock should return: `{status: "skipped", action_id, trace_id}`
  - Not: `{message, action_id, skipped}`

- [ ] `test_get_pending_actions`
  - Mock should return: `{status, trace_id, items: [...], total_count}`
  - Not: `{drafts: [...], engagements: [...], total_count}`

#### Watchlist Management Tests (7 failures)

- [ ] `test_add_watchlist_by_url`
  - Mock should return: `{status: "added", trace_id, profile: {...}}`
  - Not: `{message, profile_id, added}`

- [ ] `test_add_watchlist_by_member_id`
  - Same fix as above

- [ ] `test_add_watchlist_duplicate_error`
  - Check error handling matches ConflictError format

- [ ] `test_remove_watchlist`
  - Mock should return: `{status: "removed", trace_id, profile_id}`
  - Not: `{message, profile_id, removed}`

- [ ] `test_remove_watchlist_not_found`
  - Check error handling matches NotFoundError format

- [ ] `test_list_watchlist`
  - Mock should return: `{status: "success", trace_id, profiles: [...], total_count}`
  - Not: `{profiles: [...], total_count}` (missing status, trace_id)

- [ ] `test_list_watchlist_empty`
  - Same fix as above

#### Error Handling Test (1 failure)

- [ ] `test_internal_server_error_handling`
  - Already fixed with `raise_server_exceptions=False`
  - Verify test passes after client fixture fix

---

## Phase 3: Real Integration Tests (Days 6-8)

### 3.1 Setup Real Test Database

**File:** `backend/tests/conftest.py`

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from langgraph.checkpoint.postgres import PostgresSaver

from app.db.base import Base
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine."""
    # Use separate test database
    test_db_url = settings.DATABASE_URL.replace("linkedin_agent", "linkedin_agent_test")
    
    engine = create_async_engine(test_db_url, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def real_checkpointer():
    """Create real PostgresSaver for integration tests."""
    test_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://"
    ).replace("linkedin_agent", "linkedin_agent_test")
    
    checkpointer = PostgresSaver.from_conn_string(test_db_url)
    checkpointer.setup()
    
    yield checkpointer
    
    # Cleanup checkpoint tables
    # (implementation depends on PostgresSaver API)
```

### 3.2 Write Critical Integration Test

**File:** `backend/tests/integration/test_graph_resume.py`

```python
"""CRITICAL: Real graph interrupt/resume integration test.

This test MUST pass to prove the core value proposition works.
"""

import pytest
from datetime import datetime

from app.agents.content_creation_agent import (
    start_content_creation,
    resume_content_creation,
    build_content_creation_graph
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_graph_interrupt_and_resume(test_db_session, real_checkpointer):
    """Test real graph interrupt and resume across "restart"."""
    
    user_id = 1
    user_input = "Write a post about AI"
    
    # === Phase 1: Start graph and interrupt ===
    initial_state = await start_content_creation(
        user_id=user_id,
        user_input=user_input,
        db=test_db_session,
        checkpointer=real_checkpointer
    )
    
    thread_id = initial_state["thread_id"]
    
    # Verify graph interrupted at draft selection
    assert initial_state["status"] == "awaiting_selection"
    assert initial_state["approval_required"] is True
    assert "drafts" in initial_state
    assert len(initial_state["drafts"]) > 0
    
    # Verify checkpoint stored in Postgres
    config = {"configurable": {"thread_id": thread_id}}
    graph = build_content_creation_graph(real_checkpointer)
    
    checkpoint = await graph.aget_state(config)
    assert checkpoint is not None
    assert checkpoint.values["status"] == "awaiting_selection"
    
    print(f"✅ Phase 1: Graph interrupted and checkpoint stored")
    
    # === Phase 2: Simulate app restart ===
    # Create NEW graph instance (simulates restart)
    new_graph = build_content_creation_graph(real_checkpointer)
    
    # Verify state can be retrieved after "restart"
    restored_state = await new_graph.aget_state(config)
    assert restored_state is not None
    assert restored_state.values["thread_id"] == thread_id
    assert restored_state.values["user_id"] == user_id
    
    print(f"✅ Phase 2: State restored after restart")
    
    # === Phase 3: Resume with user selection ===
    final_state = await resume_content_creation(
        thread_id=thread_id,
        approved=True,
        selected_draft_id=1,  # Select first variant
        checkpointer=real_checkpointer
    )
    
    # Verify graph completed successfully
    assert "final_content" in final_state
    assert final_state["final_content"] is not None
    
    print(f"✅ Phase 3: Graph resumed and completed")
    
    # === Phase 4: Verify final checkpoint ===
    final_checkpoint = await new_graph.aget_state(config)
    assert final_checkpoint.values.get("final_content") is not None
    
    print(f"✅ Phase 4: Final state persisted")
    
    print(f"\n🎉 INTEGRATION TEST PASSED: Graph interrupt/resume works!")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitoring_graph_interrupt_resume(test_db_session, real_checkpointer):
    """Test monitoring agent interrupt/resume."""
    # Similar test for monitoring agent
    pytest.skip("TODO: Implement after content creation test passes")
```

### 3.3 Add Test Runner Scripts

**File:** `backend/scripts/run_integration_tests.sh`

```bash
#!/bin/bash

# Run integration tests against real PostgreSQL

echo "Setting up test database..."
export DATABASE_URL="postgresql+asyncpg://postgres:postgres123@localhost:5432/linkedin_agent_test"

echo "Running integration tests..."
pytest tests/integration -v --integration --tb=short

echo "Cleaning up test database..."
# Cleanup handled by fixtures

echo "Done!"
```

---

## Phase 4: Wire LinkedIn Operations (Days 9-11)

### 4.1 Remove TODO Comments in Agents

**Files to fix:**
- `backend/app/agents/content_creation_agent.py`
- `backend/app/agents/monitoring_agent.py`

**In content_creation_agent.py:**

```python
async def post_to_linkedin(state: ContentCreationState) -> ContentCreationState:
    """Post content to LinkedIn via LinkedIn manager."""
    log_node_entry("post_to_linkedin", state)
    
    try:
        # Check idempotency
        draft_id = state.get("draft_id")
        if draft_id and IdempotencyGuard.is_completed(state, "post_created", draft_id):
            logger.info("post_already_created_skipping", draft_id=draft_id, trace_id=state["trace_id"])
            return state
        
        validate_required_fields(state, ["final_content", "user_id", "trace_id"], "post_to_linkedin")
        
        final_content = state["final_content"]
        
        # REAL LinkedIn integration
        from app.services.linkedin import get_linkedin_manager
        linkedin = get_linkedin_manager()
        
        result = await linkedin.create_post(
            content=final_content,
            trace_id=state["trace_id"]
        )
        
        post_id = result.post_id
        
        state["post_id"] = post_id
        state["status"] = "posted"
        state["updated_at"] = datetime.utcnow()
        
        # Mark as completed
        if draft_id:
            state = IdempotencyGuard.mark_completed(state, "post_created", draft_id)
        
        logger.info("post_created_successfully", post_id=post_id, trace_id=state["trace_id"])
        
    except Exception as e:
        state = handle_node_error(state, "post_to_linkedin", e)
    
    log_node_exit("post_to_linkedin", state)
    return state
```

**In monitoring_agent.py:**

```python
async def fetch_watchlist_posts(state: MonitoringState) -> MonitoringState:
    """Fetch recent posts from watchlist profiles."""
    log_node_entry("fetch_watchlist_posts", state)
    
    try:
        validate_required_fields(state, ["watchlist_profile_ids", "trace_id"], "fetch_watchlist_posts")
        
        profile_ids = state["watchlist_profile_ids"]
        
        if not profile_ids:
            logger.info("empty_watchlist_skipping", trace_id=state["trace_id"])
            state["watchlist_posts"] = []
            return state
        
        # REAL LinkedIn integration
        from app.services.linkedin import get_linkedin_manager
        linkedin = get_linkedin_manager()
        
        watchlist_posts = []
        for profile_id in profile_ids[:10]:  # Limit to 10 profiles to avoid rate limits
            try:
                posts = await linkedin.get_profile_posts(
                    profile_id=profile_id,
                    limit=5,  # Last 5 posts per profile
                    trace_id=state["trace_id"]
                )
                watchlist_posts.extend(posts)
            except Exception as e:
                logger.warning(
                    "failed_to_fetch_profile_posts",
                    profile_id=profile_id,
                    error=str(e),
                    trace_id=state["trace_id"]
                )
                # Continue with other profiles
        
        state["watchlist_posts"] = watchlist_posts
        state["status"] = "watchlist_posts_fetched"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "watchlist_posts_fetched",
            num_posts=len(watchlist_posts),
            trace_id=state["trace_id"]
        )
        
    except Exception as e:
        state = handle_node_error(state, "fetch_watchlist_posts", e)
    
    log_node_exit("fetch_watchlist_posts", state)
    return state
```

### 4.2 Add LinkedIn Integration Tests

**File:** `backend/tests/integration/test_linkedin_live.py`

```python
"""LinkedIn live API integration tests.

WARNING: These tests interact with real LinkedIn. 
- Use test account only
- Run manually, not in CI/CD
- Respect rate limits
"""

import pytest
from app.services.linkedin import get_linkedin_manager


@pytest.mark.integration
@pytest.mark.manual  # Manual run only
@pytest.mark.asyncio
async def test_real_linkedin_create_post():
    """Test real LinkedIn post creation.
    
    WARNING: This creates a real LinkedIn post.
    Run manually with test account only.
    """
    pytest.skip("Manual test only - creates real LinkedIn post")
    
    linkedin = get_linkedin_manager()
    
    result = await linkedin.create_post(
        content="Test post from LinkedIn AI Agent - automated test",
        trace_id="test-trace"
    )
    
    assert result.post_id is not None
    assert result.success is True
    
    print(f"✅ Created post: {result.post_id}")
    print(f"⚠️  Manual cleanup required: Delete post at {result.post_url}")
```

---

## Phase 5: Test Organization (Days 12-13)

### 5.1 Reorganize Test Structure

```
backend/tests/
├── unit/                          # Fast, no external deps
│   ├── test_routes.py            # FastAPI routing + validation
│   ├── test_services.py          # Service logic with mocked repos
│   ├── test_agents.py            # Agent nodes with mocked services
│   ├── test_voice.py             # Voice utils with mocked Sarvam
│   ├── test_llm.py               # LLM manager with mocked APIs
│   └── test_linkedin_units.py    # LinkedIn classes with mocks
│
├── integration/                   # Slow, real dependencies
│   ├── test_graph_resume.py     # Real Postgres checkpointer
│   ├── test_api_integration.py  # Real DB + real services
│   └── test_linkedin_live.py    # Real LinkedIn API (manual)
│
└── conftest.py                    # Shared fixtures
```

### 5.2 Update pytest Configuration

**File:** `backend/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "unit: Unit tests (fast, mocked dependencies)",
    "integration: Integration tests (slow, real dependencies)",
    "manual: Manual tests (require human oversight)",
]

# Default: run only unit tests
addopts = "-v --tb=short -m 'not integration and not manual'"
```

### 5.3 Add Test Runner Commands

**File:** `backend/Makefile`

```makefile
.PHONY: test test-unit test-integration test-all

test:
	# Default: unit tests only (fast)
	pytest tests/unit -v

test-unit:
	# Explicit unit tests
	pytest tests/unit -v

test-integration:
	# Integration tests (requires Postgres)
	pytest tests/integration -v --integration

test-all:
	# All tests
	pytest tests/ -v --integration

test-coverage:
	# With coverage report
	pytest tests/unit --cov=app --cov-report=html
```

---

## Phase 6: Documentation & Polish (Days 14-15)

### 6.1 Update README

Add sections:
- API Contract reference
- How to run tests (unit vs integration)
- LinkedIn integration setup
- Rate limiting guidelines
- Security considerations

### 6.2 Add Deployment Guide

**File:** `backend/docs/DEPLOYMENT.md`

Include:
- Environment variables
- Database migrations
- Checkpointer setup
- LinkedIn credentials
- Rate limiting configuration

### 6.3 Security Audit

Check:
- [ ] Credentials never logged
- [ ] Encrypted password storage
- [ ] SQL injection prevention (using ORMs)
- [ ] Input validation on all endpoints
- [ ] Rate limiting (TODO - not implemented yet)

---

## Success Criteria

Backend is production-ready when:

- [ ] All 25 API integration tests passing (100%)
- [ ] API contract frozen and documented
- [ ] Response schemas use Pydantic models
- [ ] Real PostgreSQL interrupt/resume test passing
- [ ] LinkedIn operations wired (no TODO comments)
- [ ] Integration tests separated from unit tests
- [ ] Test coverage > 80%
- [ ] Documentation complete
- [ ] Security audit passed

---

## Timeline

| Week | Days | Focus | Deliverable |
|------|------|-------|-------------|
| 1 | 1-2 | API Contract | Frozen contract, response models |
| 1 | 3-5 | Fix Tests | 25/25 API tests passing |
| 2 | 6-8 | Integration | Real graph resume proven |
| 2 | 9-11 | LinkedIn | Real operations wired |
| 3 | 12-13 | Organization | Test structure clean |
| 3 | 14-15 | Polish | Docs, security audit |

**Total: 15 working days (3 weeks)**

---

## After Stabilization: UI Development

**ONLY AFTER backend is stable:**

1. Use frozen API contract as OpenAPI spec
2. Generate TypeScript types from contract
3. Build Next.js frontend against stable API
4. No more "building UI while API changes"

---

## Next Immediate Actions

1. ✅ Read this plan
2. Create `backend/app/schemas/responses.py` with canonical models
3. Fix first failing test: `test_select_draft_variant`
4. Fix second failing test: `test_select_draft_with_edit`
5. Continue until all 17 tests fixed
6. Write real graph resume integration test
7. Wire LinkedIn operations
8. Deploy to production

---

**Created:** June 25, 2026  
**Status:** Active  
**Owner:** Development Team
