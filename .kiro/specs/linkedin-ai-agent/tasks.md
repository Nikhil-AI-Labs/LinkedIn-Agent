# Implementation Plan: LinkedIn AI Agent System

## Overview

This implementation plan breaks down the LinkedIn AI Agent system into discrete implementation phases. The system uses LangGraph for workflow orchestration, FastAPI for the backend API, PostgreSQL for persistence, and a two-tiered LLM architecture. Tasks focus on completing the remaining phases (4-8) that build the LinkedIn service layer, LangGraph agents, API endpoints, voice services, and optional frontend.

## Tasks

- [ ] 4. Implement LinkedIn Service Integration Layer
  - [ ] 4.1 Fix Critical Setup Issues
    - Add PostgresSaver initialization in app/main.py
    - Update requirements.txt with linkedin-api==2.0.0a5 and playwright==1.44.0
    - Complete browser/oauth validation in test_setup.py
    - Document LINKEDIN_PASSWORD_ENCRYPTED encryption process
    - _Requirements: 7, 20_

  - [ ] 4.2 Create LinkedIn Service Base Models
    - Create backend/app/services/linkedin/base.py with data models and abstract interfaces
    - Define LinkedInPost, LinkedInComment, LinkedInProfile Pydantic models
    - Define LinkedInResult wrapper
    - Define abstract LinkedInClient and LinkedInPoster interfaces
    - _Requirements: 17, 10_

  - [ ] 4.3 Implement Voyager Client for Read Operations
    - Create backend/app/services/linkedin/voyager_client.py for READ operations using linkedin-api
    - Implement get_user_posts(), get_profile_posts()
    - Implement get_post_comments(), get_post_reactions()
    - Implement validate_profile()
    - Add executor wrapping for sync library
    - Add retry logic (2 attempts, 5s/10s backoff)
    - _Requirements: 17, 9, 10, 11_

  - [ ] 4.4 Implement Browser Poster for Write Operations
    - Create backend/app/services/linkedin/browser_poster.py with KimiBridgePoster (stub) and PlaywrightPoster
    - Implement KimiBridgePoster stubs with helpful error messages
    - Implement PlaywrightPoster with playwright + stealth plugin
    - Add human-like delays (2-7s random) before actions
    - Add session validation and retry logic
    - _Requirements: 3, 9, 22, 11_

  - [ ] 4.5 Create OAuth Client Stub
    - Create backend/app/services/linkedin/oauth_client.py stub for future OAuth implementation
    - _Requirements: 1, 2, 10_

  - [ ] 4.6 Implement LinkedIn Manager Router
    - Create backend/app/services/linkedin/linkedin_manager.py that routes based on AUTH_MODE
    - Implement routing logic (oauth vs browser mode)
    - Implement automatic fallback (Kimi → Playwright for writes)
    - Add trace_id propagation
    - Add structured logging for routing decisions
    - _Requirements: 1, 8, 10_

  - [ ]* 4.7 Write LinkedIn Integration Tests
    - Create backend/tests/test_linkedin_manager.py with test cases for all LinkedIn clients
    - Test routing logic, fallback behavior, and retry policies
    - _Requirements: 1, 9, 10_

- [ ] 5. Implement LangGraph Agent Workflows
  - [ ] 5.1 Set Up LangGraph Checkpointer
    - Create backend/app/agents/checkpointer.py to configure PostgresSaver
    - _Requirements: 7, 20_

  - [ ] 5.2 Implement Content Creation Agent
    - Create backend/app/agents/content_creation_agent.py with full LangGraph workflow
    - Define ContentCreationState TypedDict
    - Implement all node functions (generate, evaluate, persist, approve, post)
    - Compile graph with interrupt points
    - Add thread management and resumption logic
    - _Requirements: 12, 5, 6, 21_

  - [ ] 5.3 Implement Monitoring Agent
    - Create backend/app/agents/monitoring_agent.py with scheduled monitoring workflow
    - Define MonitoringState TypedDict
    - Implement node functions (fetch, classify, suggest, approve, execute)
    - Compile graph with interrupt points
    - Add APScheduler integration (every 2 hours)
    - _Requirements: 15, 16, 5, 6, 21_

  - [ ]* 5.4 Write Agent Integration Tests
    - Create backend/tests/test_agents.py with agent workflow tests
    - Test interrupt points, resumption logic, and idempotency
    - _Requirements: 5, 6, 7_

- [ ] 6. Implement API Endpoints and Chat Interface
  - [ ] 6.1 Create Intent Router Service
    - Create backend/app/services/intent_router.py using Fast LLM for intent classification
    - _Requirements: 19, 21_

  - [ ] 6.2 Implement Chat and Voice Endpoints
    - Create backend/app/api/v1/routes/chat.py with chat and voice endpoints
    - _Requirements: 19, 23, 13_

  - [ ] 6.3 Implement Approval and Action Endpoints
    - Create backend/app/api/v1/routes/actions.py with approval/skip/edit endpoints
    - _Requirements: 16, 23_

  - [ ] 6.4 Implement Watchlist Management Endpoints
    - Create backend/app/api/v1/routes/watchlist.py with watchlist CRUD endpoints
    - _Requirements: 18, 23_

  - [ ]* 6.5 Write API Integration Tests
    - Create backend/tests/test_api.py with comprehensive API tests
    - Test all endpoints, error handling, and authentication
    - _Requirements: 23, 24, 25_

- [ ] 7. Implement Voice Services
  - [ ] 7.1 Implement Voice Service Manager
    - Create backend/app/services/voice/voice_manager.py wrapping Sarvam STT and TTS
    - _Requirements: 13, 14, 21_

  - [ ]* 7.2 Write Voice Integration Tests
    - Create backend/tests/test_voice.py with voice service tests
    - Test transcription, TTS generation, and error handling
    - _Requirements: 13, 14_

- [ ] 8. Checkpoint - Ensure Backend Tests Pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Optional: Build Next.js Frontend
  - [ ]* 9.1 Set Up Next.js Project
    - Create frontend/ directory with Next.js 14 setup
    - Configure TailwindCSS and Axios

  - [ ]* 9.2 Build Chat Interface
    - Build chat interface with message history and voice input
    - _Requirements: 19, 13, 14_

  - [ ]* 9.3 Build Approvals Dashboard
    - Build pending approvals view
    - _Requirements: 16_

  - [ ]* 9.4 Build Watchlist Management UI
    - Build watchlist management interface
    - _Requirements: 18_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The checkpoint ensures backend implementation is validated before frontend work
- No property-based tests are included as the design document does not contain a Correctness Properties section
- Phase 8 (formerly a checkpoint) is now renamed to match the task numbering

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["4.1"] },
    { "id": 1, "tasks": ["4.2", "5.1"] },
    { "id": 2, "tasks": ["4.3", "4.4", "4.5"] },
    { "id": 3, "tasks": ["4.6"] },
    { "id": 4, "tasks": ["4.7", "5.2", "5.3", "6.1", "6.4"] },
    { "id": 5, "tasks": ["5.4", "6.2", "6.3", "7.1"] },
    { "id": 6, "tasks": ["6.5", "7.2"] },
    { "id": 7, "tasks": ["9.1"] },
    { "id": 8, "tasks": ["9.2", "9.3", "9.4"] }
  ]
}
```
