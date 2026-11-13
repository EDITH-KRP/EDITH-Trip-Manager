from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, ObjectId, DuplicateKeyError
from app.dependencies import get_current_user, require_admin
from app.schemas import GroupCreate, TripPlanUpdate
from app.services.audit import record_audit_log
from app.services.notifications import send_notification
from app.routes.kitty import ensure_group_contributions, get_kitty_balance_data

router = APIRouter(prefix="/groups", tags=["Groups"])


def _fmt_date(val):
    if not val:
        return None
    if isinstance(val, str):
        return val[:10]
    if hasattr(val, "date"):
        return val.date().isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def serialize_group(group: dict) -> dict:
    return {
        "id": str(group["_id"]),
        "name": group["name"],
        "group_code": group["group_code"],
        "monthly_contribution": group["monthly_contribution"],
        "duration_months": group["duration_months"],
        "start_date": _fmt_date(group.get("start_date")),
        "custody_holder_name": group["custody_holder_name"],
        "currency": group["currency"],
        "created_by": group["created_by"],
        "trip_destination": group.get("trip_destination", "To be decided"),
        "trip_start_date": _fmt_date(group.get("trip_start_date")),
        "trip_end_date": _fmt_date(group.get("trip_end_date")),
        "planned_trip_budget": group.get("planned_trip_budget", 0),
        "trip_notes": group.get("trip_notes", ""),
        "trip_stops": group.get("trip_stops", []),
        "trip_title": group.get("trip_title", group["name"]),
    }


@router.post("", status_code=201)
async def create_group(payload: GroupCreate, admin=Depends(require_admin)):
    db = get_database()
    if payload.trip_start_date and payload.trip_end_date and payload.trip_end_date < payload.trip_start_date:
        raise HTTPException(status_code=422, detail="Trip end date cannot be before trip start date")
    now = datetime.now(timezone.utc)
    document = {
        "name": payload.name,
        "group_code": payload.group_code.upper(),
        "monthly_contribution": payload.monthly_contribution,
        "duration_months": payload.duration_months,
        "start_date": datetime.combine(
            payload.start_date, datetime.min.time(), tzinfo=timezone.utc
        ),
        "custody_holder_name": payload.custody_holder_name,
        "currency": payload.currency,
        "trip_destination": payload.trip_destination,
        "trip_start_date": (
            datetime.combine(payload.trip_start_date, datetime.min.time(), tzinfo=timezone.utc)
            if payload.trip_start_date else None
        ),
        "trip_end_date": (
            datetime.combine(payload.trip_end_date, datetime.min.time(), tzinfo=timezone.utc)
            if payload.trip_end_date else None
        ),
        "planned_trip_budget": payload.planned_trip_budget,
        "trip_notes": payload.trip_notes,
        "created_by": str(admin["_id"]),
        "created_at": now,
        "max_members": 4,
        "is_active": True,
    }
    try:
        result = await db.groups.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Group code already exists")

    group_id = result.inserted_id
    # Admin is automatically a member of the group.
    await db.memberships.insert_one({
        "group_id": str(group_id),
        "user_id": str(admin["_id"]),
        "created_at": now,
    })
    created_group = {"_id": group_id, **document}
    await ensure_group_contributions(db, created_group, specific_user_id=str(admin["_id"]))

    await record_audit_log(
        db=db,
        actor=admin,
        action="create_group",
        resource_type="groups",
        resource_id=str(group_id),
        after_state={"name": payload.name, "group_code": document["group_code"]},
        notes=f"Created group {payload.name} ({document['group_code']})",
    )

    return serialize_group(created_group)


@router.post("/{group_code}/join")
async def join_group(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await db.groups.find_one({
        "group_code": group_code.upper(),
        "is_active": True,
    })
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    existing = await db.memberships.find_one({
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
    })
    if existing:
        return {"message": "Already a member of this group"}

    current_count = await db.memberships.count_documents({
        "group_id": str(group["_id"])
    })
    if current_count >= 4:
        raise HTTPException(status_code=409, detail="This private group is limited to four members")

    membership = {
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db.memberships.insert_one(membership)
    except DuplicateKeyError:
        return {"message": "Already a member of this group"}

    # Automatically generate 12-month contribution schedule for the new member
    await ensure_group_contributions(db, group, specific_user_id=str(user["_id"]))

    await record_audit_log(
        db=db,
        actor=user,
        action="join_group",
        resource_type="memberships",
        resource_id=str(group["_id"]),
        after_state={"user_id": str(user["_id"]), "group_code": group["group_code"]},
        notes=f"{user.get('name', 'Member')} joined group {group['name']}",
    )

    return {"message": f"Joined {group['name']} successfully"}


@router.get("/mine")
async def my_groups(user=Depends(get_current_user)):
    db = get_database()
    memberships = db.memberships.find({"user_id": str(user["_id"])})
    group_ids = []
    async for membership in memberships:
        if ObjectId.is_valid(membership["group_id"]):
            group_ids.append(ObjectId(membership["group_id"]))

    groups = []
    cursor = db.groups.find({"_id": {"$in": group_ids}, "is_active": True})
    async for group in cursor:
        groups.append(serialize_group(group))
    return {"groups": groups}


@router.get("/{group_code}/summary")
async def group_summary(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await db.groups.find_one({
        "group_code": group_code.upper(),
        "is_active": True,
    })
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    membership = await db.memberships.find_one({
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
    })
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    group_id_str = str(group["_id"])
    bal_data = await get_kitty_balance_data(db, group_id_str)
    member_count = await db.memberships.count_documents({"group_id": group_id_str})
    target = (
        group["monthly_contribution"]
        * group["duration_months"]
        * member_count
    )

    return {
        "group": serialize_group(group),
        "member_count": member_count,
        "fund_collected": bal_data["total_verified"],
        "fund_target": target,
        "fund_disbursed": bal_data["total_disbursed"],
        "fund_remaining": max(0, target - bal_data["total_verified"]),
        "kitty_balance": bal_data["current_balance"],
        "individual_financial_records_visible": False,
        "note": "Verified collections and balances are actively synchronized with the Kitty Ledger.",
    }


@router.patch("/{group_code}/trip")
async def update_trip_details(
    group_code: str,
    payload: GroupCreate,
    admin=Depends(require_admin),
):
    db = get_database()
    if payload.trip_start_date and payload.trip_end_date and payload.trip_end_date < payload.trip_start_date:
        raise HTTPException(status_code=422, detail="Trip end date cannot be before trip start date")
    group = await db.groups.find_one({"group_code": group_code.upper(), "is_active": True})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    update = {
        "name": payload.name,
        "monthly_contribution": payload.monthly_contribution,
        "duration_months": payload.duration_months,
        "custody_holder_name": payload.custody_holder_name,
        "trip_destination": payload.trip_destination,
        "trip_start_date": (
            datetime.combine(payload.trip_start_date, datetime.min.time(), tzinfo=timezone.utc)
            if payload.trip_start_date else None
        ),
        "trip_end_date": (
            datetime.combine(payload.trip_end_date, datetime.min.time(), tzinfo=timezone.utc)
            if payload.trip_end_date else None
        ),
        "planned_trip_budget": payload.planned_trip_budget,
        "trip_notes": payload.trip_notes,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": str(admin["_id"]),
    }
    await db.groups.update_one({"_id": group["_id"]}, {"$set": update})
    updated = await db.groups.find_one({"_id": group["_id"]})
    return serialize_group(updated)


@router.get("/{group_code}/members")
async def list_group_members(group_code: str, user=Depends(get_current_user)):
    db = get_database()
    group = await db.groups.find_one({"group_code": group_code.upper(), "is_active": True})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    membership = await db.memberships.find_one({
        "group_id": str(group["_id"]),
        "user_id": str(user["_id"]),
    })
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    cursor = db.memberships.find({"group_id": str(group["_id"])})
    members = []
    async for item in cursor:
        person = await db.users.find_one(
            {"_id": ObjectId(item["user_id"])},
            {"name": 1, "role": 1},
        )
        if person:
            members.append({
                "id": str(person["_id"]),
                "name": person.get("name", "Member"),
                "role": person.get("role", "member"),
            })
    return {"members": members, "count": len(members)}


@router.patch("/{group_code}/trip-plan")
async def update_trip_plan(
    group_code: str,
    payload: TripPlanUpdate,
    admin=Depends(require_admin),
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    db = get_database()
    if payload.trip_start_date and payload.trip_end_date and payload.trip_end_date < payload.trip_start_date:
        raise HTTPException(status_code=422, detail="Trip end date cannot be before trip start date")
    for stop in payload.stops:
        if stop.arrival_date and stop.departure_date and stop.departure_date < stop.arrival_date:
            raise HTTPException(status_code=422, detail=f"Departure cannot precede arrival for {stop.destination}")

    group = await db.groups.find_one({"group_code": group_code.upper(), "is_active": True})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    stops = []
    for stop in payload.stops:
        stops.append({
            "destination": stop.destination,
            "arrival_date": stop.arrival_date.isoformat() if stop.arrival_date else None,
            "departure_date": stop.departure_date.isoformat() if stop.departure_date else None,
            "notes": stop.notes,
            "transport": stop.transport,
            "accommodation": stop.accommodation,
        })
    await db.groups.update_one(
        {"_id": group["_id"]},
        {"$set": {
            "trip_title": payload.trip_title,
            "trip_start_date": (
                datetime.combine(payload.trip_start_date, datetime.min.time(), tzinfo=timezone.utc)
                if payload.trip_start_date else None
            ),
            "trip_end_date": (
                datetime.combine(payload.trip_end_date, datetime.min.time(), tzinfo=timezone.utc)
                if payload.trip_end_date else None
            ),
            "planned_trip_budget": payload.planned_trip_budget,
            "trip_stops": stops,
            "trip_notes": payload.notes,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": str(admin["_id"]),
        }},
    )
    updated = await db.groups.find_one({"_id": group["_id"]})

    await record_audit_log(
        db=db,
        actor=admin,
        action="update_trip_plan",
        resource_type="groups",
        resource_id=str(group["_id"]),
        after_state={"stops_count": len(stops), "title": payload.trip_title},
        notes=f"Updated trip plan with {len(stops)} stops",
    )

    # Notify members of itinerary update
    dest_summary = ", ".join(s["destination"] for s in stops[:3]) or "New destinations"
    members_cursor = db.memberships.find({"group_id": str(group["_id"])})
    async for m in members_cursor:
        if m["user_id"] != str(admin["_id"]):
            member_user = await db.users.find_one({"_id": ObjectId(m["user_id"])})
            if member_user and member_user.get("phone"):
                await send_notification(
                    db=db,
                    recipient_user_id=m["user_id"],
                    phone_number=member_user.get("phone"),
                    template_name="EDT_ITINERARY_06",
                    variables={"destination": dest_summary},
                )

    return serialize_group(updated)
