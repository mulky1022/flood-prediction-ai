# Phase 7 Starting State Checkpoint
Sri Lanka Live Early Flood Risk Prediction & Notification System

## 1. Project Safety & Git Status
- **Environment**: Windows local development workspace (`c:\Users\dj\Desktop\project\flood prediction`)
- **Version Control**: Standalone codebase directory (ready for snapshot / local checkpointing)
- **FastAPI Process**: Uvicorn server running on `http://127.0.0.1:8000` with hot-reloader active

## 2. Current Backend Status
- **FastAPI Engine**: Version 1.0.0 active, serving all versioned routes (`/api/v1/health`, `/api/v1/locations`, `/api/v1/weather`, `/api/v1/predict`, `/api/v1/predictions`, `/api/v1/alerts`)
- **Open-Meteo Client**: Active with caching and retry policies (`services/openmeteo_service.py`)
- **Feature Builder**: 64-feature vector contract strictly enforced (`services/feature_builder.py`)

## 3. Current Frontend Status
- **Technology Stack**: Vanilla HTML/CSS/JS (Google Stitch telemetry design system) with Leaflet.js GIS
- **Live Pages**:
  - `index.html`: Live Dashboard with real Leaflet mini-map preview and telemetry widgets
  - `map.html`: Interactive GIS map with 33 station markers, search, risk filters, and inspection panel
  - `district.html`: In-depth location telemetry, precipitation sums, and analysis
  - `alerts.html`: Alerts & historical inference feed
- **GIS Cartography**: OpenStreetMap Standard + Humanitarian HOT tiles (100% free open-access, zero CARTO dependency)

## 4. Current Database Status
- **Supabase Connectivity**: Remote client initialized (`SUPABASE_URL` in `.env`)
- **Persistence & Fallback**: Robust in-memory & file-based storage fallback implemented in `SupabaseService` for zero-crash resilience
- **Schema**: Full PostgreSQL schema documented in `database/schema.sql` including `locations`, `weather_observations`, `predictions`, and `alerts` tables

## 5. Current ML Status
- **Model**: `RandomForestClassifier` v1.0.0 (`model/flood_model.pkl`)
- **Preprocessor**: `StandardScaler` (`model/preprocessor.pkl`)
- **Feature Contract**: Exactly 64 validated hydro-meteorological features (`model/feature_columns.json`)
- **Model Metadata**: `model/model_metadata.json` loaded and verified at startup

## 6. Current Alert & Notification Functionality
- **Alert Service**: `services/alert_service.py` provides evaluation, creation, deduplication, resolution, and acknowledgment
- **Alert Policy**: Configured in `config/alert_config.py` (LOW = No Alert, MODERATE = Advisory, HIGH/CRITICAL = Active Actionable Alert)
- **Notification Service**: `services/notification_service.py` with multi-channel support (UI = SENT, Email/SMS = NOT_CONFIGURED)
- **Alert Routes**: Registered in `api/routes/alerts.py` (`/api/v1/alerts`, `/api/v1/alerts/active`, `/api/v1/alerts/{id}`, `/api/v1/alerts/location/{id}`)
- **Cron Scheduler**: Background daemon script available in `scripts/process_alerts_cron.py`

## 7. Automated Test Suite Baseline
- **Test Suite**: 30 passing tests in `tests/` (`test_alert_api.py`, `test_alert_service.py`, `test_carto_map_integration.py`, `test_map_verification.py`, `test_notification_service.py`)
- **Test Coverage**: Complete coverage of API contracts, map coordinates, tile availability, duplicate alert prevention, alert lifecycle, and notification status reporting

## 8. Known Issues & Operational Notes
- Remote Supabase project requires execution of `database/schema.sql` if remote DDL has not been applied; local fallback currently maintains flawless operation
- Email/SMS notification providers are intentionally marked as `NOT_CONFIGURED` unless SMTP/Twilio credentials are provided in `.env`
