# District Auto-Location Flow: Architecture & Verification Guide

## 1. Executive Summary & Problem Analysis

### Prior Behavior (The Bug)
Prior to this fix, navigation to `/district` (Location Details) suffered from missing geolocation resolution:
- The page did not request `navigator.geolocation.getCurrentPosition()`.
- It silently fell back to hardcoded `location_id = 1` (Kolonnawa).
- There was no user-facing location status banner, distance calculation, or manual station switcher dropdown.
- Deep links and query parameters were not dynamically synchronized via `history.replaceState`.

### Root Cause
1. **Frontend Disconnect**: `frontend/js/district.js` lacked the geolocation detection lifecycle, Haversine nearest-station matching algorithm, and location context UI management.
2. **Missing Backend Geometry Endpoint**: The FastAPI backend did not have an explicit `GET /api/v1/locations/nearest` endpoint to quickly compute Euclidean/spherical distances from user GPS coordinates.

---

## 2. Implemented Architecture & Flow

```
USER BROWSER
    ↓
Check URL (?location_id=X) -> If present, load directly (Priority 1)
    ↓ (If no URL param)
Check Session (sessionStorage) -> If user explicitly picked station, restore (Priority 2)
    ↓ (If initial direct visit)
navigator.geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 })
    ↓
(userLatitude, userLongitude)
    ↓
Haversine Great-Circle Distance Calculation against all 33 monitoring stations
    ↓
Find nearest station (min distance in km)
    ↓
Safety Check: distance <= 350 km (Sri Lanka catchment coverage)
    ├── If inside radius:
    │     - Selected Location ID = nearestStation.id
    │     - URL updated to /district?location_id={id} (history.replaceState)
    │     - Context Banner: "Auto-detected near {place_name}, {district} ({dist} km away)"
    └── If outside radius:
          - Display: "Your coordinates are outside Sri Lanka monitoring area"
          - Fallback to safe default (Station 1) without falsifying user position
    ↓
Sequential Concurrent Telemetry Loading (Promise.all):
    ├── GET /api/v1/locations/{id}
    ├── GET /api/v1/weather/{id}
    ├── GET /api/v1/predict/{id}
    ├── GET /api/v1/alerts/location/{id}
    └── GET /api/v1/predictions/{id}?limit=10
    ↓
Dynamic UI Rendering (Stitch Design System):
    - Location Context Toolbar with Station Selector dropdown
    - Radial Probability Gauge & Decision Threshold
    - River Proximity & Geospatial Vulnerability Matrix
    - 5 Weather Telemetry Cards & Precipitation Trend
    - Live Inundation Alert Badge
```

---

## 3. Mathematical Model: Haversine Distance Formula

The distance $d$ between two points on a spherical Earth with radius $R = 6371.0 \text{ km}$ is calculated as:

$$\Delta\phi = \text{radians}(\text{lat}_2 - \text{lat}_1)$$
$$\Delta\lambda = \text{radians}(\text{lon}_2 - \text{lon}_1)$$
$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
$$d = R \cdot c$$

This formula is implemented identically in both:
- **Client-Side**: `frontend/js/district.js` (`haversineDistanceKm`)
- **Server-Side**: `api/routes/locations.py` (`/api/v1/locations/nearest`)

---

## 4. Location Selection Precedence Matrix

| Priority | Trigger | Action | Geolocation Prompted? |
| :---: | :--- | :--- | :---: |
| **1** | **Direct URL Param** (`?location_id=16`) | Load station #16 (Peradeniya) immediately; sync selector dropdown | ❌ No |
| **2** | **Manual UI Selector** (User selects from dropdown) | Load chosen station; update URL and `sessionStorage` | ❌ No |
| **3** | **Active Session** (User previously selected station) | Load saved station; retain choice across tab navigation | ❌ No |
| **4** | **Browser Geolocation** (Direct visit to `/district`) | Acquire GPS position; compute nearest station; update URL | ✅ Yes |
| **5** | **Fallback** (GPS Denied / Timeout / Out of Bounds) | Display informative notification banner; load default station | ❌ Fallback |

---

## 5. Production Endpoint Verification Results

Tested against live deployment `https://flood-prediction-roan.vercel.app`:

```
=== Live Production Verification: District Auto-Location Flow ===
[PASS] /district                                    -> HTTP 200 (HTML: 36,681 bytes)
[PASS] /district?location_id=1                      -> HTTP 200 (Kolonnawa, Colombo)
[PASS] /district?location_id=16                     -> HTTP 200 (Peradeniya, Kandy)
[PASS] /district?location_id=12                     -> HTTP 200 (Galle Fort, Galle)
[PASS] /api/v1/locations/nearest?latitude=6.93&longitude=79.88 -> HTTP 200 (#1 Kolonnawa, 0.42 km)
[PASS] /api/v1/locations/nearest?latitude=7.29&longitude=80.63 -> HTTP 200 (#16 Peradeniya, 4.30 km)
[PASS] /api/v1/locations/nearest?latitude=6.03&longitude=80.21 -> HTTP 200 (#12 Galle Fort, 0.83 km)
[PASS] /api/v1/locations/nearest?latitude=9.66&longitude=80.01 -> HTTP 200 (#29 Jaffna City, 1.71 km)
[PASS] /api/v1/locations/1                          -> HTTP 200 (Full 26 geospatial fields)
[PASS] /api/v1/weather/1                            -> HTTP 200 (Live Open-Meteo telemetry)
[PASS] /api/v1/predict/1                            -> HTTP 200 (Risk: HIGH | Prob: 75.45%)
[PASS] /api/v1/alerts/location/1                    -> HTTP 200 (Active alert response)
```
