# Technical Design Document: LinkedIn AI Agent System

## Overview

The LinkedIn AI Agent system is a production-grade autonomous LinkedIn presence management platform. The system uses LangGraph for workflow orchestration with human-in-the-loop interrupts, FastAPI for the backend API, Next.js for the frontend, PostgreSQL for persistence, and a two-tiered LLM architecture combining Sarvam-M (reasoning) and Groq llama-3.3-70b-versatile (speed).

### Key Capabilities

- **Content Creation**: Voice/text-driven post drafting with AI evaluation and human approval
- **Engagement Monitoring**: Automated monitoring of posts and watchlist profiles with intelligent suggestion
- **Dual Authentication**: OAuth 2.0 for official API or browser automation with Playwright
- **Conversational Interface**: Text and voice chat in English, Hindi, and Hinglish
- **Human-Like Behavior**: Stealth mode automation with randomized delays
- **Production-Grade**: Encrypted credentials, structured logging, retry policies, and observability

### System Context

```mermaid
C4Context
    title System Context Diagram - LinkedIn AI Agent

    Person(user, "LinkedIn User", "Interacts via text/voice")
    
    System_Boundary(system, "LinkedIn AI Agent System") {
        System(backend, "Backend API", "FastAPI + LangGraph")
        System(frontend, "Chat Interface", "Next.js + React")
        SystemDb(db, "State Store", "PostgreSQL 14+")
    }
    
    System_Ext(linkedin, "LinkedIn Platform", "OAuth API or Browser")
    System_Ext(sarvam, "Sarvam AI", "STT (Saarika) + TTS (Bulbul v3) + LLM (Sarvam-M)")
    System_Ext(groq, "Groq API", "llama-3.3-70b-versatile")
    System_Ext(langsmith, "LangSmith", "Tracing & Observability")
    
    Rel(user, frontend, "Uses", "HTTPS")
    Rel(frontend, backend, "Calls", "REST API / HTTPS")
    Rel(backend, db, "Persists", "PostgreSQL protocol")
    Rel(backend, linkedin, "Reads/Writes", "OAuth 2.0 / Playwright")
    Rel(backend, sarvam, "Calls", "HTTPS / OpenAI-compatible")
    Rel(backend, groq, "Calls", "HTTPS / OpenAI-compatible")
    Rel(backend, langsmith, "Traces", "HTTPS")
```


## Architecture

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | Next.js | 14.x | React framework with SSR |
| | React | 18.x | UI component library |
| | TailwindCSS | 3.x | Styling framework |
| | Axios | 1.6.x | HTTP client |
| **Backend** | FastAPI | 0.109.x | Async REST API framework |
| | LangGraph | 0.0.60+ | Workflow orchestration |
| | LangSmith | 0.0.87+ | Tracing and observability |
| | PostgresSaver | (langgraph-checkpoint-postgres) | LangGraph state persistence |
| **LLM** | Sarvam-M | Latest | Primary reasoning LLM |
| | Groq llama-3.3-70b | Latest | Fast classification LLM |
| **Voice** | Sarvam Saarika | Latest | Speech-to-text (STT) |
| | Sarvam Bulbul v3 | Latest | Text-to-speech (TTS) |
| **LinkedIn** | linkedin-api-python | 0.4.x | Official OAuth client |
| | linkedin-api (Voyager) | 2.2.x | Unofficial Voyager client |
| | Playwright | 1.40.x | Browser automation |
| | playwright-stealth | Latest | Anti-detection plugin |
| **Database** | PostgreSQL | 14+ | Relational database |
| | asyncpg | 0.29.x | Async PostgreSQL driver |
| **Scheduling** | APScheduler | 3.10.x | Task scheduling |
| **Crypto** | cryptography | 42.x | AES-256 encryption |
| **HTTP** | httpx | 0.26.x | Async HTTP client |
| **Logging** | structlog | 24.x | Structured logging |


### Component Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Chat Interface<br/>Next.js + React]
        Voice[Voice Components<br/>Audio Recording/Playback]
    end
    
    subgraph "API Layer"
        API[FastAPI Application<br/>REST Endpoints]
        Auth[Auth Middleware<br/>Bearer Token]
        CORS[CORS Middleware]
    end
    
    subgraph "Agent Layer"
        Router[Intent Router<br/>Fast LLM Classification]
        CCA[Content Creation Agent<br/>LangGraph Workflow]
        MA[Monitoring Agent<br/>LangGraph Workflow]
        ChatAgent[Chat Agent<br/>Primary LLM Responses]
    end
    
    subgraph "Integration Layer"
        LLMClient[LLM Client Manager<br/>Sarvam + Groq]
        LinkedInMgr[LinkedIn Client Manager<br/>OAuth/Browser/Voyager]
        VoiceMgr[Voice Service Manager<br/>STT + TTS]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL<br/>State Store)]
        Checkpointer[LangGraph PostgresSaver<br/>Checkpoint Manager]
        Secrets[Secrets Manager<br/>Env Variables]
    end
    
    subgraph "External Services"
        LinkedIn[LinkedIn Platform]
        Sarvam[Sarvam AI APIs]
        Groq[Groq API]
        LangSmith[LangSmith Tracing]
    end
    
    UI --> API
    Voice --> API
    API --> Auth
    Auth --> Router
    Router --> CCA
    Router --> MA
    Router --> ChatAgent
    CCA --> LLMClient
    CCA --> LinkedInMgr
    MA --> LLMClient
    MA --> LinkedInMgr
    ChatAgent --> LLMClient
    Router --> LLMClient
    CCA --> Checkpointer
    MA --> Checkpointer
    Checkpointer --> DB
    LinkedInMgr --> Secrets
    LLMClient --> Secrets
    VoiceMgr --> Secrets
    LinkedInMgr --> LinkedIn
    LLMClient --> Sarvam
    LLMClient --> Groq
    VoiceMgr --> Sarvam
    API --> LangSmith
```


### Component Responsibilities

#### Frontend Layer

**Chat Interface (Next.js + React)**
- Renders conversational UI with message history
- Handles text input and voice recording
- Displays pending engagement actions for approval
- Manages watchlist UI (add/remove profiles)
- Implements audio playback for TTS responses
- Handles authentication tokens and session management

**Voice Components**
- Browser-based audio recording using MediaRecorder API
- Audio format conversion (WebM to WAV for Sarvam STT)
- Audio player for TTS responses
- Microphone permission management

#### API Layer

**FastAPI Application**
- Exposes REST endpoints per Requirement 23
- Handles request validation with Pydantic models
- Implements async request handling
- Returns structured JSON responses
- Manages HTTP error codes and responses

**Auth Middleware**
- Validates Bearer tokens on all protected endpoints
- Extracts user_id from JWT tokens
- Returns 401 Unauthorized for invalid/missing tokens

**CORS Middleware**
- Enforces origin whitelist from configuration
- Sets secure CORS headers (Requirement 25)

#### Agent Layer

**Intent Router**
- Uses Fast LLM (Groq) for sub-2-second classification
- Routes to: create_post, view_pending, add_watchlist, remove_watchlist, general_query
- Falls back to clarifying question on ambiguous intent
- Persists routing decisions to chat_history

**Content Creation Agent (LangGraph)**
- Orchestrates: draft_generation → draft_evaluation → human_approval → content_editing → post_execution
- Generates 2-3 post variations using Primary LLM
- Scores drafts 0-100 based on LinkedIn best practices
- Implements interrupt before posting for human approval
- Handles post editing and final confirmation
- Executes post via LinkedIn client matching auth_mode

**Monitoring Agent (LangGraph)**
- Scheduled execution every 2 hours via APScheduler
- Fetches comments/reactions on user posts
- Fetches recent posts from watchlist profiles (up to 5 per profile)
- Classifies engagement opportunities using Fast LLM
- Generates suggested reactions/comments using Primary LLM
- Persists suggestions to pending_engagements with status="pending"
- Implements interrupt for human approval before posting


**Chat Agent**
- Handles general_query intent
- Uses Primary LLM for conversational responses
- Accesses context from chat_history
- Does not use LangGraph (stateless responses)

#### Integration Layer

**LLM Client Manager**
- Wraps OpenAI-compatible clients for Sarvam and Groq
- Implements retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
- Enforces 30-second timeout per request
- Logs all calls with model, prompt_length, completion_length, latency
- Reads API keys from Secrets Manager
- Propagates trace_id through all calls

**LinkedIn Client Manager**
- Selects client based on AUTH_MODE environment variable
- OAuth mode: Uses linkedin-api-python for all operations
- Browser mode: Uses Playwright + playwright-stealth for writes, Voyager for reads
- Implements fallback: Browser mode tries Voyager on Playwright failure (read-only)
- Enforces rate limits: 30s delay between operations in browser mode
- Applies Human_Like_Delay (2-7s random) for browser writes
- Implements retry logic: 2 attempts with exponential backoff (5s, 10s)
- Manages OAuth token refresh automatically
- Manages browser session cookies with re-authentication on expiry
- Validates session before each operation

**Voice Service Manager**
- Wraps Sarvam STT (Saarika) for transcription
- Wraps Sarvam TTS (Bulbul v3) for speech synthesis
- Supports WebSocket (real-time) and REST (batch) for STT
- Validates audio format before sending to STT
- Implements retry logic matching LLM client
- Returns descriptive errors on service failures

#### Data Layer

**PostgreSQL State Store**
- Stores all application data per database schema (Requirement 20)
- Enforces foreign key constraints with cascade deletes
- Implements AES-256 encryption for sensitive fields
- Provides connection pooling for concurrent requests

**LangGraph PostgresSaver**
- Manages checkpoints table for LangGraph state serialization
- Persists state after each node execution
- Supports concurrent graph executions with isolated thread_ids
- Enables workflow resumption after interrupts

**Secrets Manager**
- Environment variable-based secrets (production: AWS Secrets Manager, Azure Key Vault, etc.)
- Stores: SARVAM_API_KEY, GROQ_API_KEY, DATABASE_URL, ENCRYPTION_KEY, LINKEDIN_USERNAME (browser mode), LINKEDIN_PASSWORD (browser mode)
- Validates all secrets at startup, fails fast on missing secrets


### Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        LB[Load Balancer<br/>HTTPS Termination]
        
        subgraph "Application Tier"
            API1[FastAPI Instance 1<br/>+ LangGraph Agents]
            API2[FastAPI Instance 2<br/>+ LangGraph Agents]
        end
        
        subgraph "Data Tier"
            PG[(PostgreSQL Primary<br/>State Store)]
            PGR[(PostgreSQL Replica<br/>Read Queries)]
        end
        
        subgraph "Frontend Tier"
            Next[Next.js<br/>Static + SSR]
        end
        
        subgraph "Secrets"
            SM[Secrets Manager<br/>AWS/Azure/GCP]
        end
    end
    
    Internet[Internet Users] --> LB
    LB --> Next
    Next --> LB
    LB --> API1
    LB --> API2
    API1 --> PG
    API2 --> PG
    API1 --> PGR
    API2 --> PGR
    API1 --> SM
    API2 --> SM
    PG -.Replication.-> PGR
```

**Deployment Notes:**
- FastAPI instances are horizontally scalable (stateless except LangGraph checkpoints in DB)
- PostgreSQL replication for read-heavy operations (monitoring queries)
- LangGraph checkpoints enable cross-instance workflow resumption
- Secrets Manager integration for credential management
- HTTPS enforced at load balancer
- Health checks via GET /health endpoint


## LangGraph Agent Designs

### Content Creation Agent

#### State Model

```python
from typing import TypedDict, Literal, Optional
from datetime import datetime

class ContentCreationState(TypedDict):
    """State for Content Creation Agent workflow."""
    # Inputs
    user_id: str  # UUID as string
    thread_id: str  # UUID as string
    trace_id: str  # UUID as string
    user_input: str  # Original post idea from user
    
    # Generated drafts
    drafts: list[dict]  # [{"content": str, "score": int}, ...]
    
    # User interaction
    selected_draft_index: Optional[int]  # Index of approved draft
    edited_content: Optional[str]  # User-edited final content
    
    # Execution results
    posted: bool  # Whether post was successfully published
    post_url: Optional[str]  # LinkedIn URL of posted content
    error: Optional[str]  # Error message if any step failed
    
    # Status tracking
    status: Literal[
        "draft_generation",
        "draft_evaluation",
        "awaiting_approval",
        "awaiting_edit_confirmation",
        "posting",
        "completed",
        "failed"
    ]
```


#### Graph Structure

```mermaid
stateDiagram-v2
    [*] --> CheckExistingDrafts
    
    CheckExistingDrafts --> GenerateDrafts: No drafts exist
    CheckExistingDrafts --> AwaitApproval: Drafts exist (idempotency)
    
    GenerateDrafts --> EvaluateDrafts
    EvaluateDrafts --> PersistDrafts
    PersistDrafts --> AwaitApproval
    
    AwaitApproval --> [*]: INTERRUPT (human approval needed)
    
    note right of AwaitApproval
        System persists drafts to DB
        Returns to user for review
        User calls POST /approve/{action_id}
        with selected draft index
    end note
    
    [*] --> AllowEditing: Resume after approval
    
    AllowEditing --> AwaitEditConfirmation
    AwaitEditConfirmation --> [*]: INTERRUPT (edit confirmation)
    
    note right of AwaitEditConfirmation
        User can edit selected draft
        User confirms final content
        System resumes with edited content
    end note
    
    [*] --> PostToLinkedIn: Resume after edit confirmation
    
    PostToLinkedIn --> RecordSuccess: Post succeeded
    PostToLinkedIn --> RecordFailure: Post failed
    
    RecordSuccess --> [*]
    RecordFailure --> [*]
```


#### Node Implementations

**Node: CheckExistingDrafts**
```python
def check_existing_drafts(state: ContentCreationState) -> ContentCreationState:
    """Check if drafts already exist for this thread_id (idempotency)."""
    existing_drafts = db.query(
        "SELECT content, score FROM posts_drafted WHERE thread_id = %s AND status = 'pending'",
        (state["thread_id"],)
    )
    
    if existing_drafts:
        state["drafts"] = [
            {"content": row["content"], "score": row["score"]}
            for row in existing_drafts
        ]
        state["status"] = "awaiting_approval"
    else:
        state["status"] = "draft_generation"
    
    return state
```

**Node: GenerateDrafts**
```python
def generate_drafts(state: ContentCreationState) -> ContentCreationState:
    """Generate 2-3 post variations using Primary LLM."""
    prompt = f"""Generate 2-3 LinkedIn post variations based on this idea:
    
{state['user_input']}

Requirements:
- Professional tone suitable for LinkedIn
- Engaging hooks in first line
- Use relevant hashtags
- Keep under 3000 characters
- Vary style across drafts (e.g., storytelling, list, question-based)

Return as JSON array: [{{"content": "post text"}}, ...]
"""
    
    response = llm_client.call_primary_llm(
        prompt=prompt,
        trace_id=state["trace_id"],
        response_format="json"
    )
    
    drafts_raw = json.loads(response)
    state["drafts"] = drafts_raw  # No scores yet
    state["status"] = "draft_evaluation"
    
    return state
```


**Node: EvaluateDrafts**
```python
def evaluate_drafts(state: ContentCreationState) -> ContentCreationState:
    """Score each draft 0-100 based on LinkedIn best practices."""
    for draft in state["drafts"]:
        prompt = f"""Evaluate this LinkedIn post and assign a score 0-100.

Criteria:
- Hook quality (first line captures attention)
- Professional tone and clarity
- Appropriate length (300-1500 chars ideal)
- Hashtag usage (2-5 relevant hashtags)
- Call-to-action or engagement prompt
- Grammar and formatting

Post:
{draft['content']}

Return JSON: {{"score": <int>, "reasoning": "<brief explanation>"}}
"""
        
        response = llm_client.call_primary_llm(
            prompt=prompt,
            trace_id=state["trace_id"],
            response_format="json"
        )
        
        evaluation = json.loads(response)
        draft["score"] = evaluation["score"]
        draft["reasoning"] = evaluation["reasoning"]
    
    # Sort by score descending
    state["drafts"] = sorted(state["drafts"], key=lambda d: d["score"], reverse=True)
    state["status"] = "draft_evaluation"
    
    return state
```

**Node: PersistDrafts**
```python
def persist_drafts(state: ContentCreationState) -> ContentCreationState:
    """Save drafts to database before interrupt."""
    for i, draft in enumerate(state["drafts"]):
        db.execute(
            """INSERT INTO posts_drafted 
               (draft_id, user_id, thread_id, content, score, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (draft_id) DO NOTHING""",
            (
                str(uuid.uuid4()),
                state["user_id"],
                state["thread_id"],
                draft["content"],
                draft["score"],
                "pending",
                datetime.utcnow()
            )
        )
    
    state["status"] = "awaiting_approval"
    return state
```


**Node: AwaitApproval (Interrupt Point)**
```python
def await_approval(state: ContentCreationState) -> ContentCreationState:
    """Interrupt for human approval. State is persisted, workflow pauses."""
    # This node triggers an interrupt. LangGraph persists state and returns control.
    # The workflow resumes when POST /approve/{action_id} is called.
    state["status"] = "awaiting_approval"
    return state
```

**Node: AllowEditing**
```python
def allow_editing(state: ContentCreationState) -> ContentCreationState:
    """Prepare selected draft for editing."""
    if state.get("selected_draft_index") is None:
        state["error"] = "No draft selected"
        state["status"] = "failed"
        return state
    
    selected_draft = state["drafts"][state["selected_draft_index"]]
    state["edited_content"] = selected_draft["content"]  # Default to original
    state["status"] = "awaiting_edit_confirmation"
    
    return state
```

**Node: AwaitEditConfirmation (Interrupt Point)**
```python
def await_edit_confirmation(state: ContentCreationState) -> ContentCreationState:
    """Interrupt for user to edit and confirm final content."""
    state["status"] = "awaiting_edit_confirmation"
    return state
```

**Node: PostToLinkedIn**
```python
def post_to_linkedin(state: ContentCreationState) -> ContentCreationState:
    """Post final content to LinkedIn."""
    try:
        final_content = state["edited_content"]
        
        # Apply human-like delay if browser mode
        if linkedin_client.auth_mode == "browser":
            delay = random.uniform(2.0, 7.0)
            time.sleep(delay)
        
        post_url = linkedin_client.create_post(
            user_id=state["user_id"],
            content=final_content,
            trace_id=state["trace_id"]
        )
        
        state["posted"] = True
        state["post_url"] = post_url
        state["status"] = "completed"
        
    except Exception as e:
        state["posted"] = False
        state["error"] = str(e)
        state["status"] = "failed"
    
    return state
```


**Node: RecordSuccess / RecordFailure**
```python
def record_success(state: ContentCreationState) -> ContentCreationState:
    """Update database with successful post."""
    db.execute(
        """UPDATE posts_drafted 
           SET status = 'posted', posted_at = %s 
           WHERE thread_id = %s""",
        (datetime.utcnow(), state["thread_id"])
    )
    return state

def record_failure(state: ContentCreationState) -> ContentCreationState:
    """Log failure for debugging."""
    logger.error(
        "Post creation failed",
        extra={
            "thread_id": state["thread_id"],
            "trace_id": state["trace_id"],
            "error": state["error"]
        }
    )
    return state
```

#### State Persistence Strategy

- **Checkpointer**: PostgresSaver configured with State_Store connection
- **Thread ID**: Generated as UUID v4 at workflow start, persists through interrupts
- **Persistence Timing**: After each node execution automatically via LangGraph
- **Resumption**: POST /approve/{action_id} retrieves thread_id from database, calls `graph.invoke(state, thread={"configurable": {"thread_id": thread_id}})`
- **Concurrent Execution**: Supported via isolated thread_ids
- **Cleanup**: Failed/completed threads cleaned up after 7 days via scheduled job


### Monitoring Agent

#### State Model

```python
from typing import TypedDict, Literal, Optional
from datetime import datetime

class MonitoringState(TypedDict):
    """State for Monitoring Agent workflow."""
    # Inputs
    user_id: str  # UUID as string
    thread_id: str  # UUID as string
    trace_id: str  # UUID as string
    
    # Fetched data
    user_posts: list[dict]  # [{"post_id": str, "url": str, "content": str}, ...]
    post_engagements: list[dict]  # [{"post_id": str, "comments": [...], "reactions": [...]}, ...]
    watchlist_posts: list[dict]  # [{"member_id": str, "posts": [...]}, ...]
    
    # Generated suggestions
    suggestions: list[dict]  # [{"action_type": str, "target_url": str, "content": str, "reasoning": str}, ...]
    
    # Execution tracking
    last_run_at: Optional[datetime]
    error: Optional[str]
    
    # Status tracking
    status: Literal[
        "fetching_user_posts",
        "fetching_engagements",
        "fetching_watchlist",
        "classifying_opportunities",
        "generating_suggestions",
        "awaiting_approval",
        "completed",
        "failed"
    ]
```


#### Graph Structure

```mermaid
stateDiagram-v2
    [*] --> CheckExistingSuggestions
    
    CheckExistingSuggestions --> FetchUserPosts: No suggestions exist
    CheckExistingSuggestions --> AwaitApproval: Suggestions exist (idempotency)
    
    FetchUserPosts --> FetchEngagements
    FetchEngagements --> FetchWatchlistPosts
    FetchWatchlistPosts --> ClassifyOpportunities
    
    ClassifyOpportunities --> GenerateSuggestions
    GenerateSuggestions --> PersistSuggestions
    PersistSuggestions --> AwaitApproval
    
    AwaitApproval --> [*]: INTERRUPT (human approval)
    
    note right of AwaitApproval
        System persists suggestions to pending_engagements
        User reviews via GET /pending
        User approves via POST /approve/{action_id}
        or skips via DELETE /skip/{action_id}
    end note
    
    [*] --> ExecuteEngagement: Resume after approval
    
    ExecuteEngagement --> RecordSuccess: Action succeeded
    ExecuteEngagement --> RecordFailure: Action failed
    
    RecordSuccess --> [*]
    RecordFailure --> [*]
```


#### Node Implementations

**Node: CheckExistingSuggestions**
```python
def check_existing_suggestions(state: MonitoringState) -> MonitoringState:
    """Check if suggestions already exist for this thread_id (idempotency)."""
    existing = db.query(
        """SELECT action_type, target_post_url, suggested_content 
           FROM pending_engagements 
           WHERE thread_id = %s AND status = 'pending'""",
        (state["thread_id"],)
    )
    
    if existing:
        state["suggestions"] = [
            {
                "action_type": row["action_type"],
                "target_url": row["target_post_url"],
                "content": row["suggested_content"]
            }
            for row in existing
        ]
        state["status"] = "awaiting_approval"
    else:
        state["status"] = "fetching_user_posts"
    
    return state
```

**Node: FetchUserPosts**
```python
def fetch_user_posts(state: MonitoringState) -> MonitoringState:
    """Fetch user's 10 most recent LinkedIn posts."""
    try:
        posts = linkedin_client.get_user_posts(
            user_id=state["user_id"],
            limit=10,
            trace_id=state["trace_id"]
        )
        state["user_posts"] = posts
        state["status"] = "fetching_engagements"
    except Exception as e:
        state["error"] = f"Failed to fetch user posts: {e}"
        state["status"] = "failed"
    
    return state
```

**Node: FetchEngagements**
```python
def fetch_engagements(state: MonitoringState) -> MonitoringState:
    """Fetch comments and reactions on user's posts."""
    try:
        engagements = []
        for post in state["user_posts"]:
            comments = linkedin_client.get_post_comments(
                post_id=post["post_id"],
                trace_id=state["trace_id"]
            )
            reactions = linkedin_client.get_post_reactions(
                post_id=post["post_id"],
                trace_id=state["trace_id"]
            )
            engagements.append({
                "post_id": post["post_id"],
                "comments": comments,
                "reactions": reactions
            })
        
        state["post_engagements"] = engagements
        state["status"] = "fetching_watchlist"
    except Exception as e:
        state["error"] = f"Failed to fetch engagements: {e}"
        state["status"] = "failed"
    
    return state
```


**Node: FetchWatchlistPosts**
```python
def fetch_watchlist_posts(state: MonitoringState) -> MonitoringState:
    """Fetch recent posts from watchlist profiles (5 posts per profile)."""
    try:
        watchlist = db.query(
            "SELECT member_id, profile_url FROM watchlist WHERE user_id = %s",
            (state["user_id"],)
        )
        
        watchlist_data = []
        for profile in watchlist:
            posts = linkedin_client.get_profile_posts(
                member_id=profile["member_id"],
                limit=5,
                trace_id=state["trace_id"]
            )
            watchlist_data.append({
                "member_id": profile["member_id"],
                "posts": posts
            })
        
        state["watchlist_posts"] = watchlist_data
        state["status"] = "classifying_opportunities"
    except Exception as e:
        state["error"] = f"Failed to fetch watchlist posts: {e}"
        state["status"] = "failed"
    
    return state
```

**Node: ClassifyOpportunities**
```python
def classify_opportunities(state: MonitoringState) -> MonitoringState:
    """Use Fast LLM to identify high-value engagement opportunities."""
    opportunities = []
    
    # Classify comments on user's posts
    for engagement in state["post_engagements"]:
        for comment in engagement["comments"]:
            prompt = f"""Should we respond to this comment? Answer YES or NO.
            
Comment: {comment['text']}
Author: {comment['author_name']}
Context: Comment on our post about {engagement.get('post_summary', 'N/A')}

Consider: Is it a question? Does it add value? Is the author influential?
"""
            classification = llm_client.call_fast_llm(prompt, state["trace_id"])
            
            if "YES" in classification.upper():
                opportunities.append({
                    "type": "comment_reply",
                    "target_url": comment["url"],
                    "context": comment["text"],
                    "reasoning": classification
                })
    
    # Classify watchlist posts for engagement
    for profile_data in state["watchlist_posts"]:
        for post in profile_data["posts"]:
            prompt = f"""Should we engage with this post? Answer YES or NO.
            
Post: {post['content'][:200]}...
Author: {post['author_name']}

Consider: Is it relevant to our expertise? Is it recent? Does it invite discussion?
"""
            classification = llm_client.call_fast_llm(prompt, state["trace_id"])
            
            if "YES" in classification.upper():
                opportunities.append({
                    "type": "watchlist_engagement",
                    "target_url": post["url"],
                    "context": post["content"],
                    "reasoning": classification
                })
    
    state["opportunities"] = opportunities
    state["status"] = "generating_suggestions"
    return state
```


**Node: GenerateSuggestions**
```python
def generate_suggestions(state: MonitoringState) -> MonitoringState:
    """Use Primary LLM to generate suggested comments/reactions."""
    suggestions = []
    
    for opp in state.get("opportunities", []):
        if opp["type"] == "comment_reply":
            prompt = f"""Generate a professional LinkedIn reply to this comment:
            
Comment: {opp['context']}

Requirements:
- Thoughtful and adds value
- Professional tone
- Under 500 characters
- Natural, not robotic

Return JSON: {{"content": "<reply text>", "action_type": "comment"}}
"""
        else:  # watchlist_engagement
            prompt = f"""Should we react or comment on this post? Suggest an action.

Post: {opp['context'][:300]}

Return JSON: {{
    "action_type": "reaction" or "comment",
    "content": "<comment text if commenting, or reaction type if reacting>"
}}
"""
        
        response = llm_client.call_primary_llm(
            prompt=prompt,
            trace_id=state["trace_id"],
            response_format="json"
        )
        
        suggestion = json.loads(response)
        suggestions.append({
            "action_type": suggestion["action_type"],
            "target_url": opp["target_url"],
            "content": suggestion["content"],
            "reasoning": opp["reasoning"]
        })
    
    state["suggestions"] = suggestions
    state["status"] = "generating_suggestions"
    return state
```

**Node: PersistSuggestions**
```python
def persist_suggestions(state: MonitoringState) -> MonitoringState:
    """Save suggestions to pending_engagements before interrupt."""
    for suggestion in state["suggestions"]:
        db.execute(
            """INSERT INTO pending_engagements 
               (action_id, user_id, thread_id, action_type, target_post_url, 
                suggested_content, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (action_id) DO NOTHING""",
            (
                str(uuid.uuid4()),
                state["user_id"],
                state["thread_id"],
                suggestion["action_type"],
                suggestion["target_url"],
                suggestion["content"],
                "pending",
                datetime.utcnow()
            )
        )
    
    state["status"] = "awaiting_approval"
    return state
```


**Node: ExecuteEngagement**
```python
def execute_engagement(state: MonitoringState) -> MonitoringState:
    """Execute approved engagement action on LinkedIn."""
    try:
        # Retrieve approved action from state
        action = state.get("approved_action")
        if not action:
            state["error"] = "No action to execute"
            state["status"] = "failed"
            return state
        
        # Apply human-like delay if browser mode
        if linkedin_client.auth_mode == "browser":
            delay = random.uniform(2.0, 7.0)
            time.sleep(delay)
        
        if action["action_type"] == "comment":
            linkedin_client.post_comment(
                post_url=action["target_url"],
                content=action["content"],
                trace_id=state["trace_id"]
            )
        elif action["action_type"] == "reaction":
            linkedin_client.add_reaction(
                post_url=action["target_url"],
                reaction_type=action["content"],  # e.g., "LIKE", "CELEBRATE"
                trace_id=state["trace_id"]
            )
        
        state["status"] = "completed"
        
    except Exception as e:
        state["error"] = str(e)
        state["status"] = "failed"
    
    return state
```

**Scheduling Configuration**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

def schedule_monitoring_agent():
    """Schedule monitoring agent to run every 2 hours."""
    scheduler.add_job(
        func=run_monitoring_workflow,
        trigger="interval",
        hours=2,
        id="monitoring_agent",
        replace_existing=True,
        max_instances=1  # Prevent concurrent runs
    )
    scheduler.start()

async def run_monitoring_workflow():
    """Execute monitoring agent for all active users."""
    users = db.query("SELECT user_id FROM users WHERE active = true")
    
    for user in users:
        thread_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        
        try:
            # Run monitoring graph (will interrupt at AwaitApproval)
            monitoring_graph.invoke(
                {
                    "user_id": user["user_id"],
                    "thread_id": thread_id,
                    "trace_id": trace_id,
                    "status": "fetching_user_posts"
                },
                config={"configurable": {"thread_id": thread_id}}
            )
        except Exception as e:
            logger.error(f"Monitoring failed for user {user['user_id']}: {e}")
```


## Sequence Diagrams

### Post Creation with Approval Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant IntentRouter
    participant ContentAgent
    participant PrimaryLLM
    participant DB
    participant LinkedIn
    
    User->>Frontend: "Create post about AI trends"
    Frontend->>API: POST /chat {message, user_id}
    API->>IntentRouter: Classify intent (Fast LLM)
    IntentRouter-->>API: Intent: create_post
    
    API->>ContentAgent: Start workflow (new thread_id)
    ContentAgent->>ContentAgent: CheckExistingDrafts
    ContentAgent->>PrimaryLLM: Generate 2-3 variations
    PrimaryLLM-->>ContentAgent: Draft variations
    
    ContentAgent->>PrimaryLLM: Evaluate each draft (0-100)
    PrimaryLLM-->>ContentAgent: Scores + reasoning
    
    ContentAgent->>DB: Persist drafts (status=pending)
    ContentAgent->>ContentAgent: AwaitApproval (INTERRUPT)
    ContentAgent-->>API: Workflow interrupted
    
    API-->>Frontend: {drafts: [...], thread_id}
    Frontend-->>User: Display 3 drafts with scores
    
    User->>Frontend: Select draft #2, edit content
    Frontend->>API: POST /approve/{action_id} {draft_index, edited_content}
    
    API->>DB: Retrieve thread_id for action_id
    API->>ContentAgent: Resume workflow with thread_id
    ContentAgent->>ContentAgent: AllowEditing (set edited_content)
    ContentAgent->>ContentAgent: AwaitEditConfirmation (INTERRUPT)
    ContentAgent-->>API: Workflow interrupted
    
    API-->>Frontend: {status: awaiting_confirmation}
    Frontend-->>User: "Ready to post?"
    
    User->>Frontend: Confirm
    Frontend->>API: POST /approve/{action_id} {confirmed: true}
    
    API->>ContentAgent: Resume workflow
    ContentAgent->>LinkedIn: Post content (+ human delay if browser mode)
    LinkedIn-->>ContentAgent: Post URL
    
    ContentAgent->>DB: Update status=posted, posted_at
    ContentAgent-->>API: {status: completed, post_url}
    
    API-->>Frontend: Success response
    Frontend-->>User: "Post published!"
```


### Engagement Suggestion and Approval Flow

```mermaid
sequenceDiagram
    participant Scheduler
    participant MonitoringAgent
    participant FastLLM
    participant PrimaryLLM
    participant LinkedIn
    participant DB
    participant User
    participant Frontend
    participant API
    
    Scheduler->>MonitoringAgent: Trigger (every 2 hours)
    MonitoringAgent->>DB: Fetch active users
    
    loop For each user
        MonitoringAgent->>MonitoringAgent: CheckExistingSuggestions
        MonitoringAgent->>LinkedIn: Get user's 10 recent posts
        LinkedIn-->>MonitoringAgent: Posts data
        
        MonitoringAgent->>LinkedIn: Get comments + reactions per post
        LinkedIn-->>MonitoringAgent: Engagement data
        
        MonitoringAgent->>DB: Get watchlist profiles
        MonitoringAgent->>LinkedIn: Get 5 recent posts per profile
        LinkedIn-->>MonitoringAgent: Watchlist posts
        
        MonitoringAgent->>FastLLM: Classify engagement opportunities
        FastLLM-->>MonitoringAgent: High-value items flagged
        
        MonitoringAgent->>PrimaryLLM: Generate suggestions (comments/reactions)
        PrimaryLLM-->>MonitoringAgent: Suggested actions
        
        MonitoringAgent->>DB: Persist to pending_engagements
        MonitoringAgent->>MonitoringAgent: AwaitApproval (INTERRUPT)
    end
    
    User->>Frontend: Open app
    Frontend->>API: GET /pending {user_id}
    API->>DB: Query pending_engagements
    DB-->>API: Pending actions
    API-->>Frontend: List of suggestions
    Frontend-->>User: Display pending actions
    
    User->>Frontend: Approve action #3, edit comment
    Frontend->>API: POST /approve/{action_id} {edited_content}
    
    API->>DB: Retrieve thread_id
    API->>MonitoringAgent: Resume workflow
    MonitoringAgent->>LinkedIn: Post comment (+ human delay)
    LinkedIn-->>MonitoringAgent: Success
    
    MonitoringAgent->>DB: Update status=posted, completed_at
    MonitoringAgent-->>API: {status: completed}
    
    API-->>Frontend: Success
    Frontend-->>User: "Comment posted!"
```


### OAuth Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant LinkedIn
    participant DB
    participant SecretsManager
    
    User->>Frontend: Click "Connect LinkedIn"
    Frontend->>API: GET /auth/linkedin/start
    API->>API: Generate OAuth state token
    API->>DB: Store state token temporarily
    API-->>Frontend: {auth_url: LinkedIn OAuth URL}
    
    Frontend->>LinkedIn: Redirect to OAuth consent page
    User->>LinkedIn: Authorize application
    LinkedIn-->>Frontend: Redirect with code + state
    
    Frontend->>API: GET /auth/linkedin/callback?code=...&state=...
    API->>DB: Validate state token
    API->>LinkedIn: Exchange code for tokens
    LinkedIn-->>API: {access_token, refresh_token, expires_in}
    
    API->>SecretsManager: Get encryption key
    API->>API: Encrypt tokens (AES-256)
    API->>DB: Store encrypted tokens in users table
    API->>API: Generate JWT session token
    
    API-->>Frontend: {session_token, user_id}
    Frontend->>Frontend: Store session_token in localStorage
    Frontend-->>User: "Connected successfully!"
    
    Note over API,LinkedIn: Future API calls use stored tokens
    
    Frontend->>API: POST /chat {message, bearer: session_token}
    API->>DB: Retrieve encrypted access_token
    API->>API: Decrypt access_token
    API->>LinkedIn: API call with access_token
    
    alt Token expired
        LinkedIn-->>API: 401 Unauthorized
        API->>DB: Retrieve encrypted refresh_token
        API->>LinkedIn: Refresh token request
        LinkedIn-->>API: {new_access_token, new_refresh_token}
        API->>API: Encrypt new tokens
        API->>DB: Update tokens
        API->>LinkedIn: Retry original request
    end
    
    LinkedIn-->>API: Success response
    API-->>Frontend: Data
```


### Browser Automation Session Management

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Playwright
    participant LinkedIn
    participant DB
    participant SecretsManager
    
    Note over API: AUTH_MODE=browser configured
    
    User->>Frontend: Click "Connect LinkedIn"
    Frontend->>API: POST /auth/browser/start
    
    API->>SecretsManager: Get LinkedIn username + password
    API->>Playwright: Launch browser (stealth mode)
    Playwright->>LinkedIn: Navigate to login page
    
    Playwright->>LinkedIn: Fill username (with typing delays)
    Playwright->>LinkedIn: Fill password (with typing delays)
    Playwright->>LinkedIn: Click login button
    
    LinkedIn-->>Playwright: Set session cookies
    Playwright->>Playwright: Extract cookies + localStorage
    
    API->>SecretsManager: Get encryption key
    API->>API: Encrypt session data (AES-256)
    API->>DB: Store encrypted session in users table
    API->>Playwright: Close browser
    
    API-->>Frontend: {status: connected, user_id}
    Frontend-->>User: "Connected successfully!"
    
    Note over API,LinkedIn: Future operations reuse session
    
    Frontend->>API: POST /chat {message, bearer: session_token}
    API->>DB: Retrieve encrypted browser_session
    API->>API: Decrypt session
    API->>Playwright: Launch browser with stored cookies
    Playwright->>LinkedIn: Navigate to target page
    
    alt Session valid
        LinkedIn-->>Playwright: Page loads successfully
        Playwright->>LinkedIn: Perform action (e.g., post content)
    else Session expired
        LinkedIn-->>Playwright: Redirect to login
        API->>SecretsManager: Get credentials
        API->>Playwright: Re-authenticate
        Playwright->>LinkedIn: Login flow
        LinkedIn-->>Playwright: New session
        API->>API: Encrypt new session
        API->>DB: Update browser_session
        Playwright->>LinkedIn: Retry action
    end
    
    LinkedIn-->>Playwright: Action result
    Playwright-->>API: Success
    API->>Playwright: Close browser
    API-->>Frontend: Data
```


## Data Models

### Database Schema

#### Table: users

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id TEXT NOT NULL,  -- LinkedIn member ID
    email TEXT,
    encrypted_access_token TEXT,  -- AES-256 encrypted (OAuth mode)
    encrypted_refresh_token TEXT,  -- AES-256 encrypted (OAuth mode)
    encrypted_browser_session TEXT,  -- AES-256 encrypted (browser mode)
    auth_mode TEXT NOT NULL CHECK (auth_mode IN ('oauth', 'browser')),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_member_id ON users(member_id);
CREATE INDEX idx_users_auth_mode ON users(auth_mode);
CREATE INDEX idx_users_active ON users(active);
```

#### Table: posts_drafted

```sql
CREATE TABLE posts_drafted (
    draft_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    thread_id UUID NOT NULL,  -- LangGraph thread ID
    content TEXT NOT NULL,
    score INTEGER CHECK (score >= 0 AND score <= 100),
    reasoning TEXT,  -- LLM evaluation reasoning
    status TEXT NOT NULL CHECK (status IN ('pending', 'posted', 'rejected', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    posted_at TIMESTAMP WITH TIME ZONE,
    post_url TEXT,  -- LinkedIn URL after posting
    error_message TEXT
);

CREATE INDEX idx_posts_user_id ON posts_drafted(user_id);
CREATE INDEX idx_posts_thread_id ON posts_drafted(thread_id);
CREATE INDEX idx_posts_status ON posts_drafted(status);
CREATE INDEX idx_posts_created_at ON posts_drafted(created_at DESC);
```


#### Table: pending_engagements

```sql
CREATE TABLE pending_engagements (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    thread_id UUID NOT NULL,  -- LangGraph thread ID
    action_type TEXT NOT NULL CHECK (action_type IN ('comment', 'reaction', 'message')),
    target_post_url TEXT NOT NULL,
    suggested_content TEXT NOT NULL,
    edited_content TEXT,  -- User-edited version
    reasoning TEXT,  -- Why this opportunity was flagged
    status TEXT NOT NULL CHECK (status IN ('pending', 'posted', 'skipped', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

CREATE INDEX idx_engagements_user_id ON pending_engagements(user_id);
CREATE INDEX idx_engagements_thread_id ON pending_engagements(thread_id);
CREATE INDEX idx_engagements_status ON pending_engagements(status);
CREATE INDEX idx_engagements_created_at ON pending_engagements(created_at DESC);
CREATE INDEX idx_engagements_action_type ON pending_engagements(action_type);
```

#### Table: watchlist

```sql
CREATE TABLE watchlist (
    watchlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,  -- LinkedIn member ID
    profile_url TEXT NOT NULL,
    profile_name TEXT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_checked_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, member_id)
);

CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX idx_watchlist_member_id ON watchlist(member_id);

-- Enforce max 50 profiles per user
CREATE OR REPLACE FUNCTION check_watchlist_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM watchlist WHERE user_id = NEW.user_id) >= 50 THEN
        RAISE EXCEPTION 'Watchlist limit of 50 profiles exceeded';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER watchlist_limit_trigger
BEFORE INSERT ON watchlist
FOR EACH ROW EXECUTE FUNCTION check_watchlist_limit();
```


#### Table: chat_history

```sql
CREATE TABLE chat_history (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    trace_id UUID NOT NULL,  -- For request tracing
    message TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    intent TEXT,  -- Classified intent (e.g., 'create_post', 'general_query')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_trace_id ON chat_history(trace_id);
CREATE INDEX idx_chat_created_at ON chat_history(created_at DESC);
```

#### Table: checkpoints (LangGraph)

```sql
-- Managed by LangGraph PostgresSaver
-- Schema created automatically by langgraph-checkpoint-postgres
-- Stores serialized graph state for workflow resumption

CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint BYTEA NOT NULL,  -- Serialized state
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at DESC);
```

#### Table: rate_limit_tracking

```sql
CREATE TABLE rate_limit_tracking (
    tracking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- 'post', 'comment', 'reaction'
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    auth_mode TEXT NOT NULL
);

CREATE INDEX idx_rate_limit_user_id ON rate_limit_tracking(user_id);
CREATE INDEX idx_rate_limit_timestamp ON rate_limit_tracking(timestamp DESC);

-- Cleanup old records (keep last 24 hours)
CREATE OR REPLACE FUNCTION cleanup_rate_limit_tracking()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limit_tracking WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;
```


### Encryption Strategy

**Algorithm**: AES-256-GCM (Galois/Counter Mode)

**Key Management**:
- Encryption key stored in Secrets Manager (environment variable in dev, AWS Secrets Manager/Azure Key Vault in prod)
- Key derivation: PBKDF2 with 100,000 iterations, SHA-256
- Key rotation: Supports versioned keys with metadata column

**Implementation**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os
import base64

class EncryptionService:
    def __init__(self, master_key: str):
        # Derive 256-bit key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'linkedin-ai-agent-salt',  # Use unique salt per deployment
            iterations=100000,
        )
        self.key = kdf.derive(master_key.encode())
        self.aesgcm = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext to base64-encoded ciphertext."""
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Store nonce + ciphertext as base64
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt base64-encoded ciphertext to plaintext."""
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
```

**Encrypted Fields**:
- `users.encrypted_access_token`
- `users.encrypted_refresh_token`
- `users.encrypted_browser_session`


### Migration Approach

**Tool**: Alembic (SQLAlchemy migration tool)

**Migration Strategy**:
1. Initial schema creation (all tables)
2. Add indexes for performance optimization
3. Add encryption to existing tokens (backfill with re-authentication)
4. Add rate limiting table
5. Add LangGraph checkpoints table (via langgraph-checkpoint-postgres)

**Sample Migration**:
```python
# alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', UUID, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('member_id', sa.Text, nullable=False),
        sa.Column('email', sa.Text),
        sa.Column('encrypted_access_token', sa.Text),
        sa.Column('encrypted_refresh_token', sa.Text),
        sa.Column('encrypted_browser_session', sa.Text),
        sa.Column('auth_mode', sa.Text, nullable=False),
        sa.Column('active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    
    # Add check constraint
    op.create_check_constraint(
        'auth_mode_check',
        'users',
        "auth_mode IN ('oauth', 'browser')"
    )
    
    # Create indexes
    op.create_index('idx_users_member_id', 'users', ['member_id'])
    op.create_index('idx_users_auth_mode', 'users', ['auth_mode'])
    op.create_index('idx_users_active', 'users', ['active'])

def downgrade():
    op.drop_table('users')
```


## API Contracts

### Authentication

All endpoints except `/health` require Bearer token authentication.

**Request Header**:
```
Authorization: Bearer <jwt_token>
```

**Token Payload**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1735689600,
  "iat": 1735603200
}
```

### Endpoints

#### POST /chat

**Description**: Send a text message to the agent

**Request**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Create a post about the future of AI"
}
```

**Response** (200 OK):
```json
{
  "response": "I'll help you create a post about AI's future. I'm drafting 3 variations now...",
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "action": "create_post",
  "status": "processing"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Validation error",
  "details": "message field is required"
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "Authentication required",
  "details": "Invalid or missing Bearer token"
}
```

**Response** (500 Internal Server Error):
```json
{
  "error": "LLM service unavailable",
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```


#### POST /voice/transcribe

**Description**: Transcribe audio to text using Sarvam STT

**Request**: Multipart form-data
```
Content-Type: multipart/form-data
```
```
audio: <audio_file> (WAV, MP3, or WebM)
user_id: "550e8400-e29b-41d4-a716-446655440000"
language: "en" (optional, default: "en")
```

**Response** (200 OK):
```json
{
  "transcribed_text": "Create a post about the future of AI",
  "language_detected": "en",
  "confidence": 0.95
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Unsupported audio format",
  "supported_formats": ["audio/wav", "audio/mpeg", "audio/webm"]
}
```

**Response** (500 Internal Server Error):
```json
{
  "error": "Transcription service unavailable"
}
```

#### POST /voice/speak

**Description**: Convert text to speech using Sarvam TTS

**Request**:
```json
{
  "text": "Your post has been published successfully",
  "language": "en",
  "voice": "male" 
}
```

**Response** (200 OK):
```
Content-Type: audio/mpeg
<audio_bytes>
```

**Response** (400 Bad Request):
```json
{
  "error": "Text exceeds maximum length",
  "max_length": 5000,
  "provided_length": 6200
}
```

**Response** (500 Internal Server Error):
```json
{
  "error": "TTS service unavailable"
}
```


#### GET /pending

**Description**: Retrieve pending engagement actions for approval

**Query Parameters**:
- `user_id` (required): UUID

**Response** (200 OK):
```json
{
  "pending_actions": [
    {
      "action_id": "abc123-def456-ghi789",
      "action_type": "comment",
      "target_post_url": "https://linkedin.com/posts/...",
      "suggested_content": "Great insights! I especially agree with your point about...",
      "reasoning": "High-value comment from influential connection asking for opinion",
      "created_at": "2024-01-15T10:30:00Z",
      "post_preview": "The future of AI in healthcare..."
    },
    {
      "action_id": "xyz789-uvw456-rst123",
      "action_type": "reaction",
      "target_post_url": "https://linkedin.com/posts/...",
      "suggested_content": "INSIGHTFUL",
      "reasoning": "Watchlist profile posted relevant content in your domain",
      "created_at": "2024-01-15T09:15:00Z",
      "post_preview": "New research on transformer architectures..."
    }
  ],
  "total_count": 2
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "Authentication required"
}
```

#### POST /approve/{action_id}

**Description**: Approve and optionally edit a pending engagement action

**Path Parameters**:
- `action_id` (required): UUID

**Request**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "edited_content": "Great insights! I especially agree with your point about personalization.",
  "confirmed": true
}
```

**Response** (200 OK):
```json
{
  "status": "posted",
  "action_id": "abc123-def456-ghi789",
  "posted_at": "2024-01-15T10:35:42Z"
}
```

**Response** (404 Not Found):
```json
{
  "error": "Action not found",
  "action_id": "abc123-def456-ghi789"
}
```


#### DELETE /skip/{action_id}

**Description**: Skip a pending engagement action

**Path Parameters**:
- `action_id` (required): UUID

**Request**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "status": "skipped",
  "action_id": "abc123-def456-ghi789"
}
```

#### POST /monitor/add

**Description**: Add a LinkedIn profile to the watchlist

**Request**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_url": "https://www.linkedin.com/in/john-doe/",
  "profile_name": "John Doe"
}
```

**Response** (200 OK):
```json
{
  "watchlist_id": "def789-ghi012-jkl345",
  "member_id": "ACoAABvVa2wB...",
  "profile_name": "John Doe",
  "added_at": "2024-01-15T11:00:00Z"
}
```

**Response** (404 Not Found):
```json
{
  "error": "LinkedIn profile not found",
  "profile_url": "https://www.linkedin.com/in/invalid/"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Watchlist limit exceeded",
  "limit": 50,
  "current_count": 50
}
```


#### DELETE /monitor/remove/{member_id}

**Description**: Remove a profile from the watchlist

**Path Parameters**:
- `member_id` (required): LinkedIn member ID

**Request**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "status": "removed",
  "member_id": "ACoAABvVa2wB..."
}
```

#### GET /monitor/list

**Description**: Get all profiles in the watchlist

**Query Parameters**:
- `user_id` (required): UUID

**Response** (200 OK):
```json
{
  "watchlist": [
    {
      "watchlist_id": "def789-ghi012-jkl345",
      "member_id": "ACoAABvVa2wB...",
      "profile_url": "https://www.linkedin.com/in/john-doe/",
      "profile_name": "John Doe",
      "added_at": "2024-01-15T11:00:00Z",
      "last_checked_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total_count": 1,
  "limit": 50
}
```

#### GET /health

**Description**: Health check endpoint (no authentication required)

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "dependencies": {
    "database": "healthy",
    "sarvam_api": "healthy",
    "groq_api": "healthy",
    "linkedin_oauth": "healthy",
    "langsmith": "healthy"
  },
  "auth_mode": "oauth",
  "version": "1.0.0"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "dependencies": {
    "database": "healthy",
    "sarvam_api": "degraded",
    "groq_api": "healthy",
    "linkedin_oauth": "healthy",
    "langsmith": "healthy"
  }
}
```


## Component Designs

### LLM Client Manager

**Purpose**: Unified interface for Primary LLM (Sarvam-M) and Fast LLM (Groq)

**Configuration**:
```python
from openai import OpenAI
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

class LLMClientManager:
    def __init__(self):
        self.primary_client = OpenAI(
            api_key=os.getenv("SARVAM_API_KEY"),
            base_url="https://api.sarvam.ai/v1"
        )
        
        self.fast_client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True
    )
    def call_primary_llm(
        self,
        prompt: str,
        trace_id: str,
        response_format: str = "text",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Call Sarvam-M for reasoning tasks."""
        start_time = time.time()
        
        try:
            response = self.primary_client.chat.completions.create(
                model="sarvam-m",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30.0
            )
            
            latency = time.time() - start_time
            
            logger.info(
                "Primary LLM call succeeded",
                model="sarvam-m",
                prompt_length=len(prompt),
                completion_length=len(response.choices[0].message.content),
                latency_seconds=latency,
                trace_id=trace_id
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(
                "Primary LLM call failed",
                error=str(e),
                trace_id=trace_id
            )
            raise
```


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True
    )
    def call_fast_llm(
        self,
        prompt: str,
        trace_id: str,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> str:
        """Call Groq llama-3.3-70b for speed-critical tasks."""
        start_time = time.time()
        
        try:
            response = self.fast_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30.0
            )
            
            latency = time.time() - start_time
            
            logger.info(
                "Fast LLM call succeeded",
                model="llama-3.3-70b-versatile",
                prompt_length=len(prompt),
                completion_length=len(response.choices[0].message.content),
                latency_seconds=latency,
                trace_id=trace_id
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(
                "Fast LLM call failed",
                error=str(e),
                trace_id=trace_id
            )
            raise
```

**Usage**:
- **Primary LLM**: Draft generation, content evaluation, comment generation, long-form responses
- **Fast LLM**: Intent classification, opportunity classification, quick parsing, time-sensitive sub-2s responses


### LinkedIn Client Manager

**Purpose**: Abstract LinkedIn operations across OAuth, Browser, and Voyager modes

**Architecture**:
```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import os

class LinkedInClientInterface(ABC):
    """Abstract interface for LinkedIn operations."""
    
    @abstractmethod
    def get_user_posts(self, user_id: str, limit: int, trace_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_post_comments(self, post_id: str, trace_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_post_reactions(self, post_id: str, trace_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_profile_posts(self, member_id: str, limit: int, trace_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def create_post(self, user_id: str, content: str, trace_id: str) -> str:
        pass
    
    @abstractmethod
    def post_comment(self, post_url: str, content: str, trace_id: str) -> None:
        pass
    
    @abstractmethod
    def add_reaction(self, post_url: str, reaction_type: str, trace_id: str) -> None:
        pass
```


**OAuth Implementation**:
```python
from linkedin_api import Linkedin
import structlog

logger = structlog.get_logger()

class LinkedInOAuthClient(LinkedInClientInterface):
    """OAuth-based LinkedIn client using official API."""
    
    def __init__(self, encryption_service):
        self.encryption = encryption_service
        self.auth_mode = "oauth"
    
    def _get_client(self, user_id: str) -> Linkedin:
        """Retrieve and decrypt access token, return authenticated client."""
        user = db.query_one(
            "SELECT encrypted_access_token, encrypted_refresh_token FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user or not user["encrypted_access_token"]:
            raise ValueError("No OAuth credentials found for user")
        
        access_token = self.encryption.decrypt(user["encrypted_access_token"])
        
        try:
            client = Linkedin(access_token=access_token)
            return client
        except Exception as e:
            # Token expired, try refresh
            refresh_token = self.encryption.decrypt(user["encrypted_refresh_token"])
            new_tokens = self._refresh_token(refresh_token)
            
            # Update database
            db.execute(
                """UPDATE users 
                   SET encrypted_access_token = %s, encrypted_refresh_token = %s 
                   WHERE user_id = %s""",
                (
                    self.encryption.encrypt(new_tokens["access_token"]),
                    self.encryption.encrypt(new_tokens["refresh_token"]),
                    user_id
                )
            )
            
            return Linkedin(access_token=new_tokens["access_token"])
    
    def get_user_posts(self, user_id: str, limit: int, trace_id: str) -> List[Dict]:
        """Fetch user's posts via OAuth API."""
        client = self._get_client(user_id)
        
        logger.info(
            "Fetching user posts via OAuth",
            user_id=user_id,
            limit=limit,
            trace_id=trace_id
        )
        
        # Use official LinkedIn API
        posts = client.get_profile_posts(count=limit)
        return self._normalize_posts(posts)
```


**Browser Automation Implementation**:
```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import random
import time

class LinkedInBrowserClient(LinkedInClientInterface):
    """Playwright-based LinkedIn client with stealth mode."""
    
    def __init__(self, encryption_service, secrets_manager):
        self.encryption = encryption_service
        self.secrets = secrets_manager
        self.auth_mode = "browser"
        self.last_action_time = {}  # user_id -> timestamp
        self.min_delay = 30  # seconds between operations
    
    async def _enforce_rate_limit(self, user_id: str):
        """Enforce 30-second minimum delay between operations."""
        last_time = self.last_action_time.get(user_id, 0)
        elapsed = time.time() - last_time
        
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s", user_id=user_id)
            await asyncio.sleep(wait_time)
        
        self.last_action_time[user_id] = time.time()
    
    async def _apply_human_delay(self):
        """Apply random 2-7 second delay to mimic human behavior."""
        delay = random.uniform(2.0, 7.0)
        await asyncio.sleep(delay)
    
    async def _get_browser_context(self, user_id: str):
        """Launch browser with stored session or re-authenticate."""
        user = db.query_one(
            "SELECT encrypted_browser_session FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        if user and user["encrypted_browser_session"]:
            # Restore session
            session_data = json.loads(self.encryption.decrypt(user["encrypted_browser_session"]))
            context = await browser.new_context(storage_state=session_data)
        else:
            # Fresh authentication
            context = await browser.new_context()
            await self._authenticate(context, user_id)
        
        # Apply stealth
        page = await context.new_page()
        await stealth_async(page)
        
        return browser, context, page
```


    async def _authenticate(self, context, user_id: str):
        """Perform LinkedIn login with realistic typing patterns."""
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        
        username = self.secrets.get("LINKEDIN_USERNAME")
        password = self.secrets.get("LINKEDIN_PASSWORD")
        
        # Type with human-like delays
        await page.fill("#username", "")
        for char in username:
            await page.type("#username", char, delay=random.randint(50, 150))
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        await page.fill("#password", "")
        for char in password:
            await page.type("#password", char, delay=random.randint(50, 150))
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        
        # Save session
        session_data = await context.storage_state()
        encrypted_session = self.encryption.encrypt(json.dumps(session_data))
        
        db.execute(
            "UPDATE users SET encrypted_browser_session = %s WHERE user_id = %s",
            (encrypted_session, user_id)
        )
        
        logger.info("Browser authentication successful", user_id=user_id)
    
    async def create_post(self, user_id: str, content: str, trace_id: str) -> str:
        """Create LinkedIn post via browser automation."""
        await self._enforce_rate_limit(user_id)
        await self._apply_human_delay()
        
        browser, context, page = await self._get_browser_context(user_id)
        
        try:
            await page.goto("https://www.linkedin.com/feed/")
            await page.click('button[aria-label="Start a post"]')
            await asyncio.sleep(random.uniform(1, 2))
            
            # Type content with human-like delays
            editor = await page.wait_for_selector('.ql-editor')
            for char in content:
                await editor.type(char, delay=random.randint(30, 100))
            
            await asyncio.sleep(random.uniform(1, 3))
            await page.click('button[data-test-modal-submit-button]')
            await page.wait_for_load_state("networkidle")
            
            logger.info("Post created via browser", user_id=user_id, trace_id=trace_id)
            
            # Extract post URL (implementation specific)
            post_url = await page.evaluate('window.location.href')
            
            return post_url
            
        finally:
            await browser.close()
```


**Voyager Fallback Implementation**:
```python
from linkedin_api import Linkedin as VoyagerLinkedIn

class LinkedInVoyagerClient(LinkedInClientInterface):
    """Unofficial Voyager API client as fallback for browser mode reads."""
    
    def __init__(self, encryption_service):
        self.encryption = encryption_service
        self.auth_mode = "voyager"
    
    def _get_client(self, user_id: str) -> VoyagerLinkedIn:
        """Create Voyager client using stored session cookies."""
        user = db.query_one(
            "SELECT encrypted_browser_session FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user or not user["encrypted_browser_session"]:
            raise ValueError("No browser session found for Voyager client")
        
        session_data = json.loads(self.encryption.decrypt(user["encrypted_browser_session"]))
        
        # Extract li_at cookie from session
        cookies = session_data.get("cookies", [])
        li_at = next((c["value"] for c in cookies if c["name"] == "li_at"), None)
        
        if not li_at:
            raise ValueError("No li_at cookie in session")
        
        # Voyager uses username + li_at cookie
        username = self.secrets.get("LINKEDIN_USERNAME")
        return VoyagerLinkedIn(username, "", cookies={'li_at': li_at})
    
    def get_user_posts(self, user_id: str, limit: int, trace_id: str) -> List[Dict]:
        """Fetch user posts via Voyager API (read-only)."""
        try:
            client = self._get_client(user_id)
            
            logger.info(
                "Fetching user posts via Voyager (fallback)",
                user_id=user_id,
                limit=limit,
                trace_id=trace_id
            )
            
            posts = client.get_profile_posts(count=limit)
            return self._normalize_posts(posts)
            
        except Exception as e:
            logger.error(
                "Voyager fallback failed",
                error=str(e),
                trace_id=trace_id
            )
            raise
    
    def create_post(self, user_id: str, content: str, trace_id: str) -> str:
        """Voyager does not support writes - raise error."""
        raise NotImplementedError("Voyager client is read-only. Use browser automation for writes.")
```


**Client Manager with Fallback Logic**:
```python
class LinkedInClientManager:
    """Manages LinkedIn client selection and fallback logic."""
    
    def __init__(self, encryption_service, secrets_manager):
        self.auth_mode = os.getenv("AUTH_MODE", "oauth")
        
        if self.auth_mode not in ["oauth", "browser"]:
            raise ValueError(f"Invalid AUTH_MODE: {self.auth_mode}")
        
        self.oauth_client = LinkedInOAuthClient(encryption_service)
        self.browser_client = LinkedInBrowserClient(encryption_service, secrets_manager)
        self.voyager_client = LinkedInVoyagerClient(encryption_service)
        
        logger.warning(
            "LinkedIn client initialized",
            auth_mode=self.auth_mode,
            warning="Browser mode uses unofficial methods" if self.auth_mode == "browser" else None
        )
    
    def get_client(self, operation_type: str) -> LinkedInClientInterface:
        """Select appropriate client based on auth mode and operation."""
        if self.auth_mode == "oauth":
            return self.oauth_client
        
        elif self.auth_mode == "browser":
            # Use browser for writes, browser for reads (with Voyager fallback)
            if operation_type in ["create_post", "post_comment", "add_reaction"]:
                return self.browser_client
            else:
                return self.browser_client  # Voyager as fallback in exception handling
    
    async def execute_with_fallback(self, operation: str, *args, **kwargs):
        """Execute operation with fallback to Voyager for browser mode reads."""
        client = self.get_client(operation)
        
        try:
            method = getattr(client, operation)
            return await method(*args, **kwargs) if asyncio.iscoroutinefunction(method) else method(*args, **kwargs)
            
        except Exception as e:
            # Fallback to Voyager for read operations in browser mode
            if self.auth_mode == "browser" and operation in ["get_user_posts", "get_post_comments", "get_post_reactions", "get_profile_posts"]:
                logger.warning(
                    "Browser client failed, attempting Voyager fallback",
                    operation=operation,
                    error=str(e)
                )
                
                try:
                    voyager_method = getattr(self.voyager_client, operation)
                    return voyager_method(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        "Both browser and Voyager clients failed",
                        operation=operation,
                        browser_error=str(e),
                        voyager_error=str(fallback_error)
                    )
                    raise Exception(f"Browser failed: {e}, Voyager failed: {fallback_error}")
            
            raise
```


### Voice Service Manager

**Purpose**: Integrate Sarvam STT (Saarika) and TTS (Bulbul v3)

**Implementation**:
```python
import httpx
from typing import BinaryIO

class VoiceServiceManager:
    """Manages Sarvam voice services (STT + TTS)."""
    
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.stt_url = "https://api.sarvam.ai/speech-to-text"
        self.tts_url = "https://api.sarvam.ai/text-to-speech"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str = "en",
        trace_id: str = None
    ) -> dict:
        """Transcribe audio to text using Sarvam Saarika."""
        start_time = time.time()
        
        try:
            files = {"audio": audio_file}
            data = {"language": language, "model": "saarika"}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = await self.client.post(
                self.stt_url,
                files=files,
                data=data,
                headers=headers
            )
            
            response.raise_for_status()
            result = response.json()
            
            latency = time.time() - start_time
            
            logger.info(
                "STT transcription succeeded",
                language=language,
                latency_seconds=latency,
                trace_id=trace_id
            )
            
            return {
                "transcribed_text": result["text"],
                "language_detected": result.get("language", language),
                "confidence": result.get("confidence", 1.0)
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "STT transcription failed",
                status_code=e.response.status_code,
                error=str(e),
                trace_id=trace_id
            )
            raise Exception("Transcription service unavailable")
```


    async def synthesize_speech(
        self,
        text: str,
        language: str = "en",
        voice: str = "male",
        trace_id: str = None
    ) -> bytes:
        """Convert text to speech using Sarvam Bulbul v3."""
        start_time = time.time()
        
        if len(text) > 5000:
            raise ValueError(f"Text exceeds maximum length: {len(text)} > 5000")
        
        try:
            payload = {
                "text": text,
                "language": language,
                "model": "bulbul-v3",
                "voice": voice
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = await self.client.post(
                self.tts_url,
                json=payload,
                headers=headers
            )
            
            response.raise_for_status()
            audio_bytes = response.content
            
            latency = time.time() - start_time
            
            logger.info(
                "TTS synthesis succeeded",
                text_length=len(text),
                audio_size_bytes=len(audio_bytes),
                latency_seconds=latency,
                trace_id=trace_id
            )
            
            return audio_bytes
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "TTS synthesis failed",
                status_code=e.response.status_code,
                error=str(e),
                trace_id=trace_id
            )
            raise Exception("TTS service unavailable")
```

**Supported Languages**: English (en), Hindi (hi), Hinglish (hi-en)

**Audio Format Validation**:
```python
SUPPORTED_FORMATS = ["audio/wav", "audio/mpeg", "audio/webm"]

def validate_audio_format(file) -> bool:
    """Validate audio file format before sending to STT."""
    content_type = file.content_type
    return content_type in SUPPORTED_FORMATS
```


### Scheduler Design

**Purpose**: Trigger Monitoring Agent every 2 hours

**Implementation**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import structlog

logger = structlog.get_logger()

class MonitoringScheduler:
    """Schedules periodic execution of Monitoring Agent."""
    
    def __init__(self, monitoring_graph, db):
        self.scheduler = AsyncIOScheduler()
        self.monitoring_graph = monitoring_graph
        self.db = db
        self.is_running = False
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.scheduler.add_job(
            func=self._run_monitoring_for_all_users,
            trigger=IntervalTrigger(hours=2),
            id="monitoring_agent",
            name="Monitoring Agent Execution",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs
            coalesce=True  # Combine missed runs into one
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("Monitoring scheduler started (every 2 hours)")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Monitoring scheduler stopped")
    
    async def _run_monitoring_for_all_users(self):
        """Execute monitoring workflow for all active users."""
        logger.info("Starting scheduled monitoring execution")
        
        try:
            users = self.db.query("SELECT user_id FROM users WHERE active = true")
            
            for user in users:
                await self._run_monitoring_for_user(user["user_id"])
            
            logger.info(f"Completed monitoring for {len(users)} users")
            
        except Exception as e:
            logger.error(f"Scheduled monitoring failed: {e}")
```


    async def _run_monitoring_for_user(self, user_id: str):
        """Run monitoring workflow for a single user."""
        thread_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Running monitoring for user {user_id}", trace_id=trace_id)
            
            # Execute LangGraph workflow (will interrupt at AwaitApproval)
            result = await self.monitoring_graph.ainvoke(
                {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "trace_id": trace_id,
                    "status": "fetching_user_posts"
                },
                config={"configurable": {"thread_id": thread_id}}
            )
            
            # Update last run timestamp
            self.db.execute(
                "UPDATE users SET last_monitoring_run = %s WHERE user_id = %s",
                (datetime.utcnow(), user_id)
            )
            
            logger.info(
                f"Monitoring completed for user {user_id}",
                status=result.get("status"),
                suggestions_count=len(result.get("suggestions", [])),
                trace_id=trace_id
            )
            
        except Exception as e:
            logger.error(
                f"Monitoring failed for user {user_id}",
                error=str(e),
                trace_id=trace_id
            )
            # Don't raise - continue with other users
```

**Scheduler Configuration**:
- **Trigger**: Every 2 hours (IntervalTrigger)
- **Max Instances**: 1 (prevents overlapping runs)
- **Coalesce**: True (combines missed runs if system was down)
- **Error Handling**: Logs errors but continues with remaining users
- **Startup**: Initialize in FastAPI `lifespan` event
- **Shutdown**: Graceful shutdown via FastAPI `lifespan` event


## Security Model

### Authentication Mode Architecture

**Configuration**:
```python
# Environment variable determines auth mode
AUTH_MODE = os.getenv("AUTH_MODE", "oauth")  # "oauth" or "browser"

# Validate on startup
if AUTH_MODE not in ["oauth", "browser"]:
    raise ValueError(f"Invalid AUTH_MODE: {AUTH_MODE}. Must be 'oauth' or 'browser'")

# Log mode selection
if AUTH_MODE == "browser":
    logger.warning(
        "Browser automation mode enabled",
        warning="This mode uses unofficial methods and may break without notice"
    )
else:
    logger.info("OAuth mode enabled (recommended for production)")
```

**Mode Characteristics**:

| Aspect | OAuth Mode | Browser Mode |
|--------|-----------|--------------|
| **Authentication** | LinkedIn OAuth 2.0 | Playwright login + cookie storage |
| **API Access** | Official LinkedIn API | Browser automation + Voyager |
| **Credential Storage** | Access + refresh tokens (encrypted) | Session cookies (encrypted) |
| **Rate Limiting** | Official API limits | 30s delay + 10 actions/hour |
| **Human-Like Behavior** | Not applicable | Stealth mode + random delays |
| **Fallback** | None | Voyager for reads |
| **Production Readiness** | ✅ Recommended | ⚠️ Use with caution |
| **Breaking Changes Risk** | Low | High (unofficial) |

**Runtime Mode Selection**:
- Mode is set at startup via `AUTH_MODE` environment variable
- **Cannot** switch modes at runtime (requires restart)
- User-level mode stored in `users.auth_mode` for multi-tenant scenarios
- Per-user mode selection possible via database, but global `AUTH_MODE` sets default


### Credential Encryption Approach

**Encryption Specification**:
- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-HMAC-SHA256, 100k iterations
- **Nonce**: 96-bit random nonce per encryption
- **Storage**: Base64-encoded (nonce + ciphertext)

**Encrypted Data**:
1. **OAuth Mode**:
   - `users.encrypted_access_token`
   - `users.encrypted_refresh_token`

2. **Browser Mode**:
   - `users.encrypted_browser_session` (cookies + localStorage JSON)

3. **Not Encrypted** (stored in Secrets Manager only):
   - API keys (SARVAM_API_KEY, GROQ_API_KEY)
   - Master encryption key (ENCRYPTION_KEY)
   - LinkedIn credentials for browser mode (LINKEDIN_USERNAME, LINKEDIN_PASSWORD)

**Key Rotation Strategy**:
```python
# Add key_version column to users table
ALTER TABLE users ADD COLUMN encryption_key_version INTEGER DEFAULT 1;

# Multi-version encryption service
class VersionedEncryptionService:
    def __init__(self):
        self.keys = {
            1: self._derive_key(os.getenv("ENCRYPTION_KEY_V1")),
            2: self._derive_key(os.getenv("ENCRYPTION_KEY_V2"))  # New key
        }
        self.current_version = 2
    
    def encrypt(self, plaintext: str) -> tuple[str, int]:
        """Encrypt with current key version."""
        encrypted = self._encrypt_with_key(plaintext, self.keys[self.current_version])
        return encrypted, self.current_version
    
    def decrypt(self, encrypted: str, version: int) -> str:
        """Decrypt with specified key version."""
        return self._decrypt_with_key(encrypted, self.keys[version])
```

**Background Key Rotation Job**:
```python
async def rotate_user_credentials():
    """Re-encrypt all user credentials with new key version."""
    users = db.query("SELECT user_id, encrypted_access_token, encryption_key_version FROM users WHERE encryption_key_version < 2")
    
    for user in users:
        # Decrypt with old key
        plaintext = encryption.decrypt(user["encrypted_access_token"], version=user["encryption_key_version"])
        
        # Re-encrypt with new key
        new_encrypted, new_version = encryption.encrypt(plaintext)
        
        # Update database
        db.execute(
            "UPDATE users SET encrypted_access_token = %s, encryption_key_version = %s WHERE user_id = %s",
            (new_encrypted, new_version, user["user_id"])
        )
```


### Secrets Management Strategy

**Development Environment**:
```bash
# .env file (never commit to git)
AUTH_MODE=oauth
SARVAM_API_KEY=sk_sarvam_xxxxx
GROQ_API_KEY=gsk_xxxxx
DATABASE_URL=postgresql://user:pass@localhost:5432/linkedin_agent
ENCRYPTION_KEY=your-32-byte-base64-encoded-key
LINKEDIN_USERNAME=user@example.com  # Only for browser mode
LINKEDIN_PASSWORD=securepassword  # Only for browser mode
JWT_SECRET=your-jwt-secret-key
```

**Production Environment** (AWS):
```python
import boto3
from botocore.exceptions import ClientError

class AWSSecretsManager:
    """Retrieve secrets from AWS Secrets Manager."""
    
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region_name)
        self._cache = {}
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret with caching."""
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret = response["SecretString"]
            self._cache[secret_name] = secret
            return secret
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

# Usage in application
secrets = AWSSecretsManager()
SARVAM_API_KEY = secrets.get_secret("linkedin-agent/sarvam-api-key")
GROQ_API_KEY = secrets.get_secret("linkedin-agent/groq-api-key")
ENCRYPTION_KEY = secrets.get_secret("linkedin-agent/encryption-key")
```

**Startup Validation**:
```python
def validate_secrets():
    """Validate all required secrets are present."""
    required = ["AUTH_MODE", "SARVAM_API_KEY", "GROQ_API_KEY", "DATABASE_URL", "ENCRYPTION_KEY", "JWT_SECRET"]
    
    if os.getenv("AUTH_MODE") == "browser":
        required.extend(["LINKEDIN_USERNAME", "LINKEDIN_PASSWORD"])
    
    missing = [key for key in required if not os.getenv(key)]
    
    if missing:
        raise ValueError(f"Missing required secrets: {', '.join(missing)}")
    
    logger.info("All required secrets validated")
```


### Rate Limiting Implementation

**In-Memory Rate Limiter** (for API-level limits):
```python
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    """In-memory rate limiter for LinkedIn operations."""
    
    def __init__(self):
        self.action_log = defaultdict(list)  # user_id -> [timestamps]
        self.max_actions_per_hour = 10
        self.lock = asyncio.Lock()
    
    async def check_limit(self, user_id: str) -> bool:
        """Check if user can perform an action."""
        async with self.lock:
            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)
            
            # Remove old timestamps
            self.action_log[user_id] = [
                ts for ts in self.action_log[user_id] 
                if ts > one_hour_ago
            ]
            
            # Check limit
            if len(self.action_log[user_id]) >= self.max_actions_per_hour:
                return False
            
            return True
    
    async def record_action(self, user_id: str):
        """Record an action timestamp."""
        async with self.lock:
            self.action_log[user_id].append(datetime.utcnow())
    
    async def wait_for_availability(self, user_id: str):
        """Block until user can perform an action."""
        while not await self.check_limit(user_id):
            oldest = min(self.action_log[user_id])
            wait_until = oldest + timedelta(hours=1)
            wait_seconds = (wait_until - datetime.utcnow()).total_seconds()
            
            logger.info(
                f"Rate limit reached for user {user_id}, waiting {wait_seconds:.0f}s"
            )
            
            await asyncio.sleep(min(wait_seconds, 60))  # Check every minute
```


**Database-Backed Rate Limiting** (for persistent tracking):
```python
class PersistentRateLimiter:
    """Database-backed rate limiter with cross-instance consistency."""
    
    def __init__(self, db):
        self.db = db
        self.max_actions_per_hour = 10
    
    async def check_and_record(self, user_id: str, action_type: str) -> bool:
        """Check limit and record action atomically."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Count recent actions
        count = self.db.query_scalar(
            """SELECT COUNT(*) FROM rate_limit_tracking 
               WHERE user_id = %s AND timestamp > %s""",
            (user_id, one_hour_ago)
        )
        
        if count >= self.max_actions_per_hour:
            logger.warning(
                f"Rate limit exceeded for user {user_id}",
                current_count=count,
                limit=self.max_actions_per_hour
            )
            return False
        
        # Record action
        self.db.execute(
            """INSERT INTO rate_limit_tracking (user_id, action_type, auth_mode, timestamp)
               VALUES (%s, %s, %s, %s)""",
            (user_id, action_type, os.getenv("AUTH_MODE"), datetime.utcnow())
        )
        
        return True
```

**LinkedIn API Rate Limit Handling**:
```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=5, min=5, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True
)
async def linkedin_api_call_with_retry(func, *args, **kwargs):
    """Wrapper for LinkedIn API calls with rate limit retry."""
    try:
        return await func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            # Extract retry-after header
            retry_after = int(e.response.headers.get("Retry-After", 60))
            logger.warning(f"LinkedIn rate limit hit, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            raise  # Trigger retry
        raise
```


## Observability Architecture

### Structured Logging Format

**Log Structure**:
```json
{
  "timestamp": "2024-01-15T12:34:56.789Z",
  "level": "INFO",
  "component": "LinkedInOAuthClient",
  "message": "User posts fetched successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "operation": "get_user_posts",
  "latency_ms": 342,
  "posts_count": 10,
  "auth_mode": "oauth"
}
```

**Logger Configuration**:
```python
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_log_level,
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

**Usage in Code**:
```python
# Bind trace_id to logger context
log = logger.bind(trace_id=trace_id, user_id=user_id)

# Log with structured data
log.info(
    "Fetching user posts",
    operation="get_user_posts",
    limit=10,
    auth_mode="oauth"
)

# Error logging with exception
try:
    result = await operation()
except Exception as e:
    log.error(
        "Operation failed",
        operation="get_user_posts",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True
    )
    raise
```


### Trace ID Propagation

**Request-Level Trace ID**:
```python
from fastapi import Request
import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default=None)

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """Add trace_id to all requests."""
    trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    
    # Bind to structlog context
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    
    return response
```

**Propagation Through LangGraph**:
```python
# Pass trace_id in LangGraph state
initial_state = {
    "user_id": user_id,
    "thread_id": thread_id,
    "trace_id": trace_id_var.get(),
    ...
}

# Use trace_id in all node implementations
def node_function(state: State) -> State:
    logger.info(
        "Node executed",
        node="generate_drafts",
        trace_id=state["trace_id"]
    )
    return state
```

**Propagation to External Services**:
```python
# Add trace_id to external API calls
headers = {
    "Authorization": f"Bearer {api_key}",
    "X-Trace-ID": trace_id
}

response = await client.post(url, headers=headers, json=payload)
```


### Health Check Implementation

**Health Check Endpoint**:
```python
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """Check system and dependency health."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "auth_mode": os.getenv("AUTH_MODE"),
        "dependencies": {}
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Sarvam API
    try:
        response = await httpx.AsyncClient().get(
            "https://api.sarvam.ai/health",
            timeout=5.0
        )
        health_status["dependencies"]["sarvam_api"] = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        health_status["dependencies"]["sarvam_api"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Groq API
    try:
        response = await httpx.AsyncClient().get(
            "https://api.groq.com/health",
            timeout=5.0
        )
        health_status["dependencies"]["groq_api"] = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        health_status["dependencies"]["groq_api"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check LinkedIn (depends on auth mode)
    if os.getenv("AUTH_MODE") == "oauth":
        health_status["dependencies"]["linkedin_oauth"] = "healthy"  # Can't test without user token
    else:
        health_status["dependencies"]["linkedin_browser"] = "not_tested"
    
    # Check LangSmith
    health_status["dependencies"]["langsmith"] = "healthy"  # Assume healthy if no errors
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(content=health_status, status_code=status_code)
```


### Monitoring Metrics

**Key Metrics to Track**:

1. **LLM Metrics**:
   - Calls per minute (by model)
   - Average latency (by model)
   - Token usage (prompt + completion)
   - Error rate
   - Timeout rate

2. **LinkedIn Operation Metrics**:
   - Operations per hour (by type: post, comment, reaction)
   - Success rate (by auth mode)
   - Rate limit hits
   - Fallback usage (browser → Voyager)
   - Average operation latency

3. **Workflow Metrics**:
   - Content creation workflows started/completed
   - Monitoring workflows started/completed
   - Interrupt → resumption time
   - Workflow failure rate

4. **Application Metrics**:
   - API request rate (by endpoint)
   - Response time (by endpoint)
   - Error rate (by status code)
   - Active users
   - Database connection pool usage

**Metrics Exporter** (Prometheus format):
```python
from prometheus_client import Counter, Histogram, Gauge

# LLM metrics
llm_calls = Counter("llm_calls_total", "Total LLM calls", ["model", "status"])
llm_latency = Histogram("llm_latency_seconds", "LLM call latency", ["model"])
llm_tokens = Counter("llm_tokens_total", "Total tokens used", ["model", "type"])

# LinkedIn metrics
linkedin_operations = Counter("linkedin_operations_total", "LinkedIn operations", ["type", "auth_mode", "status"])
linkedin_rate_limits = Counter("linkedin_rate_limits_total", "Rate limit hits", ["auth_mode"])

# Workflow metrics
workflow_starts = Counter("workflow_starts_total", "Workflow starts", ["type"])
workflow_completions = Counter("workflow_completions_total", "Workflow completions", ["type", "status"])

# Application metrics
http_requests = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
http_latency = Histogram("http_latency_seconds", "HTTP request latency", ["endpoint"])
active_users = Gauge("active_users", "Number of active users")
```


### LangSmith Integration

**Configuration**:
```python
import os
from langsmith import Client

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "linkedin-ai-agent"

langsmith_client = Client()
```

**Automatic Tracing**:
- LangGraph automatically sends traces to LangSmith
- All LLM calls are traced with inputs, outputs, and metadata
- Node execution timing and state transitions captured
- Error traces include full stack traces

**Custom Annotations**:
```python
from langsmith import traceable

@traceable(name="generate_post_drafts")
def generate_drafts(state: ContentCreationState) -> ContentCreationState:
    """Generate post drafts with custom tracing."""
    # Function implementation
    return state
```

**Trace Enrichment**:
```python
# Add custom metadata to traces
langsmith_client.create_run(
    name="linkedin_post_creation",
    run_type="chain",
    inputs={"user_input": state["user_input"]},
    extra={
        "user_id": state["user_id"],
        "thread_id": state["thread_id"],
        "auth_mode": os.getenv("AUTH_MODE")
    }
)
```

**Dashboard Views**:
- LLM call latency distribution
- Workflow success/failure rates
- Cost tracking per LLM provider
- Error patterns and stack traces
- User activity heatmaps


## Error Handling

### Error Classification

**Error Categories**:

1. **Validation Errors** (400):
   - Missing required fields
   - Invalid data formats
   - Business rule violations (e.g., watchlist limit exceeded)

2. **Authentication Errors** (401):
   - Missing Bearer token
   - Invalid/expired JWT
   - LinkedIn authentication expired

3. **Authorization Errors** (403):
   - User attempting to access another user's data
   - Insufficient permissions

4. **Not Found Errors** (404):
   - Resource doesn't exist (action_id, member_id)
   - LinkedIn profile not found

5. **Rate Limit Errors** (429):
   - LinkedIn API rate limit exceeded
   - System-imposed rate limit exceeded

6. **External Service Errors** (502):
   - LinkedIn API failures
   - LLM service unavailable
   - Voice service unavailable

7. **Internal Errors** (500):
   - Database connection failures
   - Unexpected exceptions
   - LangGraph execution failures


### Error Response Format

**Standard Error Response**:
```json
{
  "error": "Brief error description",
  "details": "Detailed explanation for developers",
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "timestamp": "2024-01-15T12:34:56.789Z",
  "path": "/chat",
  "suggestion": "Optional suggestion for resolution"
}
```

**Error Handler Implementation**:
```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "trace_id": trace_id_var.get(),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    trace_id = trace_id_var.get()
    
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        trace_id=trace_id,
        path=request.url.path,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": "An unexpected error occurred. Please contact support.",
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )
```


### Retry Policies

**LLM Retry Policy**:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True
)
async def call_llm_with_retry(client, prompt, trace_id):
    """Call LLM with exponential backoff retry."""
    return await client.chat.completions.create(...)
```

**LinkedIn API Retry Policy**:
```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=5, min=5, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying LinkedIn operation (attempt {retry_state.attempt_number})"
    ),
    reraise=True
)
async def linkedin_operation_with_retry(operation, *args, **kwargs):
    """LinkedIn operation with retry logic."""
    return await operation(*args, **kwargs)
```

**No Retry Scenarios**:
- 400 Bad Request (client error, retry won't help)
- 401 Unauthorized (need re-authentication)
- 403 Forbidden (permission issue)
- 404 Not Found (resource doesn't exist)

**Retry Scenarios**:
- 408 Request Timeout
- 429 Too Many Requests (with retry-after header)
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout
- Network timeouts
- Connection errors


## Testing Strategy

### Unit Testing

**Focus Areas**:
- LLM client wrappers (mock external calls)
- LinkedIn client implementations (mock API responses)
- Encryption/decryption functions
- Rate limiting logic
- Input validation
- State transformations in LangGraph nodes

**Example Unit Test**:
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_generate_drafts_node():
    """Test draft generation node."""
    # Mock LLM client
    mock_llm = Mock()
    mock_llm.call_primary_llm.return_value = json.dumps([
        {"content": "Draft 1"},
        {"content": "Draft 2"}
    ])
    
    # Initial state
    state = {
        "user_id": "test-user",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
        "user_input": "Create a post about AI",
        "status": "draft_generation"
    }
    
    # Execute node
    with patch("app.llm_client", mock_llm):
        result = generate_drafts(state)
    
    # Assertions
    assert len(result["drafts"]) == 2
    assert result["status"] == "draft_evaluation"
    assert result["drafts"][0]["content"] == "Draft 1"
```


### Integration Testing

**Focus Areas**:
- End-to-end LangGraph workflows
- Database operations with test database
- API endpoint responses
- OAuth flow simulation
- Browser automation with test LinkedIn account

**Example Integration Test**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_content_creation_workflow():
    """Test complete content creation workflow."""
    # Setup test database
    test_db = setup_test_database()
    
    # Create test user
    user_id = create_test_user(test_db, auth_mode="oauth")
    
    # Initialize graph with test checkpointer
    graph = create_content_creation_graph(test_db)
    
    # Execute workflow
    thread_id = str(uuid.uuid4())
    result = await graph.ainvoke(
        {
            "user_id": user_id,
            "thread_id": thread_id,
            "trace_id": str(uuid.uuid4()),
            "user_input": "Create a post about testing",
            "status": "draft_generation"
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    
    # Verify workflow interrupted at approval
    assert result["status"] == "awaiting_approval"
    
    # Verify drafts persisted
    drafts = test_db.query(
        "SELECT * FROM posts_drafted WHERE thread_id = %s",
        (thread_id,)
    )
    assert len(drafts) >= 2
    
    # Cleanup
    teardown_test_database(test_db)
```


### End-to-End Testing

**Focus Areas**:
- Complete user journeys (signup → post creation → approval → posting)
- Multi-agent coordination (Content Creation + Monitoring)
- Real external service calls (in staging environment)
- Browser automation against test LinkedIn account

**Test Environment**:
- Staging database with isolated test data
- Test LinkedIn account for browser automation
- Sandbox API keys for Sarvam/Groq (if available)
- LangSmith test project for tracing

### Load Testing

**Scenarios**:
1. Concurrent user requests (50 users, 100 req/min)
2. Database connection pool saturation
3. LangGraph concurrent workflow executions
4. Rate limiter under load

**Tools**:
- Locust or k6 for load generation
- PostgreSQL query analysis (pg_stat_statements)
- Application metrics monitoring

## Deployment

### Environment Configuration

**Development**:
```bash
AUTH_MODE=oauth
DATABASE_URL=postgresql://localhost:5432/linkedin_agent_dev
SARVAM_API_KEY=sk_dev_...
GROQ_API_KEY=gsk_dev_...
```

**Production**:
```bash
AUTH_MODE=oauth
DATABASE_URL=<from_secrets_manager>
SARVAM_API_KEY=<from_secrets_manager>
GROQ_API_KEY=<from_secrets_manager>
ENCRYPTION_KEY=<from_secrets_manager>
```

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (for browser mode)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Run database migrations
RUN alembic upgrade head

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


### Kubernetes Deployment

**Deployment Manifest**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: linkedin-agent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: linkedin-agent-api
  template:
    metadata:
      labels:
        app: linkedin-agent-api
    spec:
      containers:
      - name: api
        image: linkedin-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: AUTH_MODE
          value: "oauth"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: linkedin-agent-secrets
              key: database-url
        - name: SARVAM_API_KEY
          valueFrom:
            secretKeyRef:
              name: linkedin-agent-secrets
              key: sarvam-api-key
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: linkedin-agent-secrets
              key: groq-api-key
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: linkedin-agent-secrets
              key: encryption-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: linkedin-agent-api-service
spec:
  selector:
    app: linkedin-agent-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```


## Requirements Traceability

### Requirement Coverage Matrix

| Requirement ID | Design Section | Implementation Components |
|---------------|----------------|---------------------------|
| 1 | Authentication Mode Architecture | LinkedInClientManager, startup validation |
| 2 | Credential Encryption Approach | EncryptionService, OAuth token storage |
| 3 | Browser Automation Session Management | LinkedInBrowserClient, session persistence |
| 4 | Secrets Management Strategy | AWSSecretsManager, startup validation |
| 5 | LangGraph State Model | ContentCreationState, thread_id generation |
| 6 | LangGraph Node Implementations | CheckExistingDrafts, CheckExistingSuggestions |
| 7 | Database Schema | checkpoints table, PostgresSaver configuration |
| 8 | Observability Architecture | structlog, trace_id propagation, LangSmith |
| 9 | Rate Limiting Implementation | RateLimiter, retry policies |
| 10 | LinkedIn Client Manager | execute_with_fallback, Voyager fallback |
| 11 | Component Responsibilities | Startup warning, documentation |
| 12 | Content Creation Workflow | ContentCreationAgent graph |
| 13 | Voice Service Manager | transcribe_audio implementation |
| 14 | Voice Service Manager | synthesize_speech implementation |
| 15 | Scheduler Design | MonitoringScheduler, APScheduler configuration |
| 16 | Monitoring Agent | MonitoringAgent graph, pending_engagements table |
| 17 | LinkedIn Client Implementations | get_user_posts, get_post_comments, get_profile_posts |
| 18 | API Contracts | POST /monitor/add, DELETE /monitor/remove, watchlist table |
| 19 | API Contracts | POST /chat, IntentRouter |
| 20 | Database Schema | All tables with foreign keys and constraints |
| 21 | LLM Client Manager | call_primary_llm, call_fast_llm |
| 22 | LinkedIn Browser Client | _apply_human_delay, playwright-stealth |
| 23 | API Contracts | All endpoint specifications |
| 24 | Error Handling | Error handlers, structured logging |
| 25 | Security Model | HTTPS enforcement, CORS, prepared statements |


## Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-2)

**Deliverables**:
- Database schema and migrations
- Encryption service implementation
- Secrets management integration
- Structured logging setup
- Health check endpoint

**Tasks**:
1. Setup PostgreSQL database
2. Create Alembic migrations for all tables
3. Implement EncryptionService with AES-256-GCM
4. Configure structlog with JSON output
5. Create health check endpoint with dependency checks
6. Setup development environment with .env file

### Phase 2: LLM Integration (Weeks 2-3)

**Deliverables**:
- LLM client manager with retry logic
- Sarvam-M and Groq integration
- LangSmith tracing setup
- Intent classification system

**Tasks**:
1. Implement LLMClientManager with OpenAI-compatible clients
2. Add retry logic with exponential backoff
3. Configure LangSmith tracing
4. Implement intent classification with Fast LLM
5. Write unit tests for LLM clients

### Phase 3: LinkedIn Integration (Weeks 3-5)

**Deliverables**:
- OAuth client implementation
- Browser automation client with stealth mode
- Voyager fallback implementation
- LinkedIn client manager with fallback logic

**Tasks**:
1. Implement LinkedInOAuthClient with token refresh
2. Setup Playwright with playwright-stealth
3. Implement LinkedInBrowserClient with human-like delays
4. Integrate Voyager API for read fallback
5. Implement LinkedInClientManager with mode selection
6. Add rate limiting for browser mode
7. Write integration tests with test LinkedIn account


### Phase 4: LangGraph Agents (Weeks 5-7)

**Deliverables**:
- Content Creation Agent with interrupt points
- Monitoring Agent with scheduling
- PostgresSaver configuration
- Workflow resumption logic

**Tasks**:
1. Define ContentCreationState and MonitoringState models
2. Implement all Content Creation Agent nodes
3. Implement all Monitoring Agent nodes
4. Configure PostgresSaver for state persistence
5. Add interrupt points before human approval
6. Implement workflow resumption via POST /approve
7. Setup APScheduler for monitoring execution
8. Write integration tests for complete workflows

### Phase 5: Voice Services (Weeks 7-8)

**Deliverables**:
- Sarvam STT integration
- Sarvam TTS integration
- Voice endpoints in API
- Audio format validation

**Tasks**:
1. Implement VoiceServiceManager
2. Add POST /voice/transcribe endpoint
3. Add POST /voice/speak endpoint
4. Implement audio format validation
5. Add graceful degradation for voice failures
6. Test with English, Hindi, and Hinglish

### Phase 6: API & Frontend (Weeks 8-10)

**Deliverables**:
- FastAPI backend with all endpoints
- Next.js frontend with chat interface
- Voice recording/playback UI
- Watchlist management UI
- Pending actions review UI

**Tasks**:
1. Implement all REST API endpoints
2. Add authentication middleware
3. Setup CORS configuration
4. Build Next.js chat interface
5. Implement voice recording with MediaRecorder
6. Build pending actions approval UI
7. Implement watchlist management
8. Add error handling and toast notifications


### Phase 7: Testing & Optimization (Weeks 10-11)

**Deliverables**:
- Comprehensive test suite (unit, integration, e2e)
- Load testing results
- Performance optimizations
- Security audit

**Tasks**:
1. Write unit tests (target: 80% coverage)
2. Write integration tests for workflows
3. Write e2e tests for user journeys
4. Conduct load testing with Locust
5. Optimize database queries (add indexes, query analysis)
6. Optimize LLM prompt lengths
7. Conduct security audit (OWASP checklist)
8. Fix identified vulnerabilities

### Phase 8: Deployment & Monitoring (Weeks 11-12)

**Deliverables**:
- Production deployment
- Monitoring dashboards
- Documentation
- Runbooks

**Tasks**:
1. Create Docker images
2. Setup Kubernetes manifests
3. Configure secrets in AWS Secrets Manager
4. Deploy to staging environment
5. Run smoke tests in staging
6. Deploy to production
7. Setup Prometheus + Grafana dashboards
8. Write operational runbooks
9. Create user documentation
10. Train support team


## Open Questions & Considerations

### Technical Decisions

1. **OAuth vs Browser Mode Default**:
   - **Recommendation**: Default to OAuth mode for production
   - **Rationale**: Official API is more stable and compliant
   - **Browser Mode**: Reserve for users who need features not available in OAuth API

2. **Database Replication Strategy**:
   - **Question**: Should we use read replicas for monitoring queries?
   - **Consideration**: Monitoring agent reads are frequent (every 2 hours per user)
   - **Recommendation**: Implement read replicas if user count exceeds 100

3. **LangGraph Checkpoint Cleanup**:
   - **Question**: How long should we retain completed workflow checkpoints?
   - **Recommendation**: 7 days for completed, 30 days for failed (debugging)
   - **Implementation**: Scheduled cleanup job

4. **LLM Provider Fallback**:
   - **Question**: Should we implement Groq → Sarvam fallback for Primary LLM?
   - **Consideration**: Groq is cheaper but less capable
   - **Recommendation**: No fallback; fail fast and alert on Primary LLM failures

5. **Voice Service Caching**:
   - **Question**: Should we cache TTS audio for common phrases?
   - **Consideration**: "Post published", "Action recorded", etc.
   - **Recommendation**: Implement simple in-memory cache for 10 most common phrases

### Scaling Considerations

1. **Horizontal Scaling**:
   - FastAPI instances are stateless (except in-memory rate limiter)
   - Consider Redis for distributed rate limiting at scale
   - LangGraph state in PostgreSQL enables cross-instance resumption

2. **Database Connection Pooling**:
   - Use asyncpg with connection pool (min: 10, max: 50)
   - Monitor pool saturation metrics
   - Consider PgBouncer for connection pooling at scale

3. **LinkedIn API Quotas**:
   - Track API quota usage across all users
   - Implement proactive throttling to avoid account suspension
   - Consider user-level quota allocation

4. **LLM Cost Optimization**:
   - Cache LLM responses for identical inputs
   - Implement prompt length optimization
   - Monitor token usage and set per-user limits


### Security Considerations

1. **Session Hijacking Prevention**:
   - Implement JWT token rotation
   - Add device fingerprinting
   - Monitor for unusual access patterns

2. **LinkedIn Account Safety**:
   - Enforce conservative rate limits (10 actions/hour)
   - Add randomized delays for browser automation
   - Monitor for LinkedIn account restrictions
   - Implement circuit breaker on repeated failures

3. **Data Privacy**:
   - Encrypt PII at rest (email, member_id)
   - Implement data retention policies
   - Add GDPR compliance (right to deletion)
   - Anonymize logs in production

4. **API Key Security**:
   - Rotate API keys quarterly
   - Implement key versioning
   - Monitor for key leakage
   - Use separate keys per environment

### Operational Considerations

1. **Monitoring Agent Failures**:
   - What happens if monitoring fails for 24 hours?
   - **Recommendation**: Alert on 3 consecutive failures, manual intervention

2. **Workflow Deadlocks**:
   - What if a user never approves a pending action?
   - **Recommendation**: Auto-expire pending actions after 7 days

3. **Database Migrations**:
   - How to handle schema changes with zero downtime?
   - **Recommendation**: Use backward-compatible migrations, deploy in stages

4. **LinkedIn Terms of Service**:
   - Ensure browser automation complies with ToS
   - Monitor for policy changes
   - Implement kill switch for browser mode


## Appendix

### Configuration Reference

**Required Environment Variables**:
```bash
# Authentication Mode
AUTH_MODE=oauth  # or "browser"

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# LLM APIs
SARVAM_API_KEY=sk_sarvam_...
GROQ_API_KEY=gsk_...

# Voice Services (same as Sarvam)
# SARVAM_API_KEY used for both STT and TTS

# Security
ENCRYPTION_KEY=base64-encoded-32-byte-key
JWT_SECRET=your-jwt-secret-key

# LinkedIn (Browser Mode Only)
LINKEDIN_USERNAME=user@example.com
LINKEDIN_PASSWORD=secure_password

# Observability
LANGSMITH_API_KEY=ls__...
LANGCHAIN_PROJECT=linkedin-ai-agent

# Optional
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
CORS_ORIGINS=http://localhost:3000,https://app.example.com
```

### API Client Examples

**Python Client**:
```python
import httpx

class LinkedInAgentClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def send_message(self, message: str):
        """Send a chat message to the agent."""
        response = await self.client.post(
            "/chat",
            json={"message": message},
            headers=self.headers
        )
        return response.json()
    
    async def get_pending_actions(self):
        """Get pending engagement actions."""
        response = await self.client.get(
            "/pending",
            headers=self.headers
        )
        return response.json()
    
    async def approve_action(self, action_id: str, edited_content: str = None):
        """Approve a pending action."""
        response = await self.client.post(
            f"/approve/{action_id}",
            json={"edited_content": edited_content, "confirmed": True},
            headers=self.headers
        )
        return response.json()
```


### Glossary Expansion

**Additional Terms**:

- **Checkpoint**: Serialized LangGraph state stored in PostgreSQL for workflow resumption
- **Human-in-the-Loop**: Pattern where automated workflows pause for human approval
- **Interrupt Point**: LangGraph node that pauses workflow execution and persists state
- **Stealth Mode**: Browser automation technique to avoid detection (playwright-stealth)
- **Token Refresh**: OAuth process of obtaining new access token using refresh token
- **Trace ID**: Unique identifier for request tracking across distributed system
- **Thread ID**: Unique identifier for LangGraph workflow execution instance
- **Voyager API**: Unofficial reverse-engineered LinkedIn API (linkedin-api library)
- **Best Practices Score**: 0-100 score assigned to post drafts by evaluation LLM
- **Engagement Opportunity**: Comment or post flagged by monitoring agent for potential interaction
- **Member ID**: LinkedIn internal identifier (format: ACoAABvVa2wB...)
- **Profile URL**: Public LinkedIn profile URL (format: linkedin.com/in/username)
- **Post URL**: LinkedIn post permalink (format: linkedin.com/posts/...)

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time** | < 500ms (p95) | For non-LLM endpoints |
| **LLM Call Latency** | < 3s (p95) | Primary LLM |
| **LLM Call Latency** | < 2s (p95) | Fast LLM |
| **Intent Classification** | < 2s (p99) | Fast LLM classification |
| **Draft Generation** | < 10s | 3 drafts with evaluation |
| **Database Query** | < 100ms (p95) | Read queries |
| **Database Write** | < 200ms (p95) | Write operations |
| **Health Check** | < 1s | /health endpoint |
| **Workflow Resumption** | < 500ms | After interrupt |
| **Voice Transcription** | < 5s | 30-second audio |
| **Voice Synthesis** | < 3s | 500-character text |


### References

**Technologies**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Playwright Documentation](https://playwright.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Structlog Documentation](https://www.structlog.org/)

**APIs**:
- [Sarvam AI API Documentation](https://docs.sarvam.ai/)
- [Groq API Documentation](https://console.groq.com/docs)
- [LinkedIn OAuth 2.0 Documentation](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [LinkedIn REST API Documentation](https://docs.microsoft.com/en-us/linkedin/shared/integrations/people/profile-api)

**Libraries**:
- [linkedin-api (Voyager)](https://github.com/tomquirk/linkedin-api)
- [playwright-stealth](https://github.com/AtuboDad/playwright_stealth)
- [cryptography (Python)](https://cryptography.io/)
- [tenacity (Python Retry)](https://tenacity.readthedocs.io/)

**Security**:
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Encryption Guidelines](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)

