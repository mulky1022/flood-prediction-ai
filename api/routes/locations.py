"""
Locations API Routes.
"""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.location import LocationSchema, LocationListResponse, LocationDetailsResponse
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService, get_prediction_engine, PredictorService, get_alert_service, AlertService, get_official_warning_service, OfficialWarningService
from services.risk_engine import RiskEngine


from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/locations", tags=["Locations"])


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two geographic coordinates using the Haversine formula.
    """
    R = 6371.0  # Earth's radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


@router.get("", response_model=LocationListResponse)
def list_locations(
    district: Optional[str] = None,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves all static location monitoring points across Sri Lanka.
    """
    locations = db.get_locations()

    if district:
        d_lower = district.strip().lower()
        locations = [loc for loc in locations if str(loc.get("district", "")).strip().lower() == d_lower]

    return LocationListResponse(
        status="success",
        total=len(locations),
        locations=locations
    )


@router.get(
    "/nearest",
    summary="Find Nearest Monitoring Station to Coordinates",
    responses={
        200: {"description": "Nearest monitoring location found"},
        400: {"model": ErrorResponse, "description": "Invalid coordinates"},
        404: {"model": ErrorResponse, "description": "No locations found"}
    }
)
def get_nearest_location(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="User Latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="User Longitude (-180 to 180)"),
    db: SupabaseService = Depends(get_db)
):
    """
    Finds the geographically closest Sri Lanka flood monitoring station to given GPS coordinates.
    Uses Haversine distance formula.
    """
    locations = db.get_locations()
    if not locations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "NO_LOCATIONS", "message": "No monitoring stations available."}
        )

    nearest_loc = None
    min_dist_km = float("inf")

    for loc in locations:
        try:
            loc_lat = float(loc.get("latitude", 0))
            loc_lon = float(loc.get("longitude", 0))
            dist = haversine_distance_km(latitude, longitude, loc_lat, loc_lon)
            if dist < min_dist_km:
                min_dist_km = dist
                nearest_loc = loc
        except (ValueError, TypeError):
            continue

    if not nearest_loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "NEAREST_NOT_FOUND", "message": "Could not compute nearest station."}
        )

    return {
        "status": "success",
        "nearest_location": nearest_loc,
        "location_id": nearest_loc.get("id"),
        "distance_km": round(min_dist_km, 2),
        "user_coordinates": {
            "latitude": latitude,
            "longitude": longitude
        }
    }


@router.get(
    "/{location_id}/details",
    response_model=LocationDetailsResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    summary="Get aggregated location details, canonical prediction, alerts, official warnings, and history"
)
def get_location_details_aggregated(
    location_id: str,
    db: SupabaseService = Depends(get_db),
    alert_service: AlertService = Depends(get_alert_service),
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Retrieves location metadata along with canonical current prediction, active alerts, official warnings, and recent prediction history summary.
    Consumes canonical data sources only — zero client-side prediction or risk recalculations.
    """
    location = db.get_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    canonical_loc_id = location.get("id")

    # Fetch latest prediction from Phase 2 database
    latest_pred = db.get_latest_prediction(canonical_loc_id)
    current_prediction_dict = None
    status_flag = "NO_CURRENT_PREDICTION"

    if latest_pred:
        # Enforce location isolation
        rec_loc = latest_pred.get("location_id")
        if str(rec_loc) == str(canonical_loc_id):
            prob = float(latest_pred.get("flood_probability", 0.0))
            risk_lvl = latest_pred.get("risk_level") or RiskEngine.derive_risk_level(prob)
            action_blk = RiskEngine.get_canonical_action(risk_lvl)

            created_at = str(latest_pred.get("created_at") or datetime.now(timezone.utc).isoformat())
            valid_from = str(latest_pred.get("valid_from") or created_at)
            valid_until = str(latest_pred.get("valid_until") or (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat())

            # Freshness check
            try:
                vul_dt = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
                is_stale = datetime.now(timezone.utc) > vul_dt
            except Exception:
                is_stale = False

            status_flag = "STALE" if is_stale else "CURRENT"

            # Retrieve real-time weather for telemetry conditions
            try:
                from weather.weather_processor import get_weather_for_location
                wx = get_weather_for_location(canonical_loc_id, use_cache=True)
                curr_wx = wx.get("current", {}) if wx.get("status") == "success" else {}
                rain_wx = wx.get("rainfall", {}) if wx.get("status") == "success" else {}
                temp_c = curr_wx.get("temperature_c") if curr_wx.get("temperature_c") is not None else 26.5
                hum_pct = curr_wx.get("humidity_percent") if curr_wx.get("humidity_percent") is not None else 85.0
                rain_24h = rain_wx.get("rainfall_24h_forecast_mm") or rain_wx.get("rainfall_24h_mm") or curr_wx.get("precipitation_mm") or (latest_pred.get("rainfall_7d_mm", 0.0) / 7.0)
                r7 = rain_wx.get("rainfall_7d_mm", float(latest_pred.get("rainfall_7d_mm", 0.0)))
                trend = "Rising" if (r7 > 100 or (rain_24h and rain_24h > 20)) else ("Falling" if (r7 < 20 and (not rain_24h or rain_24h < 1)) else "Steady")
            except Exception:
                temp_c, hum_pct, rain_24h, trend = 26.5, 85.0, (latest_pred.get("rainfall_7d_mm", 0.0) / 7.0), "Steady"

            current_prediction_dict = {
                "prediction_id": latest_pred.get("id"),
                "location": {
                    "location_id": canonical_loc_id,
                    "record_id": location.get("record_id"),
                    "name": location.get("place_name") or location.get("name"),
                    "district": location.get("district"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude")
                },
                "prediction_time": created_at,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_stale": is_stale,
                "risk": {
                    "level": risk_lvl,
                    "score": prob,
                    "flood_probability_percent": round(prob * 100, 2)
                },
                "confidence": float(latest_pred.get("confidence", 0.90)),
                "action": action_blk,
                "conditions": {
                    "rainfall_mm_24h": round(float(rain_24h), 2),
                    "water_level_m": 0.0,
                    "water_level_trend": trend,
                    "humidity_percent": round(float(hum_pct), 1),
                    "temperature_c": round(float(temp_c), 1)
                },
                "status": status_flag
            }

    # Active alerts
    active_alerts = alert_service.get_active_alerts_for_location(canonical_loc_id)

    # Official Warning status
    official_warning_resp = warning_service.get_current_warning(canonical_loc_id)

    # Recent history (limit 5)
    recent_hist = db.get_prediction_history(canonical_loc_id, limit=5)

    return LocationDetailsResponse(
        status="success",
        location=location,
        current_prediction=current_prediction_dict,
        active_alerts=active_alerts,
        recent_history=recent_hist,
        official_warning=official_warning_resp,
        status_flag=status_flag
    )


@router.get(
    "/{location_id}",
    response_model=LocationSchema,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}}
)
def get_location_by_id(
    location_id: str,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves a single location by its numeric ID or record_id string.
    """
    location = db.get_location(location_id)

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    return location
