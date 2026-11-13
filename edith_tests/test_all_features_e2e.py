import os
import sys
from pathlib import Path

# Ensure app is importable
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# Prioritize local SQLite database initialization for testing
os.environ["SUPABASE_DB_URL"] = ""

import asyncio
from datetime import datetime, date, timezone
from app.main import app, lifespan
from app.database import get_database, ObjectId
from app.schemas import (
    LoginRequest,
    PasswordChange,
    AdminCollectPayment,
    ContributionSubmit,
    ContributionReject,
    KittyDisbursementCreate,
    KittyReconcileRequest,
    ExpenseCreate,
    ExpenseSplitInput,
    SettlementCreate,
    TripPlanUpdate,
    TripStop,
)
from app.routes.auth import login, change_password
from app.routes.groups import group_summary, update_trip_plan, list_group_members
from app.routes.kitty import (
    get_kitty_summary,
    get_all_contributions,
    get_my_contributions,
    admin_record_collection,
    submit_contribution_payment,
    verify_contribution_payment,
    reject_contribution_payment,
    create_kitty_disbursement,
    list_kitty_transactions,
    reconcile_kitty_balance,
)
from app.routes.expenses import (
    add_expense,
    reverse_expense,
    list_expenses,
    get_balances,
    record_settlement,
    confirm_settlement,
)
from app.routes.admin import admin_list_audit_logs
from fastapi import HTTPException

# Test reporter helper
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
        # FEATURE 2: AUTHENTICATION MATRIX, SECURITY & PASSWORD CHANGE
        # =====================================================================
        runner.section("2. Authentication Matrix, Security & Password Change Workflow")

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

        # Test Password Change Workflow
        prajwal_admin = user_map["Prajwal"]
        parichay_member = user_map["Parichay"]
        srujan_member = user_map["Srujan"]
        nitish_member = user_map["Nitish"]

        # 1. Change password to new password
        pwd_change_res = await change_password(
            PasswordChange(current_password="Prajwal784", new_password="PrajwalTemp456"),
            user=prajwal_admin,
        )
        runner.check("successfully" in pwd_change_res["message"].lower(), "Admin Prajwal changes password to 'PrajwalTemp456'")

        # 2. Login with old password fails
        try:
            await login(LoginRequest(email="Prajwal", password="Prajwal784"))
            runner.check(False, "Old password must be rejected after change")
        except HTTPException as e:
            runner.check(e.status_code == 401, "Old password rejected with 401 Unauthorized")

        # 3. Login with new password succeeds
        new_login = await login(LoginRequest(email="Prajwal", password="PrajwalTemp456"))
        runner.check(new_login["user"]["name"] == "Prajwal", "Login with new password 'PrajwalTemp456' succeeds")

        # 4. Change password back to Prajwal784
        # Refresh user dict with updated password_hash
        prajwal_admin = await db.users.find_one({"_id": prajwal_admin["_id"]})
        revert_pwd = await change_password(
            PasswordChange(current_password="PrajwalTemp456", new_password="Prajwal784"),
            user=prajwal_admin,
        )
        runner.check("successfully" in revert_pwd["message"].lower(), "Admin Prajwal reverts password back to 'Prajwal784'")
        prajwal_admin = await db.users.find_one({"_id": prajwal_admin["_id"]})

        # 5. Verify Prajwal784 works again
        revert_login = await login(LoginRequest(email="Prajwal", password="Prajwal784"))
        runner.check(revert_login["user"]["name"] == "Prajwal", "Reverted password 'Prajwal784' verified functional")

        # 6. Changing to same password rejected
        try:
            await change_password(
                PasswordChange(current_password="Prajwal784", new_password="Prajwal784"),
                user=prajwal_admin,
            )
            runner.check(False, "Changing to identical password must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 400, "Identical new password rejected with 400 Bad Request")

        # 7. Invalid current password rejected
        try:
            await change_password(
                PasswordChange(current_password="WrongCurrentPassword", new_password="NewOne999"),
                user=prajwal_admin,
            )
            runner.check(False, "Invalid current password must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 400, "Invalid current password rejected with 400 Bad Request")

        # =====================================================================
        # FEATURE 3: TRIP FUND (SAVINGS, ADMIN DIRECT COLLECTION & REJECTIONS)
        # =====================================================================
        runner.section("3. Trip Fund: Savings, Admin Direct Collection, Rejections & Disbursements")

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

        # Admin Direct Payment Recording (Prajwal collects directly via GPay / PhonePe / Bank)
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

        # Interim summary check: 3 paid = ₹6,000
        sum1 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum1["fund_collected"] == 6000, "Trip Fund collected is now ₹6,000", f"₹{sum1['fund_collected']:,}")
        runner.check(sum1["kitty_balance"] == 6000, "Trip Fund balance is now ₹6,000", f"₹{sum1['kitty_balance']:,}")

        # Member UTR submission workflow for Nitish Month 1
        nitish_contribs_data = await get_my_contributions("EDITH-TRIP-01", user=nitish_member)
        m1_nitish = next(c for c in nitish_contribs_data["contributions"] if c["month_index"] == 1)
        
        sub_res = await submit_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m1_nitish["id"],
            payload=ContributionSubmit(utr_reference="UPI987654321000", payment_date=date.today(), proof_url=None),
            user=nitish_member,
        )
        runner.check("submitted" in sub_res["message"].lower(), "Nitish submits UTR reference 'UPI987654321000'")

        # Duplicate UTR reference rejection
        m2_nitish = next(c for c in nitish_contribs_data["contributions"] if c["month_index"] == 2)
        try:
            await submit_contribution_payment(
                group_code="EDITH-TRIP-01",
                contribution_id=m2_nitish["id"],
                payload=ContributionSubmit(utr_reference="UPI987654321000", payment_date=date.today()), # duplicate UTR
                user=nitish_member,
            )
            runner.check(False, "Duplicate UTR reference must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 409, "Duplicate UTR reference rejected with 409 Conflict")

        # Admin Prajwal verifies Nitish's Month 1 contribution
        ver_res = await verify_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m1_nitish["id"],
            admin=prajwal_admin,
        )
        runner.check("verified" in ver_res["message"].lower(), "Admin Prajwal verifies Nitish's contribution")

        # Now all 4 members have completed Month 1 -> ₹8,000
        sum2 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum2["fund_collected"] == 8000, "All 4 members paid Month 1: Total collected is ₹8,000", f"₹{sum2['fund_collected']:,}")
        runner.check(sum2["kitty_balance"] == 8000, "Trip Fund balance is ₹8,000", f"₹{sum2['kitty_balance']:,}")

        # Contribution Rejection & Resubmission Workflow:
        # Nitish submits Month 2 with a faulty UTR
        sub_m2 = await submit_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m2_nitish["id"],
            payload=ContributionSubmit(utr_reference="FAULTY_REF_123", payment_date=date.today()),
            user=nitish_member,
        )
        runner.check(sub_m2["status"] == "submitted", "Nitish submits Month 2 with reference 'FAULTY_REF_123'")

        # Admin Prajwal rejects Nitish's Month 2 contribution with reason
        rej_res = await reject_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m2_nitish["id"],
            payload=ContributionReject(reason="Bank transfer reference not found in statement"),
            admin=prajwal_admin,
        )
        runner.check("rejected" in rej_res["message"].lower(), "Admin Prajwal rejects faulty contribution with reason", rej_res["reason"])

        # Check record status is rejected
        rejected_record = await db.contributions.find_one({"_id": ObjectId(m2_nitish["id"])})
        runner.check(rejected_record["status"] == "rejected", "Contribution status is now 'rejected'")
        runner.check(rejected_record["rejection_reason"] == "Bank transfer reference not found in statement", "Rejection reason recorded in DB")

        # Nitish corrects and resubmits Month 2
        resub_m2 = await submit_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m2_nitish["id"],
            payload=ContributionSubmit(utr_reference="CORRECTED_UPI_777", payment_date=date.today()),
            user=nitish_member,
        )
        runner.check(resub_m2["status"] == "submitted", "Nitish resubmits Month 2 with corrected UTR 'CORRECTED_UPI_777'")

        # Admin verifies corrected Month 2
        ver_m2 = await verify_contribution_payment(
            group_code="EDITH-TRIP-01",
            contribution_id=m2_nitish["id"],
            admin=prajwal_admin,
        )
        runner.check("verified" in ver_m2["message"].lower(), "Admin verifies corrected Month 2 payment")

        # Fund balance is now 8000 + 2000 = 10000
        sum2b = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum2b["kitty_balance"] == 10000, "Trip Fund balance is ₹10,000", f"₹{sum2b['kitty_balance']:,}")

        # Fund Spending Disbursement (Advance hotel booking: ₹2,500)
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
        runner.check(disb_res["new_balance"] == 7500, "Disbursement of ₹2,500 recorded from Trip Fund", disb_res["message"])

        # Verify fund balance after disbursement: 10000 - 2500 = 7500
        sum3 = await get_kitty_summary("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(sum3["fund_disbursed"] == 2500, "Total fund disbursed is ₹2,500", f"₹{sum3['fund_disbursed']:,}")
        runner.check(sum3["kitty_balance"] == 7500, "Trip Fund remaining balance is exactly ₹7,500", f"₹{sum3['kitty_balance']:,}")

        # Over-Disbursement Rejection (Attempting to disburse ₹50,000 when only ₹7,500 available)
        try:
            await create_kitty_disbursement(
                group_code="EDITH-TRIP-01",
                payload=KittyDisbursementCreate(
                    amount=50000,
                    category="Transport",
                    description="Private helicopter charter (over-budget)",
                    recipient="Heli Air Ltd",
                    disbursement_date=date.today(),
                ),
                admin=prajwal_admin,
            )
            runner.check(False, "Over-disbursement must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 400, "Over-disbursement rejected with 400 Bad Request (Insufficient funds)")

        # Physical Custodian Audit / Balance Reconciliation
        reconcile_res = await reconcile_kitty_balance(
            group_code="EDITH-TRIP-01",
            payload=KittyReconcileRequest(
                actual_bank_balance=7500,
                notes="Physical passbook audit matched exact system balance ₹7,500",
                apply_adjustment=False,
            ),
            admin=prajwal_admin,
        )
        runner.check(reconcile_res["status"] == "balanced", "Physical custodian audit successfully executed", f"System: ₹{reconcile_res['system_balance']:,}, Actual: ₹{reconcile_res['actual_balance']:,}")

        # =====================================================================
        # FEATURE 4: SPLIT EXPENSES (EQUAL, PERCENTAGE, CUSTOM & REVERSALS)
        # =====================================================================
        runner.section("4. Split Expenses: Equal, Percentage, Custom Splits, Edge Cases & Reversals")

        p_id = str(prajwal_admin["_id"])
        pa_id = str(parichay_member["_id"])
        s_id = str(srujan_member["_id"])
        n_id = str(nitish_member["_id"])
        all_ids = [p_id, pa_id, s_id, n_id]

        # Expense 1: Equal Split - Prajwal pays ₹4,000 for dinner split 4 ways (₹1,000 each)
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
        runner.check(exp1["expense"]["amount"] == 4000, "Equal Split: ₹4,000 Dinner paid by Prajwal split 4 ways")

        # Expense 2: Equal Split - Parichay pays ₹1,200 for SUV fuel split 2 ways (₹600 each: Prajwal & Parichay)
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
        runner.check(exp2["expense"]["amount"] == 1200, "Equal Split: ₹1,200 Fuel paid by Parichay split 2 ways")

        # Expense 3: Percentage Split - Srujan pays ₹2,000 for gear, 60% Srujan (₹1,200), 40% Nitish (₹800)
        # First test invalid percentage split (sum != 100)
        try:
            await add_expense(
                group_code="EDITH-TRIP-01",
                payload=ExpenseCreate(
                    title="Invalid Percentage Split",
                    amount=2000,
                    expense_date=date.today(),
                    paid_by_user_id=s_id,
                    category="Activities",
                    split_type="percentage",
                    participant_user_ids=[s_id, n_id],
                    splits=[
                        ExpenseSplitInput(user_id=s_id, share_percentage=40.0),
                        ExpenseSplitInput(user_id=n_id, share_percentage=40.0), # sum = 80% != 100%
                    ],
                ),
                user=srujan_member,
            )
            runner.check(False, "Invalid percentage split (sum != 100) must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 422, "Invalid percentage split rejected with 422 (must sum to 100)")

        # Valid Percentage Split
        exp3 = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Trekking gear rental at Solang",
                amount=2000,
                expense_date=date.today(),
                paid_by_user_id=s_id,
                category="Activities",
                split_type="percentage",
                participant_user_ids=[s_id, n_id],
                splits=[
                    ExpenseSplitInput(user_id=s_id, share_percentage=60.0),
                    ExpenseSplitInput(user_id=n_id, share_percentage=40.0),
                ],
                notes="Boots and crampons",
            ),
            user=srujan_member,
        )
        runner.check(exp3["expense"]["amount"] == 2000, "Percentage Split: ₹2,000 Gear rental (60% Srujan, 40% Nitish)")

        # Expense 4: Custom Split - Prajwal pays ₹3,000, Custom share: Prajwal ₹1,000, Parichay ₹2,000
        # First test invalid custom split (sum != amount)
        try:
            await add_expense(
                group_code="EDITH-TRIP-01",
                payload=ExpenseCreate(
                    title="Invalid Custom Split",
                    amount=3000,
                    expense_date=date.today(),
                    paid_by_user_id=p_id,
                    category="Activities",
                    split_type="custom",
                    participant_user_ids=[p_id, pa_id],
                    splits=[
                        ExpenseSplitInput(user_id=p_id, share_amount=1000),
                        ExpenseSplitInput(user_id=pa_id, share_amount=1500), # sum = 2500 != 3000
                    ],
                ),
                user=prajwal_admin,
            )
            runner.check(False, "Custom split not adding to full amount must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 422, "Invalid custom split rejected with 422 (must sum to amount)")

        # Valid Custom Split
        exp4 = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Special local guide and permits",
                amount=3000,
                expense_date=date.today(),
                paid_by_user_id=p_id,
                category="Activities",
                split_type="custom",
                participant_user_ids=[p_id, pa_id],
                splits=[
                    ExpenseSplitInput(user_id=p_id, share_amount=1000),
                    ExpenseSplitInput(user_id=pa_id, share_amount=2000),
                ],
                notes="Custom split: Prajwal 1000, Parichay 2000",
            ),
            user=prajwal_admin,
        )
        runner.check(exp4["expense"]["amount"] == 3000, "Custom Split: ₹3,000 Permits (Prajwal ₹1,000, Parichay ₹2,000)")

        # Expense Reversal Workflow:
        # Create a temporary mistake expense of ₹500
        temp_exp = await add_expense(
            group_code="EDITH-TRIP-01",
            payload=ExpenseCreate(
                title="Mistake Coffee entry to be reversed",
                amount=500,
                expense_date=date.today(),
                paid_by_user_id=p_id,
                category="Food & Dining",
                split_type="equal",
                participant_user_ids=[p_id, pa_id],
            ),
            user=prajwal_admin,
        )
        temp_id = temp_exp["id"]
        runner.check(temp_id is not None, "Temporary expense of ₹500 created for reversal test")

        # Reverse the mistake expense
        rev_res = await reverse_expense(
            group_code="EDITH-TRIP-01",
            expense_id=temp_id,
            reason="Accidental duplicate coffee invoice",
            user=prajwal_admin,
        )
        runner.check("successfully" in rev_res["message"].lower(), "Expense reversed successfully with reason")

        # Verify reversed status in DB
        rev_doc = await db.expenses.find_one({"_id": ObjectId(temp_id)})
        runner.check(rev_doc["status"] == "reversed", "Expense status in DB is 'reversed'")
        runner.check(rev_doc["reversal_reason"] == "Accidental duplicate coffee invoice", "Reversal reason stored in DB")

        # Verify listing
        all_exp_data = await list_expenses("EDITH-TRIP-01", user=prajwal_admin)
        runner.check(len(all_exp_data["expenses"]) == 5, "Expense list includes active and reversed entries (5 total)")

        # Verify Net Balances calculation:
        # Exp 1 (₹4000 paid by P, equal 4 ways): P +3000, Pa -1000, S -1000, N -1000
        # Exp 2 (₹1200 paid by Pa, equal 2 ways): P -600, Pa +600
        # Exp 3 (₹2000 paid by S, 60/40 S/N): S +800, N -800
        # Exp 4 (₹3000 paid by P, custom P:1000, Pa:2000): P +2000, Pa -2000
        # Reversal (₹500): excluded from balances!
        # Totals:
        # Prajwal: +3000 - 600 + 2000 = +4400
        # Parichay: -1000 + 600 - 2000 = -2400
        # Srujan: -1000 + 800 = -200
        # Nitish: -1000 - 800 = -1800
        # Net sum = +4400 - 2400 - 200 - 1800 = 0.00
        bal_data = await get_balances("EDITH-TRIP-01", user=prajwal_admin)
        user_balances = {b["user_id"]: b["net_balance"] for b in bal_data["member_balances"]}

        runner.check(user_balances[p_id] == 4400, "Prajwal net balance is +₹4,400 (owed back)", f"₹{user_balances[p_id]}")
        runner.check(user_balances[pa_id] == -2400, "Parichay net balance is -₹2,400 (owes)", f"₹{user_balances[pa_id]}")
        runner.check(user_balances[s_id] == -200, "Srujan net balance is -₹200 (owes)", f"₹{user_balances[s_id]}")
        runner.check(user_balances[n_id] == -1800, "Nitish net balance is -₹1,800 (owes)", f"₹{user_balances[n_id]}")

        # Total sum of all net balances must be zero
        net_sum = sum(user_balances.values())
        runner.check(net_sum == 0, "Sum of all net balances across group is exactly ₹0.00", f"Sum = {net_sum}")

        # =====================================================================
        # FEATURE 5: DEBT SETTLEMENT WORKFLOW & AUTHORIZATION
        # =====================================================================
        runner.section("5. Debt Settlement Workflow & Authorization Security")

        # Validation: Self-settlement rejection
        try:
            await record_settlement(
                group_code="EDITH-TRIP-01",
                payload=SettlementCreate(
                    from_user_id=pa_id,
                    to_user_id=pa_id, # Self settlement
                    amount=500,
                    settlement_date=date.today(),
                ),
                user=parichay_member,
            )
            runner.check(False, "Self-settlement must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 422, "Self-settlement rejected with 422 (cannot settle with oneself)")

        # Parichay proposes settlement of ₹2,400 to Prajwal
        settle_res = await record_settlement(
            group_code="EDITH-TRIP-01",
            payload=SettlementCreate(
                from_user_id=pa_id,
                to_user_id=p_id,
                amount=2400,
                settlement_date=date.today(),
                note="Settling full balance via GPay",
            ),
            user=parichay_member,
        )
        settle_id = settle_res["id"]
        runner.check(settle_res["status"] == "proposed", "Settlement proposal of ₹2,400 created (status: proposed)")

        # Security: Srujan (unrelated member) attempts to confirm Parichay's settlement to Prajwal
        try:
            await confirm_settlement(
                group_code="EDITH-TRIP-01",
                settlement_id=settle_id,
                user=srujan_member, # Unauthorized!
            )
            runner.check(False, "Unauthorized member must not confirm settlement")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Unauthorized settlement confirmation blocked with 403 Forbidden")

        # Prajwal (recipient) confirms settlement
        confirm_res = await confirm_settlement(
            group_code="EDITH-TRIP-01",
            settlement_id=settle_id,
            user=prajwal_admin,
        )
        runner.check("confirmed" in confirm_res["message"].lower(), "Prajwal confirms settlement receipt: status is 'confirmed'")

        # Verify DB status
        settle_doc = await db.settlements.find_one({"_id": ObjectId(settle_id)})
        runner.check(settle_doc["status"] == "confirmed", "Settlement record updated to confirmed in DB")
        runner.check(settle_doc["confirmed_by"] == p_id, "Confirmed by field tracks Prajwal's user ID")

        # =====================================================================
        # FEATURE 6: ITINERARY PLANNING & ROUTE STOPS VALIDATIONS
        # =====================================================================
        runner.section("6. Itinerary Planning & Route Stop Validations")

        # Validation: Trip end date before start date
        try:
            await update_trip_plan(
                group_code="EDITH-TRIP-01",
                payload=TripPlanUpdate(
                    trip_title="Invalid Dates Trip",
                    trip_start_date=date(2027, 5, 20),
                    trip_end_date=date(2027, 5, 10), # End before start!
                    planned_trip_budget=96000,
                    stops=[],
                ),
                admin=prajwal_admin,
            )
            runner.check(False, "Trip end date before start date must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 422, "Trip end date before start date rejected with 422")

        # Validation: Stop departure date before arrival date
        try:
            await update_trip_plan(
                group_code="EDITH-TRIP-01",
                payload=TripPlanUpdate(
                    trip_title="Invalid Stop Dates Trip",
                    trip_start_date=date(2027, 5, 1),
                    trip_end_date=date(2027, 5, 10),
                    planned_trip_budget=96000,
                    stops=[
                        TripStop(destination="Manali", arrival_date=date(2027, 5, 5), departure_date=date(2027, 5, 3)), # Dep before arr!
                    ],
                ),
                admin=prajwal_admin,
            )
            runner.check(False, "Stop departure before arrival must be rejected")
        except HTTPException as e:
            runner.check(e.status_code == 422, "Stop departure before arrival rejected with 422")

        # Valid 5-stop Itinerary Update
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
        runner.check(len(upd_plan["trip_stops"]) == 5, "Itinerary contains 5 confirmed stops including Chandigarh")

        # =====================================================================
        # FEATURE 7: ROLE-BASED ACCESS CONTROL (RBAC) SECURITY ENFORCEMENT
        # =====================================================================
        runner.section("7. Role-Based Access Control (RBAC) Security Enforcement")

        # Regular member blocked from Admin Direct Collection
        try:
            await admin_record_collection(
                group_code="EDITH-TRIP-01",
                payload=AdminCollectPayment(user_id=pa_id, month_index=2, amount=2000, payment_mode="Cash"),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not record admin collection")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Admin-only direct collection blocked for regular member (403 Forbidden)")

        # Regular member blocked from Trip Fund Disbursement
        try:
            await create_kitty_disbursement(
                group_code="EDITH-TRIP-01",
                payload=KittyDisbursementCreate(amount=500, category="Stay", description="test", recipient="test", disbursement_date=date.today()),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not disburse funds")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Trip fund disbursement blocked for regular member (403 Forbidden)")

        # Regular member blocked from Verifying Contribution
        try:
            await verify_contribution_payment(
                group_code="EDITH-TRIP-01",
                contribution_id=m1_nitish["id"],
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not verify contributions")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Contribution verification blocked for regular member (403 Forbidden)")

        # Regular member blocked from Rejecting Contribution
        try:
            await reject_contribution_payment(
                group_code="EDITH-TRIP-01",
                contribution_id=m1_nitish["id"],
                payload=ContributionReject(reason="Unauthorized rejection"),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not reject contributions")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Contribution rejection blocked for regular member (403 Forbidden)")

        # Regular member blocked from Updating Itinerary
        try:
            await update_trip_plan(
                group_code="EDITH-TRIP-01",
                payload=TripPlanUpdate(
                    trip_title="Hacked Title",
                    trip_start_date=date(2027, 4, 15),
                    trip_end_date=date(2027, 4, 26),
                    planned_trip_budget=96000,
                    stops=[],
                ),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not update trip plan")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Trip plan update blocked for regular member (403 Forbidden)")

        # Regular member blocked from Reconciling Fund
        try:
            await reconcile_kitty_balance(
                group_code="EDITH-TRIP-01",
                payload=KittyReconcileRequest(actual_bank_balance=1000),
                admin=parichay_member,
            )
            runner.check(False, "Regular member must not reconcile fund")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Fund reconciliation blocked for regular member (403 Forbidden)")

        # Regular member blocked from Viewing Audit Logs
        try:
            await admin_list_audit_logs(admin=parichay_member)
            runner.check(False, "Regular member must not access audit logs")
        except HTTPException as e:
            runner.check(e.status_code == 403, "Audit log viewing blocked for regular member (403 Forbidden)")

        # Admin accesses audit logs successfully
        admin_logs = await admin_list_audit_logs(limit=100, admin=prajwal_admin)
        runner.check(admin_logs["count"] >= 10, "Admin accesses full audit logs", f"{admin_logs['count']} entries tracked")

    print(f"\n{'='*75}")
    print(f"🎉 FINAL TEST RESULTS: {runner.passed} PASSED | {runner.failed} FAILED")
    print(f"{'='*75}\n")

if __name__ == "__main__":
    asyncio.run(run_all_feature_tests())
