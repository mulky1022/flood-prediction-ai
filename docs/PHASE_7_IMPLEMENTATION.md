# Phase 7 — Alert & Notification System Implementation Guide
Sri Lanka Live Early Flood Risk Prediction & Notification System

## 1. System Architecture
Phase 7 transitions Sri Lanka FloodWatch from an on-demand prediction interface into an active, operational early warning and notification platform.

```
                    ┌──────────────┐
                    │    USER      │
                    └──────┬───────┘
                           │
                           ▼
                ┌───────────────────┐
                │ Frontend (Stitch) │
                └─────────┬─────────┘
                          │ HTTPS
                          ▼
                ┌───────────────────┐
                │ FastAPI Backend   │
                └─────────┬─────────┘
                          │
                ┌─────────┴───────────┐
                │                     │
                ▼                     ▼
       ┌────────────────┐   ┌────────────────┐
       │ Location Data  │   │ Open-Meteo     │
       └────────┬───────┘   └───────┬────────┘
                │                    │
                └──────────┬─────────┘
                           ▼
                  ┌────────────────┐
                  │ Feature Builder│
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ 64 Features    │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ Scaler         │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ Random Forest  │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ Prediction     │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ Alert Policy   │
                  └───────┬────────┘
                          │
                ┌─────────┼──────────┐
                │         │          │
                ▼         ▼          ▼
              CREATE    UPDATE     RESOLVE
                │         │          │
                └─────────┼──────────┘
                          ▼
                  ┌────────────────┐
                  │ Supabase       │
                  │ Alerts Table   │
                  └───────┬────────┘
                          ▼
                  ┌────────────────┐
                  │ Notification   │
                  │ Service        │
                  └───────┬────────┘
                          ▼
            ┌─────────────┼────────────┐
            ▼             ▼            ▼
          Dashboard     Map      Alerts/History
```

## 2. Alert Data Model
- **Schema (`api/schemas/alert.py`)**:
  - `id`: Unique identifier (int)
  - `location_id`: Associated monitoring station ID (int)
  - `risk_level`: `LOW` | `MODERATE` | `HIGH` | `CRITICAL`
  - `flood_probability`: Model output float (0.0000 – 1.0000)
  - `prediction_class`: Integer class (0 = Non-flood, 1 = Flood alert)
  - `title`: Operational alert heading
  - `message`: Contextual telemetry narrative
  - `recommendation`: Actionable advisory
  - `status`: `ACTIVE` | `ACKNOWLEDGED` | `RESOLVED` | `EXPIRED`
  - `notification_status`: `SENT` | `PENDING` | `NOT_CONFIGURED` | `NOT_REQUIRED` | `FAILED`
  - `data_source`: Model & weather provenance string
  - `created_at`, `updated_at`, `acknowledged_at`, `resolved_at`: ISO 8601 Timestamps

## 3. Operational Alert Policy
- **Low Risk (<35% probability)**: No operational alert required. Automatically resolves prior active alerts for that station.
- **Moderate Risk (35%–65% probability)**: Advisory telemetry state. Can trigger informational notices if probability delta exceeds 15%.
- **High Risk (65%–80% probability)**: Actionable operational alert (`ACTIVE`). Triggers notification dispatch.
- **Critical Risk (>80% probability)**: Urgent emergency alert (`ACTIVE`). Escalates dispatch priority.

## 4. Duplicate Prevention & Lifecycle
- **Duplicate Prevention**: Before creating an alert, `AlertService.prevent_duplicate_alerts()` inspects existing `ACTIVE` records for that `location_id`. If an active alert already exists, it updates metrics without generating redundant alert IDs or spamming notifications.
- **Resolution**: When a station's risk decreases to `LOW`, any existing active alert is automatically marked `RESOLVED` with timestamp tracking.
- **Manual Acknowledgment**: Operators can mark active alerts as `ACKNOWLEDGED` via `POST /api/v1/alerts/{id}/acknowledge`.

## 5. Multi-Channel Notification Service
- **UI / Dashboard**: Dispatched in real-time, status = `SENT`.
- **Email / SMS**: Checks for active provider credentials in `.env`. If unconfigured, status is truthfully reported as `NOT_CONFIGURED`.

## 6. API Endpoints
- `GET /api/v1/alerts`: Query alerts with optional filtering (`status`, `risk_level`, `district`, `limit`, `offset`)
- `GET /api/v1/alerts/active`: Retrieve current active alerts
- `GET /api/v1/alerts/{alert_id}`: Retrieve single alert by ID
- `GET /api/v1/alerts/location/{location_id}`: Retrieve alerts for a specific station
- `POST /api/v1/alerts/{alert_id}/acknowledge`: Mark alert acknowledged
- `POST /api/v1/alerts/{alert_id}/resolve`: Manually resolve alert
- `POST /api/v1/alerts/process/{location_id}`: Execute on-demand alert evaluation for a station

## 7. Frontend Telemetry Synchronization
- **Live Dashboard**: Header active alert indicator badge + status card integration.
- **Flood Map**: Real GIS cartography with risk markers and station telemetry inspection.
- **Location Details**: Displays real-time risk level, probability, and active alert status.
- **Alerts & History**: Complete interactive alert feed with acknowledgement controls.

## 8. Scheduled Background Processing
- Dedicated server-side processing daemon: `python scripts/process_alerts_cron.py`
- Cycles through all 33 monitoring stations every 5 minutes to evaluate live predictions, update active alerts, and manage resolutions.
