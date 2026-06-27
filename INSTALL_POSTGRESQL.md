# Install PostgreSQL - Quick Guide

Your Phase 4 implementation is complete and working! The only remaining step is to install PostgreSQL.

---

## Option 1: Docker (Recommended - Easiest)

### Step 1: Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop/

### Step 2: Run PostgreSQL Container
```powershell
docker run --name linkedin-postgres `
  -e POSTGRES_PASSWORD=yourpassword `
  -e POSTGRES_DB=linkedin_agent `
  -p 5432:5432 `
  -d postgres:14
```

### Step 3: Verify PostgreSQL is Running
```powershell
docker ps
```

You should see `linkedin-postgres` container running.

### Step 4: Run Migrations
```powershell
cd C:\Users\Nikhil1616\OneDrive\Desktop\LinkedIn\backend
alembic upgrade head
```

### Step 5: Verify Setup
```powershell
python test_setup.py
```

Should show: `🎉 All systems ready! Phase 4 complete.`

---

## Option 2: Windows Installer

### Step 1: Download PostgreSQL
Visit: https://www.postgresql.org/download/windows/

Click "Download the installer" and choose:
- **Version**: PostgreSQL 14 or 15
- **Platform**: Windows x86-64

### Step 2: Run Installer
1. Run the downloaded `.exe` file
2. Click "Next" through the wizard
3. **Important Settings**:
   - Installation Directory: Default is fine
   - Components: Select all (PostgreSQL Server, pgAdmin 4, Command Line Tools)
   - Data Directory: Default is fine
   - **Password**: Use `yourpassword` (or change `DATABASE_URL` in `.env`)
   - Port: **5432** (default)
   - Locale: Default

### Step 3: Create Database
After installation:

**Option A: Using pgAdmin 4** (GUI)
1. Open pgAdmin 4 (installed with PostgreSQL)
2. Right-click "Databases" → Create → Database
3. Name: `linkedin_agent`
4. Click "Save"

**Option B: Using Command Line**
```powershell
# Open Command Prompt as Administrator
psql -U postgres
# Enter password when prompted: yourpassword

# Create database
CREATE DATABASE linkedin_agent;

# Verify
\l

# Exit
\q
```

### Step 4: Update .env (If You Changed Password)
If you used a different password during installation, update your `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_ACTUAL_PASSWORD@localhost:5432/linkedin_agent
```

### Step 5: Run Migrations
```powershell
cd C:\Users\Nikhil1616\OneDrive\Desktop\LinkedIn\backend
alembic upgrade head
```

### Step 6: Verify Setup
```powershell
python test_setup.py
```

---

## Troubleshooting

### Issue: "docker: command not found"
**Solution**: Install Docker Desktop from https://www.docker.com/products/docker-desktop/

### Issue: "Port 5432 already in use"
**Solution**: Another PostgreSQL instance is running
```powershell
# Stop the existing service
Stop-Service -Name postgresql*
# Or use Docker on a different port
docker run --name linkedin-postgres -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=linkedin_agent -p 5433:5432 -d postgres:14
# Update DATABASE_URL in .env to use port 5433
```

### Issue: "alembic: command not found"
**Solution**: Install alembic
```powershell
pip install alembic
```

### Issue: "FATAL: password authentication failed"
**Solution**: Your DATABASE_URL password doesn't match PostgreSQL password
1. Check what password you set during PostgreSQL installation
2. Update `DATABASE_URL` in `.env` with correct password

### Issue: "psql: command not found"
**Solution**: Add PostgreSQL to PATH
1. Find PostgreSQL bin directory (usually `C:\Program Files\PostgreSQL\14\bin`)
2. Add to PATH environment variable
3. Restart Command Prompt

---

## After PostgreSQL is Running

### Run All Tests
```powershell
cd backend
pytest tests/test_linkedin_manager.py -v
```

### Start the Application
```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

You should see:
```
INFO - Starting LinkedIn AI Agent
INFO - Database initialized successfully
INFO - LangGraph PostgresSaver initialized successfully
INFO - Initializing LinkedInManager auth_mode=browser
```

---

## Quick Commands Reference

### Docker Commands
```powershell
# Start PostgreSQL
docker start linkedin-postgres

# Stop PostgreSQL
docker stop linkedin-postgres

# View logs
docker logs linkedin-postgres

# Connect to PostgreSQL
docker exec -it linkedin-postgres psql -U postgres -d linkedin_agent
```

### Alembic Commands
```powershell
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history

# Rollback one migration
alembic downgrade -1
```

### Application Commands
```powershell
# Verify setup
python test_setup.py

# Run tests
pytest tests/test_linkedin_manager.py -v

# Start application
python -m uvicorn app.main:app --reload

# Run in background (Windows)
Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--reload" -WindowStyle Hidden
```

---

## Summary

Choose **Docker** if:
- ✅ You want the easiest setup
- ✅ You're familiar with containers
- ✅ You want to easily start/stop PostgreSQL

Choose **Windows Installer** if:
- ✅ You prefer GUI tools (pgAdmin)
- ✅ You want PostgreSQL to run as Windows service
- ✅ You don't want to install Docker

Either option works perfectly! Docker is slightly easier for development.

---

## Next Steps After PostgreSQL

Once PostgreSQL is running and migrations complete:

1. ✅ **Phase 4 is 100% complete**
2. ➡️ **Start Phase 5**: LangGraph Agents Implementation
3. ➡️ **Then Phase 6**: FastAPI Endpoints
4. ➡️ **Then Phase 7**: Voice Services
5. ➡️ **Finally Phase 8**: Frontend (Optional)

You're almost there! Just install PostgreSQL and you're ready for Phase 5! 🚀
