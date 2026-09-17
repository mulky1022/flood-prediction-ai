# Sri Lanka Live Early Flood Risk Prediction & Notification System
## Backend API Verification & Specification Document

**Project:** Sri Lanka Live Early Flood Risk Prediction & Notification System  
**Framework:** FastAPI (Python 3.11)  
**Host / Base URL:** `http://127.0.0.1:8000`  
**API Version:** `v1.0.0`  
**Routing Status:** `ROUTING STATUS: FIXED`

---

## 1. Executive Summary

The backend service for the **Sri Lanka Live Early Flood Risk Prediction & Notification System** provides real-time flood risk inference by orchestrating:
1. **Calibrated Geospatial Layer**: 33 static monitoring locations covering all 25 districts of Sri Lanka (`data/locations.json`).
2. **Real-Time Hydrological Telemetry**: Open-Meteo Forecast & Archive APIs with rolling 7-day and 30-day cumulative precipitation models (`services/openmeteo_service.py`).
3. **Machine Learning Pipeline**: A strict 64-feature `RandomForestClassifier` (500 estimators, max depth 10) with StandardScaler preprocessing (`model/flood_model.pkl`).
4. **Data Persistence Layer**: Supabase PostgreSQL database integration with resilient local in-memory fallback (`services/supabase_service.py`).

---

## 2. Interactive Documentation & Schema URLs

| Resource | Protocol | URL | Status |
| :--- | :--- | :--- | :--- |
| **Interactive Swagger UI** | HTTP GET | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | `PASS (200 OK)` |
| **ReDoc Documentation** | HTTP GET | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | `PASS (200 OK)` |
| **OpenAPI 3.1.0 Specification** | HTTP GET | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) | `PASS (200 OK)` |

---

## 3. Registered Route Registry

```text
============================================================
REGISTERED FASTAPI ROUTES
============================================================

APPLICATION ROUTES:
METHOD     PATH
------------------------------------------------------------
GET        /api/health
GET        /api/v1/health
GET        /api/v1/locations
GET        /api/v1/locations/{location_id}
GET        /api/v1/weather/{location_id}
GET        /api/v1/predict/{location_id}
GET        /api/v1/predictions/{location_id}
GET        /api/v1/predictions/{location_id}/latest

FASTAPI SYSTEM/DOCUMENTATION ROUTES:
METHOD     PATH
------------------------------------------------------------
GET        /openapi.json
GET        /docs
GET        /docs/oauth2-redirect
GET        /redoc

============================================================
END OF ROUTE LIST
============================================================
```

---

## 4. Route Verification & Testing Matrix

```text
============================================================
ENDPOINT VERIFICATION MATRIX
============================================================

Endpoint                                   Registered   Tested   HTTP Status   Result
--------------------------------------------------------------------------------------
/api/v1/health                             YES          YES      200 OK        PASS
/api/v1/locations                          YES          YES      200 OK        PASS
/api/v1/locations/{location_id}            YES          YES      200 OK        PASS
/api/v1/weather/{location_id}              YES          YES      200 OK        PASS
/api/v1/predict/{location_id}              YES          YES      200 OK        PASS
/api/v1/predictions/{location_id}          YES          YES      200 OK        PASS
/api/v1/predictions/{location_id}/latest   YES          YES      200 OK        PASS
============================================================
```

---

## 5. Endpoint Specifications & Sample Responses

### 5.1 Health Check Endpoint
- **Route:** `GET /api/v1/health` (also accessible at `/api/health`)
- **Purpose:** Cloud liveness and model runtime readiness probe.
- **Sample Response:**
```json
{
  "status": "ok",
  "service": "Sri Lanka FloodWatch API",
  "version": "1.0.0",
  "model_loaded": true,
  "database_connected": false
}
```

---

### 5.2 Locations Endpoint
- **Route:** `GET /api/v1/locations`
- **Purpose:** Retrieves all 33 calibrated flood monitoring stations across Sri Lanka.
- **Sample Response:**
```json
{
  "status": "success",
  "total": 33,
  "locations": [
    {
      "id": 1,
      "record_id": "LOC-001",
      "district": "Colombo",
      "place_name": "Kolonnawa (Kelani River Lower)",
      "latitude": 6.9271,
      "longitude": 79.8825,
      "elevation_m": 4.5,
      "distance_to_river_m": 220.0,
      "population_density_per_km2": 3800.0,
      "built_up_percent": 78.5,
      "drainage_index": 0.32,
      "landcover": "Urban",
      "soil_type": "Loamy"
    }
  ]
}
```

---

### 5.3 Single Location Detail Endpoint
- **Route:** `GET /api/v1/locations/{location_id}`
- **Test ID:** `1` (Kolonnawa, Colombo)
- **Sample Response:**
```json
{
  "id": 1,
  "record_id": "LOC-001",
  "district": "Colombo",
  "place_name": "Kolonnawa (Kelani River Lower)",
  "latitude": 6.9271,
  "longitude": 79.8825,
  "elevation_m": 4.5,
  "distance_to_river_m": 220.0,
  "population_density_per_km2": 3800.0,
  "built_up_percent": 78.5,
  "drainage_index": 0.32,
  "ndvi": 0.12,
  "ndwi": 0.28,
  "historical_flood_count": 7.0,
  "infrastructure_score": 68.0,
  "nearest_hospital_km": 1.8,
  "nearest_evac_km": 0.9,
  "landcover": "Urban",
  "soil_type": "Loamy",
  "water_supply": "Surface water",
  "electricity": "Mixed",
  "road_quality": "Good (paved)",
  "urban_rural": "Urban",
  "water_presence_flag": "Likely"
}
```

---

### 5.4 Live Weather Telemetry Endpoint
- **Route:** `GET /api/v1/weather/{location_id}`
- **Test ID:** `1`
- **Sample Response:**
```json
{
  "status": "success",
  "location": {
    "id": 1,
    "district": "Colombo",
    "place_name": "Kolonnawa (Kelani River Lower)",
    "latitude": 6.9271,
    "longitude": 79.8825
  },
  "current": {
    "temperature_c": 24.2,
    "humidity_percent": 96.0,
    "precipitation_mm": 0.0,
    "rain_mm": 0.0,
    "wind_speed_kmh": 6.4,
    "soil_moisture_percent": 34.0,
    "river_discharge_m3s": 12.4
  },
  "rolling_aggregations": {
    "precipitation_sum_7d_mm": 18.6,
    "precipitation_sum_30d_mm": 84.2,
    "max_daily_rainfall_7d_mm": 12.2
  },
  "source": "Open-Meteo API",
  "timestamp": "2026-09-16T23:20:55+05:30"
}
```

---

### 5.5 Real-Time ML Flood Prediction Endpoint
- **Route:** `GET /api/v1/predict/{location_id}`
- **Test ID:** `1`
- **Sample Response:**
```json
{
  "status": "success",
  "ready_for_prediction": true,
  "location": {
    "id": 1,
    "district": "Colombo",
    "place_name": "Kolonnawa (Kelani River Lower)"
  },
  "prediction": {
    "class": 1,
    "flood_probability": 0.7553,
    "flood_probability_percent": 75.53,
    "non_flood_probability": 0.2447,
    "risk_level": "HIGH",
    "recommendation": "Activate local flood response units and issue early warning notices for low-lying areas near Kelani River Lower.",
    "model_name": "RandomForestClassifier",
    "model_version": "1.0.0",
    "features_used_count": 64,
    "data_quality_status": "GOOD"
  }
}
```

---

### 5.6 Prediction History & Latest Prediction Endpoints
- **Routes:** 
  - `GET /api/v1/predictions/{location_id}`
  - `GET /api/v1/predictions/{location_id}/latest`
- **Test ID:** `1`
- **Sample Response:**
```json
{
  "id": null,
  "location_id": 1,
  "created_at": "2026-09-16T23:21:05.923564+05:30",
  "prediction_class": 1,
  "flood_probability": 0.7553,
  "non_flood_probability": 0.2447,
  "model_name": "RandomForestClassifier",
  "model_version": "1.0.0",
  "data_quality_status": "GOOD",
  "data_source": "memory"
}
```

---

## 6. Architecture & Code Structure

```text
api/
├── main.py                    # Root FastAPI app configuration & CORS
├── routes/
│   ├── health.py              # Health check & system status
│   ├── locations.py           # Static monitoring station queries
│   ├── weather.py             # Live Open-Meteo telemetry
│   └── predictions.py         # 64-feature ML inference & historical logs
└── schemas/
    ├── common.py              # Base response models
    ├── location.py            # Location response models
    ├── weather.py             # Weather telemetry models
    └── prediction.py          # Prediction output models
```

---

## 7. Status Declaration

- **Verification Date:** 2026-09-16
- **Test Results:** 100% Pass (All 7 versioned endpoints verified live)
- **Status:** **ROUTING STATUS: FIXED**
