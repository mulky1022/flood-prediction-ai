"""
Open-Meteo Weather Service Client.

Handles HTTP communication with Open-Meteo APIs:
1. Forecast API (Current + 168h Hourly Past + 24h Forecast)
2. Archive API (Historical daily precipitation for monthly rolling aggregation)

Features:
- Configurable timeouts and retries
- Asia/Colombo timezone normalization
- Local file-based caching for development efficiency
- Detailed error handling without exposing secrets or crashes
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union
import httpx

logger = logging.getLogger("OpenMeteoService")

# API Configuration Constants
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_HISTORICAL_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

OPEN_METEO_TIMEZONE = "Asia/Colombo"
OPEN_METEO_TIMEOUT_SECONDS = 20.0
OPEN_METEO_MAX_RETRIES = 2

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache" / "weather"
CACHE_EXPIRY_SECONDS = 1800  # 30 minutes cache for dev


def _get_cache_path(cache_key: str) -> Path:
    """Returns filesystem path for a given cache key."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hashed = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{hashed}.json"


def _read_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Reads valid cached response if not expired."""
    try:
        cache_file = _get_cache_path(cache_key)
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            cached_time = cached_data.get("_cached_at_epoch", 0)
            if time.time() - cached_time < CACHE_EXPIRY_SECONDS:
                logger.info(f"Cache hit for key: {cache_key}")
                return cached_data.get("data")
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    return None


def _write_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Writes response payload to local cache."""
    try:
        cache_file = _get_cache_path(cache_key)
        payload = {
            "_cached_at_epoch": time.time(),
            "_cached_at_iso": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def build_forecast_params(
    latitude: float,
    longitude: float,
    past_hours: int = 168,
    forecast_hours: int = 24
) -> Dict[str, Any]:
    """
    Constructs exact query parameters for the Open-Meteo Forecast API.
    """
    return {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "soil_moisture_0_to_7cm"
        ]),
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m"
        ]),
        "past_hours": past_hours,
        "forecast_hours": forecast_hours,
        "timezone": OPEN_METEO_TIMEZONE,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601"
    }


def fetch_forecast_data(
    latitude: float,
    longitude: float,
    past_hours: int = 168,
    forecast_hours: int = 24,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Synchronously retrieves live and recent hourly weather from Open-Meteo Forecast API.
    """
    # 1. Parameter Validation
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return {
            "status": "error",
            "error_type": "invalid_coordinates",
            "message": f"Invalid coordinates: ({latitude}, {longitude})"
        }

    params = build_forecast_params(latitude, longitude, past_hours, forecast_hours)
    cache_key = f"forecast_{latitude:.4f}_{longitude:.4f}_{past_hours}_{forecast_hours}"

    if use_cache:
        cached = _read_cache(cache_key)
        if cached:
            return cached

    # 2. HTTP Request with Retry Handling
    last_error = None
    for attempt in range(1, OPEN_METEO_MAX_RETRIES + 2):
        try:
            with httpx.Client(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
                response = client.get(OPEN_METEO_FORECAST_URL, params=params)

                if response.status_code == 400:
                    return {
                        "status": "error",
                        "error_type": "bad_request",
                        "http_status": 400,
                        "message": "Open-Meteo request configuration error: Bad Request"
                    }
                elif response.status_code == 429:
                    return {
                        "status": "error",
                        "error_type": "rate_limit",
                        "http_status": 429,
                        "message": "Open-Meteo rate limit exceeded"
                    }

                response.raise_for_status()
                data = response.json()

                result = {
                    "status": "success",
                    "source": "Open-Meteo Forecast API",
                    "endpoint": OPEN_METEO_FORECAST_URL,
                    "retrieved_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
                    "params": params,
                    "raw_data": data
                }

                if use_cache:
                    _write_cache(cache_key, result)

                return result

        except httpx.TimeoutException as e:
            last_error = f"Open-Meteo request timed out after {OPEN_METEO_TIMEOUT_SECONDS}s"
            logger.warning(f"Timeout on attempt {attempt}: {e}")
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code} error from Open-Meteo: {e}"
            logger.warning(f"HTTPStatusError on attempt {attempt}: {e}")
        except Exception as e:
            last_error = f"Network/Connection error: {str(e)}"
            logger.warning(f"Request error on attempt {attempt}: {e}")

        if attempt <= OPEN_METEO_MAX_RETRIES:
            time.sleep(0.5 * attempt)

    return {
        "status": "data_unavailable",
        "error_type": "network_failure",
        "message": f"Unable to retrieve weather data: {last_error}"
    }


def fetch_archive_daily_precipitation(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Synchronously retrieves historical daily precipitation totals from Open-Meteo Archive API.
    """
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return {
            "status": "error",
            "error_type": "invalid_coordinates",
            "message": f"Invalid coordinates: ({latitude}, {longitude})"
        }

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum",
        "timezone": OPEN_METEO_TIMEZONE,
        "precipitation_unit": "mm",
        "timeformat": "iso8601"
    }

    cache_key = f"archive_{latitude:.4f}_{longitude:.4f}_{start_date}_{end_date}"
    if use_cache:
        cached = _read_cache(cache_key)
        if cached:
            return cached

    last_error = None
    for attempt in range(1, OPEN_METEO_MAX_RETRIES + 2):
        try:
            with httpx.Client(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
                response = client.get(OPEN_METEO_ARCHIVE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                result = {
                    "status": "success",
                    "source": "Open-Meteo Archive API",
                    "endpoint": OPEN_METEO_ARCHIVE_URL,
                    "retrieved_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
                    "params": params,
                    "raw_data": data
                }

                if use_cache:
                    _write_cache(cache_key, result)

                return result

        except Exception as e:
            last_error = str(e)
            if attempt <= OPEN_METEO_MAX_RETRIES:
                time.sleep(0.5 * attempt)

    return {
        "status": "data_unavailable",
        "error_type": "archive_failure",
        "message": f"Unable to retrieve archive weather data: {last_error}"
    }
