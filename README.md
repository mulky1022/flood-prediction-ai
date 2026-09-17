# Sri Lanka Live Early Flood Risk Prediction & Notification System

A production-ready early-warning platform combining a 64-feature Random Forest machine learning model, live meteorological telemetry from Open-Meteo, static GIS baseline datasets for all 25 Sri Lankan districts, and a FastAPI backend with Supabase PostgreSQL persistence.

---

## 1. System Architecture

```text
USER / CLIENT
      ↓
FastAPI Backend (/api/v1)
      ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Location Service   (data/locations.json & Supabase DB)   │
│ 2. Weather Service    (Open-Meteo 168h + 30d telemetry)     │
│ 3. Feature Builder    (Strict 64-feature vector alignment)  │
│ 4. ML Inference       (StandardScaler + RandomForest)       │
│ 5. Database Service   (Telemetry & prediction persistence)  │
└─────────────────────────────────────────────────────────────┘
      ↓
Supabase PostgreSQL (locations, weather_observations, predictions)
```

---

## 2. API Endpoints Specification

All application endpoints are versioned under `/api/v1`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Root deployment liveness health check |
| `GET` | `/api/v1/health` | Application status, model loading state, and DB connectivity |
| `GET` | `/api/v1/locations` | List all 33 monitoring stations across 25 Sri Lankan districts |
| `GET` | `/api/v1/locations/{id}` | Retrieve static GIS profile by location ID or record_id |
| `GET` | `/api/v1/weather/{id}` | Fetch live Open-Meteo observations and 7d/30d rainfall |
| `GET` | `/api/v1/predict/{id}` | Execute live end-to-end ML flood risk prediction |
| `GET` | `/api/v1/predictions/{id}` | Query historical prediction records with pagination |
| `GET` | `/api/v1/predictions/{id}/latest` | Fetch the most recent prediction audit for a location |

---

## 3. Database Schema (Supabase PostgreSQL)

Database DDL is located in [`database/schema.sql`](file:///c:/Users/dj/Desktop/project/flood%20prediction/database/schema.sql):
* `locations`: Static GIS coordinates, elevation, river distance, drainage index, soil type, and infrastructure metrics.
* `weather_observations`: Time-series ingestion cache from Open-Meteo.
* `predictions`: Complete inference audit trail storing flood probability, model version, and quality metadata.

---

## 4. Local Quickstart

### Prerequisites
* Python 3.10+
* Virtual environment (recommended)

### Installation
```bash
pip install -r requirements.txt
```

### Seeding Static Locations
```bash
python scripts/seed_locations.py
```

### Running Backend API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger API documentation will be available at `http://localhost:8000/docs`.

### Running Complete Test Suites
```bash
# Test location service
python scripts/test_locations.py

# Test live Open-Meteo connection
python scripts/test_openmeteo.py

# Test feature builder
python scripts/test_feature_builder.py

# Test local prediction engine
python scripts/test_prediction.py

# Test database service
python scripts/test_supabase.py

# Test FastAPI core endpoints
python scripts/test_api.py

# Test FastAPI prediction endpoints
python scripts/test_prediction_api.py
```
