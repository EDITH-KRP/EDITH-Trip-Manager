import uuid
from datetime import datetime, timezone
from typing import Any, Optional
import urllib.request
import json

from app.config import settings

# Approved Indian TRAI DLT Templates
DLT_TEMPLATES = {
    "EDT_REMINDER_01": {
        "template_id": "1107168920192837461",
        "format": "EDITH TRP: Dear {member_name}, your monthly trip contribution of Rs {amount} for {month_cycle} is due on {due_date}. Please pay via UPI to {custodian_vpa}. - EDITH",
    },
    "EDT_VERIFIED_02": {
        "template_id": "1107168920192837462",
        "format": "EDITH TRP: Hi {member_name}, your trip contribution of Rs {amount} with Ref {utr} has been verified and added to the Kitty. Current Total: Rs {total}. - EDITH",
    },
    "EDT_REJECTED_03": {
        "template_id": "1107168920192837463",
        "format": "EDITH TRP: Hi {member_name}, your submission for Rs {amount} could not be verified. Reason: {reason}. Please update in the app. - EDITH",
    },
    "EDT_EXPENSE_04": {
        "template_id": "1107168920192837464",
        "format": "EDITH TRP: {payer_name} paid Rs {amount} for {title}. Your share is Rs {share}. Check details in EDITH App. - EDITH",
    },
    "EDT_SETTLE_05": {
        "template_id": "1107168920192837465",
        "format": "EDITH TRP: Settlement of Rs {amount} from {debtor_name} to {creditor_name} has been confirmed. Balance updated. - EDITH",
    },
    "EDT_ITINERARY_06": {
        "template_id": "1107168920192837466",
        "format": "EDITH TRP: Trip Itinerary updated by Admin. Destination: {destination}. Check app for transit and stay details. - EDITH",
    },
}


async def send_notification(
    db: Any,
    recipient_user_id: str,
    phone_number: Optional[str],
    template_name: str,
    variables: dict[str, Any],
) -> dict:
    """
    Constructs a DLT-compliant SMS message, logs it into the notifications collection,
    and dispatches via the configured SMS gateway (or simulation mode in dev).
    """
    tmpl = DLT_TEMPLATES.get(template_name)
    if not tmpl:
        raise ValueError(f"Unknown DLT template: {template_name}")

    try:
        message_body = tmpl["format"].format(**variables)
    except KeyError as e:
        message_body = f"Notification ({template_name}): missing variable {e}"

    notification_id = str(uuid.uuid4())
    provider_id = f"SIM-{notification_id[:8]}"
    dispatch_status = "delivered"
    error_detail = None

    # Real SMS dispatch if enabled
    if settings.sms_enabled and settings.sms_gateway_api_key and phone_number:
        try:
            clean_phone = "".join(filter(str.isdigit, phone_number))[-10:]
            payload_data = {
                "route": "dlt",
                "sender_id": settings.sms_sender_id,
                "message": tmpl["template_id"],
                "variables_values": "|".join(str(v) for v in variables.values()),
                "flash": 0,
                "numbers": clean_phone,
            }
            req = urllib.request.Request(
                settings.sms_gateway_url,
                data=json.dumps(payload_data).encode("utf-8"),
                headers={
                    "authorization": settings.sms_gateway_api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_json = json.loads(response.read().decode())
                provider_id = resp_json.get("request_id", provider_id)
                dispatch_status = "sent"
        except Exception as exc:
            dispatch_status = "failed"
            error_detail = str(exc)
            print(f"[SMS Dispatch Error] {exc}")

    doc = {
        "recipient_user_id": str(recipient_user_id),
        "phone_number": phone_number,
        "template_name": template_name,
        "template_id": tmpl["template_id"],
        "message_body": message_body,
        "status": dispatch_status,
        "provider_message_id": provider_id,
        "error_detail": error_detail,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        res = await db.notifications.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
    except Exception as e:
        print(f"[Notification Store Error] {e}")

    return doc
