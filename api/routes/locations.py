"""
Locations API Routes.
"""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.schemas.location import LocationSchema, LocationListResponse
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService

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
