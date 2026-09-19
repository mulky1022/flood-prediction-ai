"""
Phase 1: Location Data Isolation & Identity Regression Test Suite

Verifies strict end-to-end location isolation across API endpoints:
- Ratnapura (ID 7 / LOC-007) vs Kolonnawa (ID 1 / LOC-001) vs Colombo (ID 1 / LOC-001) vs Kandy (ID 13 / LOC-013)
- No cross-location fallback on missing/invalid data
- Consistent location identity across Predictions, History, Alerts, and Weather
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_ratnapura_isolation():
    """
    Test 1 — Ratnapura Isolation:
    Request prediction for Ratnapura (ID 7).
    Assert location_id == 7 and place_name contains Ratnapura.
    """
    response = client.get("/api/v1/predict/7")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == 7
    assert "Ratnapura" in data["location"]["district"] or "Ratnapura" in data["location"]["place_name"]
    assert "Kolonnawa" not in data["location"]["place_name"]


def test_kolonnawa_isolation():
    """
    Test 2 — Kolonnawa Isolation:
    Request prediction for Kolonnawa (ID 1).
    Assert location_id == 1 and place_name contains Kolonnawa.
    """
    response = client.get("/api/v1/predict/1")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["location"]["id"] == 1
    assert "Kolonnawa" in data["location"]["place_name"]
    assert "Ratnapura" not in data["location"]["place_name"]


def test_canonical_record_id_lookup():
    """
    Verify canonical string identifiers (e.g. LOC-007 vs LOC-001) resolve to correct location.
    """
    resp_ratnapura = client.get("/api/v1/locations/LOC-007")
    assert resp_ratnapura.status_code == 200
    assert resp_ratnapura.json()["id"] == 7
    assert resp_ratnapura.json()["district"] == "Ratnapura"

    resp_kolonnawa = client.get("/api/v1/locations/LOC-001")
    assert resp_kolonnawa.status_code == 200
    assert resp_kolonnawa.json()["id"] == 1
    assert "Kolonnawa" in resp_kolonnawa.json()["place_name"]


def test_no_cross_location_fallback_on_invalid_location():
    """
    Test 3 & 5 — No Cross-Location Fallback:
    Request invalid location ID (9999).
    Assert backend returns 404 LOCATION_NOT_FOUND and absolutely NOT Kolonnawa data.
    """
    response = client.get("/api/v1/predict/9999")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "LOCATION_NOT_FOUND"
    assert "location" not in data or data.get("location") is None


def test_location_switching_sequence():
    """
    Test 4 — Location Switching Sequence:
    Request sequential predictions for Ratnapura (7) -> Kolonnawa (1) -> Ratnapura (7) -> Kandy (13).
    Verify every result strictly matches the requested location.
    """
    sequence = [
        (7, "Ratnapura"),
        (1, "Kolonnawa"),
        (7, "Ratnapura"),
        (13, "Matara")
    ]

    for loc_id, expected_keyword in sequence:
        res = client.get(f"/api/v1/predict/{loc_id}")
        assert res.status_code == 200
        loc_data = res.json()["location"]
        assert loc_data["id"] == loc_id
        assert expected_keyword in loc_data["district"] or expected_keyword in loc_data["place_name"]


def test_dashboard_consistency():
    """
    Test 6 — Dashboard Consistency:
    Verify /locations/{id}, /weather/{id}, /predict/{id} all return the exact same location details.
    """
    target_id = 7 # Ratnapura
    r_loc = client.get(f"/api/v1/locations/{target_id}")
    r_weather = client.get(f"/api/v1/weather/{target_id}")
    r_pred = client.get(f"/api/v1/predict/{target_id}")

    assert r_loc.status_code == 200
    assert r_weather.status_code == 200
    assert r_pred.status_code == 200

    loc_id_from_loc = r_loc.json()["id"]
    loc_id_from_weather = r_weather.json()["location"]["id"]
    loc_id_from_pred = r_pred.json()["location"]["id"]

    assert loc_id_from_loc == target_id
    assert loc_id_from_weather == target_id
    assert loc_id_from_pred == target_id


def test_map_consistency():
    """
    Test 7 — Map Consistency:
    Verify /locations returns all locations with correct canonical IDs and no data corruption.
    """
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    locations = response.json()["locations"]
    assert len(locations) == 33

    ratnapura_nodes = [l for l in locations if l["id"] == 7]
    assert len(ratnapura_nodes) == 1
    assert ratnapura_nodes[0]["district"] == "Ratnapura"


def test_alert_consistency():
    """
    Test 8 — Alert Consistency:
    Verify /alerts/location/{location_id} strictly filters by the requested location.
    """
    target_id = 7
    response = client.get(f"/api/v1/alerts/location/{target_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    for item in data["items"]:
        assert item["location_id"] == target_id


def test_history_consistency():
    """
    Test 9 — History Consistency:
    Verify /predictions/{location_id} returns history items exclusively belonging to target_id.
    """
    target_id = 7
    # Trigger a prediction first to populate history
    client.get(f"/api/v1/predict/{target_id}")

    response = client.get(f"/api/v1/predictions/{target_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["location_id"] == target_id

    for item in data["items"]:
        assert item["location_id"] == target_id


def test_data_integrity_mismatch_guard():
    """
    Test 10 — Mismatch Integrity Guard:
    Verify that an invalid or string location parameter does not silently fall back to location 1.
    """
    invalid_ids = ["99999", "INVALID_NAME", "-1"]
    for inv_id in invalid_ids:
        r = client.get(f"/api/v1/predict/{inv_id}")
        assert r.status_code in [404, 422]
        if r.status_code == 404:
            assert r.json()["code"] == "LOCATION_NOT_FOUND"
