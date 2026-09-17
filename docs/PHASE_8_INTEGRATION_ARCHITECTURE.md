# PHASE 8 SYSTEM INTEGRATION & ARCHITECTURE DOCUMENT

**Project:** Sri Lanka Live Early Flood Risk Prediction & Notification System  
**Phase:** 8 — Full System Integration, QA & E2E Validation  
**Date:** 2026-09-17  

---

## 1. System Topology & Dataflow Architecture

The Sri Lanka Flood Risk Early Warning & Notification System integrates real-time meteorological telemetry, spatial static catchment features, ML-driven probabilistic inference, an operational alert engine, persistence mechanisms, and a multi-page Google Stitch interface:

```
                                  ┌────────────────────────┐
                                  │   OPERATOR / CITIZEN   │
                                  └───────────┬────────────┘
                                              │ Browser (HTTP)
                                              ▼
                        ┌──────────────────────────────────────────┐
                        │        GOOGLE STITCH FRONTEND UI         │
                        │  - Live Dashboard (dashboard.html)       │
                        │  - Flood Monitoring Map (map.html)       │
                        │  - Location Details (district.html)      │
                        │  - Alerts & History (alerts.html)        │
                        └─────────────────────┬────────────────────┘
                                              │ REST API (JSON)
                                              ▼
                        ┌──────────────────────────────────────────┐
                        │          FASTAPI BACKEND SERVICE         │
                        │  - Health & Telemetry Routes             │
                        │  - Locations & Spatial Endpoints         │
                        │  - Weather Aggregation Endpoints         │
                        │  - ML Prediction & Risk Endpoints        │
                        │  - Alert Management & Action Endpoints   │
                        └───────┬──────────────┬─────────────┬─────┘
                                │              │             │
                ┌───────────────┘              │             └────────────────┐
                ▼                              ▼                              ▼
┌──────────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│     STATIC LOCATION LAYER    │ │    OPEN-METEO WEATHER     │ │   PERSISTENCE LAYER       │
│  - 33 Monitoring Stations    │ │  - Live Telemetry Ingest  │ │  - Supabase PostgreSQL /   │
│  - 25 Administrative Dists   │ │  - 24h Hourly Forecast    │ │    Local Fallback Store   │
│  - Soil/Basin/Elev Metrics   │ │  - 7d/30d Antecedent Rain │ │  - Alert Records & History│
└───────────────┬──────────────┘ └─────────────┬─────────────┘ └──────────────┬────────────┘
                │                              │                              │
                └───────────────┬──────────────┘                              │
                                ▼                                             │
                ┌──────────────────────────────┐                              │
                │     64-FEATURE PIPELINE      │                              │
                │  - Spatial/Rainfall Join     │                              │
                │  - StandardScaler Normalizer │                              │
                │  - Strict Feature Ordering   │                              │
                └───────────────┬──────────────┘                              │
                                ▼                                             │
                ┌──────────────────────────────┐                              │
                │     RANDOM FOREST MODEL      │                              │
                │  - 500 Decision Trees        │                              │
                │  - Max Depth = 10            │                              │
                │  - Output: P(Flood ∈ [0, 1]) │                              │
                └───────────────┬──────────────┘                              │
                                ▼                                             │
                ┌──────────────────────────────┐                              │
                │     OPERATIONAL ALERT ENGINE ├──────────────────────────────┘
                │  - Risk Tier Evaluation      │
                │  - Deduplication & Cooldown  │
                │  - Lifecycle & Auto-Resolve  │
                └───────────────┬──────────────┘
                                ▼
                ┌──────────────────────────────┐
                │    NOTIFICATION DISPATCHER   │
                │  - Web/In-App (SENT)         │
                │  - SMS/Email (CONFIG-AWARE)  │
                └──────────────────────────────┘
```

---

## 2. Subsystem Interface Contracts

### A. Location Spatial Layer (`locations/locations.json`)
- **Total Locations:** 33 stations covering all 25 administrative districts in Sri Lanka.
- **Attributes per location:** `id`, `name`, `district`, `province`, `river_basin`, `latitude`, `longitude`, `elevation_m`, `catchment_area_sqkm`, `soil_type`, `hydrological_soil_group`, `urban_drainage_density`, `flood_history_frequency`, `distance_to_river_km`.

### B. Meteorological Aggregation Layer (`weather/open_meteo_service.py`)
- **Source:** Open-Meteo Archive and Forecast REST APIs.
- **Derived Metrics:** Current temperature, humidity, precipitation, 24-hour total, 7-day cumulative antecedent rainfall, and 30-day monthly rainfall.
- **Performance & Resilience:** Disk & memory caching with TTL preventing redundant requests.

### C. 64-Feature Machine Learning Layer (`models/`)
- **Input Contract:** Exact 64 features derived from spatial topography, soil hydrology, and meteorological telemetry.
- **Artifacts:**
  - `models/flood_model.pkl`: Scikit-Learn `RandomForestClassifier` (500 estimators, max_depth=10).
  - `models/preprocessor.pkl`: Scikit-Learn `StandardScaler` fitted on 64 dimensions.
  - `models/feature_columns.json`: Canonical feature name dictionary.

### D. Operational Alert & Policy Layer (`services/alert_service.py`)
- **Thresholds:**
  - `CRITICAL`: Flood Probability $\ge 80\%$
  - `HIGH`: Flood Probability $\ge 60\%$
  - `MODERATE`: Flood Probability $\ge 35\%$
  - `LOW`: Flood Probability $< 35\%$ (Non-alertable; triggers auto-resolution of active alerts)
- **Deduplication:** Updates existing `ACTIVE` alert records without spawning duplicates.
- **Transitions:** `ACTIVE` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`.

---

## 3. Deployment & Operational States

| Component | Development State | Production Target (Phase 9) |
|---|---|---|
| **Backend** | Uvicorn / FastAPI Local Server | Dockerized FastAPI on Cloud Run / VPS |
| **Frontend** | Google Stitch Static Assets | Vercel / Netlify / Cloudflare Pages |
| **Database** | In-Memory Local Fallback Store | Supabase Managed PostgreSQL |
| **Weather** | Open-Meteo with TTL Cache | Open-Meteo with Redis Caching |
| **Notifications** | Web Broadcast (Active), SMS/Email (Not Configured) | Web Broadcast + Twilio SMS + SMTP Email |
