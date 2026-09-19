"""
Test Object Factories for Phase 18 Quality Engineering.

Provides helper factories to construct valid test models and records for
Location, Station, Prediction, Alert, Notification, OfficialWarning, PredictionJob, and AdminUser.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class LocationFactory:
    @staticmethod
    def create(
        location_id: int = 7,
        record_id: str = "LOC-007",
        district: str = "Ratnapura",
        place_name: str = "Ratnapura Town"
    ) -> Dict[str, Any]:
        return {
            "id": location_id,
            "record_id": record_id,
            "district": district,
            "place_name": place_name,
            "latitude": 6.6828,
            "longitude": 80.4036,
            "elevation_m": 34.0,
            "distance_to_river_m": 110.0,
            "population_density_per_km2": 920.0
        }


class PredictionFactory:
    @staticmethod
    def create(
        location_id: int = 7,
        prediction_id: Optional[str] = None,
        risk_level: str = "HIGH",
        flood_prob: float = 0.82,
        model_version: str = "v1.2.0-prod"
    ) -> Dict[str, Any]:
        p_id = prediction_id or f"TEST-PRED-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "prediction_id": p_id,
            "location_id": location_id,
            "prediction_class": 1 if risk_level in ("HIGH", "MEDIUM") else 0,
            "flood_probability": flood_prob,
            "risk_level": risk_level,
            "action_code": "EVACUATE" if risk_level == "HIGH" else ("PREPARE" if risk_level == "MEDIUM" else "MONITOR"),
            "model_version": model_version,
            "created_at": now_iso,
            "valid_from": now_iso,
            "valid_until": now_iso,
            "status": "CURRENT"
        }


class AlertFactory:
    @staticmethod
    def create(
        prediction_id: str,
        location_id: str = "7",
        risk_level: str = "HIGH"
    ) -> Dict[str, Any]:
        return {
            "id": f"ALERT-{uuid.uuid4().hex[:6].upper()}",
            "prediction_id": prediction_id,
            "location_id": str(location_id),
            "risk_level": risk_level,
            "title": f"Flood Risk Alert - {risk_level}",
            "message": "Automated canonical risk alert.",
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat()
        }


class NotificationFactory:
    @staticmethod
    def create(
        alert_id: str,
        prediction_id: str,
        location_id: str = "7",
        channel: str = "sms",
        destination_masked: str = "+9477****567",
        language: str = "en"
    ) -> Dict[str, Any]:
        return {
            "id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            "alert_id": alert_id,
            "prediction_id": prediction_id,
            "location_id": str(location_id),
            "subscription_id": f"SUB-{uuid.uuid4().hex[:4].upper()}",
            "channel": channel.lower(),
            "destination_masked": destination_masked,
            "language": language,
            "risk_level": "HIGH",
            "status": "DELIVERED",
            "provider_message_id": f"MSG-{uuid.uuid4().hex[:8].upper()}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }


class OfficialWarningFactory:
    @staticmethod
    def create(
        location_id: int = 7,
        warning_type: str = "FLOOD_WARNING",
        severity: str = "MAJOR"
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "warning_id": f"WARN-DMC-{uuid.uuid4().hex[:6].upper()}",
            "location_id": location_id,
            "source_id": "DMC-SL",
            "source_name": "Disaster Management Centre (DMC) Sri Lanka",
            "source_type": "GOVERNMENT_AGENCY",
            "warning_type": warning_type,
            "severity": severity,
            "title": "Official Government Flood Warning",
            "message": "Official warning message issued by DMC.",
            "issued_at": now_iso,
            "valid_from": now_iso,
            "valid_until": now_iso,
            "status": "ACTIVE"
        }
