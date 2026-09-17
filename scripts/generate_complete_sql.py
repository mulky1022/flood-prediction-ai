import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOC_FILE = BASE_DIR / "data" / "locations.json"
OUT_FILE = BASE_DIR / "database" / "complete_supabase_setup.sql"

with open(LOC_FILE, "r", encoding="utf-8") as f:
    locs = json.load(f)

header = """-- ====================================================================
-- SRI LANKA FLOODWATCH — COMPLETE PRODUCTION SUPABASE SQL SETUP
-- Run this entire script in Supabase SQL Editor (Dashboard > SQL Editor)
-- Creates all tables, indexes, Row Level Security, and seeds all 33 stations.
-- ====================================================================

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Drop existing tables if re-initializing (Optional, commented out for safety)
-- DROP TABLE IF EXISTS alerts CASCADE;
-- DROP TABLE IF EXISTS predictions CASCADE;
-- DROP TABLE IF EXISTS weather_observations CASCADE;
-- DROP TABLE IF EXISTS locations CASCADE;

-- --------------------------------------------------------------------
-- 3. Locations Table (33 Real Hydro-Meteorological Stations)
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

CREATE INDEX IF NOT EXISTS idx_locations_district ON locations (district);
CREATE INDEX IF NOT EXISTS idx_locations_record_id ON locations (record_id);

-- --------------------------------------------------------------------
-- 4. Weather Observations Table (Open-Meteo Ingestion Cache)
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

CREATE INDEX IF NOT EXISTS idx_weather_location_id ON weather_observations (location_id);
CREATE INDEX IF NOT EXISTS idx_weather_observed_at ON weather_observations (observed_at DESC);

-- --------------------------------------------------------------------
-- 5. Predictions Table (ML Inferences & Audit Log)
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

CREATE INDEX IF NOT EXISTS idx_predictions_location_id ON predictions (location_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);

-- --------------------------------------------------------------------
-- 6. Alerts Table (Phase 7 Operational Alert Lifecycle)
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

CREATE INDEX IF NOT EXISTS idx_alerts_location_id ON alerts (location_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_updated_at ON alerts (updated_at DESC);

-- --------------------------------------------------------------------
-- 7. Row Level Security (RLS) Policies — Allow Read for Public & Full for Service Role
-- --------------------------------------------------------------------
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Locations: Anyone can view
CREATE POLICY "Allow public read on locations" ON locations FOR SELECT USING (true);
CREATE POLICY "Allow service role all on locations" ON locations FOR ALL USING (true);

-- Weather: Anyone can view
CREATE POLICY "Allow public read on weather" ON weather_observations FOR SELECT USING (true);
CREATE POLICY "Allow service role all on weather" ON weather_observations FOR ALL USING (true);

-- Predictions: Anyone can view
CREATE POLICY "Allow public read on predictions" ON predictions FOR SELECT USING (true);
CREATE POLICY "Allow service role all on predictions" ON predictions FOR ALL USING (true);

-- Alerts: Anyone can view, update or insert via API
CREATE POLICY "Allow public read on alerts" ON alerts FOR SELECT USING (true);
CREATE POLICY "Allow public insert on alerts" ON alerts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on alerts" ON alerts FOR UPDATE USING (true);
CREATE POLICY "Allow service role all on alerts" ON alerts FOR ALL USING (true);

-- --------------------------------------------------------------------
-- 8. Seed All 33 Real Monitoring Stations
-- --------------------------------------------------------------------
"""

lines = []
for l in locs:
    id_ = l["id"]
    rec = l["record_id"]
    dist = l["district"].replace("'", "''")
    place = l["place_name"].replace("'", "''")
    lat = l["latitude"]
    lon = l["longitude"]
    elev = l.get("elevation_m", 0.0)
    dist_riv = l.get("distance_to_river_m", 0.0)
    pop = l.get("population_density_per_km2", 0.0)
    built = l.get("built_up_percent", 0.0)
    drain = l.get("drainage_index", 0.0)
    ndvi = l.get("ndvi", 0.0)
    ndwi = l.get("ndwi", 0.0)
    flood_cnt = l.get("historical_flood_count", 0.0)
    infra = l.get("infrastructure_score", 0.0)
    hosp = l.get("nearest_hospital_km", 0.0)
    evac = l.get("nearest_evac_km", 0.0)
    land = l.get("landcover", "Other").replace("'", "''")
    soil = l.get("soil_type", "Other").replace("'", "''")
    water_sup = l.get("water_supply", "Other").replace("'", "''")
    elec = l.get("electricity", "Other").replace("'", "''")
    road = l.get("road_quality", "Other").replace("'", "''")
    urb = l.get("urban_rural", "Other").replace("'", "''")
    water_flag = l.get("water_presence_flag", "Other").replace("'", "''")
    
    val = f"  ({id_}, '{rec}', '{dist}', '{place}', {lat}, {lon}, {elev}, {dist_riv}, {pop}, {built}, {drain}, {ndvi}, {ndwi}, {flood_cnt}, {infra}, {hosp}, {evac}, '{land}', '{soil}', '{water_sup}', '{elec}', '{road}', '{urb}', '{water_flag}')"
    lines.append(val)

seed_sql = "INSERT INTO locations (\n  id, record_id, district, place_name, latitude, longitude, elevation_m, distance_to_river_m,\n  population_density_per_km2, built_up_percent, drainage_index, ndvi, ndwi, historical_flood_count,\n  infrastructure_score, nearest_hospital_km, nearest_evac_km, landcover, soil_type, water_supply,\n  electricity, road_quality, urban_rural, water_presence_flag\n)\nVALUES\n" + ",\n".join(lines) + "\nON CONFLICT (id) DO UPDATE SET\n  place_name = EXCLUDED.place_name,\n  latitude = EXCLUDED.latitude,\n  longitude = EXCLUDED.longitude,\n  district = EXCLUDED.district;\n\n-- Sync sequence for auto-incrementing ID\nSELECT setval('locations_id_seq', (SELECT MAX(id) FROM locations));\n"

full_content = header + seed_sql

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_content)

print(f"Generated {OUT_FILE} with {len(locs)} stations.")
