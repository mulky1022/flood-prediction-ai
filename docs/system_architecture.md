# System Architecture — Sri Lanka FloodWatch

## System Architecture Diagram

```text
       [ DATA TELEMETRY SOURCES ]
  Open-Meteo Live & Archive Weather API
                  │
                  ▼
       [ DATA VALIDATION LAYER ]
  Quality Checks, Range & Freshness Validation
                  │
                  ▼
      [ LOCATION / SPATIAL REGISTRY ]
    33 Monitoring Stations / 25 Districts
                  │
                  ▼
      [ FEATURE ENGINEERING PIPELINE ]
  64 Contract Features (32 Telemetry + 32 GIS)
                  │
                  ▼
         [ ML MODEL INFERENCE ]
  RandomForestClassifier v1.0.0 & StandardScaler
                  │
                  ▼
     [ CANONICAL RISK & ACTION ENGINE ]
    Risk Levels (LOW, MODERATE, HIGH, CRITICAL)
                  │
                  ▼
    [ DATABASE PERSISTENCE LAYER ]
  Supabase PostgreSQL + In-Memory Resilient Store
                  │
                  ▼
       [ UNIFIED PREDICTION API ]
  FastAPI Endpoints (/api/v1/health, /predictions, etc.)
                  │
                  ▼
     [ PUBLIC WEB APPLICATION ]
  Dashboard | Map | Alerts | History | Emergency Mode (117)
```

## Architectural Components

1. **Telemetry Ingestion Layer (`weather/weather_processor.py`)**:
   - Queries Open-Meteo REST API for hourly forecast & historical 30-day precipitation.
   - Enforces 30-minute caching to minimize network usage and prevent API rate limits.

2. **Spatial Location Registry (`data/locations.json`)**:
   - Maintains 33 hydrological stations with latitude, longitude, elevation, river basin, landcover, drainage index, and historical flood frequency metadata.

3. **Feature Engineering Engine (`services/feature_builder.py`)**:
   - Synthesizes exact 64-dimensional feature vector combining 32 weather/temporal inputs with 32 static geospatial hydrography attributes.

4. **Machine Learning Classifier (`services/predictor.py`)**:
   - Executes scikit-learn `RandomForestClassifier` inference, yielding class probabilities `P(Flood=1)`.

5. **Persistence Layer (`services/supabase_service.py`)**:
   - Connects to Supabase REST / PostgreSQL database. Operates in local in-memory fallback mode if remote endpoint is unreachable.

6. **Unified API Gateway (`api/main.py`)**:
   - FastAPI server exposing RESTful OpenAPI v3 endpoints protected with CORS, security headers, correlation IDs, and rate limiting.

7. **Public Web UI (`frontend/` & root SPA)**:
   - Responsive frontend built with HTML5, CSS3, Vanilla JS, OpenStreetMap GIS tiles, multilingual UI strings, and lightweight offline Emergency Mode.
