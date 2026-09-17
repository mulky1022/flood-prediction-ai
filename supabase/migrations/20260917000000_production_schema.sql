-- ====================================================================
-- SRI LANKA FLOODWATCH — PRODUCTION DATABASE MIGRATION
-- Migration Version: 20260917000000_production_schema.sql
-- Idempotent schema definition for Supabase PostgreSQL
-- ====================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------
-- 2. Locations Table (33 Validated Hydro-Meteorological Stations)
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
-- 3. Weather Observations Table (Open-Meteo Ingestion Telemetry)
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
-- 4. Predictions Table (ML Inferences & Audit Telemetry)
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
-- 5. Alerts Table (Operational Alert Lifecycle & Deduplication)
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
-- 6. Row Level Security (RLS) Configuration
-- --------------------------------------------------------------------
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    -- Public Read Policies
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'locations' AND policyname = 'Allow public read on locations') THEN
        CREATE POLICY "Allow public read on locations" ON locations FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'weather_observations' AND policyname = 'Allow public read on weather') THEN
        CREATE POLICY "Allow public read on weather" ON weather_observations FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'predictions' AND policyname = 'Allow public read on predictions') THEN
        CREATE POLICY "Allow public read on predictions" ON predictions FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alerts' AND policyname = 'Allow public read on alerts') THEN
        CREATE POLICY "Allow public read on alerts" ON alerts FOR SELECT USING (true);
    END IF;

    -- Service Role & API Modification Policies
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'locations' AND policyname = 'Allow service role all on locations') THEN
        CREATE POLICY "Allow service role all on locations" ON locations FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'weather_observations' AND policyname = 'Allow service role all on weather') THEN
        CREATE POLICY "Allow service role all on weather" ON weather_observations FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'predictions' AND policyname = 'Allow service role all on predictions') THEN
        CREATE POLICY "Allow service role all on predictions" ON predictions FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alerts' AND policyname = 'Allow public insert on alerts') THEN
        CREATE POLICY "Allow public insert on alerts" ON alerts FOR INSERT WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alerts' AND policyname = 'Allow public update on alerts') THEN
        CREATE POLICY "Allow public update on alerts" ON alerts FOR UPDATE USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'alerts' AND policyname = 'Allow service role all on alerts') THEN
        CREATE POLICY "Allow service role all on alerts" ON alerts FOR ALL USING (true);
    END IF;
END $$;

-- --------------------------------------------------------------------
-- 7. Seed All 33 Real Hydro-Meteorological Stations (Idempotent Upsert)
-- --------------------------------------------------------------------
INSERT INTO locations (
  id, record_id, district, place_name, latitude, longitude, elevation_m, distance_to_river_m,
  population_density_per_km2, built_up_percent, drainage_index, ndvi, ndwi, historical_flood_count,
  infrastructure_score, nearest_hospital_km, nearest_evac_km, landcover, soil_type, water_supply,
  electricity, road_quality, urban_rural, water_presence_flag
)
VALUES
  (1, 'LOC-001', 'Colombo', 'Kolonnawa (Kelani River Lower)', 6.9271, 79.8825, 4.5, 220.0, 3800.0, 78.5, 0.32, 0.12, 0.28, 7.0, 68.0, 1.8, 0.9, 'Urban', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (2, 'LOC-002', 'Colombo', 'Colombo Fort (Coastal Basin)', 6.9344, 79.8428, 7.0, 1800.0, 4200.0, 92.0, 0.55, 0.08, 0.05, 2.0, 88.0, 1.2, 0.6, 'Urban', 'Sandy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (3, 'LOC-003', 'Gampaha', 'Kelaniya (Kelani Floodplain)', 6.9553, 79.9186, 6.2, 150.0, 2100.0, 65.0, 0.35, 0.18, 0.22, 6.0, 62.0, 2.4, 1.1, 'Urban', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (4, 'LOC-004', 'Gampaha', 'Ja-Ela (Lagoon Basin)', 7.0744, 79.8917, 5.0, 380.0, 1850.0, 55.0, 0.4, 0.22, 0.19, 4.0, 58.0, 3.1, 1.5, 'Wetland', 'Peaty', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (5, 'LOC-005', 'Kalutara', 'Kalutara South (Kalu Ganga Estuary)', 6.5854, 79.9607, 5.5, 210.0, 1450.0, 48.0, 0.38, 0.25, 0.24, 5.0, 60.0, 2.0, 1.2, 'Plantation', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (6, 'LOC-006', 'Kalutara', 'Millaniya (Lowland Plain)', 6.6914, 80.0528, 12.0, 650.0, 680.0, 28.0, 0.42, 0.38, 0.12, 4.0, 45.0, 5.5, 2.8, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Rural', 'Unlikely'),
  (7, 'LOC-007', 'Ratnapura', 'Ratnapura Town (Kalu Ganga Upper)', 6.6828, 80.4036, 34.0, 110.0, 920.0, 52.0, 0.26, 0.28, 0.31, 9.0, 48.0, 2.1, 1.0, 'Urban', 'Silty', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (8, 'LOC-008', 'Ratnapura', 'Pelmadulla (Valley Basin)', 6.6231, 80.5489, 120.0, 420.0, 450.0, 22.0, 0.48, 0.45, 0.08, 3.0, 38.0, 6.2, 2.5, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Rural', 'Unlikely'),
  (9, 'LOC-009', 'Kegalle', 'Kegalle Town (Lowland Inundation)', 7.2513, 80.3464, 145.0, 380.0, 780.0, 38.0, 0.52, 0.35, 0.1, 4.0, 50.0, 1.9, 1.4, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (10, 'LOC-010', 'Kegalle', 'Dehiowita (Kelani Basin Upper)', 6.9856, 80.2642, 48.0, 180.0, 520.0, 24.0, 0.34, 0.42, 0.25, 6.0, 40.0, 4.2, 1.8, 'Plantation', 'Silty', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (11, 'LOC-011', 'Galle', 'Baddegama (Gin Ganga Basin)', 6.1869, 80.1831, 14.0, 140.0, 820.0, 32.0, 0.31, 0.32, 0.28, 7.0, 44.0, 3.8, 1.6, 'Plantation', 'Silty', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (12, 'LOC-012', 'Galle', 'Galle Fort (Coastal)', 6.0328, 80.217, 8.0, 2200.0, 1800.0, 75.0, 0.62, 0.14, 0.06, 1.0, 76.0, 1.5, 0.8, 'Urban', 'Sandy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (13, 'LOC-013', 'Matara', 'Akuressa (Nilwala Ganga Basin)', 6.0989, 80.4744, 18.0, 130.0, 720.0, 29.0, 0.28, 0.36, 0.27, 8.0, 42.0, 3.2, 1.5, 'Plantation', 'Silty', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (14, 'LOC-014', 'Matara', 'Matara City (Nilwala Estuary)', 5.9485, 80.5353, 6.0, 260.0, 1650.0, 68.0, 0.44, 0.16, 0.2, 5.0, 66.0, 1.6, 0.9, 'Urban', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (15, 'LOC-015', 'Hambantota', 'Tissamaharama (Kirindi Oya Basin)', 6.2778, 81.2867, 19.0, 450.0, 310.0, 18.0, 0.58, 0.28, 0.14, 2.0, 48.0, 4.1, 2.0, 'Plantation', 'Sandy', 'Well', 'Mixed', 'Good (paved)', 'Rural', 'Unlikely'),
  (16, 'LOC-016', 'Kandy', 'Peradeniya (Mahaweli River Basin)', 7.2686, 80.5975, 485.0, 180.0, 1100.0, 45.0, 0.65, 0.48, 0.12, 2.0, 68.0, 1.4, 1.0, 'Plantation', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (17, 'LOC-017', 'Kandy', 'Nawalapitiya (Highland Valley)', 7.0544, 80.5342, 590.0, 220.0, 650.0, 30.0, 0.72, 0.52, 0.08, 2.0, 46.0, 2.8, 1.6, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Rural', 'Unlikely'),
  (18, 'LOC-018', 'Matale', 'Matale Town', 7.4675, 80.6234, 364.0, 520.0, 610.0, 35.0, 0.6, 0.4, 0.05, 1.0, 54.0, 2.0, 1.5, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (19, 'LOC-019', 'Nuwara Eliya', 'Nuwara Eliya Town', 6.9497, 80.7891, 1868.0, 850.0, 420.0, 28.0, 0.78, 0.58, -0.05, 1.0, 56.0, 1.8, 1.2, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (20, 'LOC-020', 'Kurunegala', 'Kurunegala Town (Deduru Oya Basin)', 7.4863, 80.3623, 116.0, 680.0, 740.0, 42.0, 0.5, 0.32, 0.08, 3.0, 58.0, 1.7, 1.1, 'Plantation', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (21, 'LOC-021', 'Puttalam', 'Chilaw (Deduru Oya Estuary)', 7.5758, 79.7953, 6.0, 220.0, 580.0, 34.0, 0.39, 0.2, 0.22, 4.0, 48.0, 2.3, 1.4, 'Plantation', 'Sandy', 'Tube-well', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (22, 'LOC-022', 'Anuradhapura', 'Anuradhapura (Malwathu Oya)', 8.3114, 80.4037, 81.0, 310.0, 290.0, 26.0, 0.45, 0.25, 0.12, 3.0, 52.0, 2.2, 1.5, 'Scrub', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (23, 'LOC-023', 'Polonnaruwa', 'Manampitiya (Mahaweli Floodplain)', 7.9125, 81.0875, 42.0, 120.0, 210.0, 14.0, 0.25, 0.35, 0.32, 7.0, 38.0, 5.8, 1.8, 'Wetland', 'Silty', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (24, 'LOC-024', 'Badulla', 'Mahiyanganaya (Mahaweli Basin)', 7.3167, 81.0, 85.0, 240.0, 340.0, 20.0, 0.36, 0.38, 0.21, 4.0, 42.0, 3.5, 1.7, 'Plantation', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (25, 'LOC-025', 'Monaragala', 'Wellawaya (Kirindi Basin)', 6.7381, 81.1017, 180.0, 480.0, 190.0, 15.0, 0.54, 0.42, 0.06, 2.0, 40.0, 4.5, 2.2, 'Forest', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Rural', 'Unlikely'),
  (26, 'LOC-026', 'Batticaloa', 'Batticaloa Town (Lagoon Inundation)', 7.7102, 81.6924, 4.0, 180.0, 920.0, 45.0, 0.3, 0.15, 0.3, 6.0, 52.0, 1.9, 1.0, 'Urban', 'Sandy', 'Tube-well', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (27, 'LOC-027', 'Ampara', 'Kalmunai (Coastal Floodplain)', 7.4167, 81.8333, 5.0, 320.0, 1100.0, 48.0, 0.35, 0.18, 0.24, 5.0, 50.0, 2.0, 1.2, 'Urban', 'Sandy', 'Tube-well', 'Mixed', 'Good (paved)', 'Urban', 'Likely'),
  (28, 'LOC-028', 'Trincomalee', 'Kantale (Mahaweli Branch)', 8.3667, 81.0, 38.0, 290.0, 240.0, 18.0, 0.4, 0.3, 0.18, 4.0, 44.0, 4.0, 2.0, 'Wetland', 'Loamy', 'Surface water', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (29, 'LOC-029', 'Jaffna', 'Jaffna City (Peninsula Basin)', 9.6615, 80.0255, 5.0, 3500.0, 1400.0, 60.0, 0.48, 0.15, 0.08, 2.0, 64.0, 1.5, 0.9, 'Urban', 'Sandy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (30, 'LOC-030', 'Kilinochchi', 'Iranamadu (Reservoir Basin)', 9.35, 80.4, 22.0, 260.0, 120.0, 10.0, 0.38, 0.32, 0.22, 4.0, 36.0, 6.0, 2.5, 'Scrub', 'Sandy', 'Tube-well', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (31, 'LOC-031', 'Mannar', 'Murunkan (Aruvi Aru Basin)', 8.8417, 80.0333, 12.0, 210.0, 110.0, 12.0, 0.35, 0.22, 0.2, 3.0, 34.0, 7.2, 3.0, 'Scrub', 'Sandy', 'Tube-well', 'Mixed', 'Good (paved)', 'Rural', 'Likely'),
  (32, 'LOC-032', 'Vavuniya', 'Vavuniya Town', 8.7514, 80.4971, 98.0, 1200.0, 380.0, 30.0, 0.52, 0.28, 0.05, 2.0, 48.0, 2.1, 1.4, 'Scrub', 'Loamy', 'Well', 'Mixed', 'Good (paved)', 'Urban', 'Unlikely'),
  (33, 'LOC-033', 'Mullaitivu', 'Puthukkudiyiruppu (Lowland)', 9.3117, 80.6975, 15.0, 550.0, 95.0, 8.0, 0.42, 0.35, 0.12, 3.0, 32.0, 6.5, 2.8, 'Scrub', 'Sandy', 'Well', 'Off-grid (solar)', 'Poor (unpaved)', 'Rural', 'Unlikely')
ON CONFLICT (id) DO UPDATE SET
  place_name = EXCLUDED.place_name,
  latitude = EXCLUDED.latitude,
  longitude = EXCLUDED.longitude,
  district = EXCLUDED.district;

-- 8. Synchronize sequence counter
SELECT setval('locations_id_seq', (SELECT MAX(id) FROM locations));
