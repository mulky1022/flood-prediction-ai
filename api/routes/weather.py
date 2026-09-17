"""
Weather API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas.weather import WeatherResponse
from api.schemas.common import ErrorResponse
from api.dependencies import get_db, SupabaseService
from weather.weather_processor import get_weather_for_location

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get(
    "/{location_id}",
    response_model=WeatherResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Location not found"},
        503: {"model": ErrorResponse, "description": "Weather service unavailable"}
    }
)
def get_weather(
    location_id: str,
    db: SupabaseService = Depends(get_db)
):
    """
    Retrieves live Open-Meteo current observations and rolling 7-day/30-day precipitation metrics.
    """
    # Verify location exists
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "LOCATION_NOT_FOUND", "message": f"Location '{location_id}' not found."}
        )

    # Fetch and process live weather
    weather_result = get_weather_for_location(loc.get("id"), use_cache=True)

    if weather_result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "code": "WEATHER_UNAVAILABLE",
                "message": weather_result.get("message", "Unable to retrieve live weather.")
            }
        )

    # Persist weather observation asynchronously or synchronously in db service
    db.save_weather_observation(weather_result)

    return weather_result
