"""
Phase 5: Supabase Database Service Unit & Integration Test Suite

Tests:
1. Database Service Initialization & Connection Check
2. Location retrieval (All locations + Single location by ID)
3. Weather observation saving & validation
4. Prediction record persistence & validation
5. Prediction history query with pagination
6. Latest prediction lookup
"""

import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.supabase_service import get_supabase_service


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 5 Database Service Test")
    print("=" * 60)

    # 1. Initialize Service
    print("\n[TEST 1] Initializing SupabaseService...")
    db = get_supabase_service()
    print(f"  ✓ Connected to Remote Supabase: {db.is_connected}")
    print(f"  ✓ Mode: {'REMOTE_SUPABASE' if db.is_connected else 'LOCAL_FALLBACK_STORE'}")

    # 2. Location Retrieval
    print("\n[TEST 2] Fetching locations through database service...")
    locations = db.get_locations()
    assert len(locations) >= 33, f"Expected at least 33 locations, got {len(locations)}"
    print(f"  ✓ Retrieved {len(locations)} location records.")

    loc_7 = db.get_location(7)
    assert loc_7 is not None, "Location ID 7 not found"
    assert loc_7["district"] == "Ratnapura"
    print(f"  ✓ Single lookup verified: Location {loc_7['id']} = {loc_7['place_name']}")

    # 3. Save Weather Observation
    print("\n[TEST 3] Persisting weather observation...")
    mock_weather = {
        "location": {"id": 7},
        "current": {
            "temperature_c": 24.5,
            "humidity_percent": 92.0,
            "precipitation_mm": 1.2,
            "rain_mm": 1.2,
            "weather_code": 61,
            "wind_speed_kmh": 6.5,
            "observed_at": "2026-09-16T23:00:00+05:30"
        },
        "rainfall": {
            "rainfall_7d_mm": 142.0,
            "monthly_rainfall_mm": 310.0,
            "data_quality": "GOOD",
            "window_start": "2026-09-09T23:00",
            "window_end": "2026-09-16T23:00",
            "expected_hours": 168,
            "received_hours": 168,
            "missing_hours": 0
        },
        "source": {"provider": "Open-Meteo"}
    }
    save_weather_res = db.save_weather_observation(mock_weather)
    assert save_weather_res["status"] == "success"
    print(f"  ✓ Weather persisted successfully: {save_weather_res.get('persisted_to')}")

    # 4. Save Prediction Record
    print("\n[TEST 4] Persisting ML prediction result...")
    mock_prediction = {
        "status": "success",
        "ready_for_prediction": True,
        "location": {"id": 7, "district": "Ratnapura", "place_name": "Ratnapura Town"},
        "prediction": {
            "class": 1,
            "flood_probability": 0.7650,
            "non_flood_probability": 0.2350
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0", "feature_count": 64},
        "data_quality": {"weather_quality": "GOOD", "missing_features": [], "invalid_features": []},
        "input_audit": {"rainfall_7d_mm": 142.0, "monthly_rainfall_mm": 310.0, "weather_source": "Open-Meteo"}
    }
    save_pred_res = db.save_prediction(mock_prediction)
    assert save_pred_res["status"] == "success"
    print(f"  ✓ Prediction persisted successfully: {save_pred_res.get('persisted_to')}")

    # 5. Query Prediction History
    print("\n[TEST 5] Querying prediction history for Location ID 7...")
    history = db.get_prediction_history(7, limit=5)
    assert len(history) >= 1, "Expected at least 1 prediction in history"
    print(f"  ✓ Found {len(history)} historical prediction records for Location 7.")
    print(f"    - Latest Class: {history[0]['prediction_class']}")
    print(f"    - Latest Prob: {float(history[0]['flood_probability']) * 100:.2f}%")

    # 6. Query Latest Prediction
    print("\n[TEST 6] Querying latest prediction helper...")
    latest = db.get_latest_prediction(7)
    assert latest is not None
    assert latest["location_id"] == 7
    print(f"  ✓ Latest prediction helper verified: P(Flood) = {float(latest['flood_probability']) * 100:.2f}%")

    print("\n" + "=" * 60)
    print("DATABASE SERVICE TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
