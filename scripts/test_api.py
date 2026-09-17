"""
Phase 5: FastAPI Core Endpoints Integration Test Suite

Tests:
1. Root Health Check (/api/health)
2. Versioned Health Check (/api/v1/health)
3. Locations Listing (/api/v1/locations)
4. Location Filter by District (/api/v1/locations?district=Gampaha)
5. Single Location by ID (/api/v1/locations/7)
6. Live Weather Retrieval (/api/v1/weather/7)
7. Negative Tests: 404 on non-existent location ID
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app


def run_tests():
    print("=" * 60)
    print("Sri Lanka FloodWatch — Phase 5 FastAPI Core Endpoints Test")
    print("=" * 60)

    client = TestClient(app)

    # 1. Root Health Check
    print("\n[TEST 1] GET /api/health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ok"
    print(f"  ✓ Status 200 OK: {data}")

    # 2. Version 1 Health Check
    print("\n[TEST 2] GET /api/v1/health...")
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_loaded"] is True
    print(f"  ✓ Status 200 OK: model_loaded = {data['model_loaded']}, version = {data['version']}")

    # 3. Locations Listing
    print("\n[TEST 3] GET /api/v1/locations...")
    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total"] >= 33
    print(f"  ✓ Status 200 OK: Retrieved {data['total']} locations.")

    # 4. Filter Locations by District
    print("\n[TEST 4] GET /api/v1/locations?district=Gampaha...")
    resp = client.get("/api/v1/locations?district=Gampaha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    for loc in data["locations"]:
        assert loc["district"] == "Gampaha"
    print(f"  ✓ Status 200 OK: Filtered {data['total']} locations for Gampaha.")

    # 5. Single Location by ID
    print("\n[TEST 5] GET /api/v1/locations/7...")
    resp = client.get("/api/v1/locations/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 7
    assert data["district"] == "Ratnapura"
    print(f"  ✓ Status 200 OK: Found {data['place_name']} ({data['district']})")

    # 6. Live Weather Retrieval
    print("\n[TEST 6] GET /api/v1/weather/7 (Live Open-Meteo Ingestion)...")
    resp = client.get("/api/v1/weather/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "temperature_c" in data["current"]
    assert "rainfall_7d_mm" in data["rainfall"]
    print(f"  ✓ Status 200 OK: Live Temp={data['current']['temperature_c']}°C, 7d Rain={data['rainfall']['rainfall_7d_mm']}mm")

    # 7. Negative Test: 404 on Missing Location
    print("\n[TEST 7] Negative Test: GET /api/v1/locations/99999 (Expected 404)...")
    resp = client.get("/api/v1/locations/99999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "LOCATION_NOT_FOUND"
    print(f"  ✓ Status 404 Handled: {data}")

    # 8. Negative Test: 404 on Weather for Missing Location
    print("\n[TEST 8] Negative Test: GET /api/v1/weather/99999 (Expected 404)...")
    resp = client.get("/api/v1/weather/99999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "LOCATION_NOT_FOUND"
    print(f"  ✓ Status 404 Handled: {data}")

    print("\n" + "=" * 60)
    print("ALL FASTAPI CORE ENDPOINT TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
