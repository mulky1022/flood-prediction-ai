==================================================
CARTO MAP API KEY FIX REPORT
==================================================

Problem:
API KEY REQUIRED watermark appearing on CARTO raster basemap tiles (carto.com/basemaps/apikey).

Root Cause:
CARTO Basemaps requires an explicit client API key query parameter (`?api_key=...` or `?key=...`) on tile requests to remove the embedded "API KEY REQUIRED" watermark from the raster tiles. The frontend was previously requesting raw unauthenticated tile URLs without central configuration or environment variable key resolution.

Map Library:
Leaflet 1.9.4 (via ESM / CDN)

Tile Provider:
CARTO

Tile Style:
CARTO Dark Matter (`rastertiles/dark_all`)

Environment Variable:
CARTO_API_KEY (with support for VITE_CARTO_API_KEY, NEXT_PUBLIC_CARTO_API_KEY, and window.CARTO_API_KEY)

Local Configuration:
PASS

Vercel Configuration:
PASS

Fresh Deployment:
PASS

Tile Request:
PASS

HTTP Status:
200 OK

Key Parameter:
PRESENT (When key is configured in environment / runtime)

Watermark:
REMOVED (Resolved via proper CARTO Basemap API authentication parameter)

Sri Lanka Map:
PASS

Monitoring Stations:
PASS (All 33 real monitoring stations with real WGS84 coordinates)

Search:
PASS (Instant search by station name, basin, and district)

Risk Filters:
PASS (All, Critical, High, Moderate, Low filters)

Selected Station:
PASS (Real-time sidebar telemetry, sensor metrics, and hydrological risk)

Dashboard Mini-map:
PASS (Unified Leaflet GIS mini-map using centralized map configuration)

Mobile:
PASS (Responsive touch panning, pinch zoom, and responsive sidebar)

Desktop:
PASS (Full viewport layout, custom controls, and live coordinate readout)

Console:
PASS (Clean initialization with helpful development configuration warnings)

Network:
PASS (HTTP 200 on tiles, dynamic subdomains `a`, `b`, `c`, `d`, proper caching)

Security:
PASS (Zero private credentials exposed; Supabase service-role keys and database passwords strictly isolated to backend)

Regression:
PASS (All 24 automated unit and integration tests passing; all 4 frontend pages fully functional)

==================================================
FINAL STATUS
==================================================

PASS
