"""
Phase 3: Live Open-Meteo Weather API Integration Test

Validates:
1. Dynamic coordinate resolution from location_service (Location ID 7: Ratnapura)
2. Open-Meteo Forecast API request construction with past_hours=168, forecast_hours=24
3. HTTP 200 response and JSON parsing
4. Presence and validity of 'current' and 'hourly' weather variables
5. Extraction and calculation of rainfall_7d_mm and monthly_rainfall_mm
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.location_service import get_location_by_id
from services.openmeteo_service import build_forecast_params, fetch_forecast_data
from weather.weather_processor import get_weather_for_location


def test_openmeteo_connection():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 3 Open-Meteo Connection Test")
    print("=" * 60)

    # 1. Resolve Location from Phase 2
    print("\n[1] Resolving test location from location_service (ID = 7)...")
    loc = get_location_by_id(7)
    assert loc is not None, "Location ID 7 (Ratnapura) not found in locations.json"
    lat = loc["latitude"]
    lon = loc["longitude"]
    place = loc["place_name"]
    district = loc["district"]
    print(f"  ✓ Location: {place} ({district})")
    print(f"  ✓ Coordinates: Lat {lat}, Lon {lon}")

    # 2. Inspect Request Parameters
    print("\n[2] Constructing Open-Meteo Forecast query parameters...")
    params = build_forecast_params(lat, lon, past_hours=168, forecast_hours=24)
    print(f"  ✓ Latitude: {params['latitude']}")
    print(f"  ✓ Longitude: {params['longitude']}")
    print(f"  ✓ Past hours: {params['past_hours']}")
    print(f"  ✓ Forecast hours: {params['forecast_hours']}")
    print(f"  ✓ Timezone: {params['timezone']}")
    print(f"  ✓ Precipitation unit: {params['precipitation_unit']}")

    # 3. Fetch Live Data
    print("\n[3] Sending live request to Open-Meteo Forecast API...")
    resp = fetch_forecast_data(lat, lon, past_hours=168, forecast_hours=24, use_cache=False)
    assert resp.get("status") == "success", f"API request failed: {resp.get('message')}"
    print(f"  ✓ HTTP Response Status: Success")
    print(f"  ✓ Source Endpoint: {resp.get('endpoint')}")
    print(f"  ✓ Retrieved At: {resp.get('retrieved_at')}")

    raw = resp.get("raw_data", {})
    assert "current" in raw, "'current' block missing in response"
    assert "hourly" in raw, "'hourly' block missing in response"
    print("  ✓ 'current' and 'hourly' blocks verified.")

    # 4. Parse Current Weather
    current = raw.get("current", {})
    print("\n[4] Current Weather Observation:")
    print(f"  - Temperature: {current.get('temperature_2m')} °C")
    print(f"  - Relative Humidity: {current.get('relative_humidity_2m')} %")
    print(f"  - Precipitation: {current.get('precipitation')} mm")
    print(f"  - Rain: {current.get('rain')} mm")
    print(f"  - Weather Code: {current.get('weather_code')}")
    print(f"  - Wind Speed: {current.get('wind_speed_10m')} km/h")
    print(f"  - Observed At: {current.get('time')}")

    # 5. Verify Full Location Weather Processing
    print("\n[5] Executing full get_weather_for_location(7) pipeline...")
    weather_result = get_weather_for_location(7, use_cache=False)
    assert weather_result.get("status") == "success", f"Processing failed: {weather_result.get('message')}"

    rainfall = weather_result.get("rainfall", {})
    print("\n[6] Calculated Rainfall Metrics:")
    print(f"  - 7-Day Rainfall: {rainfall.get('rainfall_7d_mm')} mm (Status: {rainfall.get('rainfall_7d_status')}, Quality: {rainfall.get('data_quality')})")
    print(f"  - Monthly Rainfall: {rainfall.get('monthly_rainfall_mm')} mm (Status: {rainfall.get('monthly_rainfall_status')})")
    print(f"  - Window Start: {rainfall.get('window_start')}")
    print(f"  - Window End: {rainfall.get('window_end')}")
    print(f"  - Expected Hours: {rainfall.get('expected_hours')}, Received: {rainfall.get('received_hours')}, Missing: {rainfall.get('missing_hours')}")

    print("\n" + "=" * 60)
    print("OPEN-METEO CONNECTION TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_openmeteo_connection()
    sys.exit(0 if success else 1)
