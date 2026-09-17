# Phase 8 Starting State Checkpoint (Freeze Phase 7)
Sri Lanka Live Early Flood Risk Prediction & Notification System

## Checkpoint Metadata
- **Date**: 2026-09-17
- **Git Branch**: `master`
- **Git Commit**: `05d438f`
- **Git Freeze Tag**: `phase-7-complete-before-phase-8`

---

## 1. Backend Status
- **Framework**: FastAPI v1.0.0 running under Uvicorn (`http://127.0.0.1:8000`)
- **API Endpoints**:
  - `/api/v1/health` (Service health & readiness)
  - `/api/v1/locations`, `/api/v1/locations/{id}` (33 monitored stations)
  - `/api/v1/weather/{id}` (Open-Meteo live observations & antecedent accumulations)
  - `/api/v1/predict/{id}` (64-feature ML inference)
  - `/api/v1/predictions/{id}`, `/api/v1/predictions/{id}/latest` (Inference history)
  - `/api/v1/alerts`, `/api/v1/alerts/active`, `/api/v1/alerts/{id}`, `/api/v1/alerts/location/{id}` (Alert lifecycle)
  - `/api/v1/alerts/{id}/acknowledge`, `/api/v1/alerts/{id}/resolve`, `/api/v1/alerts/process/{id}` (Alert actions)

---

## 2. Frontend Status
- **Design Language**: Google Stitch telemetry UI system
- **Basemap Engine**: Leaflet.js v1.9.4 with 100% free open-source Humanitarian OpenStreetMap (HOT) & OpenStreetMap Standard (OSM)
- **Active Pages**:
  - `index.html` (Live Dashboard with synchronized Leaflet mini-map preview)
  - `map.html` (Full Flood Monitoring Map with 33 station nodes, search, and filters)
  - `district.html` (Detailed location telemetry & rainfall metrics)
  - `alerts.html` (Alerts & historical prediction log)

---

## 3. Database Configuration
- **Adapter**: `services/supabase_service.py`
- **Client Status**: Remote client connected (`SUPABASE_URL` in `.env`) with resilient fallback to local in-memory/file storage
- **Schema**: Defined in `database/schema.sql` (`locations`, `weather_observations`, `predictions`, `alerts`)

---

## 4. Alert & Notification Implementation
- **Alert Service**: `services/alert_service.py` with duplicate prevention, state evaluation, and lifecycle handling (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`)
- **Policy**: Configured in `config/alert_config.py` (LOW = No Alert / Resolve, MOD = Advisory, HIGH/CRIT = Operational Alert)
- **Notification Service**: `services/notification_service.py` (UI = `SENT`, Email/SMS = `NOT_CONFIGURED` without mock delivery)
- **Background Cron**: Active in `scripts/process_alerts_cron.py`

---

## 5. ML Pipeline Status
- **Model**: `RandomForestClassifier` v1.0.0 (`model/flood_model.pkl`)
- **Scaler**: `StandardScaler` (`model/preprocessor.pkl`)
- **Contract**: Exactly 64 hydro-meteorological features (`model/feature_columns.json`)
- **Metadata**: `model/model_metadata.json`

---

## 6. Known Blockers
- **None**: Baseline test suite passes (29/29 tests in `tests/`).
