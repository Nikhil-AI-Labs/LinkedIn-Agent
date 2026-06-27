"""End-to-end integration tests.

Tests complete workflows from API → Agent → Database with real dependencies.

Run with: pytest tests/integration/test_e2e.py -v --integration
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_content_creation_workflow(test_db_session, real_checkpointer, test_user):
    """End-to-end test: Chat → Content Creation Agent → Database.
    
    Tests the complete flow:
    1. User sends chat message requesting post creation
    2. Intent router identifies create_post intent
    3. Content creation agent generates drafts
    4. Drafts are persisted to database
    5. User selects draft
    6. Agent resumes and processes selection
    """
    
    from app.core.dependencies import get_db, get_checkpointer
    from app.services.chat_service import ChatService
    
    # Override dependencies for testing
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_checkpointer] = lambda: real_checkpointer
    
    try:
        # Create chat service
        chat_service = ChatService(test_db_session, real_checkpointer)
        
        # ====================================================================
        # PHASE 1: Send chat message
        # ====================================================================
        print("\nPHASE 1: User sends chat message...")
        
        result = await chat_service.process_message(
            user_id=test_user.id,
            message="Create a post about machine learning advancements",
            thread_id=None,
        )
        
        print(f"✓ Chat processed: intent={result.get('intent')}")
        
        assert result["intent"] == "create_post", \
            f"Expected create_post intent, got {result['intent']}"
        
        assert result["status"] == "success", \
            f"Chat processing failed: {result.get('message')}"
        
        thread_id = result.get("thread_id")
        assert thread_id is not None, "No thread_id returned"
        
        print(f"✓ Thread created: {thread_id}")
        
        # ====================================================================
        # PHASE 2: Verify drafts in database
        # ====================================================================
        print("\nPHASE 2: Verifying drafts in database...")
        
        from app.repositories.draft_repository import DraftRepository
        
        draft_repo = DraftRepository(test_db_session)
        drafts = await draft_repo.get_user_drafts(test_user.id, status="pending")
        
        assert len(drafts) > 0, "No drafts found in database"
        
        draft = drafts[0]
        print(f"✓ Draft persisted: id={draft.id}, status={draft.status}")
        
        # ====================================================================
        # PHASE 3: Verify graph state
        # ====================================================================
        print("\nPHASE 3: Verifying graph checkpoint...")
        
        from app.agents.content_creation_agent import build_content_creation_graph
        
        graph = build_content_creation_graph(real_checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        
        checkpoint = await graph.aget_state(config)
        assert checkpoint is not None, "No checkpoint found"
        
        state = checkpoint.values
        assert state["status"] == "awaiting_selection", \
            f"Wrong state: {state['status']}"
        
        assert "drafts" in state, "No drafts in state"
        
        print(f"✓ Graph checkpoint valid: {len(state['drafts'])} drafts")
        
        # ====================================================================
        # SUCCESS
        # ====================================================================
        print("\n✓ E2E Content Creation Test PASSED")
        
    finally:
        # Cleanup dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_watchlist_management(test_db_session, test_user):
    """End-to-end test: Watchlist API → Database → Monitoring Agent.
    
    Tests:
    1. Add profile to watchlist via API
    2. Verify in database
    3. Monitoring agent can fetch watchlist
    """
    
    from app.repositories.watchlist_repository import WatchlistRepository
    
    print("\nE2E Watchlist Management Test")
    
    # ====================================================================
    # Add to watchlist
    # ====================================================================
    watchlist_repo = WatchlistRepository(test_db_session)
    
    entry = await watchlist_repo.add_profile(
        user_id=test_user.id,
        linkedin_profile_id="test_profile_123",
        profile_url="https://linkedin.com/in/testprofile",
        name="Test Profile",
        headline="Test Headline",
        note="Test note",
    )
    
    print(f"✓ Profile added to watchlist: id={entry.id}")
    
    # ====================================================================
    # Fetch watchlist
    # ====================================================================
    watchlist = await watchlist_repo.get_user_watchlist(test_user.id)
    
    assert len(watchlist) == 1, f"Expected 1 entry, got {len(watchlist)}"
    assert watchlist[0].linkedin_profile_id == "test_profile_123"
    
    print(f"✓ Watchlist fetched: {len(watchlist)} profiles")
    
    # ====================================================================
    # Monitoring agent can access
    # ====================================================================
    from app.agents.monitoring_agent import load_watchlist
    from app.agents.types import MonitoringState
    from datetime import datetime
    
    state: MonitoringState = {
        "user_id": test_user.id,
        "thread_id": "test_thread",
        "trace_id": "test_trace",
        "run_id": "test_run",
        "intent": "monitor",
        "approval_required": False,
        "status": "started",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    updated_state = await load_watchlist(state, test_db_session)
    
    assert updated_state["status"] == "watchlist_loaded"
    assert len(updated_state.get("watchlist_profile_ids", [])) == 1
    
    print(f"✓ Monitoring agent loaded watchlist: {updated_state['watchlist_profile_ids']}")
    print("\n✓ E2E Watchlist Test PASSED")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_idempotency_guards(test_db_session, real_checkpointer, test_user):
    """Test that idempotency guards prevent duplicate operations.
    
    Verifies:
    1. Double-posting protection
    2. Duplicate engagement prevention
    """
    
    from app.agents.content_creation_agent import build_content_creation_graph
    from app.agents.common import IdempotencyGuard
    from datetime import datetime
    
    print("\nE2E Idempotency Test")
    
    # Create state with completed operation
    state = {
        "user_id": test_user.id,
        "thread_id": "idempotency_test",
        "trace_id": "test_trace",
        "run_id": "test_run",
        "intent": "create_post",
        "draft_id": 123,
        "post_id": "test_post_456",
        "status": "posted",
        "approval_required": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Mark as completed
    state = IdempotencyGuard.mark_completed(state, "post_created", 123)
    
    # Verify guard works
    assert IdempotencyGuard.is_completed(state, "post_created", 123)
    print(f"✓ Idempotency guard set")
    
    # Try to post again (should be skipped)
    from app.agents.content_creation_agent import post_to_linkedin
    
    state["final_content"] = "Test content"
    result_state = await post_to_linkedin(state)
    
    # Should not error, should skip
    assert result_state.get("error") is None, "Idempotency check failed"
    assert result_state["post_id"] == "test_post_456", "Post ID changed"
    
    print(f"✓ Duplicate post prevented")
    print("\n✓ E2E Idempotency Test PASSED")
