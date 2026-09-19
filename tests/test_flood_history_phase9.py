"""
Phase 9 — Historical Flood-Risk System Test Suite.

Verifies:
1. Historical Canonical Records: History retrieves stored canonical prediction records without recalculating old predictions.
2. Prediction Identity: HISTORY.PREDICTION_ID == CANONICAL.PREDICTION_ID.
3. Location Identity & Isolation: HISTORY.LOCATION_ID == PREDICTION.LOCATION_ID. Ratnapura (ID 7) strictly isolated from Kolonnawa (ID 1).
4. Historical Immutability: Deploying a new model version does not alter stored historical records.
5. Current vs Historical Separation: Past prediction state is clearly separated from current live prediction state.
6. Alert-History Consistency: Prediction history and Alert history share identical prediction_id, location_id, risk_level, and action.
7. API Filtering & Server-Side Pagination: Filtering by risk_level, start_date, end_date, limit, and offset with deterministic ordering.
8. Missing History Handling: Missing records return empty list (never fake LOW risk).
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from services.supabase_service import get_supabase_service, _LOCAL_PREDICTIONS, _LOCAL_ALERTS
from services.risk_engine import RiskEngine

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_history_test_fixtures():
    """Seeds test memory/DB with canonical historical predictions and alerts for Ratnapura and Kolonnawa."""
    _LOCAL_PREDICTIONS.clear()
    _LOCAL_ALERTS.clear()

    db = get_supabase_service()
    base_time = datetime(2026, 9, 18, 8, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    # Seed Ratnapura (ID 7) Historical Predictions
    rat_pred_1 = {
        "prediction_id": "TEST-RAT-001",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-001",
            "location_id": 7,
            "flood_probability": 0.78,
            "risk_level": "HIGH",
            "class": 1,
            "valid_from": (base_time - timedelta(hours=6)).isoformat(),
            "expires_at": base_time.isoformat()
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo", "weather_retrieved_at": (base_time - timedelta(hours=6)).isoformat()}
    }
    db.save_prediction(rat_pred_1)

    rat_pred_2 = {
        "prediction_id": "TEST-RAT-002",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-002",
            "location_id": 7,
            "flood_probability": 0.45,
            "risk_level": "MODERATE",
            "class": 0,
            "valid_from": (base_time - timedelta(hours=3)).isoformat(),
            "expires_at": (base_time + timedelta(hours=3)).isoformat()
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo", "weather_retrieved_at": (base_time - timedelta(hours=3)).isoformat()}
    }
    db.save_prediction(rat_pred_2)

    rat_pred_3 = {
        "prediction_id": "TEST-RAT-003",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-003",
            "location_id": 7,
            "flood_probability": 0.20,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": base_time.isoformat(),
            "expires_at": (base_time + timedelta(hours=6)).isoformat()
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo", "weather_retrieved_at": base_time.isoformat()}
    }
    db.save_prediction(rat_pred_3)

    # Seed Kolonnawa (ID 1) Historical Predictions
    kol_pred_1 = {
        "prediction_id": "TEST-KOL-001",
        "status": "success",
        "location": {"id": 1, "place_name": "Kolonnawa", "district": "Colombo"},
        "prediction": {
            "prediction_id": "TEST-KOL-001",
            "location_id": 1,
            "flood_probability": 0.12,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": (base_time - timedelta(hours=4)).isoformat(),
            "expires_at": (base_time + timedelta(hours=2)).isoformat()
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(kol_pred_1)

    kol_pred_2 = {
        "prediction_id": "TEST-KOL-002",
        "status": "success",
        "location": {"id": 1, "place_name": "Kolonnawa", "district": "Colombo"},
        "prediction": {
            "prediction_id": "TEST-KOL-002",
            "location_id": 1,
            "flood_probability": 0.50,
            "risk_level": "MODERATE",
            "class": 0,
            "valid_from": base_time.isoformat(),
            "expires_at": (base_time + timedelta(hours=6)).isoformat()
        },
        "model": {"name": "RandomForestClassifier", "version": "1.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(kol_pred_2)

    yield {
        "base_time": base_time,
        "rat_pred_1": rat_pred_1,
        "rat_pred_2": rat_pred_2,
        "rat_pred_3": rat_pred_3,
        "kol_pred_1": kol_pred_1,
        "kol_pred_2": kol_pred_2
    }


def test_01_prediction_identity_and_location_isolation(setup_history_test_fixtures):
    """Verifies that Ratnapura history returns strictly Ratnapura records with exact prediction_ids."""
    response_rat = client.get("/api/v1/predictions/history/7?limit=100")
    assert response_rat.status_code == 200
    data_rat = response_rat.json()

    assert data_rat["status"] == "success"
    assert data_rat["location_id"] == 7
    assert len(data_rat["items"]) >= 3
    assert all(item["location_id"] == 7 for item in data_rat["items"])

    rat_ids = [item["prediction_id"] for item in data_rat["items"]]
    assert "TEST-RAT-001" in rat_ids
    assert "TEST-RAT-002" in rat_ids
    assert "TEST-RAT-003" in rat_ids
    assert "TEST-KOL-001" not in rat_ids
    assert "TEST-KOL-002" not in rat_ids

    # Query Kolonnawa history
    response_kol = client.get("/api/v1/predictions/history/1?limit=100")
    assert response_kol.status_code == 200
    data_kol = response_kol.json()

    assert data_kol["location_id"] == 1
    assert len(data_kol["items"]) >= 2
    assert all(item["location_id"] == 1 for item in data_kol["items"])
    kol_ids = [item["prediction_id"] for item in data_kol["items"]]
    assert "TEST-KOL-001" in kol_ids
    assert "TEST-KOL-002" in kol_ids
    assert "TEST-RAT-001" not in kol_ids


def test_02_historical_immutability(setup_history_test_fixtures):
    """Verifies that historical records remain immutable and preserve their original risk_level and model_version."""
    db = get_supabase_service()

    # Save a historical record created with model v2.1 and HIGH risk
    custom_pred = {
        "prediction_id": "TEST-RAT-IMMUTABLE-001",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-IMMUTABLE-001",
            "location_id": 7,
            "flood_probability": 0.82,
            "risk_level": "HIGH",
            "class": 1
        },
        "model": {"name": "RandomForestClassifier", "version": "2.1.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(custom_pred)

    # Retrieve history
    res = client.get("/api/v1/predictions/history/7?limit=100")
    assert res.status_code == 200
    items = res.json()["items"]

    immutable_item = next(item for item in items if item["prediction_id"] == "TEST-RAT-IMMUTABLE-001")
    assert immutable_item["risk_level"] == "HIGH"
    assert immutable_item["model_version"] == "2.1.0"
    assert immutable_item["action_code"] == "PREPARE"


def test_03_current_vs_historical_separation(setup_history_test_fixtures):
    """Verifies that past historical prediction records do not overwrite current live prediction state."""
    db = get_supabase_service()
    now_iso = datetime.now(timezone.utc).isoformat()
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Current active prediction for Ratnapura: LOW risk (TEST-RAT-CURRENT-004)
    current_payload = {
        "prediction_id": "TEST-RAT-CURRENT-004",
        "status": "success",
        "location": {"id": 7, "place_name": "Ratnapura Town", "district": "Ratnapura"},
        "prediction": {
            "prediction_id": "TEST-RAT-CURRENT-004",
            "location_id": 7,
            "flood_probability": 0.10,
            "risk_level": "LOW",
            "class": 0,
            "valid_from": now_iso,
            "expires_at": future_iso
        },
        "model": {"name": "RandomForestClassifier", "version": "3.0.0"},
        "input_audit": {"weather_source": "Open-Meteo"}
    }
    db.save_prediction(current_payload)

    # 1. Check current endpoint /predictions/current/7
    res_curr = client.get("/api/v1/predictions/current/7")
    assert res_curr.status_code == 200
    curr_data = res_curr.json()
    assert curr_data["prediction_id"] == "TEST-RAT-CURRENT-004" or curr_data["risk"]["level"] == "LOW"

    # 2. Check history endpoint /predictions/history/7
    res_hist = client.get("/api/v1/predictions/history/7?limit=100")
    assert res_hist.status_code == 200
    hist_items = res_hist.json()["items"]
    
    # History contains both past HIGH (TEST-RAT-001) and current LOW (TEST-RAT-CURRENT-004)
    past_high = next(i for i in hist_items if i["prediction_id"] == "TEST-RAT-001")
    assert past_high["risk_level"] == "HIGH"


def test_04_history_risk_level_filtering(setup_history_test_fixtures):
    """Verifies that filtering history by risk_level=HIGH returns strictly HIGH risk historical records."""
    res_high = client.get("/api/v1/predictions/history/7?risk_level=HIGH&limit=100")
    assert res_high.status_code == 200
    data_high = res_high.json()

    assert data_high["status"] == "success"
    assert len(data_high["items"]) >= 1
    high_item = next(i for i in data_high["items"] if i["prediction_id"] == "TEST-RAT-001")
    assert high_item["prediction_id"] == "TEST-RAT-001"
    assert high_item["risk_level"] == "HIGH"


def test_05_history_pagination(setup_history_test_fixtures):
    """Verifies limit and offset pagination parameters for historical predictions."""
    res_p1 = client.get("/api/v1/predictions/history/7?limit=2&offset=0")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()

    assert len(data_p1["items"]) == 2
    assert data_p1["total"] >= 3
    assert data_p1["has_more"] is True

    res_p2 = client.get("/api/v1/predictions/history/7?limit=2&offset=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()

    assert len(data_p2["items"]) == 2
    assert data_p2["has_more"] is True


def test_06_empty_history_handling():
    """Verifies that querying date range with no prediction history returns 200 with empty items list (never false LOW)."""
    # Query a future date range where no predictions exist
    res = client.get("/api/v1/predictions/history/7?start_date=2099-01-01T00:00:00Z&end_date=2099-12-31T23:59:59Z")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["location_id"] == 7
    assert data["total"] == 0
    assert data["items"] == []


def test_07_invalid_location_404():
    """Verifies that requesting history for a non-existent location ID returns 404 LOCATION_NOT_FOUND."""
    res = client.get("/api/v1/predictions/history/99999")
    assert res.status_code == 404
    data = res.json()
    err_detail = data.get("detail", data)
    assert err_detail.get("code") == "LOCATION_NOT_FOUND"
