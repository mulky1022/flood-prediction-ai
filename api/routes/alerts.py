"""
Alerts API Routes.
"""

from typing import Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.alert import (
    AlertItem,
    AlertResponse,
    AlertListResponse,
    AlertActionResponse,
    AlertProcessResponse,
)
from api.schemas.common import ErrorResponse
from api.dependencies import get_alert_service, get_db, AlertService, SupabaseService

router = APIRouter(tags=["Alerts"])


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="List all flood alerts",
    description="Retrieves a paginated list of flood alerts with optional status and location filtering."
)
def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED, EXPIRED)"),
    location_id: Optional[str] = Query(None, description="Filter by location integer ID or record_id"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    alert_service: AlertService = Depends(get_alert_service),
    db: SupabaseService = Depends(get_db)
):
    # Resolve location if string/record_id passed
    resolved_loc_id = None
    if location_id is not None:
        loc = db.get_location(location_id)
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if hasattr(status, "HTTP_404_NOT_FOUND") else 404,
                detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
            )
        resolved_loc_id = loc.get("id")

    items = alert_service.get_alert_history(status=status, location_id=resolved_loc_id, limit=limit, offset=offset)
    active_alerts = alert_service.get_active_alerts(limit=100)

    return AlertListResponse(
        status="success",
        total=len(items),
        active_count=len(active_alerts),
        items=items
    )


from api.schemas.preferences import (
    TriggeredAlertItem,
    TriggeredAlertListResponse,
    TriggeredAlertActionResponse,
)


@router.get(
    "/alerts/active",
    response_model=AlertListResponse,
    summary="Get active alerts",
    description="Retrieves all currently active or acknowledged flood alerts across Sri Lanka."
)
def get_active_alerts(
    limit: int = Query(50, ge=1, le=100),
    alert_service: AlertService = Depends(get_alert_service)
):
    items = alert_service.get_active_alerts(limit=limit)
    return AlertListResponse(
        status="success",
        total=len(items),
        active_count=len(items),
        items=items
    )


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
    "/alerts/triggered/{alert_id:int}/read",
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
    "/alerts/triggered/{alert_id:int}/dismiss",
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


@router.get(
    "/alerts/{alert_id}",
    response_model=AlertResponse,
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
    summary="Get alert details by ID"
)
def get_alert_by_id(
    alert_id: int,
    alert_service: AlertService = Depends(get_alert_service)
):
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if hasattr(status, "HTTP_404_NOT_FOUND") else 404,
            detail={"status": "error", "code": "ALERT_NOT_FOUND", "message": f"Alert with ID {alert_id} not found."}
        )
    return AlertResponse(status="success", alert=alert)


@router.get(
    "/alerts/location/{location_id}",
    response_model=AlertListResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    summary="Get alerts for a location"
)
def get_location_alerts(
    location_id: str,
    limit: int = Query(20, ge=1, le=100),
    alert_service: AlertService = Depends(get_alert_service),
    db: SupabaseService = Depends(get_db)
):
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    items = alert_service.get_alert_history(location_id=loc.get("id"), limit=limit)
    active_items = [a for a in items if a.get("status") in ["ACTIVE", "ACKNOWLEDGED"]]

    return AlertListResponse(
        status="success",
        total=len(items),
        active_count=len(active_items),
        items=items
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertActionResponse,
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
    summary="Acknowledge an active alert"
)
def acknowledge_alert(
    alert_id: int,
    alert_service: AlertService = Depends(get_alert_service)
):
    updated = alert_service.acknowledge_alert(alert_id)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "code": "ALERT_NOT_FOUND", "message": f"Alert with ID {alert_id} not found."}
        )
    return AlertActionResponse(
        status="success",
        alert_id=alert_id,
        action="ACKNOWLEDGE",
        message=f"Alert {alert_id} acknowledged.",
        alert=updated
    )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertActionResponse,
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
    summary="Resolve a flood alert"
)
def resolve_alert(
    alert_id: int,
    alert_service: AlertService = Depends(get_alert_service)
):
    updated = alert_service.resolve_alert(alert_id)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "code": "ALERT_NOT_FOUND", "message": f"Alert with ID {alert_id} not found."}
        )
    return AlertActionResponse(
        status="success",
        alert_id=alert_id,
        action="RESOLVE",
        message=f"Alert {alert_id} resolved.",
        alert=updated
    )


@router.post(
    "/alerts/process/{location_id}",
    response_model=AlertProcessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location not found"},
        422: {"model": ErrorResponse, "description": "Prediction unavailable"}
    },
    summary="Evaluate and process alert for a location"
)
def process_location_alert(
    location_id: str,
    alert_service: AlertService = Depends(get_alert_service),
    db: SupabaseService = Depends(get_db)
):
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    result = alert_service.process_location_alert(loc.get("id"))
    if result.get("status") == "error":
        if result.get("action_taken") == "LOCATION_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result)
        else:
            raise HTTPException(status_code=422, detail=result)

    return AlertProcessResponse(
        status="success",
        location_id=loc.get("id"),
        action_taken=result.get("action_taken", "PROCESSED"),
        alert=result.get("alert"),
        message=result.get("message", "Processed alert evaluation.")
    )


@router.post(
    "/alerts/process-all",
    summary="Evaluate alerts for all monitored locations across Sri Lanka"
)
def process_all_alerts(
    alert_service: AlertService = Depends(get_alert_service)
):
    return alert_service.process_all_monitored_locations()
