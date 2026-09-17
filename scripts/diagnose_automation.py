"""
Comprehensive Automation & Pipeline Diagnostic Script.
Traces every step of the pipeline from Location/GPS to Open-Meteo to 64-feature ML,
Alert Engine, Deduplication, Notification, and Production Vercel Endpoints.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import time
import math
import requests
from datetime import datetime

# Local imports
from services.location_service import get_all_locations, get_location_by_id
from weather.weather_processor import get_weather_for_location
from services.feature_builder import build_feature_dataframe
from services.predictor import get_predictor
from services.alert_service import get_alert_service
from services.notification_service import get_notification_service
from services.supabase_service import get_supabase_service

PROD_BASE_URL = "https://flood-prediction-roan.vercel.app"

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def run_diagnostics():
    print("=" * 70)
    print("AUTOMATION PIPELINE DIAGNOSTIC TRACE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    
    report = {}

    # Step 1 & 2 & 3 & 4: Location & Nearest Station Math
    print("\n--- [STEP 1-7] LOCATION & NEAREST STATION MATH ---")
    locations = get_all_locations()
    print(f"Total Calibrated Locations Loaded: {len(locations)}")
    assert len(locations) >= 25, "Expected at least 25 calibrated locations"
    
    # Test user GPS coordinates (e.g., Colombo: 6.9271, 79.8612; Kandy: 7.2906, 80.6337; Galle: 6.0535, 80.2210)
    test_coords = [
        {"name": "Colombo User", "lat": 6.9271, "lon": 79.8612},
        {"name": "Kandy User", "lat": 7.2906, "lon": 80.6337},
        {"name": "Galle User", "lat": 6.0535, "lon": 80.2210},
    ]
    
    for tc in test_coords:
        closest = None
        min_dist = float("inf")
        for loc in locations:
            dist = haversine_distance(tc["lat"], tc["lon"], loc["latitude"], loc["longitude"])
            if dist < min_dist:
                min_dist = dist
                closest = loc
        print(f"User at {tc['name']} ({tc['lat']}, {tc['lon']}) -> Nearest Station: ID {closest['id']} ({closest['place_name']}, {closest['district']}) @ {min_dist:.2f} km")
    report["step_1_7_location"] = "PASS"

    # Step 8 & 9 & 10: Live Weather via Open-Meteo
    print("\n--- [STEP 8-10] LIVE OPEN-METEO WEATHER INTEGRATION ---")
    loc_sample = locations[0]
    loc_id = loc_sample["id"]
    print(f"Fetching live weather for Station ID {loc_id} ({loc_sample['place_name']}, {loc_sample['district']})...")
    weather_res = get_weather_for_location(loc_id, use_cache=False)
    print(f"Weather Status: {weather_res.get('status')}")
    assert weather_res.get("status") == "success", f"Weather fetch failed: {weather_res}"
    current = weather_res.get("current", {})
    rainfall = weather_res.get("rainfall", {})
    print(f"  Current Temp: {current.get('temperature_c')} C, Rain: {current.get('precipitation_mm')} mm, Wind: {current.get('wind_speed_kmh')} km/h")
    print(f"  7-Day Rain: {rainfall.get('rainfall_7d_mm')} mm (Quality: {rainfall.get('data_quality')}), Monthly: {rainfall.get('monthly_rainfall_mm')} mm")
    report["step_8_10_weather"] = "PASS"

    # Step 11: Feature Builder (Exact 64 Features)
    print("\n--- [STEP 11] FEATURE BUILDER (64 FEATURES) ---")
    df_features, q_report = build_feature_dataframe(location=loc_sample, weather=weather_res)
    print(f"  Features DataFrame Shape: {df_features.shape}")
    print(f"  Quality Gate Ready: {q_report.get('ready_for_prediction')}")
    print(f"  Missing Features: {q_report.get('missing_features')}")
    print(f"  Invalid Features: {q_report.get('invalid_features')}")
    assert df_features.shape == (1, 64), f"Feature shape mismatch! Expected (1, 64), got {df_features.shape}"
    report["step_11_features"] = "PASS"

    # Step 12 & 13 & 14: ML Prediction (Random Forest Inference)
    print("\n--- [STEP 12-14] ML PREDICTION & RISK CLASSIFICATION ---")
    predictor = get_predictor()
    pred_res = predictor.predict_location(loc_id, use_cache=False)
    print(f"Prediction Status: {pred_res.get('status')}")
    assert pred_res.get("status") == "success", f"Prediction failed: {pred_res}"
    pred_data = pred_res.get("prediction", {})
    print(f"  Class: {pred_data.get('class')}")
    print(f"  Flood Probability: {pred_data.get('flood_probability')} ({pred_data.get('flood_probability_percent')}%)")
    print(f"  Non-Flood Probability: {pred_data.get('non_flood_probability')}")
    print(f"  Risk Level: {pred_data.get('risk_level')}")
    report["step_12_14_ml_prediction"] = "PASS"

    # Step 15 & 16 & 17: Alert Engine, Policy & Duplicate Protection
    print("\n--- [STEP 15-17] ALERT POLICY & DEDUPLICATION ---")
    alert_service = get_alert_service()
    
    # 1. Evaluate policy
    eval_res = alert_service.evaluate_prediction_for_alert(pred_res)
    print(f"Policy Evaluation -> Risk: {eval_res.get('risk_level')}, Alertable: {eval_res.get('is_alertable')}")
    print(f"  Title: {eval_res.get('title')}")
    print(f"  Message: {eval_res.get('message')}")
    
    # 2. Process location alert (Run 1)
    res_1 = alert_service.process_location_alert(loc_id, pred_res)
    print(f"Alert Processing Run 1 -> Action: {res_1.get('action_taken')}")
    
    # 3. Process location alert (Run 2 - Deduplication Check)
    res_2 = alert_service.process_location_alert(loc_id, pred_res)
    print(f"Alert Processing Run 2 -> Action: {res_2.get('action_taken')}")
    if res_1.get("action_taken") == "ALERT_CREATED":
        assert res_2.get("action_taken") == "ALERT_UPDATED", "Deduplication failed! Second run should update, not create duplicate"
    report["step_15_17_alert_engine"] = "PASS"

    # Step 18 & 19 & 20: Supabase Persistence & Notification Channels
    print("\n--- [STEP 18-20] DATABASE & NOTIFICATION STATUS ---")
    db = get_supabase_service()
    print(f"Supabase Client Active: {db.is_connected}")
    notif_service = get_notification_service()
    status_summary = notif_service.get_channel_status()
    print(f"Notification Channels Config: {json.dumps(status_summary, indent=2)}")
    report["step_18_20_db_notif"] = "PASS"

    # Step 21 & 22: Production Vercel Endpoints & Frontend Loading
    print("\n--- [STEP 21-22] PRODUCTION VERCEL ENDPOINTS AUDIT ---")
    endpoints = [
        ("/", "Frontend Dashboard"),
        ("/district", "District Location Tracking Page"),
        ("/district?location_id=1", "District Deep-Link"),
        ("/map", "Interactive Leaflet Flood Map"),
        ("/alerts", "Alerts & Historical Log"),
        ("/api/health", "Backend Health Check"),
        ("/api/v1/locations", "Monitoring Stations Dataset"),
        ("/api/v1/weather/1", "Open-Meteo Weather Endpoint"),
        ("/api/v1/predict/1", "ML Inference Endpoint"),
        ("/api/v1/alerts/active", "Active Alerts Endpoint"),
    ]
    
    prod_failures = []
    for ep, desc in endpoints:
        url = f"{PROD_BASE_URL}{ep}"
        try:
            t0 = time.time()
            r = requests.get(url, timeout=15)
            dt = round((time.time() - t0) * 1000, 1)
            print(f"  [{r.status_code}] {url} ({dt}ms) - {desc}")
            if r.status_code != 200:
                prod_failures.append(f"{url} returned status {r.status_code}")
        except Exception as e:
            print(f"  [ERROR] {url}: {e}")
            prod_failures.append(f"{url} failed with exception: {e}")
            
    if not prod_failures:
        report["step_21_22_production"] = "PASS"
    else:
        report["step_21_22_production"] = f"FAIL: {prod_failures}"

    print("\n" + "=" * 70)
    print("FINAL DIAGNOSTIC SUMMARY")
    for k, v in report.items():
        print(f"  {k}: {v}")
    print("=" * 70)

if __name__ == "__main__":
    run_diagnostics()
