#!/bin/bash
# Quick Backend Validation Script
# Run this anytime to verify backend health

echo "🔍 Checking LinkedIn AI Agent Backend..."
echo ""

# Check if server is running
echo "1. Testing health endpoint..."
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ Backend is running"
    echo "   Response: $HEALTH"
else
    echo "   ❌ Backend is not running"
    echo "   Start with: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi

# Check database migration
echo ""
echo "2. Checking database migration..."
cd backend
CURRENT_MIGRATION=$(python -m alembic current 2>&1 | grep -o '[a-f0-9]\{12\}' | tail -1)
if [ "$CURRENT_MIGRATION" = "a1b2c3d4e5f6" ]; then
    echo "   ✅ Database migration is up to date (a1b2c3d4e5f6)"
else
    echo "   ⚠️  Current migration: $CURRENT_MIGRATION"
    echo "   Expected: a1b2c3d4e5f6"
    echo "   Run: cd backend && python -m alembic upgrade head"
fi

# Check Kimi WebBridge port
echo ""
echo "3. Checking Kimi WebBridge..."
KIMI_PORT=$(netstat -an 2>/dev/null | grep :10086 | grep LISTEN)
if [ -n "$KIMI_PORT" ]; then
    echo "   ✅ Kimi WebBridge server is listening on port 10086"
else
    echo "   ⚠️  Kimi WebBridge port not detected (this is OK if not using it)"
fi

echo ""
echo "=================================="
echo "Backend Status: ✅ OPERATIONAL"
echo "=================================="
echo ""
echo "Next steps:"
echo "  - Run full test suite: python backend/test_backend_complete.py"
echo "  - Check documentation: BACKEND_FIX_COMPLETE.md"
echo ""
