# Weather Data Specification & Open-Meteo Integration Guide

## 1. Overview & Provider Details
* **Provider**: Open-Meteo (Open-Source Weather API)
* **Base URL**: `https://api.open-meteo.com/v1`
* **Authentication**: None required (Public access tier, no secret keys in codebase)
* **Timezone**: `Asia/Colombo` (UTC+05:30) for all local meteorological timestamps and calendar alignment.

---

## 2. API Endpoints & Usage Matrix

| Purpose | Endpoint | Key Parameters | Output |
| :--- | :--- | :--- | :--- |
| **Current Weather & 168h Precipitation** | `https://api.open-meteo.com/v1/forecast` | `latitude`, `longitude`, `hourly` (temperature, humidity, precipitation, rain, weather_code, wind_speed, soil_moisture), `current` (temperature, humidity, precipitation, rain, weather_code, wind_speed), `past_hours=168`, `forecast_hours=24`, `timezone=Asia/Colombo`, `temperature_unit=celsius`, `wind_speed_unit=kmh`, `precipitation_unit=mm`, `timeformat=iso8601` | Live weather + 168h historical hourly time series + 24h short-term forecast |
| **Monthly Rolling Precipitation** | `https://archive-api.open-meteo.com/v1/archive` | `latitude`, `longitude`, `start_date`, `end_date`, `daily=precipitation_sum`, `timezone=Asia/Colombo`, `precipitation_unit=mm`, `timeformat=iso8601` | Daily precipitation sums across rolling 30 days |
| **Historical Forecast (Optional)** | `https://historical-forecast-api.open-meteo.com/v1/forecast` | Retained for model calibration if historical forecast data matching is needed | Historical forecast archive |

---

## 3. Variables Requested & Definitions

### A. Current Variables (`current=`)
* `temperature_2m` (°C): Air temperature at 2 meters above ground.
* `relative_humidity_2m` (%): Relative humidity percentage at 2 meters.
* `precipitation` (mm): Total current hourly precipitation.
* `rain` (mm): Liquid rain component.
* `weather_code` (WMO): Standard WMO weather interpretation code (0 = Clear, 61–65 = Rain, 80–82 = Showers, 95 = Thunderstorm).
* `wind_speed_10m` (km/h): Wind speed at 10 meters above ground.

### B. Hourly Variables (`hourly=`)
* `temperature_2m`, `relative_humidity_2m`, `precipitation`, `rain`, `weather_code`, `wind_speed_10m`, `soil_moisture_0_to_7cm` ($m^3/m^3$).

---

## 4. Rainfall Processing & Accumulation Formulas

### A. 7-Day Cumulative Rainfall (`rainfall_7d_mm`)
$$\text{rainfall\_7d\_mm} = \sum_{t=T-168\text{h}}^{T} \text{hourly.precipitation}(t)$$

> [!IMPORTANT]
> **No Double Counting**: Open-Meteo's `precipitation` represents the total liquid and water-equivalent precipitation. We strictly sum `precipitation` and do **NOT** add `rain` to avoid double-counting precipitation.

### B. Monthly Cumulative Rainfall (`monthly_rainfall_mm`)
$$\text{monthly\_rainfall\_mm} = \sum_{d=D-30\text{d}}^{D} \text{daily.precipitation\_sum}(d)$$

* **Status**: **PROVISIONAL** (The ML training dataset does not explicitly differentiate between calendar-month and rolling 30-day window; rolling 30-day was selected to maintain consistent 720-hour window dynamics without month-start reset artifacts).

---

## 5. Missing Data & Data-Quality Policy
* **Zero-Filling Prohibition**: Missing precipitation entries (`null`) are **never silently converted to 0.0**.
* **Quality Classification**:
  * `GOOD`: All 168 expected hours received with valid non-negative numbers.
  * `PARTIAL`: One or more hours missing ($1 \le \text{missing\_hours} < 168$). Result is computed on available subset and explicitly flagged as `PARTIAL`.
  * `UNAVAILABLE`: All data missing or upstream provider failure. Result flagged as `UNAVAILABLE` with clear diagnostic error message.

---

## 6. HTTP Error Handling & Resilience
* **Timeouts**: Explicit 20-second timeout (`httpx.Client(timeout=20.0)`).
* **Retry Strategy**: 2 retries with exponential backoff ($0.5\text{s} \times \text{attempt}$) for transient connection failures.
* **HTTP 400**: Catches invalid query parameters and returns clean JSON error.
* **HTTP 429**: Catches rate-limiting and returns structured `rate_limit` status.
* **HTTP 5xx**: Catches upstream server errors without throwing uncaught exceptions.

---

## 7. Local Development Caching
* **Path**: `cache/weather/{md5_hash}.json`
* **TTL**: 30 minutes (1800 seconds).
* **Metadata**: Caches payload along with `_cached_at_iso` timestamp so data age is always transparent.
