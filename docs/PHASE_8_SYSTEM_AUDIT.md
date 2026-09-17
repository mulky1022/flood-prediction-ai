# Phase 8 — Full System Architecture Audit
Sri Lanka Live Early Flood Risk Prediction & Notification System

## 1. System Architecture Overview

The system implements a synchronized, real-time hydrometeorological early warning pipeline:

```
[User Browser / Stitch UI]
        │
        ▼  (REST API / JSON)
[FastAPI Backend Engine (Port 8000)]
   ├── /api/v1/health
   ├── /api/v1/locations
   ├── /api/v1/weather/{id}
   ├── /api/v1/predict/{id}
   ├── /api/v1/predictions/{id}
   └── /api/v1/alerts
        │
        ├── Location Data (33 Monitored Stations across 25 Districts)
        └── Live Open-Meteo Synoptic Observations & 7d/30d Accumulations
                     │
                     ▼
        [Feature Builder Service (64 Features)]
                     │
                     ▼
        [StandardScaler Preprocessor]
                     │
                     ▼
        [RandomForestClassifier v1.0.0]
                     │
                     ▼
        [Prediction Engine Output]
        (Probability, Class, Risk Level)
                     │
                     ▼
        [Operational Alert Engine]
        (Policy Evaluation, Deduplication, Lifecycle)
                     │
                     ├── [Supabase Database Persistence / Resilient Fallback]
                     └── [Notification Dispatch Service (UI / Email / SMS)]
```

---

## 2. Existing APIs & Routing Matrix

| Route | Method | Description | Primary Consumer |
|---|---|---|---|
| `/api/v1/health` | GET | Health & database/model status | Health monitors / Deployment probes |
| `/api/v1/config` | GET | Client public configuration | Frontend configuration sync |
| `/api/v1/locations` | GET | All 33 monitoring stations | Map, Dashboard dropdown, District |
| `/api/v1/locations/{id}` | GET | Single station GIS metadata | District details, Inspection panels |
| `/api/v1/weather/{id}` | GET | Real-time weather & 7d/30d rainfall | Weather cards, Hydrology metrics |
| `/api/v1/predict/{id}` | GET | 64-feature ML inference & risk level | Status cards, Map tooltips |
| `/api/v1/predictions/{id}` | GET | Paginated prediction audit history | History charts, Audit tables |
| `/api/v1/predictions/{id}/latest`| GET | Latest prediction record | Quick recovery, Feed caching |
| `/api/v1/alerts` | GET | Filtered operational alerts | Alerts & History page |
| `/api/v1/alerts/active` | GET | Active emergency & advisory alerts | Header badge, Map overlays |
| `/api/v1/alerts/{id}` | GET | Single alert details | Alert dialogs |
| `/api/v1/alerts/location/{id}` | GET | Station-specific alerts | Location Details alert badge |
| `/api/v1/alerts/{id}/acknowledge`| POST | Operator acknowledgment | Alerts management console |
| `/api/v1/alerts/{id}/resolve`| POST | Operator alert resolution | Alerts management console |
| `/api/v1/alerts/process/{id}` | POST | On-demand alert evaluation | Triggered station inference |

---

## 3. Database Tables & Data Persistence

Defined in `database/schema.sql` and implemented in `services/supabase_service.py`:

1. **`locations`**:
   - Stores 33 static GIS profiles: `id`, `record_id`, `district`, `place_name`, `latitude`, `longitude`, `elevation_m`, `distance_to_river_m`, `drainage_index`, `infrastructure_score`, etc.
2. **`weather_observations`**:
   - Stores raw & processed Open-Meteo ingestions: `temperature_c`, `humidity_percent`, `precipitation_mm`, `rainfall_7d_mm`, `monthly_rainfall_mm`, `window_start`, `window_end`, etc.
3. **`predictions`**:
   - Stores complete ML audit trails: `location_id`, `prediction_class`, `flood_probability`, `non_flood_probability`, `model_name`, `model_version`, `feature_count` (64), `data_quality_status`.
4. **`alerts`**:
   - Stores alert lifecycle records: `location_id`, `risk_level`, `flood_probability`, `prediction_class`, `title`, `message`, `recommendation`, `status` (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`), `notification_status`, `created_at`, `updated_at`, `acknowledged_at`, `resolved_at`.

---

## 4. Machine Learning Pipeline Flow

1. **Input Resolution**: Resolves static GIS parameters from `data/locations.json`.
2. **Weather Retrieval**: `services/openmeteo_service.py` queries Open-Meteo forecast API (168h hourly history) and archive API (30d daily history) with 30-minute local disk cache.
3. **Feature Construction**: `services/feature_builder.py` constructs a 1-row `pandas.DataFrame` conforming strictly to `model/feature_columns.json` (64 columns in exact order).
4. **Data Quality Gate**: Validates that all 64 required columns are present, non-null, and within acceptable physical ranges.
5. **Preprocessing**: `model/preprocessor.pkl` (`StandardScaler`) standardizes features.
6. **Classification & Probability**: `model/flood_model.pkl` (`RandomForestClassifier`) calculates probability via `predict_proba()`:
   - `flood_probability = probabilities[1]`
   - `prediction_class = 1 if flood_probability >= 0.50 else 0`
   - `risk_level`: CRITICAL (>=80%), HIGH (65-80%), MODERATE (35-65%), LOW (<35%).

---

## 5. Alert & Notification Flow

1. **Evaluation**: `services/alert_service.py` inspects the prediction output against `config/alert_config.py`.
2. **Deduplication**: `prevent_duplicate_alerts()` checks for existing `ACTIVE` records for that station. If present, it updates telemetry metrics without duplicating alert records.
3. **State Transitions**:
   - No Alert -> ACTIVE (on HIGH/CRITICAL)
   - ACTIVE -> ACKNOWLEDGED (manual operator action)
   - ACTIVE / ACKNOWLEDGED -> RESOLVED (on risk drop to LOW)
4. **Notification Dispatch**: `services/notification_service.py`:
   - Web / Dashboard UI: Dispatched immediately, marked `SENT`.
   - Email / SMS: Honestly set to `NOT_CONFIGURED` when credentials are not configured in `.env`.

---

## 6. Frontend Flow & User Experience

1. **Live Dashboard (`index.html`)**:
   - Fetches locations dropdown, default station telemetry, live probability gauge, 4 weather cards, recent predictions stream, and active alert counter badge.
   - Embeds Leaflet mini-map preview bounded to Sri Lanka with risk-colored nodes.
2. **Flood Map (`map.html`)**:
   - Centralized GIS cartography powered by Humanitarian OSM (HOT) and OpenStreetMap Standard (OSM).
   - Renders 33 monitoring stations with interactive DivIcons, debounced search, risk filter pills, and selected station inspection panel.
3. **Location Details (`district.html`)**:
   - Comprehensive hydrological & atmospheric analysis for a selected station.
4. **Alerts & History (`alerts.html`)**:
   - Active operational alert feed with filter toggles and historical prediction table.

---

## 7. Known Blockers & Test Risks

- **Remote Supabase DDL**: The remote Supabase instance may not have executed `database/schema.sql`. The system currently operates seamlessly via the in-memory fallback adapter in `services/supabase_service.py`.
- **Open-Meteo Rate Limiting**: The client implements local caching (`cache/weather/`) and retry policies to prevent external throttling during automated test runs.
- **CARTO Basemap Deprecation**: CARTO basemap was replaced by 100% free open-source Humanitarian OSM and OSM Standard tiles; any legacy references have been cleanly excised.

---

## 8. Audit Conclusion
The existing Phase 1–7 implementation is robust, unified, modular, and ready for full Phase 8 integration testing without any architectural refactoring.
