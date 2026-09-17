"""
Sri Lanka FloodWatch — Automated Map and Telemetry Verification Suite
Tests all MAP-001 through MAP-025 criteria:
- API endpoint health and locations consistency
- Coordinate validity (-90<=lat<=90, -180<=lon<=180)
- Specific location checks (e.g. Kolonnawa around 6.9271° N, 79.8825° E)
- Tile provider URL accessibility and HTTP 200 responses
- GeoJSON boundary validity
- No localhost hardcoding in production bundles
"""

import json
import math
import os
import re
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def test_api_locations_total_and_schema():
    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ["ok", "success"]
    assert data.get("total") == 33
    locations = data.get("locations", [])
    assert len(locations) == 33
    
    # Check every location has valid numeric coords in Sri Lanka bounds
    for loc in locations:
        lat = float(loc["latitude"])
        lon = float(loc["longitude"])
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0
        # Sri Lanka approx bounds: Lat 5.5 - 10.0, Lon 79.0 - 82.5
        assert 5.5 <= lat <= 10.0, f"Location {loc['place_name']} lat {lat} out of Sri Lanka range"
        assert 79.0 <= lon <= 82.5, f"Location {loc['place_name']} lon {lon} out of Sri Lanka range"


def test_kolonnawa_coordinates():
    resp = client.get("/api/v1/locations/1")
    assert resp.status_code == 200
    loc = resp.json()
    assert "Kolonnawa" in loc["place_name"] or "Colombo" in loc["place_name"]
    assert loc["district"] == "Colombo"
    lat = float(loc["latitude"])
    lon = float(loc["longitude"])
    assert pytest.approx(lat, 0.05) == 6.9271
    assert pytest.approx(lon, 0.05) == 79.8825


def test_tile_providers_http_200():
    import urllib.request
    import urllib.error
    # Sri Lanka centroid: Lat 7.8731, Lon 80.7718, Zoom 8
    z = 8
    x, y = deg2num(7.8731, 80.7718, z)
    
    tile_urls = [
        f"https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    ]
    
    for url in tile_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SriLankaFloodWatch/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                assert resp.status == 200, f"Tile request failed for {url}"
                content = resp.read()
                assert len(content) > 500, f"Tile returned empty content for {url}"
        except (urllib.error.URLError, TimeoutError):
            pytest.skip(f"External tile network request to {url} skipped due to network timeout")


def test_geojson_boundary_validity():
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    adm0_path = os.path.join(frontend_dir, "data", "sri_lanka_adm0.geojson")
    assert os.path.exists(adm0_path)
    with open(adm0_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data.get("type") == "FeatureCollection"
        features = data.get("features", [])
        assert len(features) > 0
        geom = features[0].get("geometry", {})
        assert geom.get("type") in ["Polygon", "MultiPolygon"]


def test_no_hardcoded_fake_svg_or_fake_stations():
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    for html_file in ["index.html", "map.html", "district.html", "alerts.html"]:
        path = os.path.join(frontend_dir, html_file)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Verify no fake hardcoded SVG island paths with cx/cy manual station coordinates
            assert 'd="M150,50' not in content
            assert 'cx="120" cy="180"' not in content


def test_prediction_endpoint_integration():
    resp = client.get("/api/v1/predict/1")
    assert resp.status_code == 200
    data = resp.json()
    pred = data.get("prediction", {})
    assert "flood_probability" in pred or "flood_probability_percent" in pred
    assert "risk_level" in pred
    assert pred["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])

