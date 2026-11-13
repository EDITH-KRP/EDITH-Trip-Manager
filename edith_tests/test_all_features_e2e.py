import os
import sys
from pathlib import Path

# Ensure app is importable
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# Prioritize quick local database initialization for lightning-fast testing
os.environ["SUPABASE_DB_URL"] = ""

import asyncio
from datetime import datetime, date, timezone
from app.main import app, lifespan
from app.database import get_database, ObjectId
from app.schemas import (
    LoginRequest,
    AdminCollectPayment,
    ContributionSubmit,
    ContributionReject,
    KittyDisbursementCreate,
    ExpenseCreate,
    SettlementCreate,
    TripPlanUpdate,
    TripStop,
)
from app.routes.auth import login
from app.routes.groups import group_summary, update_trip_plan, list_group_members
from app.routes.kitty import (
    get_kitty_summary,
    get_all_contributions,
    get_my_contributions,
    admin_record_collection,
    submit_contribution_payment,
    verify_contribution_payment,
    create_kitty_disbursement,
    list_kitty_transactions,
)
from app.routes.expenses import (
    add_expense,
    list_expenses,
    get_balances,
    record_settlement,
    confirm_settlement,
)
from fastapi import HTTPException

# Test reporter helpers
class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.current_section = ""

    def section(self, name: str):
        self.current_section = name
        print(f"\n{'='*75}\n📌 [TEST SUITE] {name}\n{'='*75}")

    def check(self, condition: bool, description: str, detail: str = ""):
        if condition:
            self.passed += 1
            print(f"  ✅ PASS: {description} {f'({detail})' if detail else ''}")
        else:
            self.failed += 1
            print(f"  ❌ FAIL: {description} {f'({detail})' if detail else ''}")
            raise AssertionError(f"Test failed: {description}")

runner = TestRunner()

async def run_all_feature_tests():
    print("\n🚀 STARTING COMPREHENSIVE END-TO-END FEATURE VERIFICATION SUITE")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    async with lifespan(app):
        db = get_database()

        # =====================================================================
        # FEATURE 1: CREW PROVISIONING & ROSTER
        # =====================================================================
        runner.section("1. Crew Identity & Auto-Provisioning")
        
        users_list = await db.users.find({}).to_list()
        user_map = {u["name"]: u for u in users_list}
        
        runner.check(len(users_list) == 4, "Exact 4-member crew provisioned", f"Found {len(users_list)}")
        runner.check("Prajwal" in user_map and user_map["Prajwal"]["role"] == "admin", "Prajwal is Admin", user_map["Prajwal"]["email"])
        runner.check("Parichay" in user_map and user_map["Parichay"]["role"] == "member", "Parichay is Member", user_map["Parichay"]["email"])
        runner.check("Srujan" in user_map and user_map["Srujan"]["role"] == "member", "Srujan is Member", user_map["Srujan"]["email"])
        runner.check("Nitish" in user_map and user_map["Nitish"]["role"] == "member", "Nitish is Member", user_map["Nitish"]["email"])

        group = await db.groups.find_one({"group_code": "EDITH-TRIP-01"})
        runner.check(group is not None, "Group EDITH-TRIP-01 provisioned", group["name"])
        runner.check(group.get("planned_trip_budget") == 96000, "Trip budget is ₹96,000", f"₹{group.get('planned_trip_budget'):,}")

        # =====================================================================
        # FEATURE 2: AUTHENTICATION MATRIX (First name & Email + Security)
        # =====================================================================
        runner.section("2. Authentication Matrix & Role Security")

        # Test login for all 4 with first name
        tokens = {}
        for name, pwd, expected_role in [
            ("Prajwal", "Prajwal784", "admin"),
            ("Parichay", "Parichay392", "member"),
            ("Srujan", "Srujan516", "member"),
            ("Nitish", "Nitish628", "member"),
        ]:
            res = await login(LoginRequest(email=name, password=pwd))
            runner.check(res["user"]["name"] == name, f"Login via first name '{name}'", f"Role: {res['user']['role']}")
            runner.check(res["user"]["role"] == expected_role, f"Role check for '{name}'", expected_role)
            tokens[name] = res["access_token"]

        # Test login with full email
        email_res = await login(LoginRequest(email="prajwal@edith.travel", password="Prajwal784"))
        runner.check(email_res["user"]["email"] == "prajwal@edith.travel", "Login via full email 'prajwal@edith.travel'")

        # Test wrong password rejection
        try:
            await login(LoginRequest(email="Prajwal", password="WrongPassword123"))
            runner.check(False, "Wrong password must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 401, "Wrong password rejected with 401 Unauthorized")

        # Test non-existent user rejection
        try:
            await login(LoginRequest(email="UnknownPerson", password="SomePassword123"))
            runner.check(False, "Unknown user must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 401, "Non-existent user rejected with 401 Unauthorized")

        prajwal_admin = user_map["Prajwal"]
        parichay_member = user_map["Parichay"]
        srujan_member = user_map["Srujan"]
        nitish_member = user_map["Nitish"]

        # =====================================================================
        # FEATURE 3: TRIP FUND (SAVINGS LEDGER & ADMIN DIRECT COLLECTION)
        # =====================================================================
        runner.section("3. Trip Fund: Savings, Admin Direct Collection & Disbursements")

        # Reset month records and transactions for clean, repeatable testing
        await db.contributions.update_many(
            {"group_id": str(group["_id"])},
            {"$set": {"status": "pending", "amount_paid": 0, "utr_reference": None, "notes": ""}}
        )
        await db.kitty_transactions.delete_many({"group_id": str(group["_id"])})
        await db.expenses.delete_many({"group_id": str(group["_id"])})
        await db.settlements.delete_many({"group_id": str(group["_id"])})

        # Check total schedule entries (4 members * 12 months = 48)
        all_contribs_data = await get_all_contributions("EDITH-TRIP-01", admin=prajwal_admin)
        all_contribs = all_contribs_data["contributions"]
        runner.check(len(all_contribs) == 48, "48 monthly savings schedules exist (4 members × 12 months)", f"{len(all_contribs)} rows")

        # Test Admin Direct Payment Recording (Prajwal collects directly via GPay / PhonePe)
        # 1. Collect Month 1 for Parichay
        rec1 = await admin_record_collection(
            group_code="EDITH-TRIP-01",
            payload=AdminCollectPayment(
                user_id=str(parichay_member["_id"]),
                month_index=1,
                amount=2000,
                payment_mode="GPay",
                notes="Received via GPay on 5th",
            ),
            admin=prajwal_admin,
        )
        runner.check("Recorded ₹2,000 from Parichay" in rec1["message"], "Admin direct collection: Parichay Month 1 (GPay)")

        # 2. Collect Month 1 for Srujan
        rec2 = await admin_record_collection(
            group_code="EDITH-TRIP-01",
            payload=AdminCollectPayment(
                user_id=str(srujan_member["_id"]),
                month_index=1,
                amount=2000,
                payment_mode="PhonePe",
                notes="Received via PhonePe UPI",
            ),
            admin=prajwal_admin,
        )
        runner.check("Recorded ₹2,000 from Srujan" in rec2["message"], "Admin direct collection: Srujan Month 1 (PhonePe)")

        # 3. Collect Month 1 for Prajwal
        rec3 = await admin_record_collection(
            group_code="EDITH-TRIP-01",
            payload=AdminCollectPayment(
                user_id=str(prajwal_admin["_id"]),
                month_index=1,
                amount=2000,
                payment_mode="Bank Transfer",
                notes="Self-transferred to trip fund account",
            ),
            admin=prajwal_admin,
        )
        runner.check("Recorded ₹2,000 from Prajwal" in rec3["message"], "Admin direct collection: Prajwal Month 1 (Bank)")

        # Check interim summary
        sum1 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum1["fund_collected"] == 6000, "Trip Fund collected is now ₹6,000", f"₹{sum1['fund_collected']:,}")
        runner.check(sum1["kitty_balance"] == 6000, "Trip Fund balance is now ₹6,000", f"₹{sum1['kitty_balance']:,}")

        # 4. Member UTR submission workflow for Nitish Month 1
        nitish_contribs_data = await get_my_contributions("EDITH-TRIP-01", user=nitish_member)
        nitish_contribs = nitish_contribs_data["contributions"]
        m1_nitish = next(c for c in nitish_contribs if c["month_index"] == 1)
        
        # Nitish submits UTR reference
        sub_res = await submit_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m1_nitish["id"],
            payload=ContributionSubmit(utr_reference="UPI987654321000", payment_date=date.today(), proof_url=None),
            user=nitish_member,
        )
        runner.check("submitted" in sub_res["message"].lower(), "Nitish submits UTR reference 'UPI987654321000'")

        # Admin Prajwal verifies Nitish's contribution
        ver_res = await verify_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m1_nitish["id"],
            admin=prajwal_admin,
        )
        runner.check("verified" in ver_res["message"].lower(), "Admin Prajwal verifies Nitish's contribution")

        # Now all 4 members have completed Month 1!
        sum2 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum2["fund_collected"] == 8000, "All 4 members paid Month 1: Total collected is ₹8,000", f"₹{sum2['fund_collected']:,}")
        runner.check(sum2["kitty_balance"] == 8000, "Trip Fund balance is ₹8,000", f"₹{sum2['kitty_balance']:,}")

        # 5. Fund Disbursement (Paying advance hotel from the Trip Fund)
        disb_res = await create_kitty_disbursement(
            group_code="EDITH-TRIP-01",
            payload=KittyDisbursementCreate(
                amount=2500,
                category="Accommodation",
                description="Advance booking for Manali Riverside Cottage",
                recipient="Manali Cottages Ltd",
                disbursement_date=date.today(),
            ),
            admin=prajwal_admin,
        )
        runner.check(disb_res["new_balance"] == 5500, "Disbursement of ₹2,500 recorded from Trip Fund", disb_res["message"])

        # Verify fund balance after disbursement: 8000 - 2500 = 5500
        sum3 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum3["fund_disbursed"] == 2500, "Total fund disbursed is ₹2,500", f"₹{sum3['fund_disbursed']:,}")
        runner.check(sum3["kitty_balance"] == 5500, "Trip Fund remaining balance is exactly ₹5,500", f"₹{sum3['kitty_balance']:,}")

        # Verify fund transactions ledger
        tx_data = await list_kitty_transactions("EDITH-TRIP-01", user=prajwal_admin)
        txs = tx_data["transactions"]
        runner.check(len(txs) >= 5, "Fund transaction ledger has all 4 inflows and 1 disbursement", f"{len(txs)} tx entries")

        # =====================================================================
        # FEATURE 4: SPLIT EXPENSES (INDEPENDENT SHARED LEDGER & BALANCES)
        # =====================================================================
        runner.section("4. Split Expenses: Shared Ledger, Participant Chips & Net Balances")

        p_id = str(prajwal_admin["_id"])
        pa_id = str(parichay_member["_id"])
        s_id = str(srujan_member["_id"])
        n_id = str(nitish_member["_id"])
        all_ids = [p_id, pa_id, s_id, n_id]

        # Expense 1: Prajwal pays ₹4,000 for dinner, split equally among all 4 (₹1,000 each)
        exp1 = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Dinner at Johnson's Cafe Manali",
                amount=4000,
                expense_date=date.today(),
                paid_by_user_id=p_id,
                category="Food & Dining",
                split_type="equal",
                participant_user_ids=all_ids,
                notes="Day 2 dinner with trout & cider",
            ),
            user=prajwal_admin,
        )
        runner.check(exp1["expense"]["amount"] == 4000, "Expense 1: ₹4,000 Dinner paid by Prajwal split 4 ways")

        # Expense 2: Parichay pays ₹1,200 for SUV fuel, split between Prajwal and Parichay (₹600 each)
        exp2 = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Diesel top-up at Kullu fuel station",
                amount=1200,
                expense_date=date.today(),
                paid_by_user_id=pa_id,
                category="Transportation",
                split_type="equal",
                participant_user_ids=[pa_id, p_id],
                notes="Full tank top up",
            ),
            user=parichay_member,
        )
        runner.check(exp2["expense"]["amount"] == 1200, "Expense 2: ₹1,200 Fuel paid by Parichay split 2 ways")

        # Expense 3: Srujan pays ₹800 for snacks, split between Srujan and Nitish (₹400 each)
        exp3 = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Camp Snacks, Dry Fruits & Water",
                amount=800,
                expense_date=date.today(),
                paid_by_user_id=s_id,
                category="Groceries",
                split_type="equal",
                participant_user_ids=[s_id, n_id],
                notes="Snacks for Spiti transit",
            ),
            user=srujan_member,
        )
        runner.check(exp3["expense"]["amount"] == 800, "Expense 3: ₹800 Snacks paid by Srujan split 2 ways")

        # Verify expense listing
        exp_data = await list_expenses("EDITH-TRIP-01", user=prajwal_admin)
        exp_list = exp_data["expenses"]
        runner.check(len(exp_list) == 3, "All 3 shared expenses listed chronologically", f"{len(exp_list)} expenses")

        # Verify net balances:
        # Prajwal: Paid 4000, Share = 1000 + 600 = 1600. Net = +2400
        # Parichay: Paid 1200, Share = 1000 + 600 = 1600. Net = -400
        # Srujan: Paid 800, Share = 1000 + 400 = 1400. Net = -600
        # Nitish: Paid 0, Share = 1000 + 400 = 1400. Net = -1400
        bal_data = await get_balances("EDITH-TRIP-01", user=prajwal_admin)
        user_balances = {b["user_id"]: b["net_balance"] for b in bal_data["member_balances"]}

        runner.check(user_balances[p_id] == 2400, "Prajwal net balance is +₹2,400 (owed back)", f"₹{user_balances[p_id]}")
        runner.check(user_balances[pa_id] == -400, "Parichay net balance is -₹400 (owes)", f"₹{user_balances[pa_id]}")
        runner.check(user_balances[s_id] == -600, "Srujan net balance is -₹600 (owes)", f"₹{user_balances[s_id]}")
        runner.check(user_balances[n_id] == -1400, "Nitish net balance is -₹1,400 (owes)", f"₹{user_balances[n_id]}")

        # Total sum of all net balances must be zero
        net_sum = sum(user_balances.values())
        runner.check(net_sum == 0, "Sum of all net balances across group is exactly ₹0.00", f"Sum = {net_sum}")

        # Test Debt Settlement: Parichay proposes settlement of ₹400 to Prajwal
        settle_res = await record_settlement(
            group_code="EDITH-TRIP-01",
            payload=SettlementCreate(
                from_user_id=pa_id,
                to_user_id=p_id,
                amount=400,
                settlement_date=date.today(),
                note="Settling Spiti fuel balance via UPI",
            ),
            user=parichay_member,
        )
        runner.check(settle_res["status"] == "proposed", "Settlement proposal of ₹400 from Parichay to Prajwal created")

        # Prajwal confirms receipt of the settlement payment
        confirm_res = await confirm_settlement(
            group_code="EDITH-TRIP-01",
            settlement_id=settle_res["id"],
            user=prajwal_admin,
        )
        runner.check("confirmed" in confirm_res["message"].lower(), "Prajwal confirms settlement receipt: status is 'confirmed'")

        # =====================================================================
        # FEATURE 5: ITINERARY PLANNING & DESTINATIONS
        # =====================================================================
        runner.section("5. Itinerary Planning & Route Stops")

        ov = await group_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check("EDITH Northern" in ov["group"]["trip_title"], "Itinerary title verified", ov["group"]["trip_title"])
        runner.check(len(ov["group"]["trip_stops"]) >= 4, "Initial route has 4 planned destination stops", f"{len(ov['group']['trip_stops'])} stops")

        # Admin updates itinerary: add stop 5 (Chandigarh stopover)
        updated_stops = [
            TripStop(destination="Delhi", arrival_date=date(2027, 4, 15), departure_date=date(2027, 4, 16), notes="Assemble & overnight", transport="Flight", accommodation="Aerocity"),
            TripStop(destination="Manali", arrival_date=date(2027, 4, 16), departure_date=date(2027, 4, 19), notes="Acclimatize & local trails", transport="Tempo Traveler", accommodation="Old Manali Cottage"),
            TripStop(destination="Kaza / Spiti", arrival_date=date(2027, 4, 19), departure_date=date(2027, 4, 23), notes="Key Monastery, Langza, Hikkim", transport="4x4 SUV", accommodation="Homestay"),
            TripStop(destination="Shimla", arrival_date=date(2027, 4, 23), departure_date=date(2027, 4, 25), notes="Colonial ridge walk", transport="SUV", accommodation="Heritage Hotel"),
            TripStop(destination="Chandigarh", arrival_date=date(2027, 4, 25), departure_date=date(2027, 4, 26), notes="Farewell dinner before departure", transport="SUV", accommodation="City Center Hotel"),
        ]

        upd_plan = await update_trip_plan(
            group_code="EDITH-TRIP-01",
            payload=TripPlanUpdate(
                trip_title="EDITH Northern Grand Expedition 2027",
                trip_start_date=date(2027, 4, 15),
                trip_end_date=date(2027, 4, 26),
                planned_trip_budget=96000,
                stops=updated_stops,
                notes="Complete 5-stage loop through Himachal, Spiti and Punjab.",
            ),
            admin=prajwal_admin,
        )
        runner.check(upd_plan["trip_title"] == "EDITH Northern Grand Expedition 2027", "Itinerary title updated successfully")
        runner.check(len(upd_plan["trip_stops"]) == 5, "Itinerary now contains 5 confirmed stops including Chandigarh")

        # =====================================================================
        # FEATURE 6: ROLE-BASED ACCESS CONTROL & SECURITY GUARD
        # =====================================================================
        runner.section("6. Role-Based Access Control & Security Enforcement")

        # Regular member (Parichay) tries to perform Admin Direct Collection -> must be 403
        try:
            await admin_record_collection(
                group_code="EDITH-TRIP-01",
                payload=AdminCollectPayment(user_id=pa_id, month_index=2, amount=2000, payment_mode="Cash"),
                admin=parichay_member, # Regular member passed!
            )
            runner.check(False, "Regular member must not be allowed to record admin collection")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Admin-only collection blocked for regular member (403 Forbidden)")

        # Regular member tries to create a disbursement -> must be 403
        try:
            await create_kitty_disbursement(
                group_code="EDITH-TRIP-01",
                payload=KittyDisbursementCreate(amount=500, category="Stay", description="test", recipient="test", disbursement_date=date.today()),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not disburse funds")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Disbursement blocked for regular member (403 Forbidden)")

        # Verify audit logs record all administrative actions
        audit_logs = await db.audit_logs.find({}).to_list()
        runner.check(len(audit_logs) >= 5, "Audit logs tracked all actions", f"{len(audit_logs)} log entries recorded")

    print(f"\n{'='*75}")
    print(f"🎉 FINAL TEST RESULTS: {runner.passed} PASSED | {runner.failed} FAILED")
    print(f"{'='*75}\n")

if __name__ == "__main__":
    asyncio.run(run_all_feature_tests())
