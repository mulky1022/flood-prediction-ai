"""
Phase 2: Static Location Service Test Suite

Tests:
1. Load all locations from location_service.
2. Get one known location by ID.
3. Get locations filtered by district.
4. Search locations by query string.
5. Verify required fields in returned objects.
6. Verify coordinate validity.
7. Verify returned object schema and types.
"""

import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.location_service import (
    load_locations,
    get_all_locations,
    get_location_by_id,
    get_locations_by_district,
    search_locations,
)


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 2 Location Service Test")
    print("=" * 60)

    # ---------------------------------------------------------
    # Test 1: Load All Locations
    # ---------------------------------------------------------
    print("\n[TEST 1] Loading all locations...")
    locations = get_all_locations()
    assert isinstance(locations, list), "Expected list of locations"
    assert len(locations) > 0, "Location list is empty"
    print(f"  ✓ Loaded {len(locations)} locations successfully.")

    # ---------------------------------------------------------
    # Test 2: Get Location by ID
    # ---------------------------------------------------------
    print("\n[TEST 2] Fetching known location by ID (ID = 7, Ratnapura)...")
    loc_7 = get_location_by_id(7)
    assert loc_7 is not None, "Location ID 7 not found"
    assert loc_7.get("district") == "Ratnapura", f"Expected district Ratnapura, got {loc_7.get('district')}"
    assert loc_7.get("record_id") == "LOC-007", f"Expected LOC-007, got {loc_7.get('record_id')}"
    print(f"  ✓ Found location {loc_7['id']}: {loc_7['place_name']} ({loc_7['district']})")

    # String record_id lookup test
    loc_by_rec_id = get_location_by_id("LOC-001")
    assert loc_by_rec_id is not None, "Lookup by record_id LOC-001 failed"
    assert loc_by_rec_id.get("district") == "Colombo", "Expected Colombo for LOC-001"
    print(f"  ✓ Found location by record_id LOC-001: {loc_by_rec_id['place_name']}")

    # ---------------------------------------------------------
    # Test 3: Get Locations by District
    # ---------------------------------------------------------
    print("\n[TEST 3] Fetching locations by district ('Gampaha')...")
    gampaha_locs = get_locations_by_district("Gampaha")
    assert len(gampaha_locs) >= 2, f"Expected at least 2 locations for Gampaha, got {len(gampaha_locs)}"
    for gl in gampaha_locs:
        assert gl.get("district") == "Gampaha", "Mismatched district returned"
    print(f"  ✓ Found {len(gampaha_locs)} monitoring locations in Gampaha.")

    # Case-insensitivity check
    gampaha_lower = get_locations_by_district("gampaha")
    assert len(gampaha_lower) == len(gampaha_locs), "Case-insensitive lookup failed"
    print("  ✓ Case-insensitive district filtering verified.")

    # ---------------------------------------------------------
    # Test 4: Search Locations
    # ---------------------------------------------------------
    print("\n[TEST 4] Searching locations by query ('Kelani')...")
    search_results = search_locations("Kelani")
    assert len(search_results) >= 2, f"Expected at least 2 search matches for 'Kelani', got {len(search_results)}"
    for r in search_results:
        print(f"    - [{r.get('district')}] {r.get('place_name')}")
    print(f"  ✓ Search returned {len(search_results)} matching locations.")

    # ---------------------------------------------------------
    # Test 5: Validate Required Fields
    # ---------------------------------------------------------
    print("\n[TEST 5] Validating required fields across all records...")
    required_keys = ["id", "record_id", "district", "place_name", "latitude", "longitude"]
    for idx, loc in enumerate(locations):
        for k in required_keys:
            assert k in loc, f"Record {idx} missing required key: {k}"
            assert loc[k] is not None, f"Record {idx} key {k} is None"
    print(f"  ✓ All {len(locations)} records have required fields populated.")

    # ---------------------------------------------------------
    # Test 6: Validate Coordinates
    # ---------------------------------------------------------
    print("\n[TEST 6] Validating coordinate ranges (Sri Lanka bounds)...")
    for loc in locations:
        lat = loc["latitude"]
        lon = loc["longitude"]
        assert 5.8 <= lat <= 10.0, f"Latitude {lat} out of Sri Lanka range for {loc['place_name']}"
        assert 79.4 <= lon <= 82.0, f"Longitude {lon} out of Sri Lanka range for {loc['place_name']}"
    print(f"  ✓ All {len(locations)} records have verified Sri Lankan coordinates.")

    # ---------------------------------------------------------
    # Test 7: Verify Returned Object Schema
    # ---------------------------------------------------------
    print("\n[TEST 7] Verifying object schema and numeric types...")
    sample = locations[0]
    expected_types = {
        "id": int,
        "record_id": str,
        "district": str,
        "place_name": str,
        "latitude": float,
        "longitude": float,
        "elevation_m": (int, float),
        "distance_to_river_m": (int, float),
    }
    for field, exp_type in expected_types.items():
        assert isinstance(sample[field], exp_type), f"Field {field} type mismatch in sample: {type(sample[field])}"
    print("  ✓ Schema and type integrity verified.")

    print("\n" + "=" * 60)
    print("PHASE 2 LOCATION TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
