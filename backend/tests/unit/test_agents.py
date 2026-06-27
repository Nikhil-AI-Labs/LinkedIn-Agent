"""Integration tests for LangGraph agents.

Tests cover:
- Content Creation Agent workflow
- Monitoring Agent workflow
- Interrupt/resume logic
- Idempotency guards
- State persistence
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.content_creation_agent import (
    parse_request,
    generate_drafts,
    evaluate_drafts,
    persist_drafts,
    interrupt_for_selection,
    accept_user_edit,
    final_approval_interrupt,
    post_to_linkedin,
    mark_posted_or_failed,
    build_content_creation_graph,
)
from app.agents.monitoring_agent import (
    load_watchlist,
    fetch_user_post_engagement,
    fetch_watchlist_posts,
    classify_items,
    generate_suggested_actions,
    persist_pending_actions,
    post_engagement_or_skip,
    mark_result,
    build_monitoring_graph,
)
from app.agents.types import ContentCreationState, MonitoringState
from app.agents.common import (
    generate_trace_id,
    generate_run_id,
    IdempotencyGuard,
)
from app.core.enums import DraftStatus, EngagementStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def content_creation_state():
    """Base state for content creation tests."""
    return ContentCreationState(
        user_id=1,
        thread_id="test_thread_content",
        trace_id=generate_trace_id(),
        run_id=generate_run_id(),
        intent="create_post",
        user_input="Write a post about AI trends in 2024",
        messages=[],
        approval_required=False,
        status="started",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def monitoring_state():
    """Base state for monitoring tests."""
    return MonitoringState(
        user_id=1,
        thread_id="test_thread_monitoring",
        trace_id=generate_trace_id(),
        run_id=generate_run_id(),
        intent="monitor_engagement",
        approval_required=False,
        status="started",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ============================================================================
# Content Creation Agent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_parse_request(content_creation_state):
    """Test parsing user content request."""
    with patch("app.agents.content_creation_agent.llm_manager") as mock_llm:
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = '{"topic": "AI trends", "tone": "professional", "audience": "tech leaders", "cta_required": false, "language": "en"}'
        mock_llm.call = AsyncMock(return_value=mock_response)
        
        result = await parse_request(content_creation_state)
        
        assert result["status"] == "brief_created"
        assert "brief" in result
        assert result["brief"]["topic"] == "AI trends"
        assert result["brief"]["tone"] == "professional"


@pytest.mark.asyncio
async def test_generate_drafts(content_creation_state):
    """Test generating draft variants."""
    content_creation_state["brief"] = {
        "topic": "AI trends",
        "tone": "professional",
        "audience": "tech leaders",
        "cta_required": False,
        "language": "en",
    }
    
    with patch("app.agents.content_creation_agent.llm_manager") as mock_llm:
        # Mock LLM response with variants
        mock_response = MagicMock()
        mock_response.content = """
VARIANT 1:
AI is transforming industries at an unprecedented pace. Here are 3 key trends to watch in 2024.

VARIANT 2:
The future of AI is here. Let's explore what's shaping the landscape in 2024.

VARIANT 3:
From automation to augmentation, AI continues to evolve. Here's what matters most this year.
"""
        mock_llm.call = AsyncMock(return_value=mock_response)
        
        result = await generate_drafts(content_creation_state)
        
        assert result["status"] == "drafts_generated"
        assert "drafts" in result
        assert len(result["drafts"]) == 3
        assert all("content" in d for d in result["drafts"])
        assert all("variant_number" in d for d in result["drafts"])


@pytest.mark.asyncio
async def test_evaluate_drafts(content_creation_state):
    """Test draft evaluation."""
    content_creation_state["drafts"] = [
        {"variant_number": 1, "content": "Test draft 1", "word_count": 50},
        {"variant_number": 2, "content": "Test draft 2", "word_count": 45},
    ]
    
    with patch("app.agents.content_creation_agent.llm_manager") as mock_llm:
        # Mock evaluation scores
        mock_response = MagicMock()
        mock_response.content = "Score: 8.5"
        mock_llm.call = AsyncMock(return_value=mock_response)
        
        result = await evaluate_drafts(content_creation_state)
        
        assert result["status"] == "drafts_evaluated"
        assert "scores" in result
        assert len(result["scores"]) == 2
        assert all(isinstance(score, float) for score in result["scores"].values())


@pytest.mark.asyncio
async def test_persist_drafts(content_creation_state, mock_db):
    """Test persisting drafts to database."""
    content_creation_state["drafts"] = [
        {"variant_number": 1, "content": "Test draft", "score": 8.5},
    ]
    content_creation_state["brief"] = {"topic": "test"}
    
    # Mock repository
    mock_draft = MagicMock()
    mock_draft.id = 123
    
    with patch("app.agents.content_creation_agent.DraftRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.create = AsyncMock(return_value=mock_draft)
        
        result = await persist_drafts(content_creation_state, mock_db)
        
        assert result["status"] == "drafts_persisted"
        assert result["draft_id"] == 123
        mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_interrupt_for_selection(content_creation_state):
    """Test interruption for draft selection."""
    result = await interrupt_for_selection(content_creation_state)
    
    assert result["status"] == "awaiting_selection"
    assert result["approval_required"] == True
    assert result["approved"] is None


@pytest.mark.asyncio
async def test_accept_user_edit_with_selection(content_creation_state):
    """Test accepting user's draft selection."""
    content_creation_state["drafts"] = [
        {"variant_number": 1, "content": "Draft 1", "score": 7.5},
        {"variant_number": 2, "content": "Draft 2", "score": 8.5},
    ]
    content_creation_state["selected_draft_id"] = 2
    
    result = await accept_user_edit(content_creation_state)
    
    assert result["status"] == "content_finalized"
    assert result["final_content"] == "Draft 2"


@pytest.mark.asyncio
async def test_accept_user_edit_with_custom_content(content_creation_state):
    """Test accepting user's custom edited content."""
    content_creation_state["drafts"] = [
        {"variant_number": 1, "content": "Draft 1", "score": 7.5},
    ]
    content_creation_state["user_edited_content"] = "My custom post content"
    
    result = await accept_user_edit(content_creation_state)
    
    assert result["status"] == "content_finalized"
    assert result["final_content"] == "My custom post content"


@pytest.mark.asyncio
async def test_post_to_linkedin_idempotency(content_creation_state):
    """Test idempotency guard prevents duplicate posts."""
    content_creation_state["final_content"] = "Test post"
    content_creation_state["draft_id"] = 123
    
    # First call - should post
    result1 = await post_to_linkedin(content_creation_state)
    assert result1["status"] == "posted"
    assert "post_id" in result1
    
    # Second call with same state - should skip
    result2 = await post_to_linkedin(result1)
    assert "post_id" in result2  # Still has post_id from first call
    # Should not create a new post_id


@pytest.mark.asyncio
async def test_mark_posted_or_failed_success(content_creation_state, mock_db):
    """Test marking draft as posted."""
    content_creation_state["draft_id"] = 123
    content_creation_state["post_id"] = "linkedin_post_456"
    
    with patch("app.agents.content_creation_agent.DraftRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.update_status = AsyncMock()
        
        await mark_posted_or_failed(content_creation_state, mock_db)
        
        mock_repo.update_status.assert_called_once_with(123, DraftStatus.POSTED)


@pytest.mark.asyncio
async def test_mark_posted_or_failed_error(content_creation_state, mock_db):
    """Test marking draft as failed."""
    content_creation_state["draft_id"] = 123
    content_creation_state["error"] = "Posting failed"
    
    with patch("app.agents.content_creation_agent.DraftRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.update_status = AsyncMock()
        
        await mark_posted_or_failed(content_creation_state, mock_db)
        
        mock_repo.update_status.assert_called_once_with(123, DraftStatus.FAILED)


# ============================================================================
# Monitoring Agent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_load_watchlist(monitoring_state, mock_db):
    """Test loading user's watchlist."""
    mock_entry1 = MagicMock()
    mock_entry1.linkedin_profile_id = "profile_1"
    mock_entry2 = MagicMock()
    mock_entry2.linkedin_profile_id = "profile_2"
    
    with patch("app.agents.monitoring_agent.WatchlistRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_user_watchlist = AsyncMock(return_value=[mock_entry1, mock_entry2])
        
        result = await load_watchlist(monitoring_state, mock_db)
        
        assert result["status"] == "watchlist_loaded"
        assert result["watchlist_profile_ids"] == ["profile_1", "profile_2"]


@pytest.mark.asyncio
async def test_fetch_user_post_engagement(monitoring_state):
    """Test fetching engagement on user's posts."""
    result = await fetch_user_post_engagement(monitoring_state)
    
    assert result["status"] == "user_engagement_fetched"
    assert "user_engagement" in result
    assert isinstance(result["user_engagement"], list)


@pytest.mark.asyncio
async def test_fetch_watchlist_posts(monitoring_state):
    """Test fetching posts from watchlist."""
    monitoring_state["watchlist_profile_ids"] = ["profile_1", "profile_2"]
    
    result = await fetch_watchlist_posts(monitoring_state)
    
    assert result["status"] == "watchlist_posts_fetched"
    assert "watchlist_posts" in result
    assert isinstance(result["watchlist_posts"], list)


@pytest.mark.asyncio
async def test_classify_items_empty(monitoring_state):
    """Test classification with no items."""
    monitoring_state["user_engagement"] = []
    monitoring_state["watchlist_posts"] = []
    
    result = await classify_items(monitoring_state)
    
    assert result["classified_items"] == []


@pytest.mark.asyncio
async def test_classify_items_with_data(monitoring_state):
    """Test classification with engagement items."""
    monitoring_state["user_engagement"] = []
    monitoring_state["watchlist_posts"] = [
        {"id": "post_1", "text": "Interesting post about AI", "author": "John Doe"}
    ]
    
    with patch("app.agents.monitoring_agent.llm_manager") as mock_llm:
        mock_response = MagicMock()
        mock_response.content = '{"priority": "high", "reason": "Relevant to your interests", "should_engage": true}'
        mock_llm.call = AsyncMock(return_value=mock_response)
        
        result = await classify_items(monitoring_state)
        
        assert result["status"] == "items_classified"
        assert len(result["classified_items"]) == 1
        assert result["classified_items"][0]["classification"]["should_engage"] == True


@pytest.mark.asyncio
async def test_generate_suggested_actions(monitoring_state):
    """Test generating comment suggestions."""
    monitoring_state["classified_items"] = [
        {
            "id": "post_1",
            "text": "AI is transforming healthcare",
            "author": "Dr. Smith",
            "classification": {"priority": "high", "reason": "Relevant", "should_engage": True},
        }
    ]
    
    with patch("app.agents.monitoring_agent.llm_manager") as mock_llm:
        mock_response = MagicMock()
        mock_response.content = "Great insights! The intersection of AI and healthcare is particularly exciting."
        mock_llm.call = AsyncMock(return_value=mock_response)
        
        result = await generate_suggested_actions(monitoring_state)
        
        assert result["status"] == "suggestions_generated"
        assert len(result["suggested_actions"]) == 1
        assert "suggested_comment" in result["suggested_actions"][0]


@pytest.mark.asyncio
async def test_persist_pending_actions(monitoring_state, mock_db):
    """Test persisting suggested actions."""
    monitoring_state["suggested_actions"] = [
        {
            "post_id": "post_1",
            "post_author": "John",
            "post_text": "Test post",
            "engagement_type": "comment",
            "suggested_comment": "Great post!",
            "priority": "high",
            "reason": "Relevant",
        }
    ]
    
    mock_engagement = MagicMock()
    mock_engagement.id = 456
    
    with patch("app.agents.monitoring_agent.PendingEngagementRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.create = AsyncMock(return_value=mock_engagement)
        
        result = await persist_pending_actions(monitoring_state, mock_db)
        
        assert result["status"] == "actions_persisted"
        assert result["pending_action_ids"] == [456]


@pytest.mark.asyncio
async def test_post_engagement_or_skip_idempotency(monitoring_state):
    """Test idempotency guard prevents duplicate engagements."""
    monitoring_state["selected_action_id"] = 0
    monitoring_state["suggested_actions"] = [
        {
            "post_id": "post_1",
            "post_author": "John",
            "suggested_comment": "Great post!",
        }
    ]
    monitoring_state["pending_action_ids"] = [456]
    
    # First call - should post
    result1 = await post_engagement_or_skip(monitoring_state)
    assert result1["status"] == "engagement_posted"
    assert len(result1["posted_actions"]) == 1
    
    # Second call with same state - should skip due to idempotency
    result2 = await post_engagement_or_skip(result1)
    # Should not add another action to posted_actions due to idempotency guard
    assert len(result2["posted_actions"]) == 1


@pytest.mark.asyncio
async def test_mark_result_completed(monitoring_state, mock_db):
    """Test marking engagement as completed."""
    monitoring_state["pending_action_ids"] = [456]
    monitoring_state["selected_action_id"] = 0
    monitoring_state["posted_actions"] = [{"action_id": 0}]
    
    with patch("app.agents.monitoring_agent.PendingEngagementRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.update_status = AsyncMock()
        
        await mark_result(monitoring_state, mock_db)
        
        mock_repo.update_status.assert_called_once_with(456, EngagementStatus.COMPLETED)


@pytest.mark.asyncio
async def test_mark_result_skipped(monitoring_state, mock_db):
    """Test marking engagement as skipped."""
    monitoring_state["pending_action_ids"] = [456]
    monitoring_state["approved"] = False
    
    with patch("app.agents.monitoring_agent.PendingEngagementRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.update_status = AsyncMock()
        
        await mark_result(monitoring_state, mock_db)
        
        mock_repo.update_status.assert_called_once_with(456, EngagementStatus.SKIPPED)


# ============================================================================
# Common Helpers Tests
# ============================================================================

def test_idempotency_guard():
    """Test idempotency guard functionality."""
    state = {}
    
    # Mark action as completed
    state = IdempotencyGuard.mark_completed(state, "test_action", 123)
    
    # Check if completed
    assert IdempotencyGuard.is_completed(state, "test_action", 123) == True
    assert IdempotencyGuard.is_completed(state, "test_action", 456) == False
    assert IdempotencyGuard.is_completed(state, "other_action", 123) == False


# ============================================================================
# Graph Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_content_creation_graph_compilation():
    """Test that content creation graph compiles successfully."""
    # Use None for checkpointer in tests (no persistence needed)
    graph = build_content_creation_graph(None)
    
    assert graph is not None
    # Graph should have compiled without errors


@pytest.mark.asyncio
async def test_monitoring_graph_compilation():
    """Test that monitoring graph compiles successfully."""
    # Use None for checkpointer in tests (no persistence needed)
    graph = build_monitoring_graph(None)
    
    assert graph is not None
    # Graph should have compiled without errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
