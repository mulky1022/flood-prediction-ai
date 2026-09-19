# API Documentation — FastAPI Unified Gateway

## Overview
The API is built using **FastAPI** (`api/main.py`) following RESTful standards. All primary endpoints are versioned under `/api/v1/`.

---

## Core Endpoint Reference

### 1. System Health Check
`GET /api/v1/health`
- **Description**: Returns overall system operational status, model loading status, and database connectivity state.
- **Response Example**:
```json
{
  "status": "ok",
  "service": "Sri Lanka FloodWatch API",
  "version": "1.0.0",
  "model_loaded": true,
  "database_connected": true
}
```

### 2. Location Spatial Registry
`GET /api/v1/locations`
- **Description**: Returns all 33 monitoring stations across Sri Lanka.
- **Query Parameters**: `district` (Optional string filter).

`GET /api/v1/locations/{id}`
- **Description**: Returns spatial hydrography metadata for a specific station ID (e.g. `7` for Ratnapura).

### 3. Current Live Prediction
`GET /api/v1/predictions/current/{id}`
- **Description**: Executes ML inference pipeline for station `{id}` and returns canonical risk and action guidance.
- **Response Example**:
```json
{
  "prediction_id": "PRED-20260919-LOC7-001",
  "location": {
    "location_id": 7,
    "record_id": "LOC-007",
    "name": "Ratnapura Town (Kalu Ganga Upper)",
    "district": "Ratnapura"
  },
  "prediction_time": "2026-09-19T13:31:35Z",
  "risk": {
    "level": "HIGH",
    "score": 0.7238,
    "flood_probability_percent": 72.38
  },
  "action": {
    "code": "EVACUATE_WARNING",
    "message": "Evacuate low-lying areas near Kalu Ganga immediately."
  }
}
```

### 4. Active Alerts
`GET /api/v1/alerts/active`
- **Description**: Retrieves active operational alerts triggered across all monitoring stations.

### 5. Official Government Warnings
`GET /api/v1/warnings/location/{id}`
- **Description**: Returns Disaster Management Centre (DMC) and Irrigation Department official warning matrix status.

### 6. Emergency Low-Bandwidth Mode
`GET /api/v1/emergency/{id}`
- **Description**: Returns lightweight (< 2KB) emergency payload with essential safety advice and direct click-to-call **DMC Hotline 117**.
