-- ====================================================================
-- SRI LANKA FLOODWATCH — MIGRATION: PHASE 13 OFFICIAL WARNINGS
-- ====================================================================

CREATE TABLE IF NOT EXISTS official_warnings (
    id SERIAL PRIMARY KEY,
    warning_id VARCHAR(100) UNIQUE NOT NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    source_id VARCHAR(100) NOT NULL DEFAULT 'DMC-SL',
    source_name VARCHAR(200) NOT NULL DEFAULT 'Disaster Management Centre (DMC) Sri Lanka',
    source_type VARCHAR(100) NOT NULL DEFAULT 'GOVERNMENT_AGENCY',
    source_url VARCHAR(500),
    official_reference VARCHAR(100),
    warning_type VARCHAR(100) NOT NULL DEFAULT 'FLOOD_WARNING',
    severity VARCHAR(50) NOT NULL DEFAULT 'MAJOR',
    title VARCHAR(300) NOT NULL,
    message TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_official_warnings_location_id ON official_warnings(location_id);
CREATE INDEX IF NOT EXISTS idx_official_warnings_status ON official_warnings(status);
CREATE INDEX IF NOT EXISTS idx_official_warnings_warning_id ON official_warnings(warning_id);
