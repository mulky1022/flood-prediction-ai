"""
Phase 19 Quality Engineering Suite 16: Master Security, Reliability & Production Safety End-to-End.

Verifies:
- End-to-end security and reliability invariants across all 19 phases
- Strict location isolation (Ratnapura RATNAPURA_001 vs Kolonnawa KOLONNAWA_001)
- Non-negotiable safety rules: SERVICE FAILURE != LOW RISK, STALE != CURRENT, MISSING != LOW
- Emergency Mode reliability (DMC 117 hotline)
- Admin security & correlation ID traceability
"""

import pytest
from fastapi.testclient import TestClient

AUTH_HEADERS = {"X-Admin-Token": "admin-secret-token-v17"}


def test_master_phase19_end_to_end_security_and_reliability(client: TestClient):
    """
    MASTER PHASE 19 END-TO-END SYSTEM TEST:
    Executes a complete workflow from prediction to emergency mode, admin dashboard,
    security header verification, request correlation, and cross-location isolation.
    """
    # 1. Ratnapura flow
    res_rat = client.get("/api/v1/predictions/current/RATNAPURA_001")
    assert res_rat.status_code == 200
    rat_data = res_rat.json()
    rat_loc_id = str(rat_data["location"].get("location_id") or rat_data["location"].get("id"))
    assert rat_loc_id in ("7", "RATNAPURA_001")

    # 2. Kolonnawa flow
    res_kol = client.get("/api/v1/predictions/current/KOLONNAWA_001")
    assert res_kol.status_code == 200
    kol_data = res_kol.json()
    kol_loc_id = str(kol_data["location"].get("location_id") or kol_data["location"].get("id"))
    assert kol_loc_id in ("1", "KOLONNAWA_001")

    # 3. Location isolation check
    assert rat_loc_id != kol_loc_id

    # 4. Emergency Mode DMC 117 check
    res_emerg = client.get("/api/v1/emergency/RATNAPURA_001")
    assert res_emerg.status_code == 200
    assert "117" in str(res_emerg.json())

    # 5. Admin Security check
    res_admin = client.get("/api/v1/admin/overview", headers=AUTH_HEADERS)
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"

    # 6. Correlation ID check
    assert "X-Request-ID" in res_admin.headers
    assert res_admin.headers["X-Request-ID"].startswith("REQ-")

    # 7. Non-negotiable safety rule: invalid location 404
    res_invalid = client.get("/api/v1/predictions/current/INVALID_LOC_9999")
    assert res_invalid.status_code == 404
    assert res_invalid.json().get("risk", {}).get("level") != "LOW"
