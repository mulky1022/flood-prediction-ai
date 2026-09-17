"""
Feature Builder Service for Sri Lanka Flood Risk Prediction.

Translates static location characteristics and live weather observations
into the strict 64-feature vector expected by the Random Forest model.

Features:
- Reproduces training-time one-hot categorical encoding
- Distinguishes structural one-hot zeros from missing source data
- Validates data quality and tracks missing/corrupt values
- Enforces strict 64-column contract alignment
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("FeatureBuilder")

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURE_COLUMNS_PATH = BASE_DIR / "model" / "feature_columns.json"

# Load feature contract once
with open(FEATURE_COLUMNS_PATH, "r", encoding="utf-8") as f:
    FEATURE_COLUMNS: List[str] = json.load(f)[:64]

# Categorical mapping definitions matching training one-hot encoding
KNOWN_CATEGORIES = {
    "district": [
        "Anuradhapura", "Badulla", "Batticaloa", "Colombo", "Galle",
        "Gampaha", "Hambantota", "Jaffna", "Kalutara", "Kandy",
        "Kegalle", "Kilinochchi", "Kurunegala", "Mannar", "Matale",
        "Matara", "Monaragala", "Mullaitivu", "Nuwara Eliya", "Polonnaruwa",
        "Puttalam", "Ratnapura", "Trincomalee", "Vavuniya"
        # Note: Ampara is the reference category (all district_* = 0)
    ],
    "landcover": [
        "Bare Soil", "Forest", "Plantation", "Scrub", "Urban", "Wetland"
    ],
    "soil_type": [
        "Loamy", "Peaty", "Sandy", "Silty"
    ],
    "water_supply": [
        "Rainwater harvesting", "Surface water", "Tube-well", "Well"
    ],
    "electricity": [
        "Mixed", "Off-gr", "Off-grid (solar)"
    ],
    "road_quality": [
        "Good (paved)", "No road access", "Poor (unpaved)"
    ]
}

STATIC_NUMERICAL_FIELDS = [
    "latitude",
    "longitude",
    "elevation_m",
    "distance_to_river_m",
    "population_density_per_km2",
    "built_up_percent",
    "drainage_index",
    "ndvi",
    "ndwi",
    "historical_flood_count",
    "infrastructure_score",
    "nearest_hospital_km",
    "nearest_evac_km"
]


def derive_pre_event_flood_risk_score(
    elevation_m: float,
    distance_to_river_m: float,
    drainage_index: float,
    rainfall_7d_mm: float
) -> float:
    """
    Computes a deterministic pre-event hydrological composite index (0-100).
    Higher elevation and greater distance from rivers lower the baseline risk.
    """
    elev_factor = max(0.0, 1.0 - min(elevation_m, 500.0) / 500.0) * 30.0
    river_factor = max(0.0, 1.0 - min(distance_to_river_m, 2000.0) / 2000.0) * 30.0
    drain_factor = max(0.0, 1.0 - min(drainage_index, 1.0)) * 20.0
    rain_factor = min(rainfall_7d_mm / 200.0, 1.0) * 20.0

    score = elev_factor + river_factor + drain_factor + rain_factor
    return round(float(min(100.0, max(0.0, score))), 2)


def build_feature_dataframe(
    location: Dict[str, Any],
    weather: Dict[str, Any],
    derive_leakage_baselines: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Builds and validates an exact 64-feature DataFrame from location and weather objects.

    Returns:
        (df, quality_report)
    """
    raw_features: Dict[str, float] = {}
    missing_features: List[str] = []
    invalid_features: List[str] = []
    unknown_categories: List[str] = []
    structural_zeros: List[str] = []

    # -------------------------------------------------------------
    # 1. Static Numerical Features
    # -------------------------------------------------------------
    for field in STATIC_NUMERICAL_FIELDS:
        val = location.get(field)
        if val is None:
            missing_features.append(field)
            raw_features[field] = 0.0  # Placeholder for alignment; flagged in missing_features
        elif isinstance(val, (int, float)):
            raw_features[field] = float(val)
        else:
            try:
                raw_features[field] = float(val)
            except (ValueError, TypeError):
                invalid_features.append(f"{field}: {val}")
                raw_features[field] = 0.0

    # -------------------------------------------------------------
    # 2. Live Weather Features
    # -------------------------------------------------------------
    rainfall_block = weather.get("rainfall", {}) if isinstance(weather, dict) else {}

    r7d = rainfall_block.get("rainfall_7d_mm")
    if r7d is None:
        missing_features.append("rainfall_7d_mm")
        raw_features["rainfall_7d_mm"] = 0.0
    elif isinstance(r7d, (int, float)) and r7d >= 0.0:
        raw_features["rainfall_7d_mm"] = float(r7d)
    else:
        invalid_features.append(f"rainfall_7d_mm: {r7d}")
        raw_features["rainfall_7d_mm"] = 0.0

    rmonth = rainfall_block.get("monthly_rainfall_mm")
    if rmonth is None:
        missing_features.append("monthly_rainfall_mm")
        raw_features["monthly_rainfall_mm"] = 0.0
    elif isinstance(rmonth, (int, float)) and rmonth >= 0.0:
        raw_features["monthly_rainfall_mm"] = float(rmonth)
    else:
        invalid_features.append(f"monthly_rainfall_mm: {rmonth}")
        raw_features["monthly_rainfall_mm"] = 0.0

    # -------------------------------------------------------------
    # 3. Leakage / Derived Features
    # -------------------------------------------------------------
    if derive_leakage_baselines:
        # Pre-event deterministic baseline
        raw_features["flood_risk_score"] = derive_pre_event_flood_risk_score(
            elevation_m=raw_features.get("elevation_m", 50.0),
            distance_to_river_m=raw_features.get("distance_to_river_m", 500.0),
            drainage_index=raw_features.get("drainage_index", 0.5),
            rainfall_7d_mm=raw_features.get("rainfall_7d_mm", 0.0)
        )
        raw_features["inundation_area_sqm"] = 0.0  # Scaler mean=0, std=1; 0.0 = safe pre-event baseline
        raw_features["is_good_to_live_Yes"] = 1.0  # Normal baseline livability
    else:
        # If uncalibrated, marked as missing
        missing_features.extend(["flood_risk_score", "inundation_area_sqm", "is_good_to_live_Yes"])
        raw_features["flood_risk_score"] = 0.0
        raw_features["inundation_area_sqm"] = 0.0
        raw_features["is_good_to_live_Yes"] = 0.0

    # -------------------------------------------------------------
    # 4. One-Hot Categorical Encoding
    # -------------------------------------------------------------
    # District encoding (24 binary columns)
    loc_district = str(location.get("district", "")).strip()
    district_matched = False
    for dist in KNOWN_CATEGORIES["district"]:
        col_name = f"district_{dist}"
        if loc_district.lower() == dist.lower():
            raw_features[col_name] = 1.0
            district_matched = True
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    if not district_matched and loc_district.lower() != "ampara":
        unknown_categories.append(f"district: {loc_district}")

    # Landcover encoding (6 binary columns)
    loc_landcover = str(location.get("landcover", "")).strip()
    landcover_matched = False
    for lc in KNOWN_CATEGORIES["landcover"]:
        col_name = f"landcover_{lc}"
        if loc_landcover.lower() == lc.lower():
            raw_features[col_name] = 1.0
            landcover_matched = True
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    if not landcover_matched and loc_landcover:
        unknown_categories.append(f"landcover: {loc_landcover}")

    # Soil type encoding (4 binary columns)
    loc_soil = str(location.get("soil_type", "")).strip()
    soil_matched = False
    for st in KNOWN_CATEGORIES["soil_type"]:
        col_name = f"soil_type_{st}"
        if loc_soil.lower() == st.lower():
            raw_features[col_name] = 1.0
            soil_matched = True
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    if not soil_matched and loc_soil:
        unknown_categories.append(f"soil_type: {loc_soil}")

    # Water supply encoding (4 binary columns)
    loc_ws = str(location.get("water_supply", "")).strip()
    for ws in KNOWN_CATEGORIES["water_supply"]:
        col_name = f"water_supply_{ws}"
        if loc_ws.lower() == ws.lower():
            raw_features[col_name] = 1.0
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    # Electricity encoding (3 binary columns)
    loc_elec = str(location.get("electricity", "")).strip()
    for el in KNOWN_CATEGORIES["electricity"]:
        col_name = f"electricity_{el}"
        if loc_elec.lower() == el.lower():
            raw_features[col_name] = 1.0
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    # Road quality encoding (3 binary columns)
    loc_rq = str(location.get("road_quality", "")).strip()
    for rq in KNOWN_CATEGORIES["road_quality"]:
        col_name = f"road_quality_{rq}"
        if loc_rq.lower() == rq.lower():
            raw_features[col_name] = 1.0
        else:
            raw_features[col_name] = 0.0
            structural_zeros.append(col_name)

    # Binary flags
    loc_ur = str(location.get("urban_rural", "")).strip().lower()
    raw_features["urban_rural_Urban"] = 1.0 if loc_ur == "urban" else 0.0

    loc_wp = str(location.get("water_presence_flag", "")).strip().lower()
    raw_features["water_presence_flag_Unlikely"] = 1.0 if loc_wp == "unlikely" else 0.0

    # -------------------------------------------------------------
    # 5. DataFrame Construction & Exact 64-Feature Alignment
    # -------------------------------------------------------------
    df = pd.DataFrame([raw_features])
    df_aligned = df.reindex(columns=FEATURE_COLUMNS, fill_value=0.0)

    # Quality status evaluation
    is_ready = (
        len(missing_features) == 0 and
        len(invalid_features) == 0 and
        len(unknown_categories) == 0 and
        df_aligned.shape == (1, 64)
    )

    quality_report = {
        "ready_for_prediction": is_ready,
        "total_features": df_aligned.shape[1],
        "missing_features": missing_features,
        "invalid_features": invalid_features,
        "unknown_categories": unknown_categories,
        "structural_zeros_count": len(structural_zeros),
        "leakage_features_derived": ["flood_risk_score", "inundation_area_sqm", "is_good_to_live_Yes"] if derive_leakage_baselines else [],
        "weather_quality": rainfall_block.get("data_quality", "UNKNOWN")
    }

    return df_aligned, quality_report
