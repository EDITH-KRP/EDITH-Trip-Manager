from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_database, ObjectId
from app.dependencies import get_current_user, require_admin
from app.schemas import ExpenseCreate, SettlementCreate
from app.services.audit import record_audit_log
from app.services.notifications import send_notification

router = APIRouter(prefix="/groups/{group_code}", tags=["Trip expenses"])


async def _get_member_group(db, group_code, user):
    group = await db.groups.find_one({"group_code": group_code.upper(), "is_active": True})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    membership = await db.memberships.find_one({
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
    })
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    members_cursor = db.memberships.find({"group_id": str(group["_id"])})
    member_ids = []
    async for m in members_cursor:
        member_ids.append(m["user_id"])
    return group, member_ids


@router.post("/expenses", status_code=201)
async def add_expense(group_code: str, payload: ExpenseCreate, user=Depends(get_current_user)):
    db = get_database()
    group, member_ids = await _get_member_group(db, group_code, user)

    if len(member_ids) > 4:
        raise HTTPException(status_code=409, detail="Group exceeds the four-member limit")
    if payload.paid_by_user_id not in member_ids:
        raise HTTPException(status_code=422, detail="Payer must belong to this group")
    if len(set(payload.participant_user_ids)) != len(payload.participant_user_ids):
        raise HTTPException(status_code=422, detail="Duplicate participants are not allowed")
    if any(uid not in member_ids for uid in payload.participant_user_ids):
        raise HTTPException(status_code=422, detail="Every participant must belong to this group")
    if payload.paid_by_user_id not in payload.participant_user_ids:
        raise HTTPException(status_code=422, detail="Payer must be included among expense participants")

    participants = payload.participant_user_ids
    if payload.split_type == "equal":
        base, remainder = divmod(payload.amount, len(participants))
        splits = [
            {"user_id": uid, "share_amount": base + (1 if i < remainder else 0)}
            for i, uid in enumerate(participants)
        ]
    else:
        if not payload.splits:
            raise HTTPException(status_code=422, detail="Custom and percentage splits require split entries")
        if {x.user_id for x in payload.splits} != set(participants):
            raise HTTPException(status_code=422, detail="Splits must match the selected participants exactly")

        if payload.split_type == "custom":
            if any(x.share_amount is None for x in payload.splits):
                raise HTTPException(status_code=422, detail="Every custom split needs a share_amount")
            if sum(x.share_amount for x in payload.splits) != payload.amount:
                raise HTTPException(status_code=422, detail="Split shares must add up to the full expense amount")
            splits = [
                {"user_id": x.user_id, "share_amount": x.share_amount}
                for x in payload.splits
            ]
        else:
            if any(x.share_percentage is None for x in payload.splits):
                raise HTTPException(status_code=422, detail="Every percentage split needs a share_percentage")
            total_percent = sum(x.share_percentage for x in payload.splits)
            if abs(total_percent - 100.0) > 0.0001:
                raise HTTPException(status_code=422, detail="Percentage shares must add up to 100")
            raw = [
                (x.user_id, payload.amount * x.share_percentage / 100.0)
                for x in payload.splits
            ]
            rounded = [
                {"user_id": uid, "share_amount": int(value // 1), "fraction": value - int(value // 1)}
                for uid, value in raw
            ]
            remainder = payload.amount - sum(x["share_amount"] for x in rounded)
            for item in sorted(rounded, key=lambda x: x["fraction"], reverse=True)[:remainder]:
                item["share_amount"] += 1
            splits = [
                {"user_id": x["user_id"], "share_amount": x["share_amount"]}
                for x in rounded
            ]

    now = datetime.now(timezone.utc)
    doc = {
        "group_id": str(group["_id"]),
        "title": payload.title,
        "category": payload.category,
        "amount": payload.amount,
        "paid_by_user_id": payload.paid_by_user_id,
        "split_type": payload.split_type,
        "participant_user_ids": participants,
        "splits": splits,
        "expense_date": datetime.combine(payload.expense_date, datetime.min.time(), tzinfo=timezone.utc),
        "notes": payload.notes,
        "status": "active",
        "created_by": str(user["_id"]),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.expenses.insert_one(doc)
    expense_id_str = str(result.inserted_id)

    await record_audit_log(
        db=db,
        actor=user,
        action="create_expense",
        resource_type="expenses",
        resource_id=expense_id_str,
        after_state={"title": payload.title, "amount": payload.amount, "payer": payload.paid_by_user_id},
        notes=f"Recorded expense {payload.title} of Rs {payload.amount} ({payload.split_type} split)",
    )

    # Notify participants
    payer_user = await db.users.find_one({"_id": ObjectId(payload.paid_by_user_id)})
    payer_name = payer_user.get("name", "Member") if payer_user else "Member"

    for split in splits:
        if split["user_id"] != payload.paid_by_user_id:
            part_user = await db.users.find_one({"_id": ObjectId(split["user_id"])})
            if part_user and part_user.get("phone"):
                await send_notification(
                    db=db,
                    recipient_user_id=split["user_id"],
                    phone_number=part_user.get("phone"),
                    template_name="EDT_EXPENSE_04",
                    variables={
                        "payer_name": payer_name,
                        "amount": payload.amount,
                        "title": payload.title,
                        "share": split["share_amount"],
                    },
                )

    return {"id": expense_id_str, "message": "Expense recorded", "expense": doc | {"id": expense_id_str}}


@router.post("/expenses/{expense_id}/reverse")
async def reverse_expense(
    group_code: str,
    expense_id: str,
    reason: str = "Corrected duplicate or inaccurate entry",
    user=Depends(get_current_user),
):
    db = get_database()
    group, _ = await _get_member_group(db, group_code, user)
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=400, detail="Invalid expense ID")

    expense = await db.expenses.find_one({
        "_id": ObjectId(expense_id),
        "group_id": str(group["_id"]),
        "status": {"$ne": "reversed"},
    })
    if not expense:
        raise HTTPException(status_code=404, detail="Active expense not found")

    if expense["created_by"] != str(user["_id"]) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only creator or administrator can reverse this expense")

    now = datetime.now(timezone.utc)
    await db.expenses.update_one(
        {"_id": expense["_id"]},
        {"$set": {
            "status": "reversed",
            "reversed_by": str(user["_id"]),
            "reversed_at": now,
            "reversal_reason": reason,
        }},
    )

    await record_audit_log(
        db=db,
        actor=user,
        action="reverse_expense",
        resource_type="expenses",
        resource_id=str(expense["_id"]),
        before_state={"status": "active", "amount": expense["amount"]},
        after_state={"status": "reversed", "reversal_reason": reason},
        notes=f"Reversed expense {expense['title']} of Rs {expense['amount']}: {reason}",
    )

    return {"message": "Expense reversed successfully"}


@router.get("/expenses")
async def list_expenses(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group, _ = await _get_member_group(db, group_code, user)
    cursor = db.expenses.find({"group_id": str(group["_id"])}).sort("expense_date", -1)
    expenses = []
    async for item in cursor:
        item["id"] = str(item.pop("_id"))
        expenses.append(item)
    return {"expenses": expenses, "count": len(expenses)}


@router.get("/balances")
async def get_balances(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group, member_ids = await _get_member_group(db, group_code, user)
    net = defaultdict(int)
    names = {}
    for uid in member_ids:
        try:
            person = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
            names[uid] = person.get("name", "Member") if person else "Member"
        except Exception:
            names[uid] = "Member"

    cursor = db.expenses.find({"group_id": str(group["_id"]), "status": {"$ne": "reversed"}})
    total_expenses = 0
    async for expense in cursor:
        amount = int(expense["amount"])
        total_expenses += amount
        net[expense["paid_by_user_id"]] += amount
        for split in expense["splits"]:
            net[split["user_id"]] -= int(split["share_amount"])

    settlements = db.settlements.find({"group_id": str(group["_id"]), "status": "confirmed"})
    async for settlement in settlements:
        net[settlement["from_user_id"]] += int(settlement["amount"])
        net[settlement["to_user_id"]] -= int(settlement["amount"])

    creditors = [[uid, bal] for uid, bal in net.items() if bal > 0]
    debtors = [[uid, -bal] for uid, bal in net.items() if bal < 0]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        if amount:
            transfers.append({
                "from_user_id": debtors[i][0],
                "from_name": names.get(debtors[i][0], "Member"),
                "to_user_id": creditors[j][0],
                "to_name": names.get(creditors[j][0], "Member"),
                "amount": amount,
            })
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] == 0: i += 1
        if creditors[j][1] == 0: j += 1

    return {
        "group_code": group_code.upper(),
        "total_expenses": total_expenses,
        "member_balances": [
            {"user_id": uid, "name": names.get(uid, "Member"), "net_balance": net.get(uid, 0)}
            for uid in member_ids
        ],
        "suggested_settlements": transfers,
        "explanation": "Positive balance means the member should receive money; negative means they owe money.",
    }


@router.post("/settlements", status_code=201)
async def record_settlement(group_code: str, payload: SettlementCreate, user=Depends(get_current_user)):
    db = get_database()
    group, member_ids = await _get_member_group(db, group_code, user)
    if payload.from_user_id not in member_ids or payload.to_user_id not in member_ids:
        raise HTTPException(status_code=422, detail="Both people must belong to this group")
    if payload.from_user_id == payload.to_user_id:
        raise HTTPException(status_code=422, detail="A member cannot settle with themselves")
    # A settlement is recorded as proposed and must be confirmed by the receiver/admin.
    doc = {
        "group_id": str(group["_id"]),
        "from_user_id": payload.from_user_id,
        "to_user_id": payload.to_user_id,
        "amount": payload.amount,
        "settlement_date": datetime.combine(payload.settlement_date, datetime.min.time(), tzinfo=timezone.utc),
        "note": payload.note,
        "status": "proposed",
        "recorded_by": str(user["_id"]),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.settlements.insert_one(doc)
    settle_id_str = str(result.inserted_id)

    await record_audit_log(
        db=db,
        actor=user,
        action="propose_settlement",
        resource_type="settlements",
        resource_id=settle_id_str,
        after_state={"from": payload.from_user_id, "to": payload.to_user_id, "amount": payload.amount},
        notes=f"Proposed settlement payment of Rs {payload.amount}",
    )

    return {"id": settle_id_str, "status": "proposed", "message": "Settlement submitted for confirmation"}


@router.patch("/settlements/{settlement_id}/confirm")
async def confirm_settlement(group_code: str, settlement_id: str, user=Depends(get_current_user)):
    db = get_database()
    group, member_ids = await _get_member_group(db, group_code, user)
    if not ObjectId.is_valid(settlement_id):
        raise HTTPException(status_code=400, detail="Invalid settlement ID")
    item = await db.settlements.find_one({
        "_id": ObjectId(settlement_id),
        "group_id": str(group["_id"]),
        "status": "proposed",
    })
    if not item:
        raise HTTPException(status_code=404, detail="Pending settlement not found")
    if str(user["_id"]) not in (item["to_user_id"],) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only the recipient or admin can confirm this settlement")
    now = datetime.now(timezone.utc)
    await db.settlements.update_one(
        {"_id": item["_id"]},
        {"$set": {"status": "confirmed", "confirmed_by": str(user["_id"]), "confirmed_at": now}},
    )

    await record_audit_log(
        db=db,
        actor=user,
        action="confirm_settlement",
        resource_type="settlements",
        resource_id=str(item["_id"]),
        before_state={"status": "proposed"},
        after_state={"status": "confirmed", "confirmed_by": str(user["_id"])},
        notes=f"Confirmed settlement of Rs {item['amount']}",
    )

    # Notify debtor that settlement was confirmed
    debtor = await db.users.find_one({"_id": ObjectId(item["from_user_id"])})
    creditor = await db.users.find_one({"_id": ObjectId(item["to_user_id"])})
    if debtor and debtor.get("phone"):
        await send_notification(
            db=db,
            recipient_user_id=item["from_user_id"],
            phone_number=debtor.get("phone"),
            template_name="EDT_SETTLE_05",
            variables={
                "amount": item["amount"],
                "debtor_name": debtor.get("name", "Member"),
                "creditor_name": creditor.get("name", "Member") if creditor else "Member",
            },
        )

    return {"message": "Settlement confirmed"}
