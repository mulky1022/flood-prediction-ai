# Database Design & Persistence Specification

## Database Architecture Overview
The system utilizes **Supabase PostgreSQL** as its primary persistence engine, with DDL schema definitions in `database/schema.sql` and `database/complete_supabase_setup.sql`.

To ensure 100% operational uptime, the application includes a **Resilient In-Memory Fallback Layer** (`services/supabase_service.py`) that handles offline states without raising HTTP 500 errors.

---

## Entity Relationship Schema

### 1. `locations` Table
Stores spatial and hydrography metadata for all 33 monitoring stations.
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(32) UNIQUE NOT NULL,
    district VARCHAR(64) NOT NULL,
    place_name VARCHAR(128) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION,
    distance_to_river_m DOUBLE PRECISION,
    population_density_per_km2 DOUBLE PRECISION,
    built_up_percent DOUBLE PRECISION,
    drainage_index DOUBLE PRECISION,
    historical_flood_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. `weather_observations` Table
Stores time-series meteorological telemetry.
```sql
CREATE TABLE weather_observations (
    id BIGSERIAL PRIMARY KEY,
    location_id INT REFERENCES locations(id) ON DELETE CASCADE,
    temperature_c DOUBLE PRECISION,
    humidity_percent DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    rain_mm DOUBLE PRECISION,
    weather_code INT,
    wind_speed_kmh DOUBLE PRECISION,
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. `predictions` Table
Stores canonical ML inference outputs and model version traceability.
```sql
CREATE TABLE predictions (
    id BIGSERIAL PRIMARY KEY,
    prediction_id VARCHAR(64) UNIQUE NOT NULL,
    location_id INT REFERENCES locations(id) ON DELETE CASCADE,
    prediction_time TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    prediction_class INT NOT NULL,
    flood_probability_percent DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    action_code VARCHAR(64) NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. `alerts` Table
Stores triggered threshold alerts with deduplication cooldown state.
```sql
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(64) UNIQUE NOT NULL,
    location_id INT REFERENCES locations(id) ON DELETE CASCADE,
    prediction_id VARCHAR(64) REFERENCES predictions(prediction_id),
    risk_level VARCHAR(32) NOT NULL,
    action_code VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'ACTIVE',
    triggered_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Database Performance & Indexes
```sql
CREATE INDEX idx_weather_location_time ON weather_observations(location_id, observed_at DESC);
CREATE INDEX idx_predictions_location_time ON predictions(location_id, prediction_time DESC);
CREATE INDEX idx_alerts_location_status ON alerts(location_id, status);
```
