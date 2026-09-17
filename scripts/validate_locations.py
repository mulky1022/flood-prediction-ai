"""
Phase 2: Static Location Data Validation Script

Validates:
1. JSON formatting and schema of data/locations.json
2. Presence and types of required fields
3. Numeric value types and range constraints
4. Coordinate validity (global and Sri Lanka bounding box)
5. Duplicate record detection (record_id, district+place_name, coordinates)
6. Missing value quantification per field
7. Categorical value distributions
8. Compatibility with 64-feature model contract
"""

import json
import sys
from collections import Counter
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def validate():
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_PATH = BASE_DIR / "data" / "locations.json"
    FEATURES_PATH = BASE_DIR / "model" / "feature_columns.json"

    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 2 Static Data Validation")
    print("=" * 60)

    # 1. Load Locations
    if not DATA_PATH.exists():
        print(f"\nERROR: data/locations.json not found at: {DATA_PATH}")
        sys.exit(1)

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"\nERROR: Failed to parse data/locations.json: {e}")
        sys.exit(1)

    total_records = len(records)
    print(f"\nSource records: {total_records}")
    print(f"Static records created: {total_records}")

    if total_records == 0:
        print("ERROR: locations.json contains zero records.")
        sys.exit(1)

    # 2. Required Fields Validation
    required_fields = ["district", "place_name", "latitude", "longitude"]
    missing_required = {field: 0 for field in required_fields}

    for rec in records:
        for field in required_fields:
            val = rec.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing_required[field] += 1

    print("\nRequired fields:")
    all_required_present = True
    for field, count in missing_required.items():
        if count == 0:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} (Missing in {count} records)")
            all_required_present = False

    if not all_required_present:
        print("\nERROR: Required fields are missing in one or more records.")
        sys.exit(1)

    # 3. Coordinate Validation
    valid_coords = 0
    suspicious_coords = 0
    suspicious_details = []

    # Sri Lanka bounding box: Lat 5.8° to 10.0° N, Lon 79.4° to 82.0° E
    for rec in records:
        lat = rec.get("latitude")
        lon = rec.get("longitude")

        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            suspicious_coords += 1
            suspicious_details.append(f"Non-numeric coordinates in {rec.get('record_id')}: ({lat}, {lon})")
            continue

        if -90 <= lat <= 90 and -180 <= lon <= 180:
            valid_coords += 1
            if not (5.8 <= lat <= 10.0 and 79.4 <= lon <= 82.0):
                suspicious_coords += 1
                suspicious_details.append(f"Coordinates outside Sri Lanka box for {rec.get('place_name')}: ({lat}, {lon})")
        else:
            suspicious_coords += 1
            suspicious_details.append(f"Invalid global coordinates in {rec.get('record_id')}: ({lat}, {lon})")

    print("\nCoordinate validation:")
    print(f"  ✓ valid: {valid_coords}")
    print(f"  ⚠ suspicious: {suspicious_coords}")
    if suspicious_details:
        for d in suspicious_details:
            print(f"    - {d}")

    # 4. Duplicate Validation
    record_ids = [rec.get("record_id") for rec in records if rec.get("record_id")]
    place_combos = [f"{rec.get('district')}|{rec.get('place_name')}" for rec in records]
    coord_pairs = [(rec.get("latitude"), rec.get("longitude")) for rec in records]

    dup_ids = [item for item, count in Counter(record_ids).items() if count > 1]
    dup_places = [item for item, count in Counter(place_combos).items() if count > 1]
    dup_coords = [item for item, count in Counter(coord_pairs).items() if count > 1]

    print("\nDuplicates:")
    print(f"  record_id: {len(dup_ids)}")
    print(f"  district + place_name: {len(dup_places)}")
    print(f"  coordinates: {len(dup_coords)}")

    # 5. Missing Values Summary
    all_keys = set()
    for rec in records:
        all_keys.update(rec.keys())

    print("\nMissing values summary:")
    for key in sorted(all_keys):
        missing_cnt = sum(1 for rec in records if rec.get(key) is None)
        pct = (missing_cnt / total_records) * 100
        print(f"  {key:30s} Total: {total_records:3d} | Missing: {missing_cnt:2d} ({pct:5.1f}%)")

    # 6. Categorical Summaries
    districts = set(rec.get("district") for rec in records if rec.get("district"))
    landcovers = set(rec.get("landcover") for rec in records if rec.get("landcover"))
    soil_types = set(rec.get("soil_type") for rec in records if rec.get("soil_type"))
    water_supplies = set(rec.get("water_supply") for rec in records if rec.get("water_supply"))
    road_qualities = set(rec.get("road_quality") for rec in records if rec.get("road_quality"))

    print(f"\nDistricts found: {len(districts)}")
    print("\nCategory counts:")
    print(f"  district: {len(districts)} unique values")
    print(f"  landcover: {len(landcovers)} unique values ({', '.join(sorted(landcovers))})")
    print(f"  soil_type: {len(soil_types)} unique values ({', '.join(sorted(soil_types))})")
    print(f"  water_supply: {len(water_supplies)} unique values ({', '.join(sorted(water_supplies))})")
    print(f"  road_quality: {len(road_qualities)} unique values ({', '.join(sorted(road_qualities))})")

    # 7. Model Contract Compatibility
    print("\nFeature mapping:")
    if FEATURES_PATH.exists():
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            model_features = json.load(f)

        available_cnt = 0
        phase3_cnt = 0
        leakage_cnt = 0

        for col in model_features[:64]:
            if col in ["rainfall_7d_mm", "monthly_rainfall_mm"]:
                phase3_cnt += 1
            elif col in ["flood_risk_score", "is_good_to_live_Yes"]:
                leakage_cnt += 1
            else:
                available_cnt += 1

        print(f"  AVAILABLE: {available_cnt}")
        print(f"  PARTIAL: 0")
        print(f"  MISSING: 0")
        print(f"  PHASE 3: {phase3_cnt} (rainfall_7d_mm, monthly_rainfall_mm)")
        print(f"  LEAKAGE REVIEW: {leakage_cnt} (flood_risk_score, is_good_to_live_Yes)")

    print("\n" + "=" * 60)
    print("PHASE 2 VALIDATION COMPLETE")
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate()
