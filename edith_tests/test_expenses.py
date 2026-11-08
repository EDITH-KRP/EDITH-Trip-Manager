import pytest
from datetime import datetime, timezone, date
from bson import ObjectId
from fastapi import HTTPException

from app.security import hash_password
from app.schemas import (
    GroupCreate,
    ExpenseCreate,
    ExpenseSplitInput,
    SettlementCreate,
)
from app.routes.groups import create_group, join_group
from app.routes.expenses import (
    add_expense,
    list_expenses,
    get_balances,
    record_settlement,
    confirm_settlement,
    reverse_expense,
)


@pytest.mark.anyio
async def test_shared_expenses_and_settlements(setup_mock_db):
    db = setup_mock_db

    # Create 3 users (Admin, Alice, Bob)
    admin_id = ObjectId()
    admin_user = {"_id": admin_id, "name": "Admin", "email": "admin@exp.com", "role": "admin", "is_active": True}
    alice_id = ObjectId()
    alice_user = {"_id": alice_id, "name": "Alice", "email": "alice@exp.com", "role": "member", "is_active": True}
    bob_id = ObjectId()
    bob_user = {"_id": bob_id, "name": "Bob", "email": "bob@exp.com", "role": "member", "is_active": True}

    await db.users.insert_one(admin_user)
    await db.users.insert_one(alice_user)
    await db.users.insert_one(bob_user)

    # Admin creates group
    await create_group(
        GroupCreate(name="Goa Trip", group_code="GOA27", monthly_contribution=2000, duration_months=12, start_date=date(2027, 1, 1), custody_holder_name="admin@upi"),
        admin=admin_user,
    )
    await join_group("GOA27", user=alice_user)
    await join_group("GOA27", user=bob_user)

    all_ids = [str(admin_id), str(alice_id), str(bob_id)]

    # 1. Admin pays ₹3,000 for dinner shared equally by all 3 (₹1,000 each)
    exp1 = await add_expense(
        "GOA27",
        ExpenseCreate(
            title="Seafood Dinner",
            category="Food",
            amount=3000,
            paid_by_user_id=str(admin_id),
            split_type="equal",
            participant_user_ids=all_ids,
            expense_date=date(2027, 1, 5),
        ),
        user=admin_user,
    )
    assert exp1["message"] == "Expense recorded"

    # Verify balances:
    # Admin paid 3000, owes 1000 -> net +2000
    # Alice paid 0, owes 1000 -> net -1000
    # Bob paid 0, owes 1000 -> net -1000
    bal1 = await get_balances("GOA27", user=alice_user)
    admin_bal = next(b for b in bal1["member_balances"] if b["user_id"] == str(admin_id))
    alice_bal = next(b for b in bal1["member_balances"] if b["user_id"] == str(alice_id))
    bob_bal = next(b for b in bal1["member_balances"] if b["user_id"] == str(bob_id))

    assert admin_bal["net_balance"] == 2000
    assert alice_bal["net_balance"] == -1000
    assert bob_bal["net_balance"] == -1000

    # 2. Suggested settlements should show Alice -> Admin ₹1000 and Bob -> Admin ₹1000
    assert len(bal1["suggested_settlements"]) == 2

    # 3. Alice proposes settlement of ₹1,000 to Admin
    settle_resp = await record_settlement(
        "GOA27",
        SettlementCreate(
            from_user_id=str(alice_id),
            to_user_id=str(admin_id),
            amount=1000,
            settlement_date=date(2027, 1, 6),
            note="Paid via GPay",
        ),
        user=alice_user,
    )
    settle_id = settle_resp["id"]
    assert settle_resp["status"] == "proposed"

    # Prior to confirmation, balances must remain unadjusted (two-phase commit rule)
    bal_pre_confirm = await get_balances("GOA27", user=alice_user)
    alice_pre = next(b for b in bal_pre_confirm["member_balances"] if b["user_id"] == str(alice_id))
    assert alice_pre["net_balance"] == -1000

    # 4. Admin confirms settlement
    conf_resp = await confirm_settlement("GOA27", settle_id, user=admin_user)
    assert conf_resp["message"] == "Settlement confirmed"

    # After confirmation, Alice's balance must be cleared to 0
    bal_post_confirm = await get_balances("GOA27", user=alice_user)
    alice_post = next(b for b in bal_post_confirm["member_balances"] if b["user_id"] == str(alice_id))
    assert alice_post["net_balance"] == 0

    # 5. Reverse an expense
    await reverse_expense("GOA27", exp1["id"], reason="Test reversal", user=admin_user)
    bal_post_reverse = await get_balances("GOA27", user=admin_user)
    # With dinner reversed, only the confirmed settlement of ₹1000 from Alice to Admin remains
    alice_rev = next(b for b in bal_post_reverse["member_balances"] if b["user_id"] == str(alice_id))
    assert alice_rev["net_balance"] == 1000
