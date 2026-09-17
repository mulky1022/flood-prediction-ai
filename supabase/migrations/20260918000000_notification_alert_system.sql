-- ====================================================================
-- SRI LANKA FLOODWATCH — NOTIFICATION & TRIGGERED ALERTS SCHEMA
-- Migration: 20260918000000_notification_alert_system.sql
-- ====================================================================

-- 1. Alert Preferences Table
CREATE TABLE IF NOT EXISTS alert_preferences (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE, -- NULL means 'All Stations'
    risk_threshold NUMERIC(5, 2) NOT NULL DEFAULT 35.0,            -- e.g. 35.0, 65.0, 80.0 (%)
    notification_channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_preferences_device ON alert_preferences (device_id);
CREATE INDEX IF NOT EXISTS idx_alert_preferences_location ON alert_preferences (location_id);
CREATE INDEX IF NOT EXISTS idx_alert_preferences_active ON alert_preferences (is_active);

-- 2. Triggered Alerts Table
CREATE TABLE IF NOT EXISTS triggered_alerts (
    id BIGSERIAL PRIMARY KEY,
    preference_id BIGINT REFERENCES alert_preferences(id) ON DELETE SET NULL,
    device_id VARCHAR(100),
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    prediction_id BIGINT REFERENCES predictions(id) ON DELETE SET NULL,
    flood_probability NUMERIC(6, 4) NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    threshold_crossed NUMERIC(5, 2) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'UNREAD', -- UNREAD, READ, DISMISSED
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triggered_alerts_device ON triggered_alerts (device_id);
CREATE INDEX IF NOT EXISTS idx_triggered_alerts_location ON triggered_alerts (location_id);
CREATE INDEX IF NOT EXISTS idx_triggered_alerts_status ON triggered_alerts (status);
CREATE INDEX IF NOT EXISTS idx_triggered_alerts_created_at ON triggered_alerts (created_at DESC);

-- 3. Row Level Security (RLS)
ALTER TABLE alert_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE triggered_alerts   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public all on alert_preferences" ON alert_preferences;
DROP POLICY IF EXISTS "Allow service role all on alert_preferences" ON alert_preferences;
DROP POLICY IF EXISTS "Allow public all on triggered_alerts" ON triggered_alerts;
DROP POLICY IF EXISTS "Allow service role all on triggered_alerts" ON triggered_alerts;

CREATE POLICY "Allow public all on alert_preferences" ON alert_preferences FOR ALL TO public USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role all on alert_preferences" ON alert_preferences FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow public all on triggered_alerts" ON triggered_alerts FOR ALL TO public USING (true) WITH CHECK (true);
CREATE POLICY "Allow service role all on triggered_alerts" ON triggered_alerts FOR ALL TO service_role USING (true) WITH CHECK (true);
