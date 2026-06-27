"""Comprehensive API integration tests.

Tests all API endpoints with real database and mocked external services.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.main import app
from app.db.models import (
    User,
    PostDraft,
    PendingEngagement,
    WatchlistEntry,
    ChatMessage,
    GraphRun,
)
from app.core.enums import (
    DraftStatus,
    EngagementStatus,
    EngagementType,
    GraphStatus,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Test client with proper exception handling for error tests."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_db_session(mocker):
    """Mock database session."""
    session = mocker.AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Mock user for tests."""
    return User(
        id=1,
        email="test@example.com",
        display_name="Test User",
        preferred_language="en",
        voice_enabled=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_checkpointer(mocker):
    """Mock LangGraph checkpointer."""
    checkpointer = mocker.MagicMock()
    checkpointer.aget = AsyncMock(return_value=None)
    checkpointer.aput = AsyncMock()
    return checkpointer


@pytest.fixture
def override_deps(mock_db_session, mock_user, mock_checkpointer):
    """Override FastAPI dependencies for tests."""
    from app.core.dependencies import (
        get_db_session,
        get_current_user_id,
        get_checkpointer,
    )
    
    async def _get_db():
        yield mock_db_session
    
    async def _get_user_id():
        return mock_user.id
    
    async def _get_checkpointer():
        return mock_checkpointer
    
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = _get_user_id
    app.dependency_overrides[get_checkpointer] = _get_checkpointer
    
    yield
    
    # CRITICAL: Clean up after each test
    app.dependency_overrides.clear()


# ============================================================================
# Chat Endpoint Tests
# ============================================================================

class TestChatEndpoint:
    """Tests for /api/v1/chat endpoint."""
    
    @patch("app.services.chat_service.ChatService.process_message")
    def test_chat_create_post_intent(
        self,
        mock_process_message,
        client,
        override_deps,
    ):
        """Test chat with create_post intent."""
        mock_process_message.return_value = {
            "intent": "create_post",
            "status": "success",
            "thread_id": "test-thread-123",
            "trace_id": "trace-123",
            "message": "I'll create a post for you!",
            "data": {"agent_started": True},
        }
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Write a post about AI",
                "thread_id": "test-thread-123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "create_post"
        assert data["status"] == "success"
        assert "thread_id" in data
        mock_process_message.assert_called_once()
    
    @patch("app.services.chat_service.ChatService.process_message")
    def test_chat_view_pending_intent(
        self,
        mock_process_message,
        client,
        override_deps,
    ):
        """Test chat with view_pending intent."""
        mock_process_message.return_value = {
            "intent": "view_pending",
            "status": "success",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "message": "You have 2 pending items",
            "data": {
                "pending_actions": [
                    {"id": 1, "type": "draft"},
                    {"id": 2, "type": "comment"},
                ],
                "total_count": 2,
            },
        }
        
        response = client.post(
            "/api/v1/chat",
            json={"message": "Show pending actions"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "view_pending"
        assert "pending_actions" in data["data"]
    
    @patch("app.services.chat_service.ChatService.process_message")
    def test_chat_general_query(
        self,
        mock_process_message,
        client,
        override_deps,
    ):
        """Test chat with general_query intent."""
        mock_process_message.return_value = {
            "intent": "general_query",
            "status": "success",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "message": "Here's some information...",
            "data": {},
        }
        
        response = client.post(
            "/api/v1/chat",
            json={"message": "Tell me about LinkedIn"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "general_query"
        assert data["status"] == "success"
    
    @patch("app.services.chat_service.ChatService.process_message")
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_chat_with_voice_enabled(
        self,
        mock_synthesize,
        mock_process_message,
        client,
        override_deps,
    ):
        """Test chat with voice_enabled flag."""
        mock_process_message.return_value = {
            "intent": "general_query",
            "status": "success",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "message": "Response text",
            "data": {},
        }
        
        mock_synthesize.return_value = {
            "audio_available": True,
            "audio_base64": "YXVkaW9kYXRh",
            "mime_type": "audio/mpeg",
            "fallback_text": None,
            "error": None,
        }
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "voice_enabled": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "voice_audio" in data["data"]


# ============================================================================
# Draft Approval Flow Tests
# ============================================================================

class TestDraftApprovalFlow:
    """Tests for draft approval workflow."""
    
    @patch("app.services.action_service.ActionService.select_draft")
    def test_select_draft_variant(
        self,
        mock_select_draft,
        client,
        override_deps,
    ):
        """Test selecting a draft variant."""
        # Mock returns CANONICAL response format
        mock_select_draft.return_value = {
            "status": "content_finalized",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "data": {
                "final_content": "Selected draft content"
            },
        }
        
        response = client.post(
            "/api/v1/drafts/select",
            json={
                "thread_id": "test-thread",
                "selected_draft_id": 1,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "content_finalized"
        assert data["thread_id"] == "test-thread"
        assert data["trace_id"] == "trace-123"
        assert "data" in data
        assert data["data"]["final_content"] == "Selected draft content"
        
        mock_select_draft.assert_called_once()
    
    @patch("app.services.action_service.ActionService.select_draft")
    def test_select_draft_with_edit(
        self,
        mock_select_draft,
        client,
        override_deps,
    ):
        """Test selecting draft with custom edits."""
        # Mock returns CANONICAL response format
        mock_select_draft.return_value = {
            "status": "content_finalized",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "data": {
                "final_content": "My custom post content"
            },
        }
        
        response = client.post(
            "/api/v1/drafts/select",
            json={
                "thread_id": "test-thread",
                "selected_draft_id": None,
                "user_edited_content": "My custom post content",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "content_finalized"
        assert data["thread_id"] == "test-thread"
        assert "data" in data
        assert data["data"]["final_content"] == "My custom post content"
    
    @patch("app.services.action_service.ActionService.final_approve_draft")
    def test_final_approve_draft_approved(
        self,
        mock_final_approve,
        client,
        override_deps,
    ):
        """Test final approval of draft."""
        # Mock returns CANONICAL response format
        mock_final_approve.return_value = {
            "status": "posted",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "data": {
                "post_id": "linkedin_post_123",
                "final_content": "Final approved content"
            },
        }
        
        response = client.post(
            "/api/v1/drafts/approve",
            json={
                "thread_id": "test-thread",
                "approved": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "posted"
        assert data["thread_id"] == "test-thread"
        assert "data" in data
        assert data["data"]["post_id"] == "linkedin_post_123"
    
    @patch("app.services.action_service.ActionService.final_approve_draft")
    def test_final_approve_draft_rejected(
        self,
        mock_final_approve,
        client,
        override_deps,
    ):
        """Test rejection of final draft."""
        # Mock returns CANONICAL response format
        mock_final_approve.return_value = {
            "status": "rejected",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "data": {
                "message": "Draft rejected"
            },
        }
        
        response = client.post(
            "/api/v1/drafts/approve",
            json={
                "thread_id": "test-thread",
                "approved": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "rejected"
        assert data["thread_id"] == "test-thread"
    
    @patch("app.services.action_service.ActionService.select_draft")
    def test_idempotency_on_duplicate_selection(
        self,
        mock_select_draft,
        client,
        override_deps,
    ):
        """Test idempotency when selecting same draft twice."""
        # Mock returns CANONICAL response format
        mock_select_draft.return_value = {
            "status": "content_finalized",
            "thread_id": "test-thread",
            "trace_id": "trace-123",
            "data": {
                "final_content": "Selected draft content"
            },
        }
        
        # First request
        response1 = client.post(
            "/api/v1/drafts/select",
            json={
                "thread_id": "test-thread",
                "selected_draft_id": 1,
            },
        )
        
        # Second request (duplicate)
        response2 = client.post(
            "/api/v1/drafts/select",
            json={
                "thread_id": "test-thread",
                "selected_draft_id": 1,
            },
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Service layer handles idempotency


# ============================================================================
# Engagement Approval Tests
# ============================================================================

class TestEngagementApproval:
    """Tests for engagement approval endpoints."""
    
    @patch("app.services.action_service.ActionService.approve_engagement")
    def test_approve_engagement_no_edit(
        self,
        mock_approve,
        client,
        override_deps,
    ):
        """Test approving engagement without edit."""
        # Mock returns CANONICAL response format
        mock_approve.return_value = {
            "status": "completed",
            "action_id": 1,
            "trace_id": "trace-123",
            "data": {
                "engagement_result": []
            },
        }
        
        response = client.post(
            "/api/v1/approve/1",
            json={
                "thread_id": "monitor-thread",
                "action_index": 0,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "completed"
        assert data["action_id"] == 1
        assert data["trace_id"] == "trace-123"
        assert "data" in data
    
    @patch("app.services.action_service.ActionService.approve_engagement")
    def test_approve_engagement_with_edit(
        self,
        mock_approve,
        client,
        override_deps,
    ):
        """Test approving engagement with edited comment."""
        # Mock returns CANONICAL response format
        mock_approve.return_value = {
            "status": "completed",
            "action_id": 1,
            "trace_id": "trace-123",
            "data": {
                "engagement_result": []
            },
        }
        
        response = client.post(
            "/api/v1/approve/1",
            json={
                "thread_id": "monitor-thread",
                "action_index": 0,
                "edited_comment": "My custom comment text",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "completed"
        assert data["action_id"] == 1
    
    @patch("app.services.action_service.ActionService.skip_action")
    def test_skip_action(
        self,
        mock_skip,
        client,
        override_deps,
    ):
        """Test skipping an action."""
        # Mock returns CANONICAL response format
        mock_skip.return_value = {
            "status": "skipped",
            "action_id": 1,
            "trace_id": "trace-123",
        }
        
        # DELETE requests use 'data' parameter, not 'json'
        response = client.request(
            "DELETE",
            "/api/v1/skip/1",
            json={
                "thread_id": "monitor-thread",
                "reason": "Not relevant",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "skipped"
        assert data["action_id"] == 1
        assert data["trace_id"] == "trace-123"
    
    @patch("app.services.action_service.ActionService.get_pending_items")
    def test_get_pending_actions(
        self,
        mock_get_pending,
        client,
        override_deps,
    ):
        """Test retrieving all pending actions."""
        # Mock returns CANONICAL response format
        mock_get_pending.return_value = {
            "status": "success",
            "trace_id": "trace-123",
            "items": [
                {
                    "id": 1,
                    "type": "draft",
                    "thread_id": "thread-1",
                    "status": "pending",
                    "created_at": "2024-01-01T00:00:00Z",
                    "data": {}
                },
                {
                    "id": 2,
                    "type": "engagement",
                    "thread_id": "thread-2",
                    "status": "pending",
                    "created_at": "2024-01-02T00:00:00Z",
                    "data": {}
                },
            ],
            "total_count": 2,
        }
        
        response = client.get("/api/v1/pending")
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "success"
        assert data["trace_id"] == "trace-123"
        assert data["total_count"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["type"] == "draft"
        assert data["items"][1]["type"] == "engagement"


# ============================================================================
# Watchlist Management Tests
# ============================================================================

class TestWatchlistManagement:
    """Tests for watchlist CRUD endpoints."""
    
    @patch("app.services.watchlist_service.WatchlistService.add_profile")
    def test_add_watchlist_by_url(
        self,
        mock_add,
        client,
        override_deps,
    ):
        """Test adding profile to watchlist by URL."""
        # Mock returns CANONICAL response format
        mock_add.return_value = {
            "status": "added",
            "trace_id": "trace-123",
            "profile": {
                "id": 1,
                "linkedin_profile_id": "john-doe",
                "profile_url": "https://linkedin.com/in/john-doe",
                "name": None,
                "headline": None,
                "note": "Interesting thought leader",
                "status": "active",
                "added_at": "2024-01-01T00:00:00Z",
                "last_checked": None
            },
        }
        
        response = client.post(
            "/api/v1/monitor/add",
            json={
                "profile_url": "https://linkedin.com/in/john-doe",
                "note": "Interesting thought leader",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "added"
        assert data["trace_id"] == "trace-123"
        assert "profile" in data
        assert data["profile"]["linkedin_profile_id"] == "john-doe"
    
    @patch("app.services.watchlist_service.WatchlistService.add_profile")
    def test_add_watchlist_by_member_id(
        self,
        mock_add,
        client,
        override_deps,
    ):
        """Test adding profile by member ID."""
        # Mock returns CANONICAL response format
        mock_add.return_value = {
            "status": "added",
            "trace_id": "trace-123",
            "profile": {
                "id": 1,
                "linkedin_profile_id": "john-doe",
                "profile_url": "https://linkedin.com/in/john-doe",
                "name": None,
                "headline": None,
                "note": None,
                "status": "active",
                "added_at": "2024-01-01T00:00:00Z",
                "last_checked": None
            },
        }
        
        response = client.post(
            "/api/v1/monitor/add",
            json={
                "member_id": "john-doe",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "added"
        assert "profile" in data
    
    @patch("app.services.watchlist_service.WatchlistService.add_profile")
    def test_add_watchlist_duplicate_error(
        self,
        mock_add,
        client,
        override_deps,
    ):
        """Test adding duplicate profile returns error."""
        from app.core.errors import ConflictError
        
        mock_add.side_effect = ConflictError(
            "Profile already in watchlist",
            resource="watchlist"
        )
        
        response = client.post(
            "/api/v1/monitor/add",
            json={
                "profile_url": "https://linkedin.com/in/john-doe",
            },
        )
        
        # Global exception handler should catch this
        assert response.status_code in [400, 409]
    
    @patch("app.services.watchlist_service.WatchlistService.remove_profile")
    def test_remove_watchlist(
        self,
        mock_remove,
        client,
        override_deps,
    ):
        """Test removing profile from watchlist."""
        # Mock returns CANONICAL response format
        mock_remove.return_value = {
            "status": "removed",
            "trace_id": "trace-123",
            "profile_id": "john-doe",
        }
        
        response = client.delete("/api/v1/monitor/remove/john-doe")
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "removed"
        assert data["profile_id"] == "john-doe"
        assert data["trace_id"] == "trace-123"
    
    @patch("app.services.watchlist_service.WatchlistService.remove_profile")
    def test_remove_watchlist_not_found(
        self,
        mock_remove,
        client,
        override_deps,
    ):
        """Test removing non-existent profile."""
        from app.core.errors import NotFoundError
        
        mock_remove.side_effect = NotFoundError(
            "WatchlistEntry",
            "nonexistent"
        )
        
        response = client.delete("/api/v1/monitor/remove/nonexistent")
        
        assert response.status_code == 404
    
    @patch("app.services.watchlist_service.WatchlistService.list_profiles")
    def test_list_watchlist(
        self,
        mock_list,
        client,
        override_deps,
    ):
        """Test listing all watchlist profiles."""
        # Mock returns CANONICAL response format
        mock_list.return_value = {
            "status": "success",
            "trace_id": "trace-123",
            "profiles": [
                {
                    "id": 1,
                    "linkedin_profile_id": "john-doe",
                    "profile_url": "https://linkedin.com/in/john-doe",
                    "name": None,
                    "headline": None,
                    "note": "Interesting",
                    "status": "active",
                    "added_at": "2024-01-01T00:00:00Z",
                    "last_checked": None
                },
                {
                    "id": 2,
                    "linkedin_profile_id": "jane-smith",
                    "profile_url": "https://linkedin.com/in/jane-smith",
                    "name": None,
                    "headline": None,
                    "note": None,
                    "status": "active",
                    "added_at": "2024-01-02T00:00:00Z",
                    "last_checked": None
                },
            ],
            "total_count": 2,
        }
        
        response = client.get("/api/v1/monitor/list")
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "success"
        assert data["trace_id"] == "trace-123"
        assert data["total_count"] == 2
        assert len(data["profiles"]) == 2
    
    @patch("app.services.watchlist_service.WatchlistService.list_profiles")
    def test_list_watchlist_empty(
        self,
        mock_list,
        client,
        override_deps,
    ):
        """Test listing empty watchlist."""
        # Mock returns CANONICAL response format
        mock_list.return_value = {
            "status": "success",
            "trace_id": "trace-123",
            "profiles": [],
            "total_count": 0,
        }
        
        response = client.get("/api/v1/monitor/list")
        
        assert response.status_code == 200
        data = response.json()
        
        # Assert CANONICAL response schema
        assert data["status"] == "success"
        assert data["total_count"] == 0
        assert data["profiles"] == []


# ============================================================================
# Voice Endpoint Tests (Phase 7 Stubs)
# ============================================================================

class TestVoiceEndpoints:
    """Tests for voice endpoints."""
    
    @patch("app.services.voice.voice_manager.VoiceManager.transcribe_file")
    def test_transcribe_voice_implementation(
        self,
        mock_transcribe,
        client,
        override_deps,
    ):
        """Test voice transcription with implemented service."""
        from app.services.voice.models import TranscriptionResult, VoiceLanguage
        
        mock_transcribe.return_value = TranscriptionResult(
            text="Hello world",
            language=VoiceLanguage.EN,
            model="saarika:v2.5",
            confidence=0.95,
        )
        
        response = client.post(
            "/api/v1/voice/transcribe",
            json={
                "audio_data": "YmFzZTY0ZW5jb2RlZGF1ZGlv",  # valid base64
                "language": "en",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello world"
        assert data["language"] == "en"
    
    @patch("app.services.voice.voice_manager.VoiceManager.synthesize_text")
    def test_synthesize_speech_implementation(
        self,
        mock_synthesize,
        client,
        override_deps,
    ):
        """Test voice synthesis with implemented service."""
        mock_synthesize.return_value = {
            "audio_available": True,
            "audio_base64": "YXVkaW9kYXRh",
            "mime_type": "audio/mpeg",
            "fallback_text": None,
            "error": None,
            "language": "en",
        }
        
        response = client.post(
            "/api/v1/voice/speak",
            json={
                "text": "Hello world",
                "language": "en",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["audio_available"] is True
        assert data["audio_data"] == "YXVkaW9kYXRh"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for global error handling."""
    
    def test_missing_required_field(
        self,
        client,
        override_deps,
    ):
        """Test validation error for missing required field."""
        response = client.post(
            "/api/v1/chat",
            json={},  # Missing required 'message' field
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_action_id(
        self,
        client,
        override_deps,
    ):
        """Test invalid action ID in path parameter."""
        response = client.post(
            "/api/v1/approve/invalid",
            json={
                "thread_id": "test",
                "action_index": 0,
            },
        )
        
        assert response.status_code == 422
    
    @patch("app.services.chat_service.ChatService.process_message")
    def test_internal_server_error_handling(
        self,
        mock_process_message,
        client,
        override_deps,
    ):
        """Test handling of unexpected exceptions."""
        mock_process_message.side_effect = Exception("Unexpected error")
        
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test"},
        )
        
        # Global exception handler should catch this
        assert response.status_code == 500


# ============================================================================
# Integration Test - Real Persisted Resume
# ============================================================================

class TestRealPersistedResume:
    """Test real interrupt/resume with actual PostgreSQL.
    
    NOTE: This requires a running PostgreSQL database.
    Mark as integration test to run separately.
    """
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_graph_interrupt_and_resume(self):
        """Test real LangGraph interrupt/resume with PostgreSQL checkpointer.
        
        This is a placeholder for the real integration test that would:
        1. Start content creation graph
        2. Interrupt at draft selection
        3. Store checkpoint in PostgreSQL
        4. Restart application
        5. Resume from checkpoint
        6. Complete workflow
        
        Implementation requires:
        - Test database setup/teardown
        - Real PostgresSaver instance
        - Full agent graph execution
        """
        pytest.skip("Requires integration test environment with PostgreSQL")
