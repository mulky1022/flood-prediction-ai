"""
Verification script for Part 1 and Part 2 of user QA requirements.
"""

import os
import json
from services.supabase_service import get_supabase_service
from services.predictor import get_predictor
from services.location_service import get_all_locations, get_location_by_id

def verify_system():
    print("=== 1. Checking Supabase Connection & Schema ===")
    db = get_supabase_service()
    print(f"Supabase connected: {db.is_connected}")
    
    print("\n=== 2. Triggering Live Inference for Location 1 (Kolonnawa) ===")
    predictor = get_predictor()
    pred_res = predictor.predict_location(1, use_cache=False, derive_leakage_baselines=True)
    print(f"Inference Status: {pred_res.get('status')}")
    print(f"Flood Probability: {pred_res.get('prediction', {}).get('flood_probability_percent')}%")
    print(f"Risk Level: {pred_res.get('prediction', {}).get('risk_level')}")
    
    print("\n=== 3. Persisting to Database ===")
    save_res = db.save_prediction(pred_res)
    print(f"Save Result: {save_res.get('status')} -> {save_res.get('persisted_to')}")
    
    print("\n=== 4. Querying Prediction History for Location 1 ===")
    history = db.get_prediction_history(1, limit=5)
    print(f"Retrieved {len(history)} history records for Location 1:")
    for i, h in enumerate(history):
        print(f"  [{i+1}] ID: {h.get('id')}, Created At: {h.get('created_at')}, Prob: {h.get('flood_probability')}, Class: {h.get('prediction_class')}, Quality: {h.get('data_quality_status')}")
    
    print("\n=== 5. Querying Alerts Stream / Active Alerts ===")
    active_alerts = db.get_active_alerts(limit=5)
    print(f"Active Alerts Count: {len(active_alerts)}")
    for a in active_alerts:
        print(f"  Alert ID {a.get('id')}: {a.get('title')} ({a.get('risk_level')}) - Status: {a.get('status')}")

    print("\n=== 6. Total Monitored Locations ===")
    locs = get_all_locations()
    print(f"Total stations: {len(locs)}")
    print(f"First 3: {[l['place_name'] for l in locs[:3]]}")

if __name__ == "__main__":
    verify_system()
