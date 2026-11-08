from fastapi import APIRouter, Depends, Request
from app.database import get_database
from app.dependencies import require_admin

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/history")
async def list_notification_history(limit: int = 50, admin=Depends(require_admin)):
    """Admin view of recently dispatched SMS and app alerts."""
    db = get_database()
    cursor = db.notifications.find({}).sort("created_at", -1).limit(limit)

    logs = []
    async for item in cursor:
        item["id"] = str(item.pop("_id"))
        if "created_at" in item and item["created_at"]:
            item["created_at"] = item["created_at"].isoformat()
        logs.append(item)

    return {"notifications": logs, "count": len(logs)}


@router.post("/webhook")
async def sms_gateway_webhook(request: Request):
    """
    Receives delivery report callbacks from Indian SMS gateway (e.g. Fast2SMS / Msg91).
    Updates status in the notifications collection.
    """
    db = get_database()
    try:
        body = await request.json()
    except Exception:
        body = {}

    provider_id = body.get("request_id") or body.get("message_id")
    status = body.get("status", "DELIVRD").lower()

    if provider_id:
        mapped_status = "delivered" if "deliv" in status else "failed"
        await db.notifications.update_one(
            {"provider_message_id": provider_id},
            {"$set": {"status": mapped_status, "provider_callback": body}},
        )

    return {"status": "received"}
