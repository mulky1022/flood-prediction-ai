-- ====================================================================
-- Sri Lanka Live Early Flood Risk Prediction System - Supabase Schema
-- ====================================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------
-- 1. Locations Table (Static GIS & Environmental Baselines)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(50) UNIQUE NOT NULL,
    district VARCHAR(100) NOT NULL,
    place_name VARCHAR(200) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    elevation_m NUMERIC(8, 2),
    distance_to_river_m NUMERIC(10, 2),
    population_density_per_km2 NUMERIC(10, 2),
    built_up_percent NUMERIC(5, 2),
    drainage_index NUMERIC(4, 2),
    ndvi NUMERIC(4, 2),
    ndwi NUMERIC(4, 2),
    historical_flood_count NUMERIC(6, 2) DEFAULT 0.0,
    infrastructure_score NUMERIC(5, 2),
    nearest_hospital_km NUMERIC(6, 2),
    nearest_evac_km NUMERIC(6, 2),
    landcover VARCHAR(100),
    soil_type VARCHAR(100),
    water_supply VARCHAR(100),
    electricity VARCHAR(100),
    road_quality VARCHAR(100),
    urban_rural VARCHAR(50),
    water_presence_flag VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on district for spatial and regional lookups
CREATE INDEX IF NOT EXISTS idx_locations_district ON locations (district);
CREATE INDEX IF NOT EXISTS idx_locations_record_id ON locations (record_id);

-- --------------------------------------------------------------------
-- 2. Weather Observations Table (Open-Meteo Ingestion Cache)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_observations (
    id BIGSERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c NUMERIC(5, 2),
    humidity_percent NUMERIC(5, 2),
    precipitation_mm NUMERIC(8, 2),
    rain_mm NUMERIC(8, 2),
    weather_code INTEGER,
    wind_speed_kmh NUMERIC(6, 2),
    rainfall_7d_mm NUMERIC(8, 2),
    monthly_rainfall_mm NUMERIC(8, 2),
    source VARCHAR(100) DEFAULT 'Open-Meteo',
    data_quality_status VARCHAR(50) DEFAULT 'GOOD',
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    expected_hours INTEGER DEFAULT 168,
    received_hours INTEGER DEFAULT 168,
    missing_hours INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes on weather telemetry
CREATE INDEX IF NOT EXISTS idx_weather_location_id ON weather_observations (location_id);
CREATE INDEX IF NOT EXISTS idx_weather_observed_at ON weather_observations (observed_at DESC);

-- --------------------------------------------------------------------
-- 3. Predictions Table (ML Inference Audit & History)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    prediction_class INTEGER NOT NULL,
    flood_probability NUMERIC(6, 4) NOT NULL,
    non_flood_probability NUMERIC(6, 4) NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'RandomForestClassifier',
    model_version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    feature_count INTEGER NOT NULL DEFAULT 64,
    weather_observed_at TIMESTAMPTZ,
    data_source VARCHAR(100) DEFAULT 'Open-Meteo',
    data_quality_status VARCHAR(50) DEFAULT 'GOOD',
    ready_for_prediction BOOLEAN DEFAULT TRUE,
    prediction_status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    audit_metadata JSONB
);

-- Indexes on predictions
CREATE INDEX IF NOT EXISTS idx_predictions_location_id ON predictions (location_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);

-- --------------------------------------------------------------------
-- 4. Alerts Table (Phase 7 Alert & Operational Life-Cycle)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    risk_level VARCHAR(50) NOT NULL,
    flood_probability NUMERIC(6, 4) NOT NULL,
    prediction_class INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    recommendation TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    notification_status VARCHAR(50) NOT NULL DEFAULT 'NOT_REQUIRED',
    data_source VARCHAR(100) DEFAULT 'Open-Meteo / RandomForest v1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

-- Indexes on alerts
CREATE INDEX IF NOT EXISTS idx_alerts_location_id ON alerts (location_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_updated_at ON alerts (updated_at DESC);

