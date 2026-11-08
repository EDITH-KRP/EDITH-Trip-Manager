from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database, DuplicateKeyError
from app.dependencies import require_admin
from app.schemas import MemberCreate, MemberResponse
from app.security import hash_password
from app.services.audit import record_audit_log

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post("/members", response_model=MemberResponse, status_code=201)
async def create_member(payload: MemberCreate, admin=Depends(require_admin)):
    db = get_database()
    email = payload.email.lower()

    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email is already registered")

    now = datetime.now(timezone.utc)
    document = {
        "name": payload.name.strip(),
        "email": email,
        "phone": payload.phone.strip(),
        "password_hash": hash_password(payload.temporary_password),
        "role": "member",
        "is_active": True,
        "created_at": now,
        "created_by": str(admin["_id"]),
        "must_change_password": True,
    }
    result = await db.users.insert_one(document)

    await record_audit_log(
        db=db,
        actor=admin,
        action="create_member",
        resource_type="users",
        resource_id=str(result.inserted_id),
        after_state={"name": document["name"], "email": document["email"], "role": document["role"]},
        notes=f"Admin created member account for {document['name']}",
    )

    # Do not return password hashes or phone numbers in the general member view.
    return {
        "id": str(result.inserted_id),
        "name": document["name"],
        "email": document["email"],
        "role": document["role"],
        "is_active": True,
    }


@router.get("/members")
async def admin_list_members(admin=Depends(require_admin)):
    db = get_database()
    cursor = db.users.find(
        {"role": "member"},
        {"name": 1, "email": 1, "phone": 1, "is_active": 1, "_id": 1},
    )
    members = []
    async for user in cursor:
        members.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone"),
            "is_active": user.get("is_active", False),
        })
    return {"members": members, "count": len(members)}


@router.get("/audit-logs")
async def admin_list_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    limit: int = 50,
    admin=Depends(require_admin),
):
    db = get_database()
    query = {}
    if resource_type:
        query["resource_type"] = resource_type
    if action:
        query["action"] = action

    cursor = db.audit_logs.find(query).sort("timestamp", -1).limit(limit)
    logs = []
    async for item in cursor:
        item["id"] = str(item.pop("_id"))
        if "timestamp" in item and item["timestamp"]:
            item["timestamp"] = item["timestamp"].isoformat()
        logs.append(item)

    return {"audit_logs": logs, "count": len(logs)}

