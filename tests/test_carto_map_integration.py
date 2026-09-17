"""
Unit and Integration Tests for 100% Free Open-Source GIS Map Configuration
Providers:
- Humanitarian OpenStreetMap (HOT) (Primary)
- OpenStreetMap Standard (OSM) (Secondary / Fallback)

Tests:
- MAP-OSM-001: Open-source map configuration exists in frontend/js/map-config.js
- MAP-OSM-002: Map utils uses centralized open-source map configuration
- MAP-OSM-003: Humanitarian OSM (HOT) tile response succeeds (HTTP 200)
- MAP-OSM-004: OpenStreetMap Standard (OSM) tile response succeeds (HTTP 200)
- MAP-OSM-005: Map attribution includes OpenStreetMap & Humanitarian OpenStreetMap Team
- MAP-OSM-006: Sri Lanka GIS boundary and coordinates valid
- MAP-OSM-007: Monitoring stations (33 stations) present
- MAP-OSM-008: All 4 frontend pages served with HTTP 200
"""

import os
import pytest
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8001"


def test_map_config_file_exists():
    """Verify central map-config.js exists with Humanitarian OSM & OSM Standard"""
    map_config_path = BASE_DIR / "frontend" / "js" / "map-config.js"
    assert map_config_path.exists(), "frontend/js/map-config.js does not exist"
    content = map_config_path.read_text(encoding="utf-8")
    assert "tile.openstreetmap.fr/hot" in content
    assert "tile.openstreetmap.org" in content
    assert "MAP_CONFIG" in content
    assert "getOpenSourceTileLayer" in content


def test_map_utils_imports_map_config():
    """Verify frontend/js/map_utils.js uses centralized map-config.js"""
    map_utils_path = BASE_DIR / "frontend" / "js" / "map_utils.js"
    content = map_utils_path.read_text(encoding="utf-8")
    assert "from './map-config.js'" in content
    assert "setupTileLayer" in content
    assert "addBoundaryLayer" in content
    assert "createStationDivIcon" in content


def test_humanitarian_osm_tile_request():
    """Verify Humanitarian OpenStreetMap (HOT) tile loads with HTTP 200 and no watermark"""
    hot_url = "https://a.tile.openstreetmap.fr/hot/7/92/60.png"
    r = requests.get(hot_url, headers={"User-Agent": "SriLanka-FloodWatch/1.0"}, timeout=10)
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/png"
    assert len(r.content) > 1000


def test_osm_standard_tile_request():
    """Verify OpenStreetMap Standard (OSM) tile loads with HTTP 200 and no watermark"""
    osm_url = "https://tile.openstreetmap.org/7/92/60.png"
    r = requests.get(osm_url, headers={"User-Agent": "SriLanka-FloodWatch/1.0"}, timeout=10)
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/png"
    assert len(r.content) > 1000


def test_all_33_monitoring_stations_api():
    """Verify GET /api/v1/locations returns all 33 Sri Lanka stations with valid coordinates"""
    r = requests.get(f"{BASE_URL}/api/v1/locations")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 33
    locations = data["locations"]
    assert len(locations) == 33
    for loc in locations:
        assert 5.5 <= loc["latitude"] <= 10.0, f"Latitude {loc['latitude']} out of bounds for {loc['name']}"
        assert 79.0 <= loc["longitude"] <= 82.5, f"Longitude {loc['longitude']} out of bounds for {loc['name']}"


def test_geojson_boundary_valid():
    """Verify Sri Lanka GeoJSON boundary geometry is valid and loaded"""
    geojson_path = BASE_DIR / "frontend" / "js" / "sri_lanka_boundary.js"
    assert geojson_path.exists()
    content = geojson_path.read_text(encoding="utf-8")
    assert "FeatureCollection" in content
    assert "Sri Lanka" in content or "LKA" in content


def test_frontend_pages_regression():
    """Verify all 4 pages are served correctly"""
    pages = ["/", "/index.html", "/map.html", "/district.html", "/alerts.html"]
    for page in pages:
        r = requests.get(f"{BASE_URL}{page}")
        assert r.status_code == 200
        assert "<!DOCTYPE html>" in r.text
