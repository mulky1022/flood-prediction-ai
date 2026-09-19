"""
Canonical Test Fixtures for Phase 18 Quality Engineering.

Provides deterministic, immutable test records for Ratnapura, Kolonnawa,
historical predictions, alerts, notification logs, and official warnings.
"""

from typing import Dict, Any, List

RATNAPURA_LOCATION_FIXTURE: Dict[str, Any] = {
    "id": 7,
    "record_id": "LOC-007",
    "location_id": "RATNAPURA_001",
    "district": "Ratnapura",
    "place_name": "Ratnapura Town (Kalu Ganga Upper)",
    "latitude": 6.6828,
    "longitude": 80.4036,
    "elevation_m": 34.0,
    "distance_to_river_m": 110.0,
    "population_density_per_km2": 920.0,
    "built_up_percent": 52.0,
    "drainage_index": 0.26,
    "ndvi": 0.28,
    "ndwi": 0.31,
    "historical_flood_count": 9.0,
    "infrastructure_score": 48.0,
    "nearest_hospital_km": 2.1,
    "nearest_evac_km": 1.0,
    "landcover": "Urban",
    "soil_type": "Silty",
    "water_supply": "Surface water",
    "electricity": "Mixed",
    "road_quality": "Good (paved)",
    "urban_rural": "Urban",
    "water_presence_flag": "Likely"
}

KOLONNAWA_LOCATION_FIXTURE: Dict[str, Any] = {
    "id": 1,
    "record_id": "LOC-001",
    "location_id": "KOLONNAWA_001",
    "district": "Colombo",
    "place_name": "Kolonnawa (Kelani River Lower)",
    "latitude": 6.9271,
    "longitude": 79.8814,
    "elevation_m": 5.0,
    "distance_to_river_m": 85.0,
    "population_density_per_km2": 3100.0,
    "built_up_percent": 78.0,
    "drainage_index": 0.15,
    "ndvi": 0.18,
    "ndwi": 0.42,
    "historical_flood_count": 14.0,
    "infrastructure_score": 62.0,
    "nearest_hospital_km": 1.2,
    "nearest_evac_km": 0.5,
    "landcover": "Urban",
    "soil_type": "Clay",
    "water_supply": "Municipal",
    "electricity": "Grid",
    "road_quality": "Paved",
    "urban_rural": "Urban",
    "water_presence_flag": "High"
}

RATNAPURA_CURRENT_PREDICTION_FIXTURE: Dict[str, Any] = {
    "prediction_id": "TEST-RAT-004",
    "location_id": 7,
    "location_alias": "RATNAPURA_001",
    "prediction_class": 1,
    "flood_probability": 0.8642,
    "flood_probability_percent": 86.42,
    "non_flood_probability": 0.1358,
    "risk_level": "HIGH",
    "risk_score": 0.8642,
    "action_code": "EVACUATE",
    "action_message": "Move immediately to designated higher ground evacuation centers.",
    "model_name": "XGBoostClassifier",
    "model_version": "v1.2.0-prod",
    "created_at": "2026-09-18T20:00:00Z",
    "valid_from": "2026-09-18T20:00:00Z",
    "valid_until": "2026-09-19T08:00:00Z",
    "status": "CURRENT",
    "is_stale": False
}

KOLONNAWA_CURRENT_PREDICTION_FIXTURE: Dict[str, Any] = {
    "prediction_id": "TEST-KOL-004",
    "location_id": 1,
    "location_alias": "KOLONNAWA_001",
    "prediction_class": 0,
    "flood_probability": 0.1210,
    "flood_probability_percent": 12.10,
    "non_flood_probability": 0.8790,
    "risk_level": "LOW",
    "risk_score": 0.1210,
    "action_code": "MONITOR",
    "action_message": "Normal conditions. Continue monitoring weather bulletins.",
    "model_name": "XGBoostClassifier",
    "model_version": "v1.2.0-prod",
    "created_at": "2026-09-18T20:00:00Z",
    "valid_from": "2026-09-18T20:00:00Z",
    "valid_until": "2026-09-19T08:00:00Z",
    "status": "CURRENT",
    "is_stale": False
}

RATNAPURA_HISTORICAL_PREDICTIONS_FIXTURE: List[Dict[str, Any]] = [
    {
        "prediction_id": "TEST-RAT-001",
        "location_id": 7,
        "prediction_class": 1,
        "flood_probability": 0.9100,
        "risk_level": "HIGH",
        "model_version": "v2.1",
        "created_at": "2026-09-15T08:00:00Z"
    },
    {
        "prediction_id": "TEST-RAT-002",
        "location_id": 7,
        "prediction_class": 1,
        "flood_probability": 0.5500,
        "risk_level": "MEDIUM",
        "model_version": "v2.1",
        "created_at": "2026-09-16T08:00:00Z"
    },
    {
        "prediction_id": "TEST-RAT-003",
        "location_id": 7,
        "prediction_class": 0,
        "flood_probability": 0.1800,
        "risk_level": "LOW",
        "model_version": "v2.1",
        "created_at": "2026-09-17T08:00:00Z"
    }
]

KOLONNAWA_HISTORICAL_PREDICTIONS_FIXTURE: List[Dict[str, Any]] = [
    {
        "prediction_id": "TEST-KOL-001",
        "location_id": 1,
        "prediction_class": 0,
        "flood_probability": 0.0900,
        "risk_level": "LOW",
        "model_version": "v2.1",
        "created_at": "2026-09-15T08:00:00Z"
    },
    {
        "prediction_id": "TEST-KOL-002",
        "location_id": 1,
        "prediction_class": 1,
        "flood_probability": 0.4800,
        "risk_level": "MEDIUM",
        "model_version": "v2.1",
        "created_at": "2026-09-16T08:00:00Z"
    }
]

CANONICAL_ALERT_FIXTURE: Dict[str, Any] = {
    "id": "ALERT-RAT-001",
    "prediction_id": "TEST-RAT-004",
    "location_id": "7",
    "location_name": "Ratnapura Town",
    "risk_level": "HIGH",
    "title": "Flood Alert - High Risk (Ratnapura)",
    "message": "Water level rising rapidly in Kalu Ganga Upper reach.",
    "status": "ACTIVE",
    "created_at": "2026-09-18T20:05:00Z"
}

CANONICAL_NOTIFICATION_LOG_FIXTURE: Dict[str, Any] = {
    "id": "NOTIF-TEST-101",
    "alert_id": "ALERT-RAT-001",
    "prediction_id": "TEST-RAT-004",
    "location_id": "7",
    "subscription_id": "SUB-RAT-88",
    "channel": "sms",
    "destination_masked": "+9477****567",
    "language": "en",
    "risk_level": "HIGH",
    "status": "DELIVERED",
    "created_at": "2026-09-18T20:06:00Z"
}

CANONICAL_OFFICIAL_WARNING_FIXTURE: Dict[str, Any] = {
    "warning_id": "WARN-DMC-20260918-01",
    "location_id": 7,
    "source_id": "DMC-SL",
    "source_name": "Disaster Management Centre (DMC) Sri Lanka",
    "source_type": "GOVERNMENT_AGENCY",
    "warning_type": "FLOOD_EVACUATION",
    "severity": "CRITICAL",
    "title": "Red Alert Flood Evacuation Order",
    "message": "Immediate evacuation ordered for Kalu Ganga riverbanks.",
    "issued_at": "2026-09-18T19:30:00Z",
    "valid_from": "2026-09-18T19:30:00Z",
    "valid_until": "2026-09-19T19:30:00Z",
    "status": "ACTIVE"
}
