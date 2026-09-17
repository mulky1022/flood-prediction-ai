"""
Phase 5: FastAPI Prediction & History Endpoints Test Suite

Tests:
1. Live Prediction Pipeline (/api/v1/predict/7)
2. Database Persistence Verification of generated prediction
3. Prediction History Retrieval (/api/v1/predictions/7)
4. Latest Prediction Retrieval (/api/v1/predictions/7/latest)
5. Negative Tests: 404 on invalid locations across prediction routes
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
    print("Sri Lanka FloodWatch — Phase 5 Prediction API Test Suite")
    print("=" * 60)

    client = TestClient(app)

    # 1. Live Prediction
    print("\n[TEST 1] GET /api/v1/predict/7 (Live Prediction for Ratnapura)...")
    resp = client.get("/api/v1/predict/7")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "success"
    assert data["ready_for_prediction"] is True

    pred = data["prediction"]
    assert "flood_probability" in pred
    assert "class" in pred
    assert 0.0 <= pred["flood_probability"] <= 1.0

    print("  ✓ Status 200 OK — Prediction Generated:")
    print(f"    - Location: {data['location']['place_name']} ({data['location']['district']})")
    print(f"    - Class: {pred['class']}")
    print(f"    - Flood Probability: {pred['flood_probability'] * 100:.2f}%")
    print(f"    - Model: {data['model']['name']} v{data['model']['version']}")
    print(f"    - Quality Status: {data['data_quality']['weather_quality']}")

    # 2. Prediction History
    print("\n[TEST 2] GET /api/v1/predictions/7 (Querying Prediction History)...")
    resp_hist = client.get("/api/v1/predictions/7?limit=5")
    assert resp_hist.status_code == 200
    data_hist = resp_hist.json()
    assert data_hist["status"] == "success"
    assert data_hist["total"] >= 1
    print(f"  ✓ Status 200 OK — Found {data_hist['total']} historical records.")
    print(f"    - Most recent: {data_hist['items'][0]['created_at']} | P={data_hist['items'][0]['flood_probability']}")

    # 3. Latest Prediction Lookup
    print("\n[TEST 3] GET /api/v1/predictions/7/latest (Querying Latest Record)...")
    resp_latest = client.get("/api/v1/predictions/7/latest")
    assert resp_latest.status_code == 200
    data_latest = resp_latest.json()
    assert data_latest["location_id"] == 7
    assert "flood_probability" in data_latest
    print(f"  ✓ Status 200 OK — Latest Record Verified (P = {data_latest['flood_probability'] * 100:.2f}%)")

    # 4. Negative Test: Prediction for Missing Location
    print("\n[TEST 4] Negative Test: GET /api/v1/predict/99999 (Expected 404)...")
    resp_neg = client.get("/api/v1/predict/99999")
    assert resp_neg.status_code == 404
    data_neg = resp_neg.json()
    assert data_neg["status"] == "error"
    assert data_neg["code"] == "LOCATION_NOT_FOUND"
    print(f"  ✓ Handled correctly with 404: {data_neg}")

    # 5. Negative Test: History for Missing Location
    print("\n[TEST 5] Negative Test: GET /api/v1/predictions/99999 (Expected 404)...")
    resp_neg_h = client.get("/api/v1/predictions/99999")
    assert resp_neg_h.status_code == 404
    print(f"  ✓ Handled correctly with 404: {resp_neg_h.json()}")

    print("\n" + "=" * 60)
    print("ALL PREDICTION API TESTS PASSED (100% SUCCESS)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
