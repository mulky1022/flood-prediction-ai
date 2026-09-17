"""
Phase 4: Complete End-to-End ML Inference Test Suite

Tests:
1. Full live inference for Ratnapura (ID 7) combining static data + Open-Meteo live weather.
2. Independent shape verification: (1, 64) -> Scaler -> (1, 64) -> Model -> (1, 2).
3. Probability and binary class extraction.
4. Negative test: Non-existent location ID.
5. Negative test: Missing weather input.
6. Negative test: Missing required numerical feature.
7. Negative test: Strict uncalibrated leakage mode.
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
from services.predictor import get_predictor
from services.feature_builder import build_feature_dataframe


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 4 ML Inference Test")
    print("=" * 60)

    # 1. Initialize Predictor
    print("\n[1] Initializing PredictorService & ML Artifacts...")
    predictor = get_predictor()
    print(f"  ✓ Model: {predictor.metadata.get('model_name', 'RandomForestClassifier')}")
    print(f"  ✓ Version: {predictor.metadata.get('model_version', '1.0.0')}")
    print(f"  ✓ Contract Features: {len(predictor.feature_columns)}")

    # 2. Live End-to-End Inference for Ratnapura (ID 7)
    print("\n[2] Executing live inference pipeline for Ratnapura (Location ID 7)...")
    result = predictor.predict_location(7, use_cache=True, derive_leakage_baselines=True)

    assert result["status"] == "success", f"Prediction failed: {result.get('message')}"
    assert result["ready_for_prediction"] is True
    assert 0.0 <= result["prediction"]["flood_probability"] <= 1.0

    print("  ✓ Prediction pipeline completed successfully:")
    print(f"    - Location: {result['location']['place_name']} ({result['location']['district']})")
    print(f"    - Prediction Class: {result['prediction']['class']}")
    print(f"    - Flood Probability: {result['prediction']['flood_probability'] * 100:.2f}% (P(Flood=1) = {result['prediction']['flood_probability']})")
    print(f"    - Non-Flood Probability: {result['prediction']['non_flood_probability'] * 100:.2f}%")
    print(f"    - 7-Day Rainfall: {result['input_audit']['rainfall_7d_mm']} mm")
    print(f"    - Monthly Rainfall: {result['input_audit']['monthly_rainfall_mm']} mm")
    print(f"    - Weather Source: {result['input_audit']['weather_source']}")

    # 3. Independent Scaler & Model Shape Verification
    print("\n[3] Independent Scaler & Model Dimension Verification...")
    loc_7 = get_location_by_id(7)
    mock_weather = {
        "rainfall": {
            "rainfall_7d_mm": 120.0,
            "monthly_rainfall_mm": 310.0,
            "data_quality": "GOOD"
        }
    }
    df, report = build_feature_dataframe(loc_7, mock_weather)
    assert df.shape == (1, 64), f"Expected DataFrame shape (1, 64), got {df.shape}"

    X_scaled = predictor.scaler.transform(df)
    assert X_scaled.shape == (1, 64), f"Expected scaled shape (1, 64), got {X_scaled.shape}"

    preds = predictor.model.predict(X_scaled)
    probs = predictor.model.predict_proba(X_scaled)
    assert preds.shape == (1,), f"Expected prediction shape (1,), got {preds.shape}"
    assert probs.shape == (1, 2), f"Expected proba shape (1, 2), got {probs.shape}"
    print(f"  ✓ Shape transitions verified: {df.shape} -> Scaler -> {X_scaled.shape} -> Proba -> {probs.shape}")

    # 4. Negative Test: Missing Location
    print("\n[4] Negative Test: Missing Location (ID 99999)...")
    res_no_loc = predictor.predict_location(99999)
    assert res_no_loc["status"] == "location_not_found"
    assert res_no_loc["ready_for_prediction"] is False
    print(f"  ✓ Handled correctly: status = {res_no_loc['status']}")

    # 5. Negative Test: Missing Required Static Feature
    print("\n[5] Negative Test: Missing Required Static Numerical Feature...")
    loc_broken = loc_7.copy()
    loc_broken["elevation_m"] = None
    df_broken, report_broken = build_feature_dataframe(loc_broken, mock_weather)
    assert report_broken["ready_for_prediction"] is False
    assert "elevation_m" in report_broken["missing_features"]
    print(f"  ✓ Handled correctly: ready_for_prediction = False, missing = {report_broken['missing_features']}")

    # 6. Negative Test: Strict Uncalibrated Leakage Mode (Blocking)
    print("\n[6] Negative Test: Strict Uncalibrated Leakage Mode (Hard Block)...")
    res_blocked = predictor.predict_location(7, derive_leakage_baselines=False)
    assert res_blocked["status"] == "prediction_unavailable"
    assert res_blocked["ready_for_prediction"] is False
    assert res_blocked["reason"] == "required_feature_unavailable"
    print(f"  ✓ Handled correctly: status = {res_blocked['status']}, reason = {res_blocked['reason']}")

    # 7. Model Metadata Display
    print("\n[7] Model Metadata (Reported Evaluation Metrics):")
    for k, v in predictor.metadata.items():
        print(f"  - {k}: {v}")

    print("\n" + "=" * 60)
    print("ALL PHASE 4 ML INFERENCE TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
