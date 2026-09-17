"""
Weather Processing Engine.

Processes raw Open-Meteo payloads into normalized weather variables
and calibrated rainfall accumulation metrics (7-day and 30-day).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union

from services.location_service import get_location_by_id
from services.openmeteo_service import (
    fetch_forecast_data,
    fetch_archive_daily_precipitation,
    OPEN_METEO_TIMEZONE
)
from weather.weather_models import CurrentWeather, RainfallMetrics

logger = logging.getLogger("WeatherProcessor")


def extract_current_weather(raw_forecast: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and normalizes the 'current' weather block from Open-Meteo forecast JSON.
    """
    if not isinstance(raw_forecast, dict):
        return CurrentWeather(None, None, None, None, None, None, None).to_dict()

    raw_current = raw_forecast.get("current", {})
    if not isinstance(raw_current, dict):
        return CurrentWeather(None, None, None, None, None, None, None).to_dict()

    return CurrentWeather(
        temperature_c=raw_current.get("temperature_2m"),
        humidity_percent=raw_current.get("relative_humidity_2m"),
        precipitation_mm=raw_current.get("precipitation"),
        rain_mm=raw_current.get("rain"),
        weather_code=raw_current.get("weather_code"),
        wind_speed_kmh=raw_current.get("wind_speed_10m"),
        observed_at=raw_current.get("time")
    ).to_dict()


def calculate_rainfall_7d(
    hourly_times: List[str],
    hourly_precipitation: List[Any],
    expected_hours: int = 168
) -> Dict[str, Any]:
    """
    Calculates 7-day cumulative precipitation from hourly time series.

    Strict rules:
    - Uses ONLY 'precipitation' (never add 'rain' to avoid double-counting)
    - Validates expected 168 hours
    - Detects and reports missing values
    - Assigns quality status: GOOD, PARTIAL, or UNAVAILABLE
    """
    if not hourly_times or not hourly_precipitation:
        return {
            "rainfall_7d_mm": 0.0,
            "window_start": None,
            "window_end": None,
            "expected_hours": expected_hours,
            "received_hours": 0,
            "missing_hours": expected_hours,
            "status": "UNAVAILABLE",
            "definition": "rolling_168_hourly_precipitation_sum",
            "training_alignment_status": "VERIFIED"
        }

    # Extract the historical window (last `expected_hours` records before forecast horizon)
    total_points = len(hourly_precipitation)
    window_precip = hourly_precipitation[-expected_hours:] if total_points >= expected_hours else hourly_precipitation
    window_times = hourly_times[-expected_hours:] if total_points >= expected_hours else hourly_times

    valid_sum = 0.0
    missing_count = 0
    received_count = 0

    for val in window_precip:
        if val is None:
            missing_count += 1
        elif isinstance(val, (int, float)):
            if val < 0.0:
                # Negative precipitation is physically invalid; treat as missing/corrupt
                missing_count += 1
            else:
                valid_sum += float(val)
                received_count += 1
        else:
            missing_count += 1

    if received_count == 0:
        quality_status = "UNAVAILABLE"
    elif missing_count > 0 or received_count < expected_hours:
        quality_status = "PARTIAL"
    else:
        quality_status = "GOOD"

    window_start = window_times[0] if window_times else None
    window_end = window_times[-1] if window_times else None

    return {
        "rainfall_7d_mm": round(valid_sum, 2),
        "window_start": window_start,
        "window_end": window_end,
        "expected_hours": expected_hours,
        "received_hours": received_count,
        "missing_hours": missing_count + max(0, expected_hours - len(window_precip)),
        "status": quality_status,
        "definition": "rolling_168_hourly_precipitation_sum",
        "training_alignment_status": "VERIFIED"
    }


def calculate_monthly_rainfall(
    daily_times: Optional[List[str]] = None,
    daily_precipitation: Optional[List[Any]] = None,
    fallback_hourly_precip: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Calculates monthly rainfall metrics (rolling 30-day sum).

    Clearly marked as PROVISIONAL because the ML training dataset
    does not unambiguously fix rolling 30-day vs calendar month.
    """
    if daily_precipitation and daily_times:
        valid_sum = 0.0
        missing_count = 0
        received_count = 0

        for val in daily_precipitation:
            if val is None:
                missing_count += 1
            elif isinstance(val, (int, float)) and val >= 0.0:
                valid_sum += float(val)
                received_count += 1
            else:
                missing_count += 1

        window_start = daily_times[0] if daily_times else None
        window_end = daily_times[-1] if daily_times else None

        return {
            "monthly_rainfall_mm": round(valid_sum, 2),
            "window_start": window_start,
            "window_end": window_end,
            "expected_days": 30,
            "received_days": received_count,
            "missing_days": missing_count,
            "definition": "rolling_30_days_daily_precipitation_sum",
            "status": "GOOD" if missing_count == 0 else "PARTIAL",
            "training_alignment_status": "PROVISIONAL"
        }

    # Fallback estimate from available 7d data if archive endpoint unavailable
    if fallback_hourly_precip:
        recent_sum = sum(float(v) for v in fallback_hourly_precip if isinstance(v, (int, float)) and v >= 0)
        # Scaled provisional estimate based on available hours
        ratio = 720.0 / max(len(fallback_hourly_precip), 1)
        estimated_monthly = round(recent_sum * min(ratio, 4.3), 2)
        return {
            "monthly_rainfall_mm": estimated_monthly,
            "window_start": None,
            "window_end": None,
            "expected_days": 30,
            "received_days": int(len(fallback_hourly_precip) / 24),
            "missing_days": 0,
            "definition": "estimated_rolling_30_days_from_hourly",
            "status": "PARTIAL",
            "training_alignment_status": "PROVISIONAL"
        }

    return {
        "monthly_rainfall_mm": 0.0,
        "window_start": None,
        "window_end": None,
        "expected_days": 30,
        "received_days": 0,
        "missing_days": 30,
        "definition": "rolling_30_days_daily_precipitation_sum",
        "status": "UNAVAILABLE",
        "training_alignment_status": "PROVISIONAL"
    }


def get_weather_for_location(location_id: Union[int, str], use_cache: bool = True) -> Dict[str, Any]:
    """
    Coordinates end-to-end weather retrieval for a static location.

    Flow:
    location_id -> location_service -> (lat, lon) -> Open-Meteo -> WeatherProcessor -> Normalized JSON
    """
    # 1. Resolve Location
    location = get_location_by_id(location_id)
    if not location:
        return {
            "status": "data_unavailable",
            "location_id": location_id,
            "source": "Open-Meteo",
            "message": f"Location ID '{location_id}' not found in locations database."
        }

    lat = location.get("latitude")
    lon = location.get("longitude")

    if lat is None or lon is None:
        return {
            "status": "data_unavailable",
            "location_id": location_id,
            "source": "Open-Meteo",
            "message": f"Location '{location.get('place_name')}' is missing valid coordinates."
        }

    # 2. Fetch Live Forecast Data (Past 168h + Current + 24h Forecast)
    forecast_response = fetch_forecast_data(
        latitude=float(lat),
        longitude=float(lon),
        past_hours=168,
        forecast_hours=24,
        use_cache=use_cache
    )

    if forecast_response.get("status") != "success":
        return {
            "status": "data_unavailable",
            "location_id": location_id,
            "location": {
                "id": location.get("id"),
                "district": location.get("district"),
                "place_name": location.get("place_name"),
                "latitude": lat,
                "longitude": lon
            },
            "source": "Open-Meteo",
            "message": forecast_response.get("message", "Unable to retrieve forecast weather data.")
        }

    raw_forecast = forecast_response.get("raw_data", {})
    hourly_block = raw_forecast.get("hourly", {})
    hourly_times = hourly_block.get("time", [])
    hourly_precip = hourly_block.get("precipitation", [])

    # 3. Calculate 7-Day Rainfall
    rainfall_7d_result = calculate_rainfall_7d(hourly_times, hourly_precip, expected_hours=168)

    # 4. Fetch Rolling 30-Day Archive Data for Monthly Calculation
    now_sl = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    end_date_str = now_sl.strftime("%Y-%m-%d")
    start_date_str = (now_sl - timedelta(days=30)).strftime("%Y-%m-%d")

    archive_response = fetch_archive_daily_precipitation(
        latitude=float(lat),
        longitude=float(lon),
        start_date=start_date_str,
        end_date=end_date_str,
        use_cache=use_cache
    )

    if archive_response.get("status") == "success":
        raw_archive = archive_response.get("raw_data", {})
        daily_block = raw_archive.get("daily", {})
        daily_times = daily_block.get("time", [])
        daily_precip = daily_block.get("precipitation_sum", [])
        monthly_result = calculate_monthly_rainfall(daily_times, daily_precip)
    else:
        # Graceful fallback to hourly series estimation
        monthly_result = calculate_monthly_rainfall(fallback_hourly_precip=hourly_precip)

    # 5. Extract Current Weather
    current_weather = extract_current_weather(raw_forecast)

    # 6. Assemble Structured Response
    return {
        "status": "success",
        "location": {
            "id": location.get("id"),
            "district": location.get("district"),
            "place_name": location.get("place_name"),
            "latitude": lat,
            "longitude": lon
        },
        "current": current_weather,
        "rainfall": {
            "rainfall_7d_mm": rainfall_7d_result["rainfall_7d_mm"],
            "monthly_rainfall_mm": monthly_result["monthly_rainfall_mm"],
            "rainfall_7d_definition": rainfall_7d_result["definition"],
            "monthly_rainfall_definition": monthly_result["definition"],
            "rainfall_7d_status": rainfall_7d_result["training_alignment_status"],
            "monthly_rainfall_status": monthly_result["training_alignment_status"],
            "window_start": rainfall_7d_result["window_start"],
            "window_end": rainfall_7d_result["window_end"],
            "expected_hours": rainfall_7d_result["expected_hours"],
            "received_hours": rainfall_7d_result["received_hours"],
            "missing_hours": rainfall_7d_result["missing_hours"],
            "data_quality": rainfall_7d_result["status"]
        },
        "forecast": {
            "available": bool(raw_forecast.get("hourly", {}).get("time")),
            "forecast_hours_available": 24
        },
        "source": {
            "provider": "Open-Meteo",
            "forecast_endpoint": forecast_response.get("endpoint"),
            "archive_endpoint": archive_response.get("endpoint"),
            "retrieved_at": forecast_response.get("retrieved_at")
        }
    }
