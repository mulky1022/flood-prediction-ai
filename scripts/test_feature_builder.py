"""
Phase 4: Feature Builder Unit Test Suite

Tests:
1. Full 64-feature vector generation from valid location and weather objects.
2. Exact column count and ordering matching model/feature_columns.json.
3. Categorical one-hot encoding verification (e.g. district_Ratnapura = 1.0, other districts = 0.0).
4. Structural one-hot zeros vs missing source value distinction.
5. Detection of missing static features (e.g., elevation_m = None).
6. Detection of missing live weather metrics (e.g., rainfall_7d_mm = None).
7. Unknown category detection.
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
from services.feature_builder import build_feature_dataframe, FEATURE_COLUMNS


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 4 Feature Builder Test Suite")
    print("=" * 60)

    # 1. Test Valid End-to-End Feature Assembly (Ratnapura ID 7)
    print("\n[TEST 1] Assembling features from valid static location and mock weather...")
    loc_7 = get_location_by_id(7)
    assert loc_7 is not None, "Location ID 7 not found"

    mock_weather = {
        "status": "success",
        "current": {"temperature_c": 26.5, "precipitation_mm": 2.0},
        "rainfall": {
            "rainfall_7d_mm": 165.0,
            "monthly_rainfall_mm": 380.0,
            "data_quality": "GOOD"
        }
    }

    df, report = build_feature_dataframe(loc_7, mock_weather)

    assert df.shape == (1, 64), f"Expected shape (1, 64), got {df.shape}"
    assert list(df.columns) == FEATURE_COLUMNS, "Columns do not match feature contract order"
    assert report["ready_for_prediction"] is True, "Report should be ready_for_prediction"
    assert len(report["missing_features"]) == 0, "No features should be missing"
    assert len(report["invalid_features"]) == 0, "No features should be invalid"
    assert len(report["unknown_categories"]) == 0, "No categories should be unknown"
    print(f"  ✓ Output shape verified: {df.shape}")
    print(f"  ✓ 64 contract columns aligned in exact order.")
    print(f"  ✓ Quality gate: ready_for_prediction = {report['ready_for_prediction']}")

    # 2. Test One-Hot Categorical Encoding
    print("\n[TEST 2] Verifying one-hot categorical encoding for Ratnapura...")
    assert df["district_Ratnapura"].iloc[0] == 1.0, "Expected district_Ratnapura == 1.0"
    assert df["district_Colombo"].iloc[0] == 0.0, "Expected district_Colombo == 0.0"
    assert df["district_Galle"].iloc[0] == 0.0, "Expected district_Galle == 0.0"
    assert df["landcover_Urban"].iloc[0] == 1.0, "Expected landcover_Urban == 1.0"
    assert df["soil_type_Silty"].iloc[0] == 1.0, "Expected soil_type_Silty == 1.0"
    print("  ✓ District, landcover, and soil_type one-hot encoding verified.")

    # 3. Test Structural Zero vs Missing Source Value Distinction
    print("\n[TEST 3] Testing missing static numerical source detection...")
    loc_corrupt = loc_7.copy()
    loc_corrupt["elevation_m"] = None  # Missing source value

    df_corrupt, report_corrupt = build_feature_dataframe(loc_corrupt, mock_weather)
    assert "elevation_m" in report_corrupt["missing_features"], "elevation_m should be flagged missing"
    assert report_corrupt["ready_for_prediction"] is False, "Corrupted record must block prediction"
    print(f"  ✓ Missing source field caught: {report_corrupt['missing_features']} (ready = {report_corrupt['ready_for_prediction']})")

    # 4. Test Missing Live Weather Detection
    print("\n[TEST 4] Testing missing live weather metrics detection...")
    empty_weather = {"rainfall": {}}
    df_no_weather, report_no_weather = build_feature_dataframe(loc_7, empty_weather)
    assert "rainfall_7d_mm" in report_no_weather["missing_features"]
    assert "monthly_rainfall_mm" in report_no_weather["missing_features"]
    assert report_no_weather["ready_for_prediction"] is False
    print(f"  ✓ Missing live weather caught: {report_no_weather['missing_features']} (ready = False)")

    # 5. Test Unknown Categorical Values
    print("\n[TEST 5] Testing unknown category handling...")
    loc_unknown = loc_7.copy()
    loc_unknown["district"] = "NonExistentDistrictXYZ"
    df_unk, report_unk = build_feature_dataframe(loc_unknown, mock_weather)
    assert len(report_unk["unknown_categories"]) > 0
    assert report_unk["ready_for_prediction"] is False
    print(f"  ✓ Unknown category caught: {report_unk['unknown_categories']}")

    print("\n" + "=" * 60)
    print("FEATURE BUILDER TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
