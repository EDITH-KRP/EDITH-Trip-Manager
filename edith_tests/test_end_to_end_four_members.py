import pytest
from datetime import datetime, timezone, date
from bson import ObjectId
from fastapi import HTTPException

from app.security import hash_password
from app.schemas import (
    MemberCreate,
    GroupCreate,
    ContributionSubmit,
    KittyDisbursementCreate,
    KittyReconcileRequest,
    ExpenseCreate,
    SettlementCreate,
    TripPlanUpdate,
    TripStop,
)
from app.routes.admin import create_member, admin_list_audit_logs
from app.routes.groups import create_group, join_group, group_summary, update_trip_plan
from app.routes.kitty import (
    get_kitty_summary,
    get_my_contributions,
    get_all_contributions,
    submit_contribution_payment,
    verify_contribution_payment,
    create_kitty_disbursement,
    reconcile_kitty_balance,
)
from app.routes.expenses import (
    add_expense,
    get_balances,
    record_settlement,
    confirm_settlement,
)


@pytest.mark.anyio
async def test_complete_four_member_lifecycle(setup_mock_db):
    db = setup_mock_db

    # ==========================================
    # 1. ONBOARD 1 ADMIN + 3 MEMBERS
    # ==========================================
    admin_id = ObjectId()
    admin_user = {
        "_id": admin_id,
        "name": "Prajwal (Admin)",
        "email": "prajwal@edith.org",
        "password_hash": hash_password("pass"),
        "role": "admin",
        "is_active": True,
        "phone": "+919876543210",
    }
    await db.users.insert_one(admin_user)

    # Admin creates 3 members
    members_data = [
        {"name": "Alice", "email": "alice@edith.org", "phone": "+919876543211"},
        {"name": "Bob", "email": "bob@edith.org", "phone": "+919876543212"},
        {"name": "Charlie", "email": "charlie@edith.org", "phone": "+919876543213"},
    ]
    created_members = []
    for m in members_data:
        res = await create_member(
            MemberCreate(name=m["name"], email=m["email"], phone=m["phone"], temporary_password="TempPass12345!"),
            admin=admin_user,
        )
        user_doc = await db.users.find_one({"_id": ObjectId(res["id"])})
        created_members.append(user_doc)

    alice, bob, charlie = created_members

    # ==========================================
    # 2. GROUP CREATION & MEMBERSHIP (MAX 4)
    # ==========================================
    group_res = await create_group(
        GroupCreate(
            name="Grand Ladakh Expedition 2027",
            group_code="LDKH27",
            monthly_contribution=2000,
            duration_months=12,
            start_date=date(2027, 1, 1),
            custody_holder_name="Prajwal HDFC UPI",
            trip_destination="Leh, Ladakh",
        ),
        admin=admin_user,
    )
    assert group_res["group_code"] == "LDKH27"

    # All 3 members join group
    await join_group("LDKH27", user=alice)
    await join_group("LDKH27", user=bob)
    await join_group("LDKH27", user=charlie)

    # Verify 4-member limit: 5th member attempt must raise 409 Conflict
    eve_user = {"_id": ObjectId(), "name": "Eve", "email": "eve@edith.org", "role": "member", "is_active": True}
    await db.users.insert_one(eve_user)
    with pytest.raises(HTTPException) as exc_info:
        await join_group("LDKH27", user=eve_user)
    assert exc_info.value.status_code == 409

    # Verify group summary target = 4 members * 12 months * 2000 = ₹96,000
    summary = await group_summary("LDKH27", user=alice)
    assert summary["member_count"] == 4
    assert summary["fund_target"] == 96000
    assert summary["fund_collected"] == 0

    # ==========================================
    # 3. PRIVACY ENFORCEMENT
    # ==========================================
    alice_contribs = await get_my_contributions("LDKH27", user=alice)
    assert alice_contribs["count"] == 12
    # Verify non-admin member cannot view all members' contribution records
    with pytest.raises(HTTPException) as exc_info:
        await get_all_contributions("LDKH27", admin=alice)
    assert exc_info.value.status_code == 403

    # ==========================================
    # 4. MONTH 1 SAVINGS: ALL 4 PAY ₹2,000
    # ==========================================
    all_four = [admin_user, alice, bob, charlie]
    for idx, user in enumerate(all_four):
        user_contribs = await get_my_contributions("LDKH27", user=user)
        m1_contrib = user_contribs["contributions"][0]
        utr_num = f"43210987654{idx}"
        await submit_contribution_payment(
            "LDKH27",
            m1_contrib["id"],
            ContributionSubmit(utr_reference=utr_num, payment_date=date(2027, 1, 5)),
            user=user,
        )
        # Admin approves
        await verify_contribution_payment("LDKH27", m1_contrib["id"], admin=admin_user)

    # Verified pool is now ₹8,000!
    kitty_summary = await get_kitty_summary("LDKH27", user=bob)
    assert kitty_summary["fund_collected"] == 8000
    assert kitty_summary["kitty_balance"] == 8000

    # ==========================================
    # 5. MULTI-DESTINATION TRIP ITINERARY
    # ==========================================
    stops_payload = [
        TripStop(destination="New Delhi", arrival_date=date(2027, 6, 1), departure_date=date(2027, 6, 2), transport="Flight"),
        TripStop(destination="Manali Old Town", arrival_date=date(2027, 6, 2), departure_date=date(2027, 6, 4), transport="Volvo Bus", accommodation="Cedar Cottage"),
        TripStop(destination="Jispa", arrival_date=date(2027, 6, 4), departure_date=date(2027, 6, 5), transport="4x4 Tempo", accommodation="Campsite"),
        TripStop(destination="Leh Ladakh", arrival_date=date(2027, 6, 5), departure_date=date(2027, 6, 10), transport="4x4 Tempo", accommodation="Grand Dragon"),
    ]
    await update_trip_plan(
        "LDKH27",
        TripPlanUpdate(
            trip_title="Himalayan Crossing 2027",
            trip_start_date=date(2027, 6, 1),
            trip_end_date=date(2027, 6, 10),
            planned_trip_budget=120000,
            stops=stops_payload,
        ),
        admin=admin_user,
    )
    grp_check = await group_summary("LDKH27", user=charlie)
    assert len(grp_check["group"]["trip_stops"]) == 4

    # ==========================================
    # 6. COMMON KITTY DISBURSEMENT (NO PEER DEBT)
    # ==========================================
    await create_kitty_disbursement(
        "LDKH27",
        KittyDisbursementCreate(amount=3000, category="stay", description="Manali Cedar Cottage 50% advance", recipient="Cedar Cottage"),
        admin=admin_user,
    )
    kitty_after_disb = await get_kitty_summary("LDKH27", user=admin_user)
    assert kitty_after_disb["fund_collected"] == 8000
    assert kitty_after_disb["fund_disbursed"] == 3000
    assert kitty_after_disb["kitty_balance"] == 5000

    # Crucial Rule Check: Kitty disbursement must NEVER create balances in Kitty Split
    bal_after_disb = await get_balances("LDKH27", user=admin_user)
    assert bal_after_disb["total_expenses"] == 0
    assert all(b["net_balance"] == 0 for b in bal_after_disb["member_balances"])

    # ==========================================
    # 7. PERSONAL SHARED EXPENSES (KITTY SPLIT)
    # ==========================================
    all_member_ids = [str(u["_id"]) for u in all_four]

    # Bob pays ₹4,000 for shared dinner equally across all 4 (₹1,000 each)
    await add_expense(
        "LDKH27",
        ExpenseCreate(
            title="Old Manali Cafe Dinner",
            category="Food",
            amount=4000,
            paid_by_user_id=str(bob["_id"]),
            split_type="equal",
            participant_user_ids=all_member_ids,
            expense_date=date(2027, 6, 3),
        ),
        user=bob,
    )

    # Charlie pays ₹2,000 for fuel shared equally across all 4 (₹500 each)
    await add_expense(
        "LDKH27",
        ExpenseCreate(
            title="Diesel Refuel at Tandi",
            category="Fuel",
            amount=2000,
            paid_by_user_id=str(charlie["_id"]),
            split_type="equal",
            participant_user_ids=all_member_ids,
            expense_date=date(2027, 6, 4),
        ),
        user=charlie,
    )

    # Net check:
    # Admin paid 0, owes 1000 + 500 = -1500
    # Alice paid 0, owes 1000 + 500 = -1500
    # Bob paid 4000, owes 1000 + 500 = +2500
    # Charlie paid 2000, owes 1000 + 500 = +500
    # Sum: -1500 + -1500 + 2500 + 500 = 0 (Zero-sum invariant preserved!)
    bal = await get_balances("LDKH27", user=admin_user)
    net_map = {b["user_id"]: b["net_balance"] for b in bal["member_balances"]}
    assert net_map[str(admin_user["_id"])] == -1500
    assert net_map[str(alice["_id"])] == -1500
    assert net_map[str(bob["_id"])] == 2500
    assert net_map[str(charlie["_id"])] == 500

    # Min Cash Flow transfers generated
    assert len(bal["suggested_settlements"]) <= 3

    # ==========================================
    # 8. TWO-PHASE SETTLEMENTS
    # ==========================================
    # Alice settles ₹1,500 to Bob
    s1 = await record_settlement(
        "LDKH27",
        SettlementCreate(from_user_id=str(alice["_id"]), to_user_id=str(bob["_id"]), amount=1500, settlement_date=date(2027, 6, 5)),
        user=alice,
    )
    # Bob confirms receipt
    await confirm_settlement("LDKH27", s1["id"], user=bob)

    # Admin settles ₹1,000 to Bob and ₹500 to Charlie
    s2 = await record_settlement(
        "LDKH27",
        SettlementCreate(from_user_id=str(admin_user["_id"]), to_user_id=str(bob["_id"]), amount=1000, settlement_date=date(2027, 6, 5)),
        user=admin_user,
    )
    await confirm_settlement("LDKH27", s2["id"], user=bob)

    s3 = await record_settlement(
        "LDKH27",
        SettlementCreate(from_user_id=str(admin_user["_id"]), to_user_id=str(charlie["_id"]), amount=500, settlement_date=date(2027, 6, 5)),
        user=admin_user,
    )
    await confirm_settlement("LDKH27", s3["id"], user=charlie)

    # After confirmed settlements: All balances must be exactly 0!
    final_bal = await get_balances("LDKH27", user=admin_user)
    assert all(b["net_balance"] == 0 for b in final_bal["member_balances"])
    assert len(final_bal["suggested_settlements"]) == 0

    # ==========================================
    # 9. RECONCILIATION & AUDIT INTEGRITY
    # ==========================================
    recon = await reconcile_kitty_balance(
        "LDKH27",
        KittyReconcileRequest(actual_bank_balance=5000, notes="Bank statement matched exactly"),
        admin=admin_user,
    )
    assert recon["status"] == "balanced"
    assert recon["variance"] == 0

    # Verify audit logs captured all events
    audit_resp = await admin_list_audit_logs(limit=100, admin=admin_user)
    actions = [log["action"] for log in audit_resp["audit_logs"]]
    assert "create_group" in actions
    assert "submit_contribution" in actions
    assert "verify_contribution" in actions
    assert "kitty_disbursement" in actions
    assert "create_expense" in actions
    assert "confirm_settlement" in actions
    assert "reconcile_kitty" in actions
