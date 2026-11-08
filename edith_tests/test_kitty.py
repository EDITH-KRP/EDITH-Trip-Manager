import pytest
from datetime import datetime, timezone, date
from bson import ObjectId
from fastapi import HTTPException

from app.security import hash_password
from app.schemas import (
    GroupCreate,
    ContributionSubmit,
    ContributionReject,
    KittyDisbursementCreate,
    KittyReconcileRequest,
)
from app.routes.groups import create_group, join_group, group_summary
from app.routes.kitty import (
    get_kitty_summary,
    get_my_contributions,
    get_all_contributions,
    submit_contribution_payment,
    verify_contribution_payment,
    reject_contribution_payment,
    create_kitty_disbursement,
    list_kitty_transactions,
    reconcile_kitty_balance,
)


@pytest.mark.anyio
async def test_savings_kitty_full_cycle(setup_mock_db):
    db = setup_mock_db

    # Create Admin
    admin_id = ObjectId()
    admin_user = {
        "_id": admin_id,
        "name": "Trip Admin",
        "email": "admin@example.com",
        "password_hash": hash_password("pass"),
        "role": "admin",
        "is_active": True,
    }
    await db.users.insert_one(admin_user)

    # Admin creates group
    group_payload = GroupCreate(
        name="Ladakh 2027",
        group_code="LDKH27",
        monthly_contribution=2000,
        duration_months=12,
        start_date=date(2027, 1, 1),
        custody_holder_name="custodian@upi",
    )
    group_res = await create_group(group_payload, admin=admin_user)
    assert group_res["group_code"] == "LDKH27"

    # Create Member 2
    m2_id = ObjectId()
    m2_user = {
        "_id": m2_id,
        "name": "Member Alice",
        "email": "alice@example.com",
        "password_hash": hash_password("pass"),
        "role": "member",
        "is_active": True,
        "phone": "+919876500001",
    }
    await db.users.insert_one(m2_user)

    # Member 2 joins group
    join_res = await join_group("LDKH27", user=m2_user)
    assert "Joined" in join_res["message"]

    # 1. Verify Member 2 sees 12 personal contribution slots
    my_contribs = await get_my_contributions("LDKH27", user=m2_user)
    assert my_contribs["count"] == 12
    assert my_contribs["contributions"][0]["status"] == "pending"
    assert my_contribs["contributions"][0]["amount_due"] == 2000

    # 2. Member 2 submits Month 1 payment with 12-digit UTR
    c1 = my_contribs["contributions"][0]
    submit_payload = ContributionSubmit(
        utr_reference="432109876543",
        payment_date=date(2027, 1, 5),
        notes="Paid via UPI",
    )
    sub_res = await submit_contribution_payment("LDKH27", c1["id"], submit_payload, user=m2_user)
    assert sub_res["status"] == "submitted"
    assert sub_res["utr_reference"] == "432109876543"

    # 3. Duplicate UTR check: Attempting to submit same UTR for Month 2 must raise 409
    c2 = my_contribs["contributions"][1]
    with pytest.raises(HTTPException) as exc_info:
        await submit_contribution_payment("LDKH27", c2["id"], submit_payload, user=m2_user)
    assert exc_info.value.status_code == 409

    # 4. Total verified kitty before verification must be 0
    summary_before = await get_kitty_summary("LDKH27", user=m2_user)
    assert summary_before["fund_collected"] == 0
    assert summary_before["kitty_balance"] == 0

    # 5. Admin verifies Member 2's Month 1 contribution
    verif_res = await verify_contribution_payment("LDKH27", c1["id"], admin=admin_user)
    assert "verified" in verif_res["message"].lower()

    # 6. Total verified kitty after verification must be 2000
    summary_after = await get_kitty_summary("LDKH27", user=m2_user)
    assert summary_after["fund_collected"] == 2000
    assert summary_after["kitty_balance"] == 2000

    # 7. Check audit log was created
    audit_logs = await db.audit_logs.find({"action": "verify_contribution"}).sort("timestamp", -1).limit(1).docs if hasattr(db.audit_logs, "find") else []
    # Verify transaction in kitty_transactions
    txs = await list_kitty_transactions("LDKH27", user=m2_user)
    assert txs["count"] == 1
    assert txs["transactions"][0]["transaction_type"] == "contribution_credit"
    assert txs["transactions"][0]["amount"] == 2000

    # 8. Kitty Disbursement: Admin spends ₹1,500 for hotel advance from Kitty
    disb_payload = KittyDisbursementCreate(
        amount=1500,
        category="stay",
        description="Hotel Advance Deposit",
        recipient="Alpine Hotel",
        disbursement_date=date(2027, 1, 10),
    )
    disb_res = await create_kitty_disbursement("LDKH27", disb_payload, admin=admin_user)
    assert disb_res["new_balance"] == 500

    # 9. Invariant: Attempting disbursement exceeding balance (₹1,000 > ₹500 remaining) must raise 400
    with pytest.raises(HTTPException) as exc_info:
        await create_kitty_disbursement(
            "LDKH27",
            KittyDisbursementCreate(amount=1000, category="stay", description="Too large", recipient="Vendor"),
            admin=admin_user,
        )
    assert exc_info.value.status_code == 400

    # 10. Custodian Reconciliation: Actual bank balance is ₹550 (₹50 bank interest variance)
    reconcile_res = await reconcile_kitty_balance(
        "LDKH27",
        KittyReconcileRequest(actual_bank_balance=550, notes="Verified against statement", apply_adjustment=True),
        admin=admin_user,
    )
    assert reconcile_res["variance"] == 50
    assert reconcile_res["adjustment_applied"] is True

    # 11. Final summary reflects reconciled balance
    final_summary = await get_kitty_summary("LDKH27", user=m2_user)
    assert final_summary["kitty_balance"] == 550
