"""
Phase 7 — Flood Map Verification Test Suite.
Verifies GIS map prediction endpoints, location isolation, canonical risk and action
consumption, timing validity, missing/stale data handling, and CRS 84 coordinate validity.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from services.risk_engine import RiskEngine

client = TestClient(app)


def test_01_map_predictions_endpoint_canonical_contract():
    """
    Test 1: Verify /api/v1/predictions/map returns valid batch predictions for all map stations
    with canonical risk_level, action_code, action_message, and status.
    """
    response = client.get("/api/v1/predictions/map")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "total" in data
    assert "predictions" in data
    assert isinstance(data["predictions"], list)
    assert len(data["predictions"]) > 0

    first_item = data["predictions"][0]
    assert "location_id" in first_item
    assert "record_id" in first_item
    assert "name" in first_item
    assert "district" in first_item
    assert "latitude" in first_item
    assert "longitude" in first_item
    assert "risk_level" in first_item
    assert first_item["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert "action_code" in first_item
    assert first_item["action_code"] in ["SAFE", "MONITOR", "PREPARE", "EVACUATE"]
    assert "action_message" in first_item
    assert "status" in first_item


def test_02_map_station_canonical_prediction_consumption():
    """
    Test 2: Verify station detail query /api/v1/predictions/current/7 returns
    complete canonical Phase 5 risk and action block.
    """
    response = client.get("/api/v1/predictions/current/7")
    assert response.status_code == 200
    data = response.json()

    # Location identity match
    assert data["location"]["location_id"] == 7
    assert "Ratnapura" in data["location"]["name"]

    # Canonical Risk & Action pairing
    risk_level = data["risk"]["level"]
    action_code = data["action"]["code"]

    if risk_level == "LOW":
        assert action_code == "SAFE"
    elif risk_level == "MODERATE":
        assert action_code == "MONITOR"
    elif risk_level == "HIGH":
        assert action_code == "PREPARE"
    elif risk_level == "CRITICAL":
        assert action_code == "EVACUATE"

    assert len(data["action"]["message"]) > 0


def test_03_ratnapura_vs_kolonnawa_map_isolation():
    """
    Test 3: Ratnapura (ID 7) vs Kolonnawa (ID 1) location isolation on Map data.
    Ratnapura must NEVER return Kolonnawa data or vice versa.
    """
    res_rat = client.get("/api/v1/predictions/current/7")
    res_kol = client.get("/api/v1/predictions/current/1")

    assert res_rat.status_code == 200
    assert res_kol.status_code == 200

    data_rat = res_rat.json()
    data_kol = res_kol.json()

    assert data_rat["location"]["location_id"] == 7
    assert data_kol["location"]["location_id"] == 1
    assert data_rat["location"]["location_id"] != data_kol["location"]["location_id"]


def test_04_dashboard_map_location_id_preservation():
    """
    Test 4: Verify location_id query parameters for Ratnapura and Kolonnawa
    consistently yield matching canonical location records across API calls.
    """
    for loc_id in [1, 4, 7, 10, 13]:
        res = client.get(f"/api/v1/predictions/current/{loc_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["location"]["location_id"] == loc_id


def test_05_missing_station_prediction_404_handling():
    """
    Test 5: Requesting non-existent station ID 9999 returns HTTP 404,
    triggering missing prediction state on Map instead of fake LOW risk.
    """
    res = client.get("/api/v1/predictions/current/9999")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data or "code" in data


def test_06_stale_prediction_flag_detection():
    """
    Test 6: Verify canonical prediction API returns is_stale boolean flag and validity range.
    """
    res = client.get("/api/v1/predictions/current/7")
    assert res.status_code == 200
    data = res.json()

    assert "is_stale" in data
    assert isinstance(data["is_stale"], bool)
    assert "valid_from" in data
    assert "valid_until" in data


def test_07_geojson_export_crs84_validation():
    """
    Test 7: Verify all 33 monitoring stations have valid EPSG:4326 (WGS 84) coordinates
    suitable for standard GeoJSON feature collection export.
    """
    res = client.get("/api/v1/locations")
    assert res.status_code == 200
    data = res.json()

    assert "locations" in data
    locations = data["locations"]
    assert len(locations) > 0

    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        assert lat is not None and -90.0 <= lat <= 90.0, f"Invalid latitude {lat} for station {loc.get('id')}"
        assert lon is not None and -180.0 <= lon <= 180.0, f"Invalid longitude {lon} for station {loc.get('id')}"
