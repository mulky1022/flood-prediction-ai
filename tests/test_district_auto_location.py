"""
Unit & Integration Tests for District Auto-Location Flow
Tests Haversine distance, nearest station matching, out-of-bounds detection,
and API response integrity.
"""

import math
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.routes.locations import haversine_distance_km

client = TestClient(app)


def test_haversine_distance_accuracy():
    """Verify Haversine formula against known geographic baselines."""
    # Colombo (6.9271, 79.8825) to Kandy (7.2906, 80.6337) is approx 95-97 km
    colombo_lat, colombo_lon = 6.9271, 79.8825
    kandy_lat, kandy_lon = 7.2906, 80.6337
    dist = haversine_distance_km(colombo_lat, colombo_lon, kandy_lat, kandy_lon)
    assert 90.0 <= dist <= 105.0, f"Expected 90-105km, got {dist}"

    # Zero distance
    assert haversine_distance_km(6.9271, 79.8825, 6.9271, 79.8825) == 0.0


def test_nearest_location_colombo():
    """Test nearest station detection for Colombo coordinates."""
    response = client.get("/api/v1/locations/nearest?latitude=6.93&longitude=79.88")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["nearest_location"]["id"] == 1
    assert "Kolonnawa" in data["nearest_location"]["place_name"]
    assert data["distance_km"] < 1.0


def test_nearest_location_kandy():
    """Test nearest station detection for Kandy coordinates."""
    response = client.get("/api/v1/locations/nearest?latitude=7.29&longitude=80.63")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["nearest_location"]["district"] == "Kandy"


def test_nearest_location_galle():
    """Test nearest station detection for Galle coordinates."""
    response = client.get("/api/v1/locations/nearest?latitude=6.03&longitude=80.21")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["nearest_location"]["district"] == "Galle"


def test_nearest_location_jaffna():
    """Test nearest station detection for Jaffna coordinates."""
    response = client.get("/api/v1/locations/nearest?latitude=9.66&longitude=80.01")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["nearest_location"]["district"] == "Jaffna"


def test_nearest_location_invalid_coords():
    """Test input validation for out-of-range coordinates."""
    response = client.get("/api/v1/locations/nearest?latitude=100.0&longitude=80.0")
    assert response.status_code == 422  # Validation error

    response = client.get("/api/v1/locations/nearest?latitude=6.9&longitude=200.0")
    assert response.status_code == 422  # Validation error


def test_district_location_details_pipeline():
    """Test full telemetry pipeline for a selected station."""
    station_id = 1
    # 1. Location Details
    loc_resp = client.get(f"/api/v1/locations/{station_id}")
    assert loc_resp.status_code == 200
    loc_data = loc_resp.json()
    assert loc_data["district"] == "Colombo"
    assert "elevation_m" in loc_data
    assert "distance_to_river_m" in loc_data

    # 2. Weather
    weather_resp = client.get(f"/api/v1/weather/{station_id}")
    assert weather_resp.status_code == 200
    weather_data = weather_resp.json()
    assert "current" in weather_data
    assert "rainfall" in weather_data or "rolling_aggregations" in weather_data

    # 3. Prediction
    pred_resp = client.get(f"/api/v1/predict/{station_id}")
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert "prediction" in pred_data
    assert "flood_probability" in pred_data["prediction"]
    assert "risk_level" in pred_data["prediction"]

    # 4. Alerts
    alert_resp = client.get(f"/api/v1/alerts/location/{station_id}")
    assert alert_resp.status_code == 200


def test_district_invalid_location_handling():
    """Test that invalid location IDs return 404 without crashing."""
    invalid_id = 999999
    loc_resp = client.get(f"/api/v1/locations/{invalid_id}")
    assert loc_resp.status_code == 404

    weather_resp = client.get(f"/api/v1/weather/{invalid_id}")
    assert weather_resp.status_code == 404

    pred_resp = client.get(f"/api/v1/predict/{invalid_id}")
    assert pred_resp.status_code == 404

    alert_resp = client.get(f"/api/v1/alerts/location/{invalid_id}")
    assert alert_resp.status_code == 404


def test_locations_list_contract():
    """Test locations list schema returns all Sri Lankan monitoring locations."""
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total"] >= 25
    assert len(data["locations"]) == data["total"]

    # Ensure each location has valid coordinates and names
    for loc in data["locations"]:
        assert -90.0 <= float(loc["latitude"]) <= 90.0
        assert -180.0 <= float(loc["longitude"]) <= 180.0
        assert len(loc["place_name"]) > 0
        assert len(loc["district"]) > 0

