"""
Phase 3: Deterministic Weather Processing Test Suite

Tests:
1. Deterministic 168-hour rainfall aggregation (168h @ 1.0mm = 168.0mm)
2. Deterministic 24-hour rainfall aggregation (24h @ 2.0mm = 48.0mm)
3. Missing data detection and partial status assignment (1.0 + None + 2.0 = 3.0mm, PARTIAL)
4. Invalid/corrupt data handling (negative values, strings, non-numeric types)
5. Location integration pipeline using Phase 2 location data
6. Failure handling and graceful fallback for invalid locations
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from weather.weather_processor import (
    extract_current_weather,
    calculate_rainfall_7d,
    calculate_monthly_rainfall,
    get_weather_for_location
)


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 3 Weather Processing Test Suite")
    print("=" * 60)

    # -------------------------------------------------------------
    # Test 1: Deterministic 168-Hour Aggregation
    # -------------------------------------------------------------
    print("\n[TEST 1] Deterministic 168-Hour Rainfall Aggregation...")
    base_time = datetime(2026, 9, 10, 0, 0)
    times_168 = [(base_time + timedelta(hours=i)).isoformat() for i in range(168)]
    precip_168 = [1.0 for _ in range(168)]  # Exactly 1.0mm per hour

    res_168 = calculate_rainfall_7d(times_168, precip_168, expected_hours=168)
    assert res_168["rainfall_7d_mm"] == 168.0, f"Expected 168.0mm, got {res_168['rainfall_7d_mm']}"
    assert res_168["expected_hours"] == 168
    assert res_168["received_hours"] == 168
    assert res_168["missing_hours"] == 0
    assert res_168["status"] == "GOOD"
    assert res_168["training_alignment_status"] == "VERIFIED"
    print(f"  ✓ 168h aggregation exact match: {res_168['rainfall_7d_mm']} mm (Quality: {res_168['status']})")

    # -------------------------------------------------------------
    # Test 2: Deterministic 24-Hour Aggregation
    # -------------------------------------------------------------
    print("\n[TEST 2] Deterministic 24-Hour Rainfall Aggregation...")
    times_24 = [(base_time + timedelta(hours=i)).isoformat() for i in range(24)]
    precip_24 = [2.0 for _ in range(24)]  # Exactly 2.0mm per hour

    res_24 = calculate_rainfall_7d(times_24, precip_24, expected_hours=24)
    assert res_24["rainfall_7d_mm"] == 48.0, f"Expected 48.0mm, got {res_24['rainfall_7d_mm']}"
    assert res_24["received_hours"] == 24
    assert res_24["status"] == "GOOD"
    print(f"  ✓ 24h aggregation exact match: {res_24['rainfall_7d_mm']} mm (Quality: {res_24['status']})")

    # -------------------------------------------------------------
    # Test 3: Missing Data Detection
    # -------------------------------------------------------------
    print("\n[TEST 3] Missing Data Detection (None values in time series)...")
    times_3 = ["2026-09-16T10:00", "2026-09-16T11:00", "2026-09-16T12:00"]
    precip_3 = [1.5, None, 2.5]

    res_missing = calculate_rainfall_7d(times_3, precip_3, expected_hours=3)
    assert res_missing["rainfall_7d_mm"] == 4.0, f"Expected 4.0mm valid sum, got {res_missing['rainfall_7d_mm']}"
    assert res_missing["received_hours"] == 2
    assert res_missing["missing_hours"] == 1
    assert res_missing["status"] == "PARTIAL", f"Expected PARTIAL, got {res_missing['status']}"
    print(f"  ✓ Missing value handled: Sum={res_missing['rainfall_7d_mm']}mm, Missing={res_missing['missing_hours']}h (Status: {res_missing['status']})")

    # -------------------------------------------------------------
    # Test 4: Invalid and Negative Data Handling
    # -------------------------------------------------------------
    print("\n[TEST 4] Invalid Data Handling (Negative & Non-numeric inputs)...")
    times_invalid = ["2026-09-16T01:00", "2026-09-16T02:00", "2026-09-16T03:00", "2026-09-16T04:00"]
    precip_invalid = [5.0, -99.0, "CORRUPT_STR", 3.0]

    res_invalid = calculate_rainfall_7d(times_invalid, precip_invalid, expected_hours=4)
    # Valid elements: 5.0 and 3.0 = 8.0mm. Negative and string counted as missing.
    assert res_invalid["rainfall_7d_mm"] == 8.0, f"Expected 8.0mm, got {res_invalid['rainfall_7d_mm']}"
    assert res_invalid["received_hours"] == 2
    assert res_invalid["missing_hours"] == 2
    assert res_invalid["status"] == "PARTIAL"
    print(f"  ✓ Corrupt/negative values safely excluded: Sum={res_invalid['rainfall_7d_mm']}mm, Missing={res_invalid['missing_hours']}h")

    # -------------------------------------------------------------
    # Test 5: Monthly Rolling 30-Day Aggregation
    # -------------------------------------------------------------
    print("\n[TEST 5] Monthly Rolling 30-Day Calculation...")
    daily_times = [(base_time + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
    daily_precip = [10.0 for _ in range(30)]  # 10.0mm per day for 30 days = 300.0mm

    res_monthly = calculate_monthly_rainfall(daily_times, daily_precip)
    assert res_monthly["monthly_rainfall_mm"] == 300.0
    assert res_monthly["training_alignment_status"] == "PROVISIONAL"
    assert res_monthly["status"] == "GOOD"
    print(f"  ✓ Monthly aggregation exact match: {res_monthly['monthly_rainfall_mm']} mm (Status: {res_monthly['training_alignment_status']})")

    # -------------------------------------------------------------
    # Test 6: Location Integration (Phase 2 Location Lookup)
    # -------------------------------------------------------------
    print("\n[TEST 6] Location Integration Pipeline (Location ID 1: Colombo Kolonnawa)...")
    colombo_weather = get_weather_for_location(1, use_cache=True)
    assert colombo_weather["status"] == "success", f"Colombo fetch failed: {colombo_weather.get('message')}"
    assert colombo_weather["location"]["district"] == "Colombo"
    assert "temperature_c" in colombo_weather["current"]
    assert "rainfall_7d_mm" in colombo_weather["rainfall"]
    print(f"  ✓ Successfully fetched and processed live weather for: {colombo_weather['location']['place_name']}")
    print(f"    - Current Temp: {colombo_weather['current']['temperature_c']} °C")
    print(f"    - Rainfall 7d: {colombo_weather['rainfall']['rainfall_7d_mm']} mm")

    # -------------------------------------------------------------
    # Test 7: Non-existent Location Fail-Safe Handling
    # -------------------------------------------------------------
    print("\n[TEST 7] Invalid Location Fail-Safe Error Handling (ID 9999)...")
    invalid_loc_weather = get_weather_for_location(9999)
    assert invalid_loc_weather["status"] == "data_unavailable", "Expected data_unavailable status"
    assert "not found" in invalid_loc_weather["message"].lower()
    print(f"  ✓ Graceful error returned: {invalid_loc_weather['message']}")

    print("\n" + "=" * 60)
    print("ALL WEATHER PROCESSING TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
