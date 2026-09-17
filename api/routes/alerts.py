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
        action="ACKNOWLEDGE",
        alert_id=alert_id,
        message=f"Alert {alert_id} marked as ACKNOWLEDGED.",
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
        action="RESOLVE",
        alert_id=alert_id,
        message=f"Alert {alert_id} marked as RESOLVED.",
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
