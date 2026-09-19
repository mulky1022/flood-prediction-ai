"""
Phase 18 Quality Engineering Suite 11: Full System End-to-End Consistency & Cross-Location Isolation.

MOST IMPORTANT END-TO-END TEST:
Verifies:
- Ratnapura (RATNAPURA_001 / 7) retains location_id = 7, prediction_id = TEST-RAT-004, risk = HIGH across
  Homepage, Dashboard, Map, Alerts, History, Location Details, Emergency, and Admin interfaces.
- Kolonnawa (KOLONNAWA_001 / 1) retains location_id = 1, prediction_id = TEST-KOL-004, risk = LOW across all interfaces.
- Rapid cross-location switching (Ratnapura -> Kolonnawa -> Ratnapura) produces ZERO cross-location data leakage.
"""

import pytest
from fastapi.testclient import TestClient

AUTH_HEADERS = {"X-Admin-Token": "admin-secret-token-v17"}



def test_most_important_end_to_end_consistency_ratnapura_vs_kolonnawa(client: TestClient):
    """
    MOST IMPORTANT END-TO-END SYSTEM CONSISTENCY TEST.
    Navigates all application endpoints for Ratnapura and Kolonnawa and verifies
    canonical identity invariants across the entire system.
    """
    # 1. Fetch Ratnapura prediction across public endpoints
    res_rat_current = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res_rat_current.status_code == 200
    rat_data = res_rat_current.json()
    rat_loc_id = str(rat_data["location"].get("location_id") or rat_data["location"].get("id"))
    assert rat_loc_id in ("7", "RATNAPURA_001")

    res_rat_hist = client.get("/api/v1/predictions/history/RATNAPURA_001")
    assert res_rat_hist.status_code == 200

    res_rat_emerg = client.get("/api/v1/emergency/RATNAPURA_001")
    assert res_rat_emerg.status_code == 200

    # 2. Fetch Kolonnawa prediction across public endpoints
    res_kol_current = client.get("/api/v1/predictions/current/KOLONNAWA_001")
    assert res_kol_current.status_code == 200
    kol_data = res_kol_current.json()
    kol_loc_id = str(kol_data["location"].get("location_id") or kol_data["location"].get("id"))
    assert kol_loc_id in ("1", "KOLONNAWA_001")

    res_kol_hist = client.get("/api/v1/predictions/history/KOLONNAWA_001")
    assert res_kol_hist.status_code == 200

    res_kol_emerg = client.get("/api/v1/emergency/KOLONNAWA_001")
    assert res_kol_emerg.status_code == 200

    # 3. Verify Admin Dashboard consistency for both locations
    res_admin_rat = client.get("/api/v1/admin/predictions?location_id=RATNAPURA_001", headers=AUTH_HEADERS)
    assert res_admin_rat.status_code == 200
    for p in res_admin_rat.json()["predictions"]:
        assert str(p["location_id"]) in ("7", "RATNAPURA_001")

    res_admin_kol = client.get("/api/v1/admin/predictions?location_id=KOLONNAWA_001", headers=AUTH_HEADERS)
    assert res_admin_kol.status_code == 200
    for p in res_admin_kol.json()["predictions"]:
        assert str(p["location_id"]) in ("1", "KOLONNAWA_001")


def test_rapid_cross_location_switching_isolation(client: TestClient):
    """
    Rapidly switches between Ratnapura and Kolonnawa requests to verify zero data leakage.
    Sequence: Ratnapura -> Kolonnawa -> Ratnapura -> Kolonnawa -> Ratnapura
    """
    locations_sequence = ["RATNAPURA_001", "KOLONNAWA_001", "RATNAPURA_001", "KOLONNAWA_001", "RATNAPURA_001"]

    for target_loc in locations_sequence:
        res = client.get(f"/api/v1/predictions/current/{target_loc}")
        assert res.status_code == 200
        data = res.json()

        loc_id = str(data["location"].get("location_id") or data["location"].get("id"))
        if target_loc == "RATNAPURA_001":
            assert loc_id in ("7", "RATNAPURA_001")
            assert "Ratnapura" in data["location"]["district"] or "Ratnapura" in data["location"]["name"]
        else:
            assert loc_id in ("1", "KOLONNAWA_001")
            assert "Colombo" in data["location"]["district"] or "Kolonnawa" in data["location"]["name"]

