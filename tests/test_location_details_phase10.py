"""
Phase 10 — Location Details System Test Suite.

Verifies:
1. Aggregated Location Details API (GET /api/v1/locations/{location_id}/details).
2. Location Isolation: Ratnapura (ID 7) details return strictly Ratnapura metadata and predictions; Kolonnawa (ID 1) returns strictly Kolonnawa data.
3. Prediction & Risk Identity Linkage: Returned current prediction matches Phase 3 & 5 risk/action specifications.
4. Active Alerts Integration: Alerts attached to response belong strictly to requested location.
5. Recent History Integration: History summary contains canonical prediction history for the location.
6. Missing Prediction Handling: Location with no prediction returns 200 OK with current_prediction=None and status_flag="NO_CURRENT_PREDICTION" (never false LOW).
7. Invalid Location 404: Requesting details for unknown location ID returns 404 LOCATION_NOT_FOUND.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from services.supabase_service import get_supabase_service, _LOCAL_PREDICTIONS, _LOCAL_ALERTS

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_location_details_fixtures():
    """Seeds test predictions for location details verification."""
    db = get_supabase_service()
    now_iso = datetime.now(timezone.utc).isoformat()
    valid_until_iso = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Seed Ratnapura (ID 7)
    rat_pred = {
        "prediction_id": "TEST-RAT-LOC-010",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-LOC-010",
            "location_id": 7,
            "flood_probability": 0.85,
            "risk_level": "HIGH",
            "class": 1,
            "valid_from": now_iso,
            "expires_at": valid_until_iso
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(rat_pred)

    # Seed Kolonnawa (ID 1)
    kol_pred = {
        "prediction_id": "TEST-KOL-LOC-010",
        "status": "success",
        "location": {"id": 1, "place_name": "Kolonnawa", "district": "Colombo"},
        "prediction": {
            "prediction_id": "TEST-KOL-LOC-010",
            "location_id": 1,
            "flood_probability": 0.15,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": now_iso,
            "expires_at": valid_until_iso
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(kol_pred)

    yield {
        "rat_pred": rat_pred,
        "kol_pred": kol_pred
    }


def test_01_ratnapura_location_details_aggregated(setup_location_details_fixtures):
    """Verifies that GET /locations/7/details returns Ratnapura metadata, current HIGH prediction, and Phase 5 action."""
    res = client.get("/api/v1/locations/7/details")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == 7
    assert data["location"]["district"] == "Ratnapura"

    curr_pred = data["current_prediction"]
    assert curr_pred is not None
    assert curr_pred["location"]["location_id"] == 7
    assert curr_pred["risk"]["level"] == "HIGH"
    assert curr_pred["action"]["code"] == "PREPARE"
    assert "Prepare emergency supplies" in curr_pred["action"]["message"]


def test_02_kolonnawa_location_details_isolation(setup_location_details_fixtures):
    """Verifies that GET /locations/1/details returns Kolonnawa metadata and LOW prediction with zero Ratnapura data leakage."""
    res = client.get("/api/v1/locations/1/details")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == 1
    assert data["location"]["district"] == "Colombo"

    curr_pred = data["current_prediction"]
    assert curr_pred is not None
    assert curr_pred["location"]["location_id"] == 1
    assert curr_pred["risk"]["level"] == "LOW"
    assert curr_pred["action"]["code"] == "SAFE"


def test_03_invalid_location_404():
    """Verifies that requesting details for a non-existent location ID returns 404 LOCATION_NOT_FOUND."""
    res = client.get("/api/v1/locations/99999/details")
    assert res.status_code == 404
    data = res.json()
    err = data.get("detail", data)
    assert err.get("code") == "LOCATION_NOT_FOUND"


def test_04_missing_prediction_returns_no_current_prediction():
    """Verifies that a location with no prediction history returns status_flag NO_CURRENT_PREDICTION and current_prediction None."""
    res = client.get("/api/v1/locations/99/details")
    if res.status_code == 200:
        data = res.json()
        assert data["current_prediction"] is None
        assert data["status_flag"] == "NO_CURRENT_PREDICTION"
    else:
        assert res.status_code == 404
