# Phase 4 Installation & Verification Guide

## Quick Start

Phase 4 is complete. Follow these steps to install and verify the LinkedIn integration.

---

## Step 1: Install Updated Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**New packages installed**:
- `linkedin-api==2.0.0a5` - Voyager API for READ operations
- `playwright==1.44.0` - Browser automation
- `playwright-stealth==0.0.28` - Anti-detection

### Install Playwright Browsers

```bash
playwright install chromium
```

This downloads the Chromium browser for Playwright automation.

---

## Step 2: Configure Environment Variables

### Option A: Browser Mode (Recommended)

Edit your `.env` file:

```env
# Authentication
AUTH_MODE=browser
BROWSER_PROVIDER=kimi_webbridge

# LinkedIn Credentials (for Voyager READ + Playwright WRITE)
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD_ENCRYPTED=<run encrypt_password.py to get this>

# Encryption Key (already set)
ENCRYPTION_KEY=your_existing_encryption_key
```

### Encrypt Your LinkedIn Password

```bash
cd backend
python scripts/encrypt_password.py
```

Follow the prompts to encrypt your password, then add the output to your `.env` file.

### Option B: OAuth Mode (Not Implemented)

```env
AUTH_MODE=oauth
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

**Note**: OAuth will return "not implemented" errors. Use browser mode.

---

## Step 3: Verify Setup

Run the setup verification script:

```bash
cd backend
python test_setup.py
```

**Expected output**:

```
======================================================================
LinkedIn AI Agent - Setup Verification
======================================================================

✓ Testing configuration...
  Auth mode: browser
  Browser provider: kimi_webbridge
  LinkedIn username: your.email@example.com
  ✓ Kimi WebBridge mode - will reuse existing browser session
  Database URL: postgresql+asyncpg://...

✓ Testing encryption...
  Encryption working correctly

✓ Testing database connection...
  Database connected successfully

======================================================================
🎉 All systems ready! Phase 4 complete.
======================================================================
```

---

## Step 4: Run Tests

Run the LinkedIn integration tests:

```bash
cd backend
pytest tests/test_linkedin_manager.py -v
```

**Expected output**:

```
tests/test_linkedin_manager.py::test_voyager_client_authentication PASSED
tests/test_linkedin_manager.py::test_voyager_client_get_user_posts PASSED
tests/test_linkedin_manager.py::test_kimi_bridge_not_implemented PASSED
tests/test_linkedin_manager.py::test_playwright_poster_validation PASSED
tests/test_linkedin_manager.py::test_playwright_poster_session_expired PASSED
tests/test_linkedin_manager.py::test_linkedin_manager_browser_mode PASSED
tests/test_linkedin_manager.py::test_linkedin_manager_write_fallback PASSED
tests/test_linkedin_manager.py::test_linkedin_manager_oauth_mode PASSED
tests/test_linkedin_manager.py::test_linkedin_manager_read_operations PASSED

========================= 9 passed in 2.50s =========================
```

---

## Step 5: Manual Testing (Optional)

### Test Voyager Client (READ operations)

Create `backend/test_voyager.py`:

```python
import asyncio
from app.services.linkedin.voyager_client import VoyagerClient

async def main():
    client = VoyagerClient()
    
    # Fetch your posts
    result = await client.get_user_posts(
        user_id="your_member_id",  # Replace with your member ID
        limit=5
    )
    
    if result.success:
        print(f"✓ Fetched {len(result.data)} posts")
        for post in result.data:
            print(f"  - {post.content[:50]}...")
    else:
        print(f"✗ Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python test_voyager.py
```

### Test LinkedIn Manager

Create `backend/test_manager.py`:

```python
import asyncio
from app.services.linkedin.linkedin_manager import LinkedInManager

async def main():
    manager = LinkedInManager()
    
    # Test READ
    print("Testing READ operations...")
    result = await manager.get_user_posts(user_id="your_member_id", limit=3)
    if result.success:
        print(f"✓ Fetched {len(result.data)} posts")
    else:
        print(f"✗ Error: {result.error}")
    
    # Test WRITE (will use fallback since Kimi not implemented)
    print("\nTesting WRITE operations...")
    result = await manager.create_post(
        user_id="your_member_id",
        content="Test post from LinkedIn AI Agent"
    )
    if result.success:
        print(f"✓ Post created: {result.data}")
    else:
        print(f"✗ Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python test_manager.py
```

---

## Step 6: Start Application

Start the FastAPI application:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Check the logs for:
```
INFO - Starting LinkedIn AI Agent
INFO - Database initialized successfully
INFO - LangGraph PostgresSaver initialized successfully
INFO - Initializing LinkedInManager auth_mode=browser
```

Visit: http://localhost:8000/docs to see the API docs.

---

## Troubleshooting

### Issue: "LINKEDIN_PASSWORD_ENCRYPTED not found"

**Solution**: Run the encryption script:
```bash
cd backend
python scripts/encrypt_password.py
```

### Issue: "playwright not found"

**Solution**: Install Playwright browsers:
```bash
playwright install chromium
```

### Issue: "linkedin-api import error"

**Solution**: Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

### Issue: "Voyager authentication failed"

**Causes**:
1. Wrong username/password
2. LinkedIn detected automation
3. Account requires 2FA

**Solutions**:
1. Verify credentials in `.env`
2. Re-encrypt password with correct credentials
3. Try logging in manually first

### Issue: "Playwright session expired"

**Solution**: Playwright will automatically re-login. Check logs for authentication flow.

---

## Directory Structure After Phase 4

```
backend/
├── app/
│   ├── services/
│   │   └── linkedin/
│   │       ├── __init__.py
│   │       ├── base.py                    # NEW - Data models
│   │       ├── voyager_client.py          # NEW - READ client
│   │       ├── browser_poster.py          # NEW - WRITE client
│   │       ├── oauth_client.py            # NEW - OAuth stub
│   │       └── linkedin_manager.py        # NEW - Router
│   └── main.py                            # UPDATED - PostgresSaver
├── tests/
│   └── test_linkedin_manager.py           # NEW - Tests
├── scripts/
│   ├── __init__.py                        # NEW
│   └── encrypt_password.py                # NEW - Encryption utility
├── docs/
│   └── LINKEDIN_PASSWORD_ENCRYPTION.md    # NEW - Guide
└── requirements.txt                        # UPDATED - New deps
```

---

## API Usage Examples

Once Phase 6 (API Endpoints) is complete, you'll be able to use:

```python
# GET /api/v1/linkedin/posts?user_id=123&limit=10
# Returns recent posts

# POST /api/v1/linkedin/posts
# Body: {"content": "Hello LinkedIn!"}
# Creates new post

# POST /api/v1/linkedin/comments
# Body: {"post_id": "123", "content": "Great post!"}
# Creates comment
```

---

## Security Checklist

Before deploying:

- [ ] `.env` file is NOT committed to git (check `.gitignore`)
- [ ] `ENCRYPTION_KEY` is securely stored
- [ ] `LINKEDIN_PASSWORD_ENCRYPTED` is used (not plain password)
- [ ] Test setup verification passes
- [ ] All tests pass
- [ ] Logs don't expose credentials
- [ ] Session validation works
- [ ] Error handling tested

---

## Performance Notes

### Voyager Client
- **Latency**: 1-3 seconds per operation (sync library in executor)
- **Rate Limiting**: No explicit limits, but be reasonable
- **Concurrency**: ThreadPoolExecutor with 4 workers

### Playwright Poster
- **Latency**: 5-15 seconds per operation (browser automation + human delays)
- **Rate Limiting**: 30s delay between operations (in design)
- **Concurrency**: Single browser instance (not thread-safe)

---

## Next Steps

Phase 4 is complete and verified! Proceed to:

### Phase 5: LangGraph Agents
- Checkpointer setup
- Content Creation Agent
- Monitoring Agent
- Agent tests

### Phase 6: FastAPI Endpoints
- Chat endpoints
- Approval endpoints
- Watchlist endpoints
- API tests

---

## Support

If you encounter issues:

1. Check logs: `structlog` output shows detailed errors
2. Run tests: `pytest tests/test_linkedin_manager.py -v`
3. Verify config: `python test_setup.py`
4. Check documentation: `backend/docs/LINKEDIN_PASSWORD_ENCRYPTION.md`

---

## Summary

Phase 4 Installation Complete:
- ✅ Dependencies installed
- ✅ Environment configured
- ✅ Setup verified
- ✅ Tests passing
- ✅ Application running

**Status**: Ready for Phase 5
