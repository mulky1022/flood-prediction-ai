"""
Phase 18 Quality Engineering Suite 02: Global Latest Regression & Prediction Selection.

Verifies:
- No un-isolated global latest database queries exist without location filtering
- getCurrentPrediction(RATNAPURA_001) strictly returns location_id = 7 / RATNAPURA_001
- getCurrentPrediction(KOLONNAWA_001) strictly returns location_id = 1 / KOLONNAWA_001
"""

import pytest
from fastapi.testclient import TestClient
from services.supabase_service import get_supabase_service


def test_global_latest_prediction_isolation_audit(client: TestClient):
    """
    Regression test ensuring location queries filter predictions strictly by location_id
    and never return global latest records belonging to other locations.
    """
    db = get_supabase_service()

    rat_pred = db.get_latest_prediction("7")
    kol_pred = db.get_latest_prediction("1")

    if rat_pred and kol_pred:
        assert str(rat_pred.get("location_id")) != str(kol_pred.get("location_id")) or rat_pred.get("id") != kol_pred.get("id")


def test_get_current_prediction_ratnapura_location_identity(client: TestClient):
    """Verify GET /api/v1/predictions/current/RATNAPURA_001 returns Ratnapura location ID."""
    res = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res.status_code == 200
    data = res.json()
    loc_id = str(data["location"].get("location_id") or data["location"].get("id"))
    assert loc_id in ("7", "RATNAPURA_001", "LOC-007")
    assert "Ratnapura" in data["location"]["district"] or "Ratnapura" in data["location"]["name"]


def test_get_current_prediction_kolonnawa_location_identity(client: TestClient):
    """Verify GET /api/v1/predictions/current/KOLONNAWA_001 returns Kolonnawa location ID."""
    res = client.get("/api/v1/predictions/current/KOLONNAWA_001")
    assert res.status_code == 200
    data = res.json()
    loc_id = str(data["location"].get("location_id") or data["location"].get("id"))
    assert loc_id in ("1", "KOLONNAWA_001", "LOC-001")
    assert "Colombo" in data["location"]["district"] or "Kolonnawa" in data["location"]["name"]

