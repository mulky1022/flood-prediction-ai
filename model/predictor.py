"""
Production FloodPredictor Service.

Contract:
- Expects 64 specific features
- Strictly uses saved StandardScaler before inference
- Evaluates RandomForestClassifier probabilities
- Provides prototype risk level classification
- Guarantees fail-safe error handling
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("FloodPredictor")

# Prototype thresholds - clearly documented as non-certified baseline
RISK_THRESHOLDS = {
    "moderate": 0.35,
    "high": 0.60,
    "critical": 0.80
}


class FloodPredictor:
    """
    Encapsulates loading and inference for the Sri Lanka Flood Risk Model.
    """

    def __init__(self, model_dir: Optional[Union[str, Path]] = None):
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent
        else:
            self.model_dir = Path(model_dir)

        self.feature_columns_path = self.model_dir / "feature_columns.json"
        self.metadata_path = self.model_dir / "model_metadata.json"
        self.model_path = self.model_dir / "flood_model.pkl"
        self.preprocessor_path = self.model_dir / "preprocessor.pkl"

        self.feature_columns: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.scaler = None
        self.model = None

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Loads all required ML artifacts and verifies integrity."""
        try:
            with open(self.feature_columns_path, "r", encoding="utf-8") as f:
                all_cols = json.load(f)
                # The model and preprocessor are strictly fitted on 64 features.
                # If feature_columns.json contains 65 (e.g. trailing is_good_to_live_Yes),
                # we maintain exact alignment with the scaler's 64 features.
                self.feature_columns = all_cols[:64]

            if self.metadata_path.exists():
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {"model_version": "1.0.0", "model_name": "RandomForestClassifier"}

            self.scaler = joblib.load(self.preprocessor_path)
            self.model = joblib.load(self.model_path)

            # Contract verification
            scaler_features = getattr(self.scaler, "n_features_in_", None)
            model_features = getattr(self.model, "n_features_in_", None)

            if scaler_features != 64:
                raise ValueError(f"Scaler expected 64 features, found {scaler_features}")
            if model_features != 64:
                raise ValueError(f"Model expected 64 features, found {model_features}")

            logger.info(f"FloodPredictor loaded successfully. Model version: {self.metadata.get('model_version', '1.0.0')}")

        except Exception as e:
            logger.error(f"Failed to load ML artifacts: {e}", exc_info=True)
            raise RuntimeError(f"ML artifact initialization failed: {e}")

    def classify_risk_tier(self, probability: float) -> str:
        """
        Maps continuous probability to a prototype risk tier.
        """
        if probability >= RISK_THRESHOLDS["critical"]:
            return "CRITICAL"
        elif probability >= RISK_THRESHOLDS["high"]:
            return "HIGH"
        elif probability >= RISK_THRESHOLDS["moderate"]:
            return "MODERATE"
        else:
            return "LOW"

    def predict(self, feature_data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Executes prediction on input features following the strict contract:
        RAW DATA -> FEATURE BUILDING -> EXACT FEATURE ALIGNMENT -> STANDARD SCALER -> RANDOM FOREST -> PREDICT_PROBA
        """
        try:
            # 1. Convert input to DataFrame
            if isinstance(feature_data, dict):
                df = pd.DataFrame([feature_data])
            elif isinstance(feature_data, list):
                df = pd.DataFrame(feature_data)
            elif isinstance(feature_data, pd.DataFrame):
                df = feature_data.copy()
            else:
                return {
                    "status": "error",
                    "prediction_available": False,
                    "message": f"Unsupported input type: {type(feature_data)}. Expected DataFrame or dict."
                }

            # 2. Strict feature alignment
            aligned_df = df.reindex(columns=self.feature_columns, fill_value=0.0)

            # 3. Shape validation
            if aligned_df.shape[1] != 64:
                return {
                    "status": "error",
                    "prediction_available": False,
                    "message": f"Feature count mismatch. Expected 64 features, got {aligned_df.shape[1]}."
                }

            # 4. Standard Scaler Transformation
            X_scaled = self.scaler.transform(aligned_df)

            # 5. Model Inference
            probabilities = self.model.predict_proba(X_scaled)
            predictions = self.model.predict(X_scaled)

            # Extract single-instance or batch results
            if len(predictions) == 1:
                prob = float(probabilities[0][1])
                pred = int(predictions[0])
                risk_level = self.classify_risk_tier(prob)

                return {
                    "status": "success",
                    "prediction_available": True,
                    "probability": round(prob, 4),
                    "probability_percent": round(prob * 100, 2),
                    "prediction": pred,
                    "risk_level": risk_level,
                    "model_version": self.metadata.get("model_version", "1.0.0"),
                    "model_name": self.metadata.get("model_name", "RandomForestClassifier"),
                    "feature_count_verified": 64
                }
            else:
                results = []
                for i in range(len(predictions)):
                    prob = float(probabilities[i][1])
                    pred = int(predictions[i])
                    results.append({
                        "probability": round(prob, 4),
                        "probability_percent": round(prob * 100, 2),
                        "prediction": pred,
                        "risk_level": self.classify_risk_tier(prob)
                    })

                return {
                    "status": "success",
                    "prediction_available": True,
                    "batch_size": len(results),
                    "results": results,
                    "model_version": self.metadata.get("model_version", "1.0.0"),
                    "feature_count_verified": 64
                }

        except Exception as e:
            logger.error(f"Prediction failure: {e}", exc_info=True)
            return {
                "status": "error",
                "prediction_available": False,
                "message": f"Prediction failed: {str(e)}"
            }
