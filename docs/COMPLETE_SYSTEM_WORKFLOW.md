# Complete System Workflow Specification
## Sri Lanka Live Early Flood Risk Prediction & Notification System

---

## 1. End-to-End System Execution Flow

```mermaid
flowchart TD
    User([User / Browser]) -->|1. Request Dashboard / Map / Details| Frontend[Frontend UI - Google Stitch]
    Frontend -->|2. GET /api/v1/predict/location_id| FastAPI[FastAPI Server - api/main.py]
    FastAPI -->|3. Get Station Spatial Profile| LocService[Location Service - services/location_service.py]
    LocService -->|Static GIS Attributes| FeatureBuilder[Feature Builder - services/feature_builder.py]
    FastAPI -->|4. Ingest Live Weather| OpenMeteo[Open-Meteo Ingestion - weather/weather_processor.py]
    OpenMeteo -->|Hourly & Rolling Rainfall| FeatureBuilder
    FeatureBuilder -->|5. 64-Feature Vector (1, 64)| Scaler[StandardScaler - model/preprocessor.pkl]
    Scaler -->|6. Scaled Features (1, 64)| RandomForest[RandomForestClassifier - model/flood_model.pkl]
    RandomForest -->|7. Probabilities: P(Flood), Class| PredService[Predictor Service - services/predictor.py]
    PredService -->|8. Raw Inference Output| AlertEngine[Alert Engine - services/alert_service.py]
    AlertEngine -->|9. Risk Tier & Policy Evaluation| Supabase[(Supabase PostgreSQL Database)]
    AlertEngine -->|10. Alert Event / Cooldown Trigger| NotifService[Notification Dispatcher - services/notification_service.py]
    NotifService -->|11. Truthful Delivery Logs| Supabase
    FastAPI -->|12. JSON Response Payload| Frontend
    Frontend -->|13. Interactive Telemetry Render| User
```

---

## 2. Granular Stage-by-Stage Breakdown

### Stage 1: User Request & Frontend Navigation
- **Input:** User navigates to Live Dashboard (`/index.html`), Flood Map (`/map.html`), Location Details (`/district.html`), or Alerts Archive (`/alerts.html`).
- **Output:** DOM elements initialized; script modules (`dashboard.js`, `map.js`, `district.js`, `alerts.js`) initiate asynchronous data fetching.
- **Source Files:** `frontend/*.html`, `frontend/js/*.js`, `frontend/css/*.css`.
- **API:** Browser DOM / HTTP requests.
- **Database Interaction:** None.
- **Failure Behavior:** Offline notification banner; graceful fallback to cached UI structure.

---

### Stage 2: API Client Dispatch
- **Input:** Target endpoint path (e.g. `/api/v1/predict/1`, `/api/v1/alerts/active`).
- **Output:** HTTP GET/POST request with JSON headers and 15s timeout abort controller.
- **Source File:** `frontend/js/api.js`.
- **API:** `fetchJson(endpoint, options)`.
- **Database Interaction:** None.
- **Failure Behavior:** If backend is unreachable or request times out, catches `AbortError` and surfaces user-friendly error toast without crashing page.

---

### Stage 3: FastAPI Routing & Request Resolution
- **Input:** Incoming HTTP request with path parameters, query strings, and CORS headers.
- **Output:** Parameter validation via Pydantic; dispatches to matched route controller.
- **Source Files:** `api/main.py`, `api/routes/predictions.py`, `api/routes/alerts.py`, `api/routes/locations.py`, `api/routes/weather.py`.
- **API:** `/api/v1/predict/{location_id}`, `/api/v1/alerts`, `/api/v1/locations`, `/api/v1/weather/{location_id}`.
- **Database Interaction:** Queries `locations` table or in-memory station registry.
- **Failure Behavior:** If `location_id` is invalid/unknown, returns HTTP 404 with structured error `{status: "error", code: "LOCATION_NOT_FOUND"}`.

---

### Stage 4: Location Spatial Profile Resolution
- **Input:** Location identifier (numeric ID `1`..`33` or record string `LOC-001`..`LOC-033`).
- **Output:** Complete GIS dictionary containing 13 numerical fields (elevation, distance to river, drainage index, population density, ndvi, ndwi, etc.) and categorical attributes (district, landcover, soil type, etc.).
- **Source Files:** `services/location_service.py`, `data/locations.json`.
- **API:** Internal Python function `get_location_by_id(location_id)`.
- **Database Interaction:** `SELECT * FROM locations WHERE id = ?`.
- **Failure Behavior:** Returns `None`, prompting route to raise HTTP 404.

---

### Stage 5: Live Weather & Antecedent Telemetry Ingestion
- **Input:** Station coordinates `(latitude, longitude)`.
- **Output:** Normalized weather payload:
  - `current`: Temperature (°C), Relative Humidity (%), Current Precipitation (mm), Weather Code, Wind Speed (km/h).
  - `rainfall`: 7-day cumulative precipitation (`rainfall_7d_mm`, rolling 168 hours), 30-day cumulative precipitation (`monthly_rainfall_mm`, rolling 30 days).
  - `data_quality`: `GOOD` / `PARTIAL` / `UNAVAILABLE`.
- **Source Files:** `weather/weather_processor.py`, `services/openmeteo_service.py`.
- **API:** Open-Meteo Forecast API (`https://api.open-meteo.com/v1/forecast`) and Archive API (`https://archive-api.open-meteo.com/v1/archive`).
- **Database Interaction:** Persists observation record into `weather_observations` table.
- **Failure Behavior:** 3-tier fallback: (1) Local cache hit (30-min TTL), (2) Upstream HTTP retry with exponential backoff, (3) Graceful hourly extrapolation. If completely unavailable, returns HTTP 503 `WEATHER_UNAVAILABLE`.

---

### Stage 6: 64-Feature Synthesis & Quality Validation Gate
- **Input:** Static location profile dictionary + Live weather observation dictionary.
- **Output:** Formatted `pandas.DataFrame` with shape `(1, 64)` and strict column ordering, accompanied by `quality_report`.
- **Source File:** `services/feature_builder.py`.
- **API:** `build_feature_dataframe(location, weather, derive_leakage_baselines=True)`.
- **Encoding Rules:**
  - 13 Static Numerical Features
  - 2 Live Weather Features (`rainfall_7d_mm`, `monthly_rainfall_mm`)
  - 3 Deterministic Baseline / Leakage Features (`flood_risk_score`, `inundation_area_sqm`, `is_good_to_live_Yes`)
  - 46 One-Hot Categorical Features (District, Landcover, Soil Type, Water Supply, Electricity, Road Quality, Urban/Rural, Water Presence)
- **Database Interaction:** None.
- **Failure Behavior:** If any required numerical feature is missing or categorical mapping fails, flags `ready_for_prediction = False` and halts inference with HTTP 422 `PREDICTION_UNAVAILABLE`.

---

### Stage 7: Standard Scaling Preprocessor
- **Input:** Raw unscaled feature vector `X` `(1, 64)`.
- **Output:** Scaled numpy array `X_scaled` `(1, 64)` with mean=0, variance=1 normalization.
- **Source Files:** `model/preprocessor.pkl`, `services/predictor.py`.
- **API:** `scaler.transform(X)`.
- **Database Interaction:** None.
- **Failure Behavior:** If shape mismatch occurs, raises `ValueError` caught and handled gracefully by predictor service.

---

### Stage 8: Random Forest Probabilistic Inference
- **Input:** Scaled feature array `X_scaled` `(1, 64)`.
- **Output:**
  - `class`: Binary prediction integer (`0` = Non-Flood, `1` = Flood).
  - `flood_probability`: Continuous float `[0.0, 1.0]`.
  - `non_flood_probability`: Complementary float `1.0 - flood_probability`.
- **Source Files:** `model/flood_model.pkl`, `services/predictor.py`.
- **API:** `model.predict(X_scaled)`, `model.predict_proba(X_scaled)`.
- **Database Interaction:** None.
- **Failure Behavior:** Catches any internal estimator exception and returns structured error.

---

### Stage 9: Operational Risk Tier & Policy Evaluation
- **Input:** Inference output `flood_probability`.
- **Output:** Evaluated alert decision payload:
  - `risk_level`: `LOW` (<35%), `MODERATE` (35–64%), `HIGH` (65–79%), `CRITICAL` (>=80%).
  - `is_alertable`: `True` for HIGH and CRITICAL; `False` for LOW and MODERATE.
  - `auto_resolve`: `True` when risk drops to LOW from an active alert.
  - Operational title, factual impact message, and standard recommendation.
- **Source Files:** `config/alert_config.py`, `services/alert_service.py`.
- **API:** `alert_service.evaluate_prediction_for_alert(prediction_payload)`.
- **Database Interaction:** None.
- **Failure Behavior:** Defaults safely to `LOW` risk tier and routine monitoring recommendation.

---

### Stage 10: Alert Lifecycle Management & Deduplication
- **Input:** Evaluated alert decision + Station ID.
- **Output:** Action executed: `ALERT_CREATED`, `ALERT_UPDATED`, `ALERT_RESOLVED`, or `NO_ALERT_REQUIRED`.
- **Source File:** `services/alert_service.py`.
- **API:** `alert_service.process_location_alert(location_id)`.
- **Deduplication Logic:**
  - If existing active alert exists and new risk is HIGH/CRITICAL: Updates existing record with latest probability and timestamp; avoids duplicate alert flooding.
  - If existing active alert exists and new risk is LOW: Automatically resolves active alert with `resolved_at` timestamp.
- **Database Interaction:**
  - `INSERT INTO alerts` (on new alert)
  - `UPDATE alerts SET ... WHERE id = ?` (on update / acknowledge / resolve)
- **Failure Behavior:** Falls back to in-memory alert store if Supabase database is unreachable.

---

### Stage 11: Notification Dispatch
- **Input:** Alert record dictionary.
- **Output:** Multi-channel delivery status report:
  - `web_dashboard`: `SENT` (in-app telemetry always broadcasted)
  - `email`: `NOT_CONFIGURED` (or `SENT` / `FAILED` if SMTP credentials provided)
  - `sms`: `NOT_CONFIGURED` (or `SENT` / `FAILED` if SMS gateway provided)
- **Source File:** `services/notification_service.py`.
- **API:** `notification_service.send_notification(alert)`.
- **Database Interaction:** Updates `notification_status` column in `alerts` table.
- **Failure Behavior:** Truthful reporting of channel statuses without fabricating delivery success.

---

### Stage 12: Supabase Audit & History Persistence
- **Input:** Complete prediction payload and alert action record.
- **Output:** Persisted rows in PostgreSQL database.
- **Source File:** `services/supabase_service.py`.
- **Database Interaction:**
  - `INSERT INTO predictions (location_id, prediction_class, flood_probability, ...)`
  - `INSERT INTO alerts (location_id, risk_level, flood_probability, title, ...)`
- **Failure Behavior:** Resilient fallback stores records in `_LOCAL_PREDICTIONS` and `_LOCAL_ALERTS` lists so API consumers experience zero interruption.

---

### Stage 13: Frontend Telemetry & Map Visualization
- **Input:** JSON response payload from `/api/v1/predict/{id}` or `/api/v1/alerts`.
- **Output:**
  - Dashboard gauges and probability meters updated.
  - Interactive map markers updated with pulsing rings for HIGH/CRITICAL stations.
  - Location deep-dive cards populated with 64-feature telemetry breakdown.
  - Alerts table refreshed with live status badges.
- **Source Files:** `frontend/js/*.js`, `frontend/css/*.css`.
- **API:** DOM manipulation via vanilla ES6 modules.
- **Database Interaction:** None.
- **Failure Behavior:** Error boundaries display informative contextual banners with retry buttons.
