"""
Production FloodPredictor Service.

Orchestrates the complete ML pipeline:
Location Data + Live Weather -> Feature Builder -> Quality Gate -> StandardScaler -> RandomForest -> Prediction Result
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from services.location_service import get_location_by_id
from weather.weather_processor import get_weather_for_location
from services.feature_builder import build_feature_dataframe, FEATURE_COLUMNS
from services.data_quality_service import get_data_quality_service, DATA_STATE_INVALID


logger = logging.getLogger("PredictorService")

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"


class PredictorService:
    """
    Singleton-style predictor service caching loaded model and scaler in memory.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or MODEL_DIR
        self.model_path = self.model_dir / "flood_model.pkl"
        self.scaler_path = self.model_dir / "preprocessor.pkl"
        self.features_path = self.model_dir / "feature_columns.json"
        self.metadata_path = self.model_dir / "model_metadata.json"

        self.model = None
        self.scaler = None
        self.metadata: Dict[str, Any] = {}
        self.feature_columns: List[str] = []

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Loads and verifies model artifacts."""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model artifact not found at: {self.model_path}")
            if not self.scaler_path.exists():
                raise FileNotFoundError(f"Scaler artifact not found at: {self.scaler_path}")

            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)

            if self.metadata_path.exists():
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

            if self.features_path.exists():
                with open(self.features_path, "r", encoding="utf-8") as f:
                    self.feature_columns = json.load(f)[:64]
            else:
                self.feature_columns = FEATURE_COLUMNS

            logger.info("PredictorService ML artifacts loaded successfully.")

        except Exception as e:
            logger.error(f"Failed to load ML artifacts: {e}", exc_info=True)
            raise RuntimeError(f"Predictor initialization failed: {e}")

    def predict_from_features(self, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes inference directly on a validated (1, 64) DataFrame.
        Enforces feature order and model output validation via DataQualityService.
        """
        quality_svc = get_data_quality_service()

        # Phase 20 Feature Validation Guardrail
        feature_val = quality_svc.validate_feature_dataframe(X, self.feature_columns)
        if not feature_val["valid"]:
            return {
                "status": "error",
                "ready_for_prediction": False,
                "message": feature_val["message"],
                "quality_details": feature_val
            }

        try:
            X_scaled = self.scaler.transform(X)
            prediction_class = int(self.model.predict(X_scaled)[0])
            probabilities = self.model.predict_proba(X_scaled)[0]

            non_flood_prob = float(probabilities[0])
            flood_prob = float(probabilities[1])

            # Calibrated Risk Level Categorization
            if flood_prob >= 0.80:
                risk_level = "CRITICAL"
            elif flood_prob >= 0.65:
                risk_level = "HIGH"
            elif flood_prob >= 0.35:
                risk_level = "MODERATE"
            else:
                risk_level = "LOW"

            res = {
                "status": "success",
                "ready_for_prediction": True,
                "prediction": {
                    "class": prediction_class,
                    "flood_probability": round(flood_prob, 4),
                    "flood_probability_percent": round(flood_prob * 100, 2),
                    "non_flood_probability": round(non_flood_prob, 4),
                    "risk_level": risk_level
                },
                "model": {
                    "name": self.metadata.get("model_name", "RandomForestClassifier"),
                    "version": self.metadata.get("model_version", "1.0.0"),
                    "feature_count": 64
                }
            }

            # Phase 20 Model Output Validation
            out_val = quality_svc.validate_model_output(res)
            if not out_val["valid"]:
                return {
                    "status": "error",
                    "ready_for_prediction": False,
                    "message": f"Model output validation failed: {out_val.get('message')}"
                }

            return res

        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            return {
                "status": "error",
                "ready_for_prediction": False,
                "message": f"Inference execution failed: {str(e)}"
            }

    def predict_location(
        self,
        location_id: Union[int, str],
        use_cache: bool = True,
        derive_leakage_baselines: bool = True
    ) -> Dict[str, Any]:
        """
        Coordinates end-to-end live inference for a location.
        """
        quality_svc = get_data_quality_service()

        # 1. Resolve Location
        location = get_location_by_id(location_id)
        if not location:
            return {
                "status": "location_not_found",
                "ready_for_prediction": False,
                "location_id": location_id,
                "message": f"Location ID '{location_id}' not found in locations database."
            }

        # Validate Location Isolation Invariant
        mapping_val = quality_svc.validate_location_station_mapping(location_id, location.get("id"))
        if not mapping_val["valid"]:
            return {
                "status": "prediction_unavailable",
                "ready_for_prediction": False,
                "reason": "location_mapping_mismatch",
                "message": mapping_val["message"]
            }

        # 2. Fetch Weather
        weather_result = get_weather_for_location(location_id, use_cache=use_cache)
        if weather_result.get("status") != "success":
            return {
                "status": "prediction_unavailable",
                "ready_for_prediction": False,
                "reason": "weather_data_unavailable",
                "location": {
                    "id": location.get("id"),
                    "district": location.get("district"),
                    "place_name": location.get("place_name")
                },
                "message": weather_result.get("message", "Unable to retrieve weather data for prediction.")
            }

        # Validate Weather Units & Ranges (flags suspicious data without discarding extreme floods)
        weather_val = quality_svc.validate_weather_units_and_ranges(weather_result.get("current", {}))

        # 3. Build Feature Vector
        df_features, quality_report = build_feature_dataframe(
            location=location,
            weather=weather_result,
            derive_leakage_baselines=derive_leakage_baselines
        )

        # 4. Quality Gate
        if not quality_report["ready_for_prediction"]:
            return {
                "status": "prediction_unavailable",
                "ready_for_prediction": False,
                "reason": "required_feature_unavailable",
                "location": {
                    "id": location.get("id"),
                    "district": location.get("district"),
                    "place_name": location.get("place_name")
                },
                "data_quality": quality_report,
                "message": "One or more required model features could not be validated."
            }

        # 5. Execute Prediction
        inference_result = self.predict_from_features(df_features)

        if inference_result.get("status") != "success":
            return inference_result

        # Track Station Health Telemetry
        quality_svc.record_station_observation_telemetry(
            station_id=location.get("id"),
            location_id=location_id,
            observation_success=True,
            is_invalid=(weather_val.get("status") == DATA_STATE_INVALID)
        )

        # 6. Assemble Full Response
        return {
            "status": "success",
            "ready_for_prediction": True,
            "location": {
                "id": location.get("id"),
                "district": location.get("district"),
                "place_name": location.get("place_name")
            },
            "prediction": inference_result["prediction"],
            "model": inference_result["model"],
            "data_quality": {
                "missing_features": quality_report["missing_features"],
                "invalid_features": quality_report["invalid_features"],
                "unknown_categories": quality_report["unknown_categories"],
                "weather_quality": quality_report["weather_quality"],
                "leakage_features_derived": quality_report["leakage_features_derived"],
                "weather_validation": weather_val
            },
            "input_audit": {
                "feature_count": 64,
                "rainfall_7d_mm": df_features["rainfall_7d_mm"].iloc[0],
                "monthly_rainfall_mm": df_features["monthly_rainfall_mm"].iloc[0],
                "weather_source": weather_result.get("source", {}).get("provider", "Open-Meteo"),
                "weather_retrieved_at": weather_result.get("source", {}).get("retrieved_at")
            }
        }



# Global singleton instance
_PREDICTOR_INSTANCE: Optional[PredictorService] = None


def get_predictor() -> PredictorService:
    global _PREDICTOR_INSTANCE
    if _PREDICTOR_INSTANCE is None:
        _PREDICTOR_INSTANCE = PredictorService()
    return _PREDICTOR_INSTANCE
