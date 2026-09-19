"""
Official Government Warnings API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas.official_warning import (
    OfficialWarningCurrentResponse,
    OfficialWarningListResponse,
    OfficialWarningIngestRequest,
    OfficialWarningItem
)
from api.schemas.common import ErrorResponse
from services.official_warning_service import (
    OfficialWarningService,
    get_official_warning_service
)
from services.supabase_service import SupabaseService, get_supabase_service

router = APIRouter(prefix="/warnings", tags=["Official Warnings"])


@router.get(
    "/active",
    summary="Get all active official government warnings across all locations"
)
def get_all_active_warnings_endpoint(
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Retrieves all currently active official government warnings across all locations.
    """
    warnings = warning_service.get_all_active_warnings()
    items = [OfficialWarningItem(**w) for w in warnings]
    return {
        "status": "success",
        "total": len(items),
        "warnings": items
    }


@router.get(
    "/current/{location_id}",
    response_model=OfficialWarningCurrentResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    summary="Get current active official government warning for a location"
)
def get_current_official_warning(
    location_id: str,
    db: SupabaseService = Depends(get_supabase_service),
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Retrieves the active official government warning for a specific location.
    Enforces location isolation. Returns state ACTIVE, NO_ACTIVE_WARNING, EXPIRED, or UNAVAILABLE.
    """
    location = db.get_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    result = warning_service.get_current_warning(location.get("id"))
    return OfficialWarningCurrentResponse(**result)


@router.get(
    "/location/{location_id}",
    response_model=OfficialWarningListResponse,
    responses={404: {"model": ErrorResponse, "description": "Location not found"}},
    summary="Get official warning history log for a location"
)
def get_location_warning_history(
    location_id: str,
    db: SupabaseService = Depends(get_supabase_service),
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Retrieves historical official government warnings issued for a location.
    """
    location = db.get_location(location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    warnings = warning_service.get_warning_history(location.get("id"))
    return OfficialWarningListResponse(
        status="success",
        total=len(warnings),
        location_id=location.get("id"),
        warnings=[OfficialWarningItem(**w) for w in warnings]
    )


@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest official government warning record"
)
def ingest_official_warning(
    payload: OfficialWarningIngestRequest,
    warning_service: OfficialWarningService = Depends(get_official_warning_service)
):
    """
    Ingests an official government warning issued by DMC, Irrigation Dept, or Met Dept.
    Performs timestamp validation and deduplication by warning_id.
    """
    try:
        saved = warning_service.ingest_warning(payload.model_dump())
        return {
            "status": "success",
            "message": "Official warning ingested successfully.",
            "warning": OfficialWarningItem(**saved)
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "code": "INVALID_WARNING_DATA", "message": str(ve)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "code": "INGESTION_FAILED", "message": str(e)}
        )
