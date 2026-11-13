from datetime import datetime, date, timezone
from typing import Any, Optional


def _clean_state(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _clean_state(v) for k, v in data.items()}
    if isinstance(data, (list, tuple, set)):
        return [_clean_state(x) for x in data]
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    return data


async def record_audit_log(
    db: Any,
    actor: Any,
    action: str,
    resource_type: str,
    resource_id: str,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    ip_address: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Persists an immutable audit log entry into the database.
    Tracks all financial mutations, status transitions, and critical system events.
    """
    actor_id = str(actor.get("_id", "system")) if isinstance(actor, dict) else str(getattr(actor, "id", "system"))
    actor_name = actor.get("name", "System") if isinstance(actor, dict) else getattr(actor, "name", "System")
    actor_role = actor.get("role", "system") if isinstance(actor, dict) else getattr(actor, "role", "system")

    log_entry = {
        "actor_id": actor_id,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "before_state": _clean_state(before_state),
        "after_state": _clean_state(after_state),
        "ip_address": ip_address,
        "notes": notes,
        "timestamp": datetime.now(timezone.utc),
    }

    try:
        result = await db.audit_logs.insert_one(log_entry)
        log_entry["_id"] = result.inserted_id
    except Exception as e:
        # Fallback logging should not crash the main transaction
        print(f"[AuditLog Error] Failed to write audit log: {e}")

    return log_entry
