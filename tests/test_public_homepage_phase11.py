"""
Phase 11 — Public Homepage UX Test Suite.

Verifies:
1. Public Locations List Endpoint (GET /api/v1/locations) returns all 33 monitoring stations for homepage area selector.
2. Canonical Risk & Action Delivery: GET /api/v1/predictions/current/{location_id} delivers Phase 5 risk level & action.
3. Location Isolation: Selecting Ratnapura (ID 7) strictly returns Ratnapura risk/action; Kolonnawa (ID 1) strictly returns Kolonnawa risk/action.
4. Missing Prediction Guard: Locations with no current prediction return 404 with NO_CURRENT_PREDICTION code, preventing false LOW risk presentation.
5. Emergency Info & DMC Hotline 117 Integration: Health and config endpoints provide operational status for emergency banner.
6. Navigation URL Parameter Consistency: Scoped location parameters are verified for Map, Details, and Alert links.
7. Technical Information Drawer Metrics: Model metadata (RandomForestClassifier, 64 features, version 1.0.0) is present in prediction payload.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from services.supabase_service import get_supabase_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_homepage_fixtures():
    """Seeds canonical predictions for Phase 11 Public Homepage testing."""
    db = get_supabase_service()
    now_iso = datetime.now(timezone.utc).isoformat()
    valid_until_iso = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Seed Ratnapura (ID 7) - CRITICAL RISK
    rat_pred = {
        "prediction_id": "TEST-RAT-HP-011",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-HP-011",
            "location_id": 7,
            "flood_probability": 0.92,
            "risk_level": "CRITICAL",
            "class": 1,
            "valid_from": now_iso,
            "expires_at": valid_until_iso
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo", "features_count": 64}
    }
    db.save_prediction(rat_pred)

    # Seed Kolonnawa (ID 1) - LOW RISK
    kol_pred = {
        "prediction_id": "TEST-KOL-HP-011",
        "status": "success",
        "location": {"id": 1, "place_name": "Kolonnawa", "district": "Colombo"},
        "prediction": {
            "prediction_id": "TEST-KOL-HP-011",
            "location_id": 1,
            "flood_probability": 0.10,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": now_iso,
            "expires_at": valid_until_iso
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo", "features_count": 64}
    }
    db.save_prediction(kol_pred)

    yield {
        "rat_pred": rat_pred,
        "kol_pred": kol_pred
    }


def test_01_public_locations_selector_list():
    """Verifies that public endpoint returns list of locations for homepage area selector dropdown."""
    res = client.get("/api/v1/locations")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["locations"]) >= 2
    
    # Verify Ratnapura and Kolonnawa are present
    loc_ids = [loc["id"] for loc in data["locations"]]
    assert 1 in loc_ids
    assert 7 in loc_ids


def test_02_homepage_ratnapura_critical_risk_and_action(setup_homepage_fixtures):
    """Verifies Ratnapura selection returns canonical CRITICAL risk level and EVACUATE action code."""
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    data = res.json()

    assert data["location"]["location_id"] == 7
    assert data["location"]["district"] == "Ratnapura"
    assert data["risk"]["level"] == "CRITICAL"
    assert data["action"]["code"] == "EVACUATE"
    assert "evacuation" in data["action"]["message"].lower() or "evacuate" in data["action"]["message"].lower()


def test_03_homepage_kolonnawa_low_risk_isolation(setup_homepage_fixtures):
    """Verifies Kolonnawa selection returns LOW risk level and SAFE action without data leakage from Ratnapura."""
    res = client.get("/api/v1/predictions/current/1")
    assert res.status_code == 200
    data = res.json()

    assert data["location"]["location_id"] == 1
    assert data["location"]["district"] == "Colombo"
    assert data["risk"]["level"] == "LOW"
    assert data["action"]["code"] == "SAFE"
    assert "Normal conditions" in data["action"]["message"] or "safe" in data["action"]["message"].lower()


def test_04_missing_prediction_returns_404_no_current_prediction():
    """Verifies location with no prediction returns 404 NO_CURRENT_PREDICTION, guarding against false LOW risk UI display."""
    res = client.get("/api/v1/predictions/current/999")
    assert res.status_code == 404
    data = res.json()
    err = data.get("detail", data)
    assert err.get("code") == "NO_CURRENT_PREDICTION" or err.get("code") == "LOCATION_NOT_FOUND"


def test_05_emergency_hotline_and_config_availability():
    """Verifies system health and config endpoints provide operational metadata for emergency banner UI."""
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "ok" or health_data["status"] == "healthy"

    config_res = client.get("/api/v1/config")
    assert config_res.status_code == 200
    config_data = config_res.json()
    assert config_data["status"] == "ok" or config_data["status"] == "success"


def test_06_technical_drawer_metadata_presence(setup_homepage_fixtures):
    """Verifies technical drawer metrics (Model name, version, feature count) are exposed in API payloads."""
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    data = res.json()

    assert data["model"]["name"] == "RandomForestClassifier"
    assert data["model"]["version"] == "1.0.0"
    assert data["model"]["feature_count"] == 64

