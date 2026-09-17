"""
Phase 1: Local ML Inference Validation Script

Validates:
1. ML artifact file existence
2. Model class and 64-feature input expectation
3. StandardScaler preprocessor and 64-feature expectation
4. Feature contract columns and ordering from feature_columns.json
5. End-to-end transformation and prediction with controlled sample
6. Display of model metadata
"""

import json
import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")



def main():
    print("=" * 60)
    print("Sri Lanka FloodWatch - Phase 1 ML Inference Test")
    print("=" * 60)

    # -------------------------------------------------------------
    # Step 1: Resolve Paths & Validate Artifact Existence
    # -------------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODEL_DIR = BASE_DIR / "model"

    model_file = MODEL_DIR / "flood_model.pkl"
    scaler_file = MODEL_DIR / "preprocessor.pkl"
    features_file = MODEL_DIR / "feature_columns.json"
    metadata_file = MODEL_DIR / "model_metadata.json"

    print("\n[1] Artifact validation")
    missing_files = []
    if not model_file.exists():
        missing_files.append(str(model_file))
    else:
        print("✓ Model found:", model_file.name)

    if not scaler_file.exists():
        missing_files.append(str(scaler_file))
    else:
        print("✓ Preprocessor found:", scaler_file.name)

    if not features_file.exists():
        missing_files.append(str(features_file))
    else:
        print("✓ Feature columns found:", features_file.name)

    if not metadata_file.exists():
        missing_files.append(str(metadata_file))
    else:
        print("✓ Metadata found:", metadata_file.name)

    if missing_files:
        print(f"\nERROR: Required ML artifact(s) missing:\n" + "\n".join(missing_files))
        sys.exit(1)

    # -------------------------------------------------------------
    # Step 2: Load and Validate Model
    # -------------------------------------------------------------
    print("\n[2] Model validation")
    try:
        model = joblib.load(model_file)
    except Exception as e:
        print(f"ERROR: Failed to load model artifact: {e}")
        sys.exit(1)

    model_class_name = type(model).__name__
    print(f"✓ Model class: {model_class_name}")

    model_features = getattr(model, "n_features_in_", None)
    if model_features != 64:
        print(f"\nERROR: Model feature count mismatch.\nExpected: 64\nActual: {model_features}")
        sys.exit(1)
    print(f"✓ Model feature count: {model_features}")

    # -------------------------------------------------------------
    # Step 3: Load and Validate Preprocessor
    # -------------------------------------------------------------
    print("\n[3] Preprocessor validation")
    try:
        scaler = joblib.load(scaler_file)
    except Exception as e:
        print(f"ERROR: Failed to load preprocessor artifact: {e}")
        sys.exit(1)

    scaler_class_name = type(scaler).__name__
    print(f"✓ Preprocessor class: {scaler_class_name}")

    scaler_features = getattr(scaler, "n_features_in_", None)
    if scaler_features != 64:
        print(f"\nERROR: Scaler feature count mismatch.\nExpected: 64\nActual: {scaler_features}")
        sys.exit(1)
    print(f"✓ Scaler feature count: {scaler_features}")

    # -------------------------------------------------------------
    # Step 4: Load and Validate Feature Columns JSON
    # -------------------------------------------------------------
    print("\n[4] Feature validation")
    try:
        with open(features_file, "r", encoding="utf-8") as f:
            FEATURE_COLUMNS = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse feature_columns.json: {e}")
        sys.exit(1)

    if not isinstance(FEATURE_COLUMNS, list):
        print(f"ERROR: feature_columns.json must contain a JSON array (list). Got: {type(FEATURE_COLUMNS)}")
        sys.exit(1)

    feature_count = len(FEATURE_COLUMNS)
    if feature_count != 64:
        print(f"ERROR: Feature count mismatch in feature_columns.json.\nExpected: 64\nActual: {feature_count}")
        sys.exit(1)

    print(f"✓ Feature count: {feature_count}")

    # Print feature names with index
    print("\n--- Feature Contract Ordering (1-64) ---")
    for idx, col_name in enumerate(FEATURE_COLUMNS, start=1):
        print(f"  {idx:2d}. {col_name}")
    print("----------------------------------------")

    # Joint contract verification
    if feature_count == 64 and model_features == 64 and scaler_features == 64:
        print("✓ Feature contract validated")
    else:
        print("ERROR: Incompatible feature dimensions across model, scaler, and JSON.")
        sys.exit(1)

    # -------------------------------------------------------------
    # Step 5: Create Controlled Demonstration Sample
    # -------------------------------------------------------------
    print("\n[5] Input preparation")
    sample_data = {
        "latitude": 6.68,
        "longitude": 80.40,
        "elevation_m": 100,
        "distance_to_river_m": 500,
        "population_density_per_km2": 1000,
        "built_up_percent": 40,
        "rainfall_7d_mm": 180,
        "monthly_rainfall_mm": 420,
        "drainage_index": 0.4,
        "ndvi": 0.45,
        "ndwi": 0.20,
        "historical_flood_count": 8,
        "infrastructure_score": 40,
        "nearest_hospital_km": 4,
        "nearest_evac_km": 2,
        "flood_risk_score": 50,
        "inundation_area_sqm": 1000,
        "district_Ratnapura": 1.0,
        "landcover_Urban": 1.0,
        "soil_type_Loamy": 1.0,
        "water_supply_Surface water": 1.0,
        "electricity_Mixed": 1.0,
        "road_quality_Good (paved)": 1.0,
        "urban_rural_Urban": 1.0,
        "water_presence_flag_Unlikely": 0.0,
        "is_good_to_live_Yes": 1.0
    }

    try:
        X = pd.DataFrame([sample_data])
        X = X.reindex(columns=FEATURE_COLUMNS, fill_value=0)
    except Exception as e:
        print(f"ERROR: Failed to prepare input DataFrame: {e}")
        sys.exit(1)

    if X.shape != (1, 64):
        print(f"ERROR: DataFrame shape is invalid. Expected: (1, 64), Actual: {X.shape}")
        sys.exit(1)

    print(f"✓ Input shape: {X.shape}")

    # -------------------------------------------------------------
    # Step 6: Apply Saved Preprocessor (StandardScaler)
    # -------------------------------------------------------------
    print("\n[6] Scaling")
    try:
        X_scaled = scaler.transform(X)
    except Exception as e:
        print(f"ERROR: Preprocessor scaling failed: {e}")
        sys.exit(1)

    print(f"Original shape: {X.shape}")
    print(f"Scaled shape: {X_scaled.shape}")
    print(f"✓ Scaled shape: {X_scaled.shape}")

    # -------------------------------------------------------------
    # Step 7: Model Inference
    # -------------------------------------------------------------
    print("\n[7] Prediction")
    try:
        prediction = model.predict(X_scaled)
        probabilities = model.predict_proba(X_scaled)
        prediction_value = int(prediction[0])
        flood_probability = float(probabilities[0][1])
    except Exception as e:
        print(f"ERROR: Model prediction failed: {e}")
        sys.exit(1)

    print("✓ Prediction completed")
    print(f"\nPrediction class: {prediction_value}")
    print(f"Flood probability: {flood_probability * 100:.2f}%")

    # -------------------------------------------------------------
    # Step 8: Load and Display Model Metadata
    # -------------------------------------------------------------
    print("\n[8] Model Metadata")
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        for key, val in metadata.items():
            print(f"  {key}: {val}")
    except Exception as e:
        print(f"WARNING: Could not read metadata: {e}")

    print("\n" + "=" * 60)
    print("PHASE 1 TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
