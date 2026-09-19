"""
Phase 15 — WhatsApp & SMS Alert Delivery API Routes.
Provides subscription management, multi-channel notification dispatch,
delivery tracking logs, and provider webhook status callbacks.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

from api.schemas.notification_delivery import (
    SubscriptionCreate,
    SubscriptionVerify,
    SubscriptionItem,
    SubscriptionResponse,
    SubscriptionListResponse,
    NotificationDispatchRequest,
    NotificationLogItem,
    NotificationLogListResponse,
    DeliveryWebhookPayload
)
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService
from services.delivery_providers import (
    normalize_phone_number,
    mask_phone_number,
    render_alert_template,
    SMSNotificationProvider,
    WhatsAppNotificationProvider
)
from services.risk_engine import RiskEngine

router = APIRouter(prefix="/notifications", tags=["WhatsApp & SMS Notification Delivery"])

sms_provider = SMSNotificationProvider()
whatsapp_provider = WhatsAppNotificationProvider()


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update SMS / WhatsApp alert subscription"
)
def create_subscription(
    payload: SubscriptionCreate,
    db: SupabaseService = Depends(get_db)
):
    """
    Subscribes a user phone number to receive flood-risk alerts via SMS or WhatsApp for a location.
    Normalizes phone numbers to E.164 (+94771234567) and enforces location validation.
    """
    # 1. Validate location
    loc = db.get_location(payload.location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{payload.location_id}' not found."}
        )

    canonical_loc_id = loc.get("id")

    # 2. Normalize destination phone number to E.164 format
    try:
        norm_destination = normalize_phone_number(payload.destination)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"status": "error", "code": "INVALID_PHONE_NUMBER", "message": str(ve)}
        )

    masked_phone = mask_phone_number(norm_destination)

    # 3. Save subscription record
    sub_dict = {
        "user_id": payload.user_id,
        "device_id": payload.device_id,
        "location_id": str(payload.location_id),
        "channel": payload.channel.lower(),
        "destination": norm_destination,
        "destination_masked": masked_phone,
        "language": (payload.language or "en").lower(),
        "minimum_risk_level": (payload.minimum_risk_level or "HIGH").upper(),
        "enabled": True,
        "verified": True,
        "verification_code": "123456"
    }

    saved = db.save_subscription(sub_dict)

    item = SubscriptionItem(
        id=saved["id"],
        user_id=saved.get("user_id"),
        device_id=saved.get("device_id"),
        location_id=saved["location_id"],
        location_name=loc.get("place_name") or loc.get("name"),
        channel=saved["channel"],
        destination_masked=saved["destination_masked"],
        language=saved["language"],
        minimum_risk_level=saved["minimum_risk_level"],
        enabled=saved["enabled"],
        verified=saved["verified"],
        created_at=saved["created_at"],
        updated_at=saved["updated_at"]
    )

    return SubscriptionResponse(
        status="success",
        message="Alert subscription created successfully.",
        subscription=item
    )


@router.post(
    "/subscriptions/verify",
    response_model=SubscriptionResponse,
    summary="Verify subscription phone OTP code"
)
def verify_subscription(
    payload: SubscriptionVerify,
    db: SupabaseService = Depends(get_db)
):
    """
    Verifies subscription OTP verification code.
    """
    verified_item = db.verify_subscription(payload.subscription_id, payload.verification_code)
    if not verified_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "code": "VERIFICATION_FAILED", "message": "Invalid subscription ID or verification code."}
        )

    loc = db.get_location(verified_item.get("location_id"))

    item = SubscriptionItem(
        id=verified_item["id"],
        user_id=verified_item.get("user_id"),
        device_id=verified_item.get("device_id"),
        location_id=verified_item["location_id"],
        location_name=loc.get("place_name") if loc else None,
        channel=verified_item["channel"],
        destination_masked=verified_item["destination_masked"],
        language=verified_item["language"],
        minimum_risk_level=verified_item["minimum_risk_level"],
        enabled=verified_item["enabled"],
        verified=verified_item["verified"],
        created_at=verified_item["created_at"],
        updated_at=verified_item["updated_at"]
    )

    return SubscriptionResponse(
        status="success",
        message="Subscription verified and activated successfully.",
        subscription=item
    )


@router.get(
    "/subscriptions",
    response_model=SubscriptionListResponse,
    summary="List active notification subscriptions"
)
def list_subscriptions(
    user_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves subscriptions filtered by user, device, location, or channel.
    """
    subs_raw = db.get_subscriptions(
        user_id=user_id,
        device_id=device_id,
        location_id=location_id,
        channel=channel,
        enabled_only=True
    )

    items = []
    for raw in subs_raw:
        loc = db.get_location(raw.get("location_id"))
        items.append(
            SubscriptionItem(
                id=raw["id"],
                user_id=raw.get("user_id"),
                device_id=raw.get("device_id"),
                location_id=str(raw["location_id"]),
                location_name=loc.get("place_name") if loc else None,
                channel=raw["channel"],
                destination_masked=raw["destination_masked"],
                language=raw["language"],
                minimum_risk_level=raw["minimum_risk_level"],
                enabled=raw["enabled"],
                verified=raw["verified"],
                created_at=raw["created_at"],
                updated_at=raw["updated_at"]
            )
        )

    return SubscriptionListResponse(
        status="success",
        total=len(items),
        subscriptions=items
    )


@router.delete(
    "/subscriptions/{subscription_id}",
    summary="Unsubscribe / disable alert subscription"
)
def delete_subscription(
    subscription_id: str,
    db: SupabaseService = Depends(get_db)
):
    """
    Deactivates an active alert subscription.
    """
    success = db.delete_subscription(subscription_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "SUBSCRIPTION_NOT_FOUND", "message": f"Subscription '{subscription_id}' not found."}
        )
    return {"status": "success", "message": f"Subscription '{subscription_id}' unsubscribed successfully."}


@router.post(
    "/dispatch",
    response_model=NotificationLogListResponse,
    summary="Dispatch multi-channel SMS / WhatsApp notifications for a canonical alert"
)
def dispatch_alert_notifications(
    payload: NotificationDispatchRequest,
    db: SupabaseService = Depends(get_db)
):
    """
    Triggers SMS and WhatsApp alert dispatches for active subscriptions matching location_id and risk_level.
    Consumes canonical Phase 5 action recommendation. Idempotency guarantees prevent duplicate dispatches.
    """
    # 1. Validate location
    loc = db.get_location(payload.location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{payload.location_id}' not found."}
        )

    canonical_loc_id = str(loc.get("id"))
    loc_name = loc.get("place_name") or loc.get("name", "Unknown Location")

    # 2. Retrieve canonical Phase 5 action message
    risk_lvl = payload.risk_level.upper()
    action_info = RiskEngine.get_canonical_action(risk_lvl)
    action_msg = action_info["message"]

    # 3. Retrieve matching active subscriptions for this location (supporting numeric ID or alias string)
    req_loc_id = str(payload.location_id)
    raw_subs = db.get_subscriptions(location_id=canonical_loc_id, enabled_only=True) + db.get_subscriptions(location_id=req_loc_id, enabled_only=True)
    seen_sub_ids = set()
    active_subs = []
    for s in raw_subs:
        if s["id"] not in seen_sub_ids:
            seen_sub_ids.add(s["id"])
            active_subs.append(s)

    # 4. Check existing notification logs for idempotency (same alert_id + sub_id + channel)
    existing_logs = db.get_notification_logs(alert_id=payload.alert_id)
    existing_sub_channels = set((log.get("subscription_id"), log.get("channel")) for log in existing_logs)

    sent_logs = []

    for sub in active_subs:
        sub_id = sub["id"]
        chan = sub["channel"].lower()
        sub_min_risk = sub.get("minimum_risk_level", "HIGH").upper()

        # Idempotency check — skip if already dispatched for this alert + subscription + channel
        if (sub_id, chan) in existing_sub_channels:
            logger.info(f"Idempotency skip: Alert {payload.alert_id} already sent to Sub {sub_id} ({chan})")
            continue

        # Render localized message text
        msg_text = render_alert_template(
            channel=chan,
            language=sub.get("language", "en"),
            location_name=loc_name,
            risk_level=risk_lvl,
            action_message=action_msg
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        dest = sub.get("destination", "+94771234567")

        # Provider dispatch
        if chan == "whatsapp":
            provider_res = whatsapp_provider.send(dest, msg_text)
        else:
            provider_res = sms_provider.send(dest, msg_text)

        log_record = {
            "alert_id": payload.alert_id,
            "prediction_id": payload.prediction_id,
            "location_id": str(payload.location_id),
            "subscription_id": sub_id,
            "channel": chan,
            "destination_masked": sub.get("destination_masked") or mask_phone_number(dest),
            "language": sub.get("language", "en"),
            "risk_level": risk_lvl,
            "status": provider_res.get("status", "SENT"),
            "provider_message_id": provider_res.get("provider_message_id"),
            "retry_count": 0 if provider_res.get("status") == "SENT" else 1,
            "failure_code": provider_res.get("failure_code"),
            "failure_message": provider_res.get("failure_message"),
            "created_at": now_iso,
            "sent_at": now_iso if provider_res.get("status") == "SENT" else None
        }

        saved_log = db.save_notification_log(log_record)

        sent_logs.append(
            NotificationLogItem(
                id=saved_log["id"],
                alert_id=saved_log["alert_id"],
                prediction_id=saved_log.get("prediction_id"),
                location_id=saved_log["location_id"],
                subscription_id=saved_log["subscription_id"],
                channel=saved_log["channel"],
                destination_masked=saved_log["destination_masked"],
                language=saved_log["language"],
                risk_level=saved_log["risk_level"],
                status=saved_log["status"],
                provider_message_id=saved_log.get("provider_message_id"),
                retry_count=saved_log.get("retry_count", 0),
                failure_code=saved_log.get("failure_code"),
                failure_message=saved_log.get("failure_message"),
                created_at=saved_log["created_at"],
                sent_at=saved_log.get("sent_at")
            )
        )

    return NotificationLogListResponse(
        status="success",
        total=len(sent_logs),
        notifications=sent_logs
    )


@router.get(
    "/logs",
    response_model=NotificationLogListResponse,
    summary="List notification delivery audit logs"
)
def list_notification_logs(
    alert_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves notification delivery audit logs.
    """
    logs_raw = db.get_notification_logs(alert_id=alert_id, location_id=location_id, limit=limit)
    items = []
    for raw in logs_raw:
        items.append(
            NotificationLogItem(
                id=raw["id"],
                alert_id=raw["alert_id"],
                prediction_id=raw.get("prediction_id"),
                location_id=str(raw["location_id"]),
                subscription_id=str(raw["subscription_id"]),
                channel=raw["channel"],
                destination_masked=raw["destination_masked"],
                language=raw["language"],
                risk_level=raw["risk_level"],
                status=raw["status"],
                provider_message_id=raw.get("provider_message_id"),
                retry_count=raw.get("retry_count", 0),
                failure_code=raw.get("failure_code"),
                failure_message=raw.get("failure_message"),
                created_at=raw["created_at"],
                sent_at=raw.get("sent_at"),
                delivered_at=raw.get("delivered_at")
            )
        )

    return NotificationLogListResponse(
        status="success",
        total=len(items),
        notifications=items
    )


@router.post(
    "/webhooks/{channel}",
    summary="Provider delivery status webhook callback"
)
def provider_webhook_callback(
    channel: str,
    payload: DeliveryWebhookPayload,
    db: SupabaseService = Depends(get_db)
):
    """
    Handles provider delivery status callbacks (e.g. SENT -> DELIVERED, FAILED).
    Prevents out-of-order state overwrites.
    """
    updated = db.update_notification_status(
        provider_message_id=payload.provider_message_id,
        new_status=payload.status,
        failure_reason=payload.failure_reason
    )

    if not updated:
        return {"status": "ignored", "message": "Provider message ID not found or state change invalid."}

    return {"status": "success", "message": "Notification delivery status updated.", "log": updated}
