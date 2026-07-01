# Backend Connection Troubleshooting Guide

## Error: "Failed to fetch. Is the backend running on port 8000?"

This means the frontend cannot connect to the backend API.

## Quick Diagnosis

### Step 1: Check if Backend is Running

Open your terminal where you ran the backend. You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**If you see this** → Backend is running, go to Step 2
**If you DON'T see this** → Backend failed to start, go to Step 3

### Step 2: Test Backend Directly

Open a NEW terminal and run:

```bash
curl http://localhost:8000/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "auth_mode": "browser"
}
```

**If this works** → Backend is running fine, check CORS settings (Step 4)
**If this fails** → Backend is not responding (Step 3)

### Step 3: Backend Failed to Start

Look at your backend terminal for error messages. Common issues:

#### Issue A: Checkpointer Error

**Error message**:
```
ERROR: Application startup failed. Exiting.
AttributeError: '_GeneratorContextManager' object has no attribute 'setup'
```

**Or**:
```
Failed to initialize checkpointer
```

**Solution**: The checkpointer is having issues. Let's temporarily disable it:

1. Stop the backend (Ctrl+C)
2. Edit `backend/app/main.py`
3. Comment out the checkpointer initialization:

```python
# Initialize LangGraph checkpointer
try:
    from app.agents.checkpointer import init_checkpointer
    
    # init_checkpointer()  # COMMENTED OUT TEMPORARILY
    logger.info("LangGraph checkpointer initialization SKIPPED")
except Exception as e:
    logger.error("Failed to initialize checkpointer", error=str(e))
    # raise  # COMMENTED OUT - don't fail startup
```

4. Restart backend:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Note**: With checkpointer disabled, content creation won't work, but general chat will work.

#### Issue B: Database Connection Error

**Error message**:
```
Failed to initialize database
```

**Solution**: 
1. Start PostgreSQL:
```bash
docker start linkedin-postgres
```

2. Verify it's running:
```bash
docker ps
```

3. Restart backend

#### Issue C: Port 8000 Already in Use

**Error message**:
```
OSError: [Errno 48] Address already in use
```

**Solution**:
```bash
# Find and kill the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F

# Then restart backend
```

### Step 4: CORS Issue (Frontend Can't Reach Backend)

If backend is running BUT frontend still shows "Failed to fetch":

1. Check `backend/.env` file has CORS settings:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

2. Make sure frontend is running on one of these ports

3. Check browser console (F12) for CORS errors

## Quick Test Commands

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

### Test 2: Chat Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -d '{"message": "hello", "thread_id": null, "voice_enabled": false}'
```

### Test 3: Pending Actions
```bash
curl http://localhost:8000/api/v1/pending \
  -H "X-User-ID: 1"
```

## Common Solutions Summary

| Issue | Solution |
|-------|----------|
| Backend not running | Start it: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| PostgreSQL not running | Start it: `docker start linkedin-postgres` |
| Port 8000 in use | Kill the process: `taskkill /PID <PID> /F` |
| Checkpointer error | Temporarily comment out `init_checkpointer()` |
| CORS error | Add frontend URL to `CORS_ORIGINS` in `.env` |

## Current Status Check

Run these commands to check everything:

```bash
# 1. Check if PostgreSQL is running
docker ps | findstr postgres

# 2. Check if backend is listening on port 8000
netstat -ano | findstr :8000

# 3. Test backend health
curl http://localhost:8000/health

# 4. Check backend logs
# Look at the terminal where you ran uvicorn
```

## What Happens When You Send a Message

When you type in the chat and hit send, this happens:

1. **Frontend** sends POST request to `http://localhost:8000/api/v1/chat`
2. **Backend** receives the request
3. **Backend** classifies intent (create_post, general_query, etc.)
4. **Backend** processes the message
5. **Backend** sends response back to frontend
6. **Frontend** displays the response

If you see "Failed to fetch", the connection fails at step 1.

## Next Steps Based on Your Situation

### Situation A: Backend Terminal Shows "Application startup complete"
→ Backend is running
→ Test with `curl http://localhost:8000/health`
→ If curl works, check CORS/frontend port
→ If curl fails, check firewall/antivirus

### Situation B: Backend Terminal Shows Error Messages
→ Read the error message
→ Apply the relevant solution above
→ Restart backend
→ Test with health check

### Situation C: No Backend Terminal Open
→ Backend is not running
→ Start it:
```bash
cd C:\Users\Nikhil1616\OneDrive\Desktop\LinkedIn\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Need More Help?

Please share:
1. The LAST 20 lines from your backend terminal
2. The output of: `curl http://localhost:8000/health`
3. Any error messages from browser console (F12 → Console tab)
