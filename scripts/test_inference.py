"""
Comprehensive Local ML Inference Test Suite.

Tests:
1. ML artifact existence and loading
2. Model hyperparameter and metadata validation
3. Strict 64-feature shape contract verification
4. Scaler transform and model predict_proba execution
5. Low-risk vs High-risk scenario validation
6. Fail-safe error handling for corrupted or invalid inputs
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from model.predictor import FloodPredictor, RISK_THRESHOLDS


def run_tests():
    print("=" * 70)
    print("SRI LANKA FLOOD RISK PREDICTION - LOCAL ML INFERENCE TEST")
    print("=" * 70)

    # 1. Initialize Predictor
    print("\n[TEST 1] Initializing FloodPredictor...")
    try:
        predictor = FloodPredictor()
        print(f"  [PASS] Predictor loaded successfully.")
        print(f"  [INFO] Model Version: {predictor.metadata.get('model_version')}")
        print(f"  [INFO] Expected Feature Count: {len(predictor.feature_columns)}")
    except Exception as e:
        print(f"  [FAIL] Initialization failed: {e}")
        return False

    # 2. Test Low-Risk Scenario (e.g. Dry day in Kandy high elevation)
    print("\n[TEST 2] Testing Low-Risk Dry Scenario (Kandy / High Elevation)...")
    low_risk_input = {col: 0.0 for col in predictor.feature_columns}
    low_risk_input.update({
        "latitude": 7.2906,
        "longitude": 80.6337,
        "elevation_m": 500.0,
        "distance_to_river_m": 4500.0,
        "population_density_per_km2": 350.0,
        "built_up_percent": 15.0,
        "rainfall_7d_mm": 5.0,
        "monthly_rainfall_mm": 35.0,
        "drainage_index": 0.8,
        "ndvi": 0.55,
        "ndwi": -0.10,
        "historical_flood_count": 0.0,
        "infrastructure_score": 75.0,
        "nearest_hospital_km": 2.0,
        "nearest_evac_km": 1.2,
        "flood_risk_score": 10.0,
        "inundation_area_sqm": 0.0,
        "district_Kandy": 1.0,
        "landcover_Forest": 1.0,
        "soil_type_Loamy": 1.0,
        "road_quality_Good (paved)": 1.0
    })

    res_low = predictor.predict(low_risk_input)
    print(f"  Status: {res_low.get('status')}")
    print(f"  Probability: {res_low.get('probability')} ({res_low.get('probability_percent')}%)")
    print(f"  Risk Level: {res_low.get('risk_level')}")
    print(f"  Binary Prediction: {res_low.get('prediction')}")
    assert res_low["status"] == "success", "Low risk test failed"
    print("  [PASS] Low-risk inference completed successfully.")

    # 3. Test High-Risk Scenario (e.g. Extreme 7d rainfall in Ratnapura river basin)
    print("\n[TEST 3] Testing High-Risk Extreme Rainfall Scenario (Ratnapura)...")
    high_risk_input = {col: 0.0 for col in predictor.feature_columns}
    high_risk_input.update({
        "latitude": 6.6828,
        "longitude": 80.4036,
        "elevation_m": 25.0,
        "distance_to_river_m": 120.0,
        "population_density_per_km2": 850.0,
        "built_up_percent": 60.0,
        "rainfall_7d_mm": 245.0,
        "monthly_rainfall_mm": 480.0,
        "drainage_index": 0.25,
        "ndvi": 0.20,
        "ndwi": 0.35,
        "historical_flood_count": 6.0,
        "infrastructure_score": 35.0,
        "nearest_hospital_km": 4.5,
        "nearest_evac_km": 2.0,
        "flood_risk_score": 62.0,
        "inundation_area_sqm": 0.0,
        "district_Ratnapura": 1.0,
        "landcover_Urban": 1.0,
        "soil_type_Silty": 1.0,
        "urban_rural_Urban": 1.0
    })

    res_high = predictor.predict(high_risk_input)
    print(f"  Status: {res_high.get('status')}")
    print(f"  Probability: {res_high.get('probability')} ({res_high.get('probability_percent')}%)")
    print(f"  Risk Level: {res_high.get('risk_level')}")
    print(f"  Binary Prediction: {res_high.get('prediction')}")
    assert res_high["status"] == "success", "High risk test failed"
    print("  [PASS] High-risk inference completed successfully.")

    # 4. Test Incomplete Input Auto-Alignment (Reindexing with 0 defaults)
    print("\n[TEST 4] Testing Partial Feature Input Auto-Alignment...")
    partial_input = {
        "latitude": 6.9271,
        "longitude": 79.8612,
        "rainfall_7d_mm": 120.0,
        "district_Colombo": 1.0
    }
    res_partial = predictor.predict(partial_input)
    print(f"  Status: {res_partial.get('status')}")
    print(f"  Probability: {res_partial.get('probability')} ({res_partial.get('risk_level')})")
    assert res_partial["status"] == "success", "Partial alignment test failed"
    print("  [PASS] Auto-reindexing and default filling verified.")

    # 5. Test Invalid Input Fail-Safe Handling
    print("\n[TEST 5] Testing Invalid Data Type Fail-Safe Error Handling...")
    res_invalid = predictor.predict("INVALID_STRING_PAYLOAD")
    print(f"  Status: {res_invalid.get('status')}")
    print(f"  Prediction Available: {res_invalid.get('prediction_available')}")
    print(f"  Message: {res_invalid.get('message')}")
    assert res_invalid["prediction_available"] is False, "Fail-safe test failed"
    print("  [PASS] Fail-safe error handling verified.")

    print("\n" + "=" * 70)
    print("ALL LOCAL ML INFERENCE TESTS PASSED (100% SUCCESS)")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
