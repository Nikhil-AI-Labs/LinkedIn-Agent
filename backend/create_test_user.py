"""Create a test user for testing the API."""

import asyncio
import uuid
from app.db.session import get_engine
from sqlalchemy import text

async def create_test_user():
    """Create a test user with ID=1."""
    engine = get_engine()
    
    # Use a fixed UUID that looks like integer 1 when cast
    test_user_id = '00000000-0000-0000-0000-000000000001'
    
    try:
        async with engine.begin() as conn:
            # Check if user already exists
            result = await conn.execute(
                text("SELECT id FROM users WHERE id = :user_id"),
                {"user_id": test_user_id}
            )
            if result.fetchone():
                print(f"✓ Test user already exists (ID: {test_user_id})")
                return True
            
            # Insert test user
            await conn.execute(
                text("""
                    INSERT INTO users (id, email, display_name, created_at, updated_at)
                    VALUES (:id, :email, :display_name, NOW() AT TIME ZONE 'utc', NOW() AT TIME ZONE 'utc')
                """),
                {
                    "id": test_user_id,
                    "email": "test@example.com",
                    "display_name": "Test User"
                }
            )
            
            print(f"✓ Test user created successfully (ID: {test_user_id})")
            print(f"  Email: test@example.com")
            print(f"  Name: Test User")
            return True
            
    except Exception as e:
        print(f"✗ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_test_user())
    exit(0 if success else 1)
