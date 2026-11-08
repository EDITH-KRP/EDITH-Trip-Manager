from datetime import datetime, timezone, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, ObjectId
from app.dependencies import get_current_user, require_admin
from app.schemas import (
    ContributionSubmit,
    ContributionReject,
    KittyDisbursementCreate,
    KittyReconcileRequest,
)
from app.services.audit import record_audit_log
from app.services.notifications import send_notification

router = APIRouter(prefix="/groups/{group_code}/kitty", tags=["Savings Kitty"])


async def _get_member_group(db, group_code: str, user: dict):
    group = await db.groups.find_one({"group_code": group_code.upper(), "is_active": True})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    membership = await db.memberships.find_one({
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
    })
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    return group


def calculate_due_date(start_date: datetime, month_index: int) -> datetime:
    """Calculate the 10th of each respective month in the savings timeline."""
    year = start_date.year + (start_date.month - 1 + (month_index - 1)) // 12
    month = ((start_date.month - 1 + (month_index - 1)) % 12) + 1
    day = 10
    return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)


async def ensure_group_contributions(db, group: dict, specific_user_id: Optional[str] = None):
    """
    Ensures that 12-month contribution obligation records exist for all group members.
    """
    group_id_str = str(group["_id"])
    duration = group.get("duration_months", 12)
    monthly_amt = group.get("monthly_contribution", 2000)
    start_dt = group.get("start_date") or datetime.now(timezone.utc)

    if specific_user_id:
        user_ids = [specific_user_id]
    else:
        cursor = db.memberships.find({"group_id": group_id_str})
        user_ids = [m["user_id"] async for m in cursor]

    for uid in user_ids:
        for m_idx in range(1, duration + 1):
            due_dt = calculate_due_date(start_dt, m_idx)
            cycle_str = due_dt.strftime("%b-%Y")
            existing = await db.contributions.find_one({
                "group_id": group_id_str,
                "user_id": uid,
                "month_index": m_idx,
            })
            if not existing:
                await db.contributions.insert_one({
                    "group_id": group_id_str,
                    "user_id": uid,
                    "month_index": m_idx,
                    "cycle_month": cycle_str,
                    "due_date": due_dt,
                    "amount_due": monthly_amt,
                    "amount_paid": 0,
                    "utr_reference": None,
                    "proof_url": None,
                    "status": "pending",  # pending | submitted | verified | rejected
                    "submitted_at": None,
                    "verified_at": None,
                    "verified_by": None,
                    "rejection_reason": None,
                    "notes": "",
                    "created_at": datetime.now(timezone.utc),
                })


async def get_kitty_balance_data(db, group_id_str: str) -> dict:
    """Calculates live verified kitty total, disbursements, adjustments, and balance."""
    verified_cursor = db.contributions.find({"group_id": group_id_str, "status": "verified"})
    total_verified_contributions = 0
    async for c in verified_cursor:
        total_verified_contributions += c.get("amount_due", 0)

    tx_cursor = db.kitty_transactions.find({"group_id": group_id_str})
    total_disbursements = 0
    total_adjustments = 0
    async for tx in tx_cursor:
        if tx.get("transaction_type") == "disbursement":
            total_disbursements += tx.get("amount", 0)
        elif tx.get("transaction_type") == "adjustment":
            adj_type = tx.get("adjustment_type", "credit")
            amt = tx.get("amount", 0)
            if adj_type == "credit":
                total_adjustments += amt
            else:
                total_adjustments -= amt

    current_balance = total_verified_contributions - total_disbursements + total_adjustments
    return {
        "total_verified": total_verified_contributions,
        "total_disbursed": total_disbursements,
        "total_adjustments": total_adjustments,
        "current_balance": current_balance,
    }


@router.post("/initialize", status_code=200)
async def initialize_kitty_schedule(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await _get_member_group(db, group_code, user)
    await ensure_group_contributions(db, group)
    return {"message": "Savings schedule initialized successfully for all members"}


@router.get("/summary")
async def get_kitty_summary(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await _get_member_group(db, group_code, user)
    group_id_str = str(group["_id"])

    await ensure_group_contributions(db, group)

    bal_data = await get_kitty_balance_data(db, group_id_str)
    member_count = await db.memberships.count_documents({"group_id": group_id_str})
    target = group.get("monthly_contribution", 2000) * group.get("duration_months", 12) * member_count
    remaining = max(0, target - bal_data["total_verified"])
    pct = (bal_data["total_verified"] / target * 100.0) if target > 0 else 0.0

    # User personal progress
    my_verified = await db.contributions.count_documents({
        "group_id": group_id_str,
        "user_id": str(user["_id"]),
        "status": "verified",
    })
    my_pending = await db.contributions.count_documents({
        "group_id": group_id_str,
        "user_id": str(user["_id"]),
        "status": {"$in": ["pending", "rejected"]},
    })

    return {
        "group_name": group["name"],
        "group_code": group["group_code"],
        "monthly_contribution": group["monthly_contribution"],
        "duration_months": group["duration_months"],
        "member_count": member_count,
        "fund_target": target,
        "fund_collected": bal_data["total_verified"],
        "fund_remaining": remaining,
        "fund_disbursed": bal_data["total_disbursed"],
        "fund_adjustments": bal_data["total_adjustments"],
        "kitty_balance": bal_data["current_balance"],
        "progress_percentage": round(pct, 1),
        "my_stats": {
            "verified_months": my_verified,
            "pending_months": my_pending,
            "total_months": group["duration_months"],
        },
    }


@router.get("/contributions/my")
async def get_my_contributions(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await _get_member_group(db, group_code, user)
    group_id_str = str(group["_id"])
    user_id_str = str(user["_id"])

    await ensure_group_contributions(db, group, specific_user_id=user_id_str)

    cursor = db.contributions.find({
        "group_id": group_id_str,
        "user_id": user_id_str,
    }).sort("month_index", 1)

    items = []
    async for c in cursor:
        items.append({
            "id": str(c["_id"]),
            "month_index": c["month_index"],
            "cycle_month": c.get("cycle_month"),
            "due_date": c["due_date"].date().isoformat() if c.get("due_date") else None,
            "amount_due": c["amount_due"],
            "amount_paid": c.get("amount_paid", 0),
            "utr_reference": c.get("utr_reference"),
            "proof_url": c.get("proof_url"),
            "status": c["status"],
            "submitted_at": c["submitted_at"].isoformat() if c.get("submitted_at") else None,
            "verified_at": c["verified_at"].isoformat() if c.get("verified_at") else None,
            "rejection_reason": c.get("rejection_reason"),
            "notes": c.get("notes", ""),
        })

    return {"contributions": items, "count": len(items)}


@router.get("/contributions/all")
async def get_all_contributions(group_code: str, admin=Depends(require_admin)):
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    group_id_str = str(group["_id"])

    await ensure_group_contributions(db, group)

    cursor = db.contributions.find({"group_id": group_id_str}).sort([("month_index", 1), ("user_id", 1)])
    
    # Pre-fetch user names
    users_cursor = db.users.find({}, {"name": 1, "email": 1, "_id": 1})
    name_map = {str(u["_id"]): u.get("name", "Member") async for u in users_cursor}

    items = []
    async for c in cursor:
        items.append({
            "id": str(c["_id"]),
            "user_id": c["user_id"],
            "user_name": name_map.get(c["user_id"], "Member"),
            "month_index": c["month_index"],
            "cycle_month": c.get("cycle_month"),
            "due_date": c["due_date"].date().isoformat() if c.get("due_date") else None,
            "amount_due": c["amount_due"],
            "amount_paid": c.get("amount_paid", 0),
            "utr_reference": c.get("utr_reference"),
            "proof_url": c.get("proof_url"),
            "status": c["status"],
            "submitted_at": c["submitted_at"].isoformat() if c.get("submitted_at") else None,
            "verified_at": c["verified_at"].isoformat() if c.get("verified_at") else None,
            "rejection_reason": c.get("rejection_reason"),
        })

    return {"contributions": items, "count": len(items)}


@router.post("/contributions/{contribution_id}/submit")
async def submit_contribution_payment(
    group_code: str,
    contribution_id: str,
    payload: ContributionSubmit,
    user=Depends(get_current_user),
):
    db = get_database()
    group = await _get_member_group(db, group_code, user)
    if not ObjectId.is_valid(contribution_id):
        raise HTTPException(status_code=400, detail="Invalid contribution ID")

    c = await db.contributions.find_one({
        "_id": ObjectId(contribution_id),
        "group_id": str(group["_id"]),
    })
    if not c:
        raise HTTPException(status_code=404, detail="Contribution record not found")

    # Only owner or admin can submit
    if c["user_id"] != str(user["_id"]) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Cannot submit payment for another member")

    if c["status"] == "verified":
        raise HTTPException(status_code=400, detail="This contribution has already been verified")

    utr_clean = payload.utr_reference.strip().upper()
    # Check for duplicate UTR within group
    duplicate = await db.contributions.find_one({
        "group_id": str(group["_id"]),
        "utr_reference": utr_clean,
        "_id": {"$ne": c["_id"]},
    })
    if duplicate:
        raise HTTPException(status_code=409, detail=f"UTR Reference {utr_clean} has already been registered")

    now = datetime.now(timezone.utc)
    payment_dt = datetime.combine(payload.payment_date, datetime.min.time(), tzinfo=timezone.utc)

    update = {
        "status": "submitted",
        "utr_reference": utr_clean,
        "amount_paid": c["amount_due"],
        "payment_date": payment_dt,
        "proof_url": payload.proof_url,
        "notes": payload.notes,
        "submitted_at": now,
        "rejection_reason": None,
    }

    before_state = {"status": c["status"], "utr_reference": c.get("utr_reference")}
    await db.contributions.update_one({"_id": c["_id"]}, {"$set": update})

    await record_audit_log(
        db=db,
        actor=user,
        action="submit_contribution",
        resource_type="contributions",
        resource_id=str(c["_id"]),
        before_state=before_state,
        after_state=update,
        notes=f"Submitted Month {c['month_index']} contribution with UTR {utr_clean}",
    )

    return {
        "message": "Payment details submitted for verification",
        "contribution_id": str(c["_id"]),
        "status": "submitted",
        "utr_reference": utr_clean,
    }


@router.put("/contributions/{contribution_id}/verify")
async def verify_contribution_payment(
    group_code: str,
    contribution_id: str,
    admin=Depends(require_admin),
):
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    if not ObjectId.is_valid(contribution_id):
        raise HTTPException(status_code=400, detail="Invalid contribution ID")

    c = await db.contributions.find_one({
        "_id": ObjectId(contribution_id),
        "group_id": str(group["_id"]),
    })
    if not c:
        raise HTTPException(status_code=404, detail="Contribution record not found")

    if c["status"] == "verified":
        return {"message": "Contribution is already verified"}

    now = datetime.now(timezone.utc)
    before_state = {"status": c["status"]}

    await db.contributions.update_one(
        {"_id": c["_id"]},
        {"$set": {
            "status": "verified",
            "verified_at": now,
            "verified_by": str(admin["_id"]),
        }},
    )

    # Credit to kitty transaction ledger
    member = await db.users.find_one({"_id": ObjectId(c["user_id"])})
    member_name = member.get("name", "Member") if member else "Member"

    tx_doc = {
        "group_id": str(group["_id"]),
        "transaction_type": "contribution_credit",
        "amount": c["amount_due"],
        "category": "monthly_contribution",
        "reference_id": str(c["_id"]),
        "description": f"Month {c['month_index']} savings contribution verified for {member_name}",
        "authorized_by": str(admin["_id"]),
        "created_at": now,
    }
    await db.kitty_transactions.insert_one(tx_doc)

    await record_audit_log(
        db=db,
        actor=admin,
        action="verify_contribution",
        resource_type="contributions",
        resource_id=str(c["_id"]),
        before_state=before_state,
        after_state={"status": "verified", "verified_by": str(admin["_id"])},
        notes=f"Approved Month {c['month_index']} contribution of Rs {c['amount_due']}",
    )

    # Trigger SMS notification to contributing member
    bal_data = await get_kitty_balance_data(db, str(group["_id"]))
    if member and member.get("phone"):
        await send_notification(
            db=db,
            recipient_user_id=c["user_id"],
            phone_number=member.get("phone"),
            template_name="EDT_VERIFIED_02",
            variables={
                "member_name": member_name,
                "amount": c["amount_due"],
                "utr": c.get("utr_reference", "N/A"),
                "total": bal_data["current_balance"],
            },
        )

    return {"message": "Contribution verified and added to Kitty balance"}


@router.put("/contributions/{contribution_id}/reject")
async def reject_contribution_payment(
    group_code: str,
    contribution_id: str,
    payload: ContributionReject,
    admin=Depends(require_admin),
):
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    if not ObjectId.is_valid(contribution_id):
        raise HTTPException(status_code=400, detail="Invalid contribution ID")

    c = await db.contributions.find_one({
        "_id": ObjectId(contribution_id),
        "group_id": str(group["_id"]),
    })
    if not c:
        raise HTTPException(status_code=404, detail="Contribution record not found")

    now = datetime.now(timezone.utc)
    before_state = {"status": c["status"]}

    await db.contributions.update_one(
        {"_id": c["_id"]},
        {"$set": {
            "status": "rejected",
            "rejection_reason": payload.reason,
            "rejected_at": now,
            "rejected_by": str(admin["_id"]),
        }},
    )

    await record_audit_log(
        db=db,
        actor=admin,
        action="reject_contribution",
        resource_type="contributions",
        resource_id=str(c["_id"]),
        before_state=before_state,
        after_state={"status": "rejected", "rejection_reason": payload.reason},
        notes=f"Rejected Month {c['month_index']} contribution: {payload.reason}",
    )

    member = await db.users.find_one({"_id": ObjectId(c["user_id"])})
    if member and member.get("phone"):
        await send_notification(
            db=db,
            recipient_user_id=c["user_id"],
            phone_number=member.get("phone"),
            template_name="EDT_REJECTED_03",
            variables={
                "member_name": member.get("name", "Member"),
                "amount": c["amount_due"],
                "reason": payload.reason,
            },
        )

    return {"message": "Contribution marked as rejected", "reason": payload.reason}


@router.post("/disbursements", status_code=201)
async def create_kitty_disbursement(
    group_code: str,
    payload: KittyDisbursementCreate,
    admin=Depends(require_admin),
):
    """
    Records an expenditure directly funded from the collective Kitty pool
    (e.g., flight booking, hotel deposit advance, rental vehicle).
    Does NOT create personal debt in Kitty Split.
    """
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    group_id_str = str(group["_id"])

    bal_data = await get_kitty_balance_data(db, group_id_str)
    if bal_data["current_balance"] < payload.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient Kitty balance. Current balance is Rs {bal_data['current_balance']}, cannot disburse Rs {payload.amount}",
        )

    now = datetime.now(timezone.utc)
    disb_date = (
        datetime.combine(payload.disbursement_date, datetime.min.time(), tzinfo=timezone.utc)
        if payload.disbursement_date else now
    )

    doc = {
        "group_id": group_id_str,
        "transaction_type": "disbursement",
        "amount": payload.amount,
        "category": payload.category,
        "description": payload.description,
        "recipient": payload.recipient,
        "authorized_by": str(admin["_id"]),
        "disbursement_date": disb_date,
        "created_at": now,
    }
    result = await db.kitty_transactions.insert_one(doc)

    await record_audit_log(
        db=db,
        actor=admin,
        action="kitty_disbursement",
        resource_type="kitty_transactions",
        resource_id=str(result.inserted_id),
        before_state={"kitty_balance": bal_data["current_balance"]},
        after_state={"kitty_balance": bal_data["current_balance"] - payload.amount, "disbursed": payload.amount},
        notes=f"Disbursed Rs {payload.amount} for {payload.description} ({payload.category})",
    )

    return {
        "id": str(result.inserted_id),
        "message": f"Kitty disbursement of Rs {payload.amount} recorded",
        "new_balance": bal_data["current_balance"] - payload.amount,
    }


@router.get("/transactions")
async def list_kitty_transactions(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await _get_member_group(db, group_code, user)
    cursor = db.kitty_transactions.find({"group_id": str(group["_id"])}).sort("created_at", -1)

    txs = []
    async for item in cursor:
        item["id"] = str(item.pop("_id"))
        if "created_at" in item and item["created_at"]:
            item["created_at"] = item["created_at"].isoformat()
        if "disbursement_date" in item and item["disbursement_date"]:
            item["disbursement_date"] = item["disbursement_date"].date().isoformat()
        txs.append(item)

    return {"transactions": txs, "count": len(txs)}


@router.post("/reconcile")
async def reconcile_kitty_balance(
    group_code: str,
    payload: KittyReconcileRequest,
    admin=Depends(require_admin),
):
    """
    Physical balance audit: compares confirmed physical funds held by Custodian
    against system recorded balance and optionally applies compensating adjustment.
    """
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    group_id_str = str(group["_id"])

    bal_data = await get_kitty_balance_data(db, group_id_str)
    system_bal = bal_data["current_balance"]
    actual_bal = payload.actual_bank_balance
    variance = actual_bal - system_bal

    now = datetime.now(timezone.utc)
    adjustment_applied = False

    if payload.apply_adjustment and variance != 0:
        adj_type = "credit" if variance > 0 else "debit"
        doc = {
            "group_id": group_id_str,
            "transaction_type": "adjustment",
            "adjustment_type": adj_type,
            "amount": abs(variance),
            "description": payload.notes or f"Reconciliation adjustment ({adj_type})",
            "authorized_by": str(admin["_id"]),
            "created_at": now,
        }
        await db.kitty_transactions.insert_one(doc)
        adjustment_applied = True

    await record_audit_log(
        db=db,
        actor=admin,
        action="reconcile_kitty",
        resource_type="kitty_reconciliation",
        resource_id=group_id_str,
        before_state={"system_balance": system_bal},
        after_state={"actual_balance": actual_bal, "variance": variance, "adjusted": adjustment_applied},
        notes=payload.notes,
    )

    return {
        "system_balance": system_bal,
        "actual_balance": actual_bal,
        "variance": variance,
        "adjustment_applied": adjustment_applied,
        "status": "balanced" if variance == 0 or adjustment_applied else "variance_detected",
    }


@router.post("/reminders")
async def trigger_contribution_reminders(
    group_code: str,
    month_index: int = 1,
    admin=Depends(require_admin),
):
    """
    Sends DLT SMS reminders to all members whose contribution for `month_index` is pending.
    """
    db = get_database()
    group = await _get_member_group(db, group_code, admin)
    group_id_str = str(group["_id"])

    pending_cursor = db.contributions.find({
        "group_id": group_id_str,
        "month_index": month_index,
        "status": {"$in": ["pending", "rejected"]},
    })

    dispatched = 0
    async for c in pending_cursor:
        member = await db.users.find_one({"_id": ObjectId(c["user_id"])})
        if member and member.get("phone"):
            due_str = c["due_date"].strftime("%d-%b") if c.get("due_date") else "10th"
            await send_notification(
                db=db,
                recipient_user_id=c["user_id"],
                phone_number=member.get("phone"),
                template_name="EDT_REMINDER_01",
                variables={
                    "member_name": member.get("name", "Member"),
                    "amount": c["amount_due"],
                    "month_cycle": c.get("cycle_month", f"Month {month_index}"),
                    "due_date": due_str,
                    "custodian_vpa": group.get("custody_holder_name", "custodian@upi"),
                },
            )
            dispatched += 1

    return {"message": f"Reminders dispatched to {dispatched} members", "count": dispatched}
