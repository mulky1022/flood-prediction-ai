"""
Central Risk & Action Engine.
Provides a single authoritative backend service for interpreting predictions, deriving canonical risk levels,
and generating deterministic action recommendations with contradiction protection.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("RiskEngine")

# Canonical Risk Levels
RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MODERATE = "MODERATE"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_CRITICAL = "CRITICAL"

VALID_RISK_LEVELS = {RISK_LEVEL_LOW, RISK_LEVEL_MODERATE, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL}

# Canonical Action Codes
ACTION_CODE_SAFE = "SAFE"
ACTION_CODE_MONITOR = "MONITOR"
ACTION_CODE_PREPARE = "PREPARE"
ACTION_CODE_EVACUATE = "EVACUATE"

VALID_ACTION_CODES = {ACTION_CODE_SAFE, ACTION_CODE_MONITOR, ACTION_CODE_PREPARE, ACTION_CODE_EVACUATE}

# Authoritative Action Mappings
ACTION_MAPPINGS: Dict[str, Dict[str, str]] = {
    RISK_LEVEL_LOW: {
        "code": ACTION_CODE_SAFE,
        "message": "Normal conditions. No immediate flood risk detected."
    },
    RISK_LEVEL_MODERATE: {
        "code": ACTION_CODE_MONITOR,
        "message": "Stay alert and keep updated on weather forecasts."
    },
    RISK_LEVEL_HIGH: {
        "code": ACTION_CODE_PREPARE,
        "message": "Prepare emergency supplies and monitor local water levels."
    },
    RISK_LEVEL_CRITICAL: {
        "code": ACTION_CODE_EVACUATE,
        "message": "Immediate evacuation or move to high ground advised."
    }
}


class RiskAssessment(BaseModel):
    """
    Canonical Risk & Action Assessment Model.
    Preserves prediction identity, location identity, model version, and valid timestamps.
    """
    prediction_id: Optional[int] = Field(None, example=101)
    location_id: int = Field(..., example=7)
    risk_level: str = Field(..., example="HIGH")
    flood_probability: float = Field(..., ge=0.0, le=1.0, example=0.72)
    flood_probability_percent: float = Field(..., example=72.0)
    action_code: str = Field(..., example="PREPARE")
    action_message: str = Field(..., example="Prepare emergency supplies and monitor local water levels.")
    status: str = Field(default="CURRENT", example="CURRENT")
    model_version: str = Field(default="1.0.0", example="1.0.0")

    @field_validator("risk_level")
    def validate_risk_level(cls, v):
        upper_v = str(v).upper()
        if upper_v not in VALID_RISK_LEVELS:
            raise ValueError(f"Invalid risk_level '{v}'. Must be one of {VALID_RISK_LEVELS}.")
        return upper_v

    @field_validator("action_code")
    def validate_action_code(cls, v):
        upper_v = str(v).upper()
        if upper_v not in VALID_ACTION_CODES:
            raise ValueError(f"Invalid action_code '{v}'. Must be one of {VALID_ACTION_CODES}.")
        return upper_v


class RiskEngine:
    """
    Central Risk Engine implementation.
    """

    @staticmethod
    def derive_risk_level(probability: float) -> str:
        """
        Derives canonical operational risk level from ML probability output.
        Authoritative bounds:
        - LOW: < 0.35 (0 - 35%)
        - MODERATE: 0.35 - 0.599 (35 - 59%)
        - HIGH: 0.60 - 0.799 (60 - 79%)
        - CRITICAL: >= 0.80 (80 - 100%)
        """
        p = float(probability)
        if p >= 0.80:
            return RISK_LEVEL_CRITICAL
        elif p >= 0.60:
            return RISK_LEVEL_HIGH
        elif p >= 0.35:
            return RISK_LEVEL_MODERATE
        else:
            return RISK_LEVEL_LOW

    @staticmethod
    def get_canonical_action(risk_level: str) -> Dict[str, str]:
        """
        Retrieves the single canonical action mapping for a risk level.
        Throws ValueError on invalid risk levels.
        """
        lvl = str(risk_level or "").strip().upper()
        if lvl not in VALID_RISK_LEVELS:
            raise ValueError(f"Invalid risk level '{risk_level}'. Must be one of {VALID_RISK_LEVELS}.")
        return ACTION_MAPPINGS[lvl]

    @classmethod
    def evaluate_prediction(
        cls,
        prediction_payload: Dict[str, Any],
        override_risk_level: Optional[str] = None
    ) -> RiskAssessment:
        """
        Evaluates a prediction payload and derives a deterministic RiskAssessment object.
        Preserves prediction identity, location identity, and model version.
        Provides contradiction protection against invalid risk levels or mismatched actions.
        """
        if not prediction_payload:
            raise ValueError("Cannot evaluate empty prediction payload.")

        loc = prediction_payload.get("location", {})
        loc_id = loc.get("id") or prediction_payload.get("location_id")
        if loc_id is None:
            raise ValueError("Prediction payload must contain valid location_id.")

        pred_id = prediction_payload.get("prediction_id") or prediction_payload.get("id")
        pred_data = prediction_payload.get("prediction", prediction_payload)

        # Extract flood probability
        prob = float(pred_data.get("flood_probability", 0.0))
        prob_pct = round(prob * 100, 2)

        # Derive or validate risk level
        derived_risk = cls.derive_risk_level(prob)
        risk_lvl = override_risk_level or pred_data.get("risk_level") or derived_risk
        risk_lvl = str(risk_lvl).strip().upper()

        if risk_lvl not in VALID_RISK_LEVELS:
            raise ValueError(f"Invalid risk level '{risk_lvl}'. Must be one of {VALID_RISK_LEVELS}.")

        # Derive canonical action for risk level (contradiction protection)
        action_mapping = cls.get_canonical_action(risk_lvl)

        model_info = prediction_payload.get("model", {})
        model_ver = model_info.get("version", "1.0.0") if isinstance(model_info, dict) else "1.0.0"

        return RiskAssessment(
            prediction_id=pred_id,
            location_id=int(loc_id),
            risk_level=risk_lvl,
            flood_probability=prob,
            flood_probability_percent=prob_pct,
            action_code=action_mapping["code"],
            action_message=action_mapping["message"],
            status=prediction_payload.get("status", "CURRENT"),
            model_version=model_ver
        )
