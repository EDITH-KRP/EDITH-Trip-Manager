import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from app.database import get_database, ObjectId

async def run_test():
    db = get_database()
    print("Database connected successfully.")
    
    # Test insertion
    res = await db.users.insert_one({
        "name": "Integration User",
        "email": "test_integ@example.com",
        "password_hash": "testhash",
        "role": "member",
        "is_active": True,
        "created_at": "2026-11-07T00:00:00Z",
        "must_change_password": False
    })
    uid = res.inserted_id
    print("Inserted User ID:", uid)
    
    # Test find_one by ID
    user = await db.users.find_one({"_id": uid})
    assert user is not None
    assert user["name"] == "Integration User"
    print("Found user:", user["name"], user["_id"])
    
    # Test update_one
    up_res = await db.users.update_one({"_id": uid}, {"$set": {"name": "Integration User Updated"}})
    assert up_res.modified_count == 1
    
    # Verify update
    user_updated = await db.users.find_one({"_id": uid})
    assert user_updated["name"] == "Integration User Updated"
    print("Updated user:", user_updated["name"])
    
    # Test count
    count = await db.users.count_documents({"email": "test_integ@example.com"})
    assert count == 1
    print("Count matched:", count)
    
    # Clean up test user
    from sqlalchemy import text
    with db.engine.begin() as conn:
        conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
    print("Cleanup successful. ALL DATABASE TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_test())
