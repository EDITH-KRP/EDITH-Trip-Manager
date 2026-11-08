import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from app.main import app, lifespan
from app.database import get_database
from app.routes.auth import login
from app.schemas import LoginRequest

async def verify_bootstrap():
    async with lifespan(app):
        db = get_database()
        users = await db.users.find({}).to_list()
        print(f"Total users in DB: {len(users)}")
        for u in users:
            print(f"- {u['name']}: {u['email']} (role: {u['role']})")
        
        # Test login for all 4 users (both full email and simple name)
        test_credentials = [
            ("prajwal@edith.travel", "Prajwal784"),
            ("Prajwal", "Prajwal784"),
            ("parichay@edith.travel", "Parichay392"),
            ("Parichay", "Parichay392"),
            ("srujan@edith.travel", "Srujan516"),
            ("Srujan", "Srujan516"),
            ("nitish@edith.travel", "Nitish628"),
            ("Nitish", "Nitish628"),
        ]
        
        print("\nTesting user logins:")
        for ident, pwd in test_credentials:
            res = await login(LoginRequest(email=ident, password=pwd))
            print(f"✓ Login SUCCESS for '{ident}': Logged in as {res['user']['name']} ({res['user']['role']})")
            
        # Verify group
        group = await db.groups.find_one({"group_code": "EDITH-TRIP-01"})
        assert group is not None
        print(f"\n✓ Group '{group['name']}' ({group['group_code']}) verified. Target: ₹{group['planned_trip_budget']:,}")
        
        # Verify memberships
        memberships = await db.memberships.find({"group_id": str(group["_id"])}).to_list()
        print(f"✓ Total active members in group: {len(memberships)} / 4")
        assert len(memberships) == 4
        
        # Verify savings kitty schedules
        contribs = await db.contributions.find({"group_id": str(group["_id"])}).to_list()
        print(f"✓ Total savings schedule entries: {len(contribs)} (4 members × 12 months = 48)")
        assert len(contribs) == 48

    print("\n🎉 ALL 4 CREW MEMBERS & SAVINGS SCHEDULES ARE FULLY VERIFIED!")

if __name__ == "__main__":
    asyncio.run(verify_bootstrap())

