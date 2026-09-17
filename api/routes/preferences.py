"""
Alert Preferences & Triggered Alerts API Routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.preferences import (
    AlertPreferenceCreate,
    AlertPreferenceUpdate,
    AlertPreferenceItem,
    AlertPreferenceResponse,
    AlertPreferenceListResponse,
    TriggeredAlertItem,
    TriggeredAlertListResponse,
    TriggeredAlertActionResponse,
)
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService

router = APIRouter(tags=["Alert Preferences & Triggered Alerts"])


@router.post(
    "/preferences",
    response_model=AlertPreferenceResponse,
    summary="Create or update user alert preference",
    description="Saves or updates a flood-risk notification preference for a specific station or all stations."
)
def save_preference(
    preference: AlertPreferenceCreate,
    db: SupabaseService = Depends(get_db)
):
    # If a specific location_id is supplied, verify it exists
    if preference.location_id is not None:
        loc = db.get_location(preference.location_id)
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{preference.location_id}' not found."}
            )

    result = db.save_alert_preference(preference.model_dump())
    data = result.get("data", {})
    return AlertPreferenceResponse(
        status="success",
        preference=AlertPreferenceItem(
            id=data.get("id", 1),
            device_id=data.get("device_id", preference.device_id),
            location_id=data.get("location_id"),
            location_name=data.get("location_name"),
            district=data.get("district"),
            risk_threshold=float(data.get("risk_threshold", preference.risk_threshold)),
            notification_channels=data.get("notification_channels", preference.notification_channels),
            is_active=bool(data.get("is_active", preference.is_active)),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at"))
        )
    )


@router.get(
    "/preferences",
    response_model=AlertPreferenceListResponse,
    summary="List alert preferences",
    description="Retrieves alert preferences filtered by device ID, location ID, or active status."
)
def get_preferences(
    device_id: Optional[str] = Query(None, description="Client device or session identifier"),
    location_id: Optional[int] = Query(None, description="Specific location ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: SupabaseService = Depends(get_db)
):
    items_raw = db.get_alert_preferences(device_id=device_id, location_id=location_id, is_active=is_active)
    items = []
    for raw in items_raw:
        items.append(
            AlertPreferenceItem(
                id=raw.get("id", 1),
                device_id=raw.get("device_id", ""),
                location_id=raw.get("location_id"),
                location_name=raw.get("location_name"),
                district=raw.get("district"),
                risk_threshold=float(raw.get("risk_threshold", 35.0)),
                notification_channels=raw.get("notification_channels", ["in_app"]),
                is_active=bool(raw.get("is_active", True)),
                created_at=str(raw.get("created_at")),
                updated_at=str(raw.get("updated_at"))
            )
        )
    return AlertPreferenceListResponse(
        status="success",
        total=len(items),
        items=items
    )


@router.get(
    "/preferences/{device_id}",
    response_model=AlertPreferenceListResponse,
    summary="Get alert preferences for a specific device"
)
def get_device_preferences(
    device_id: str,
    db: SupabaseService = Depends(get_db)
):
    items_raw = db.get_alert_preferences(device_id=device_id)
    items = []
    for raw in items_raw:
        items.append(
            AlertPreferenceItem(
                id=raw.get("id", 1),
                device_id=raw.get("device_id", device_id),
                location_id=raw.get("location_id"),
                location_name=raw.get("location_name"),
                district=raw.get("district"),
                risk_threshold=float(raw.get("risk_threshold", 35.0)),
                notification_channels=raw.get("notification_channels", ["in_app"]),
                is_active=bool(raw.get("is_active", True)),
                created_at=str(raw.get("created_at")),
                updated_at=str(raw.get("updated_at"))
            )
        )
    return AlertPreferenceListResponse(
        status="success",
        total=len(items),
        items=items
    )


@router.delete(
    "/preferences/{preference_id}",
    response_model=AlertPreferenceResponse,
    responses={404: {"model": ErrorResponse, "description": "Preference not found"}},
    summary="Delete an alert preference by ID"
)
def delete_preference(
    preference_id: int,
    db: SupabaseService = Depends(get_db)
):
    success = db.delete_alert_preference(preference_id=preference_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "PREFERENCE_NOT_FOUND", "message": f"Preference {preference_id} not found."}
        )
    return {
        "status": "success",
        "preference": {
            "id": preference_id,
            "device_id": "",
            "location_id": None,
            "risk_threshold": 0.0,
            "notification_channels": [],
            "is_active": False,
            "created_at": "",
            "updated_at": ""
        }
    }


@router.delete(
    "/preferences/{device_id}/{location_id}",
    summary="Delete preference for device and location"
)
def delete_device_location_preference(
    device_id: str,
    location_id: str,
    db: SupabaseService = Depends(get_db)
):
    loc_val = None if location_id.lower() in ["all", "null", "none"] else int(location_id)
    db.delete_alert_preference(device_id=device_id, location_id=loc_val)
    return {"status": "success", "message": f"Preference deleted for device '{device_id}' and location '{location_id}'."}


# --------------------------------------------------------------------
# Triggered Alerts Routes
# --------------------------------------------------------------------
@router.get(
    "/alerts/triggered",
    response_model=TriggeredAlertListResponse,
    summary="List triggered alerts from inferences crossing user thresholds"
)
def get_triggered_alerts(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    status: Optional[str] = Query(None, description="Filter by status (UNREAD, READ, DISMISSED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: SupabaseService = Depends(get_db)
):
    alerts_raw = db.get_triggered_alerts(device_id=device_id, location_id=location_id, status=status, limit=limit, offset=offset)
    all_unread = db.get_triggered_alerts(device_id=device_id, status="UNREAD", limit=200)

    items = []
    for a in alerts_raw:
        prob = float(a.get("flood_probability", 0.0))
        items.append(
            TriggeredAlertItem(
                id=a.get("id", 1),
                preference_id=a.get("preference_id"),
                device_id=a.get("device_id"),
                location_id=a.get("location_id", 1),
                location_name=a.get("location_name"),
                district=a.get("district"),
                prediction_id=a.get("prediction_id"),
                flood_probability=prob,
                flood_probability_percent=round(prob * 100, 2),
                risk_level=a.get("risk_level", "LOW"),
                threshold_crossed=float(a.get("threshold_crossed", 35.0)),
                title=a.get("title", ""),
                message=a.get("message", ""),
                status=a.get("status", "UNREAD"),
                created_at=str(a.get("created_at"))
            )
        )

    return TriggeredAlertListResponse(
        status="success",
        total=len(items),
        unread_count=len(all_unread),
        items=items
    )


@router.post(
    "/alerts/triggered/{alert_id}/read",
    response_model=TriggeredAlertActionResponse,
    summary="Mark triggered alert as read"
)
def mark_triggered_alert_read(
    alert_id: int,
    db: SupabaseService = Depends(get_db)
):
    updated = db.update_triggered_alert_status(alert_id, "READ")
    if not updated:
        raise HTTPException(status_code=404, detail={"status": "error", "message": f"Alert {alert_id} not found."})
    return TriggeredAlertActionResponse(status="success", alert_id=alert_id, action="READ", message="Alert marked as read.")


@router.post(
    "/alerts/triggered/{alert_id}/dismiss",
    response_model=TriggeredAlertActionResponse,
    summary="Dismiss triggered alert"
)
def dismiss_triggered_alert(
    alert_id: int,
    db: SupabaseService = Depends(get_db)
):
    updated = db.update_triggered_alert_status(alert_id, "DISMISSED")
    if not updated:
        raise HTTPException(status_code=404, detail={"status": "error", "message": f"Alert {alert_id} not found."})
    return TriggeredAlertActionResponse(status="success", alert_id=alert_id, action="DISMISSED", message="Alert dismissed.")
