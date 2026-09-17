"""
Locations API Routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas.location import LocationSchema, LocationListResponse
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService

router = APIRouter(prefix="/locations", tags=["Locations"])


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
