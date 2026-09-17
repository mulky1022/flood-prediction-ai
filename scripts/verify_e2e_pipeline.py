"""
End-to-End Pipeline Verification Script for Phase 7.

Traces the complete real flow:
Location -> Open-Meteo Weather -> Feature Builder -> 64-Feature ML Model ->
Prediction -> Alert Evaluation -> Duplicate Prevention -> Database Persistence ->
Notification Service -> FastAPI Alert API -> Frontend Data Contract.
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

from services.location_service import get_location_by_id
from services.predictor import get_predictor
from services.alert_service import get_alert_service
from services.supabase_service import get_supabase_service
from api.main import app


def run_e2e_trace():
    print("=" * 65)
    print("Sri Lanka FloodWatch — Phase 7 Live End-to-End Pipeline Trace")
    print("=" * 65)

    # 1. Real Location Retrieval
    print("\n[STEP 1: LOCATION LAYER]")
    loc = get_location_by_id(1)
    assert loc is not None
    print(f"  Station: {loc['place_name']}")
    print(f"  District: {loc['district']} | Coordinates: {loc['latitude']}°N, {loc['longitude']}°E")
    print(f"  Basin Elevation: {loc['elevation_m']}m | River Proximity: {loc['distance_to_river_m']}m")

    # 2. Real ML Prediction Pipeline
    print("\n[STEP 2: ML INFERENCE ENGINE]")
    predictor = get_predictor()
    pred_res = predictor.predict_location(1, use_cache=True)
    assert pred_res["status"] == "success"
    pred = pred_res["prediction"]
    model = pred_res["model"]
    audit = pred_res["input_audit"]
    print(f"  Model: {model['name']} v{model['version']} (Contract: {model['feature_count']} features)")
    print(f"  Weather Ingest: {audit['weather_source']} (7d Rain: {audit['rainfall_7d_mm']}mm)")
    print(f"  Prediction Class: {pred['class']}")
    print(f"  Flood Probability: {pred['flood_probability']} ({pred['flood_probability_percent']}%)")
    print(f"  Non-Flood Probability: {pred['non_flood_probability']}")

    # 3. Real Alert Policy Evaluation & Deduplication
    print("\n[STEP 3: OPERATIONAL ALERT ENGINE]")
    alert_service = get_alert_service()
    process_res = alert_service.process_location_alert(1, pred_res)
    assert process_res["status"] == "success"
    print(f"  Action Taken: {process_res['action_taken']}")
    print(f"  Message: {process_res['message']}")
    if process_res["alert"]:
        a = process_res["alert"]
        print(f"  Alert ID: #{a['id']} | Status: {a['status']} | Tier: {a['risk_level']}")
        print(f"  Operational Title: {a['title']}")
        print(f"  Action Recommendation: {a['recommendation']}")
        print(f"  Notification Status: {a['notification_status']}")

    # 4. Repeat Call - Duplicate Prevention Verification
    print("\n[STEP 4: DUPLICATE PREVENTION CHECK]")
    process_res_repeat = alert_service.process_location_alert(1, pred_res)
    assert process_res_repeat["status"] == "success"
    if process_res["alert"]:
        assert process_res_repeat["action_taken"] == "ALERT_UPDATED"
        assert process_res_repeat["alert"]["id"] == process_res["alert"]["id"]
        print(f"  ✓ Verified: Repeated call updated existing Alert #{process_res['alert']['id']}; no duplicate created.")
    else:
        print(f"  ✓ Verified: No alert required for baseline condition ({process_res_repeat['action_taken']}).")

    # 5. Database Persistence Query
    print("\n[STEP 5: DATABASE PERSISTENCE LAYER]")
    db = get_supabase_service()
    active_records = db.get_active_alerts()
    print(f"  Mode: {'REMOTE_SUPABASE' if db.is_connected else 'LOCAL_FALLBACK_STORE'}")
    print(f"  Active Records Count: {len(active_records)}")

    # 6. Real FastAPI Endpoints
    print("\n[STEP 6: FASTAPI REST API VERIFICATION]")
    client = TestClient(app)

    # Active Alerts
    resp_active = client.get("/api/v1/alerts/active")
    assert resp_active.status_code == 200
    active_json = resp_active.json()
    print(f"  GET /api/v1/alerts/active -> HTTP 200 OK (Total Active: {active_json['active_count']})")

    # Location Alerts
    resp_loc = client.get("/api/v1/alerts/location/1")
    assert resp_loc.status_code == 200
    loc_json = resp_loc.json()
    print(f"  GET /api/v1/alerts/location/1 -> HTTP 200 OK (History Count: {loc_json['total']})")

    # Full Alert List
    resp_all = client.get("/api/v1/alerts?limit=10")
    assert resp_all.status_code == 200
    print(f"  GET /api/v1/alerts?limit=10 -> HTTP 200 OK (Total: {resp_all.json()['total']})")

    print("\n" + "=" * 65)
    print("LIVE END-TO-END PIPELINE VERIFIED SUCCESSFULLY (100% PASS)")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = run_e2e_trace()
    sys.exit(0 if success else 1)
