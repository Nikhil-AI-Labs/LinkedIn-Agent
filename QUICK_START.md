# Quick Start Guide - LinkedIn AI Agent

## Phase 3 Complete! ✅

All code is written. Now you need to set up the environment and run tests.

## Immediate Actions (Do These Now)

### 1. Update Your .env File

Add these new secrets (old ones are compromised):

```bash
ENCRYPTION_KEY=/8x6mMQjvZmoyntfCYJP4lFGrBisIhyLf8Qm0SQ8Pyo=
JWT_SECRET=GOrN3igZaW994-Ve03JFmfWsRQhK4AddzzLb0ZlArKiMXJI0tQmddjpzfPcSmty1
```

Your `.env` should also have (you already have these):
```bash
SARVAM_API_KEY=sk_l2o5v7ir_5tIIpIq3ohr3uePRYMOiUZeZ
GROQ_API_KEY=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
LANGSMITH_API_KEY=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
```

### 2. Start PostgreSQL

**Option A: Docker (Easiest)**
```bash
docker run --name linkedin-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=linkedin_agent \
  -p 5432:5432 \
  -d postgres:16
```

**Option B: Local Install**
- Download from: https://www.postgresql.org/download/windows/
- Create database: `linkedin_agent`

**Then update .env:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/linkedin_agent
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- FastAPI, SQLAlchemy, Alembic (already installed)
- groq (NEW - Groq Python SDK)
- httpx (upgraded version)
- pytest-mock (NEW - for tests)

### 4. Run Database Migration

```bash
cd backend
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

This creates tables for:
- users, oauth_accounts, browser_sessions
- posts_drafted, pending_engagements
- watchlist, chat_history
- graph_runs, audit_logs
- linkedin_profiles

### 5. Verify Setup

```bash
cd backend
python test_setup.py
```

**Expected output:**
```
======================================================================
LinkedIn AI Agent - Setup Verification
======================================================================

✓ Testing configuration...
✓ Testing encryption...
✓ Testing database connection...

======================================================================
🎉 All systems ready! Phase 2 complete.
======================================================================
```

### 6. Run LLM Tests

```bash
cd backend
pytest tests/test_llm_manager.py -v -s
```

**Expected:** All 4 tests pass
- test_groq_intent_classification ✓
- test_sarvam_draft_post ✓
- test_health_check ✓
- test_retry_on_failure ✓

## If Tests Fail

### "No module named 'app'"
```bash
# Add backend to Python path
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
$env:PYTHONPATH="$(pwd)"  # Windows PowerShell
```

Or run from backend directory:
```bash
cd backend
python -m pytest tests/test_llm_manager.py -v
```

### "Connection to api.sarvam.ai refused"
Check that SARVAM_API_KEY is valid in .env

### "Connection to api.groq.com refused"
Check that GROQ_API_KEY is valid in .env

### "Database connection failed"
- PostgreSQL not running: `docker ps` (should show linkedin-postgres)
- Wrong DATABASE_URL in .env
- Wrong password in DATABASE_URL

## What You Have Now

### Phase 2 (Database) ✅
- 10 SQLAlchemy models
- 6 repositories with status validation
- Browser controller abstraction (Kimi + Playwright stubs)
- Encryption service
- Async session management

### Phase 3 (LLM Manager) ✅
- Sarvam-M client (primary reasoning)
- Groq client (fast classification)
- Task-based routing
- Retry logic with exponential backoff
- 5 prompt templates
- Health checks
- 4 tests

## What's Next (Phase 4)

**LinkedIn Integration** - Build after Phase 3 tests pass:
1. Voyager client (read LinkedIn data)
2. Browser poster (write via Kimi WebBridge)
3. LinkedIn manager (route based on auth_mode)

**Do NOT start Phase 4 until:**
- ✅ PostgreSQL running
- ✅ Migrations applied
- ✅ test_setup.py shows green
- ✅ All LLM tests pass

## Files Created in Phase 3

```
backend/app/services/llm/
├── base.py              (Abstract interface)
├── sarvam_client.py     (Primary LLM)
├── groq_client.py       (Fast LLM)
├── llm_manager.py       (Router + retry)
├── prompts.py           (5 templates)
└── __init__.py          (Exports)

backend/tests/
├── test_llm_manager.py  (4 test cases)
└── __init__.py

backend/
└── test_setup.py        (Verification script)
```

## Key Commands Reference

```bash
# Start PostgreSQL (Docker)
docker run --name linkedin-postgres -e POSTGRES_PASSWORD=pwd -e POSTGRES_DB=linkedin_agent -p 5432:5432 -d postgres:16

# Stop PostgreSQL
docker stop linkedin-postgres

# Restart PostgreSQL
docker start linkedin-postgres

# Install dependencies
cd backend && pip install -r requirements.txt

# Run migrations
cd backend && alembic upgrade head

# Verify setup
cd backend && python test_setup.py

# Run tests
cd backend && pytest tests/test_llm_manager.py -v

# Run all tests
cd backend && pytest -v

# Generate new migration (after model changes)
cd backend && alembic revision --autogenerate -m "description"
```

## Getting Help

If stuck:
1. Check `PHASE_3_COMPLETE.md` for detailed documentation
2. Check `PHASE_2_STATUS.md` for database info
3. Review error messages carefully
4. Ensure all secrets in .env are correct
5. Verify PostgreSQL is running: `docker ps`

## Success Criteria

✅ **Phase 3 is complete when:**
- PostgreSQL running
- Migrations applied
- test_setup.py shows all green
- All 4 LLM tests pass

Then you're ready for Phase 4! 🚀
