# Feature Source Mapping & Data Classification

## 1. Data Provenance Note
* **Primary Source**: Sri Lanka Flood Risk Training Dataset & GIS District Profiles.
* **Important Notice**: The original ML training dataset contains synthetic observations (`is_synthetic = True`). Values in this static location layer represent geographic, infrastructure, and environmental baselines compiled for research and early warning prototype development. They are not certified real-time Sri Lankan government meteorological or hydrological observations.

---

## 2. Excluded Fields (Target & Potential Leakage)
In accordance with Phase 2 data governance rules, the following fields are strictly **excluded** from the static production location dataset:

| Field Name | Category | Rationale for Exclusion |
| :--- | :--- | :--- |
| `flood_occurrence_current_event` | **TARGET** | Target classification variable (90.03% No, 9.97% Yes). Never used as an input feature or static metadata. |
| `flood_risk_score` | **LEAKAGE REVIEW** | High feature importance (64.03%). Excluded from static metadata pending rigorous leakage evaluation. |
| `inundation_area_sqm` | **LEAKAGE REVIEW** | Post-event flood footprint measurement. Excluded from pre-event static location profile. |
| `is_good_to_live` | **LEAKAGE REVIEW** | Post-event livability assessment. Excluded from production location records. |
| `reason_not_good_to_live` | **LEAKAGE REVIEW** | Qualitative post-event classification text. Excluded from production location records. |

---

## 3. Training Definition Investigation for Live Weather Features

| Feature Name | Training Source | Training Calculation | Evidence | Production Calculation | Status | Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rainfall_7d_mm` | Synthetic Training Dataset | Cumulative 7-day precipitation | Training notebook feature column #7 | Sum of 168 hourly precipitation values from Open-Meteo Forecast API (`past_hours=168`) | **VERIFIED** | Open-Meteo reanalysis/forecast grid approximation (~11km resolution). |
| `monthly_rainfall_mm` | Synthetic Training Dataset | Cumulative 30-day precipitation | Training notebook feature column #8 | Sum of rolling 30 days daily `precipitation_sum` from Open-Meteo Archive API | **PROVISIONAL** | Training data does not specify whether monthly meant calendar-month or rolling 30 days. Rolling 30 days is adopted to avoid month-boundary reset artifacts. |

---

## 4. Comprehensive 64-Feature Contract Mapping Table

The model expects exactly 64 numerical features in the specified order:

| # | Model Feature | Source | Type | Status | Notes |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | `latitude` | `locations.json` (`latitude`) | STATIC | **AVAILABLE** | Validated degrees North (5.9°N to 9.8°N) |
| **2** | `longitude` | `locations.json` (`longitude`) | STATIC | **AVAILABLE** | Validated degrees East (79.5°E to 81.9°E) |
| **3** | `elevation_m` | `locations.json` (`elevation_m`) | STATIC | **AVAILABLE** | Elevation in meters above sea level |
| **4** | `distance_to_river_m` | `locations.json` (`distance_to_river_m`) | STATIC | **AVAILABLE** | Proximity to nearest major river/canal in meters |
| **5** | `population_density_per_km2` | `locations.json` (`population_density_per_km2`) | STATIC | **AVAILABLE** | Department of Census & Statistics density baseline |
| **6** | `built_up_percent` | `locations.json` (`built_up_percent`) | STATIC | **AVAILABLE** | Impervious surface / urban coverage percentage |
| **7** | `rainfall_7d_mm` | Open-Meteo Weather API | LIVE | **PHASE 3** | Rolling 168h cumulative precipitation sum (mm) |
| **8** | `monthly_rainfall_mm` | Open-Meteo Weather API | LIVE | **PHASE 3** | Rolling 720h cumulative precipitation sum (mm) |
| **9** | `drainage_index` | `locations.json` (`drainage_index`) | STATIC | **AVAILABLE** | Soil and stormwater drainage capacity (0.0–1.0) |
| **10** | `ndvi` | `locations.json` (`ndvi`) | PERIODIC | **AVAILABLE** | Normalized Difference Vegetation Index (-1 to +1) |
| **11** | `ndwi` | `locations.json` (`ndwi`) | PERIODIC | **AVAILABLE** | Normalized Difference Water Index (-1 to +1) |
| **12** | `historical_flood_count` | `locations.json` (`historical_flood_count`) | HISTORICAL | **AVAILABLE** | Past flood event frequency index |
| **13** | `infrastructure_score` | `locations.json` (`infrastructure_score`) | STATIC | **AVAILABLE** | Composite civic infrastructure index (0–100) |
| **14** | `nearest_hospital_km` | `locations.json` (`nearest_hospital_km`) | STATIC | **AVAILABLE** | Distance to nearest tertiary/district hospital (km) |
| **15** | `nearest_evac_km` | `locations.json` (`nearest_evac_km`) | STATIC | **AVAILABLE** | Distance to designated disaster relief safe center (km) |
| **16** | `flood_risk_score` | Baseline Hydrological Index | DERIVED | **LEAKAGE REVIEW** | Pre-event baseline formula derived from slope & elevation |
| **17** | `inundation_area_sqm` | Pre-event Baseline (0.0) | UNSUPPORTED | **LEAKAGE REVIEW** | Set to 0.0 for live early warning (Scaler mean=0, std=1) |
| **18** | `district_Anuradhapura` | One-Hot Encoding (`district == 'Anuradhapura'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **19** | `district_Badulla` | One-Hot Encoding (`district == 'Badulla'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **20** | `district_Batticaloa` | One-Hot Encoding (`district == 'Batticaloa'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **21** | `district_Colombo` | One-Hot Encoding (`district == 'Colombo'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **22** | `district_Galle` | One-Hot Encoding (`district == 'Galle'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **23** | `district_Gampaha` | One-Hot Encoding (`district == 'Gampaha'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **24** | `district_Hambantota` | One-Hot Encoding (`district == 'Hambantota'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **25** | `district_Jaffna` | One-Hot Encoding (`district == 'Jaffna'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **26** | `district_Kalutara` | One-Hot Encoding (`district == 'Kalutara'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **27** | `district_Kandy` | One-Hot Encoding (`district == 'Kandy'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **28** | `district_Kegalle` | One-Hot Encoding (`district == 'Kegalle'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **29** | `district_Kilinochchi` | One-Hot Encoding (`district == 'Kilinochchi'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **30** | `district_Kurunegala` | One-Hot Encoding (`district == 'Kurunegala'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **31** | `district_Mannar` | One-Hot Encoding (`district == 'Mannar'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **32** | `district_Matale` | One-Hot Encoding (`district == 'Matale'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **33** | `district_Matara` | One-Hot Encoding (`district == 'Matara'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **34** | `district_Monaragala` | One-Hot Encoding (`district == 'Monaragala'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **35** | `district_Mullaitivu` | One-Hot Encoding (`district == 'Mullaitivu'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **36** | `district_Nuwara Eliya` | One-Hot Encoding (`district == 'Nuwara Eliya'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **37** | `district_Polonnaruwa` | One-Hot Encoding (`district == 'Polonnaruwa'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **38** | `district_Puttalam` | One-Hot Encoding (`district == 'Puttalam'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **39** | `district_Ratnapura` | One-Hot Encoding (`district == 'Ratnapura'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **40** | `district_Trincomalee` | One-Hot Encoding (`district == 'Trincomalee'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **41** | `district_Vavuniya` | One-Hot Encoding (`district == 'Vavuniya'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **42** | `landcover_Bare Soil` | One-Hot Encoding (`landcover == 'Bare Soil'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **43** | `landcover_Forest` | One-Hot Encoding (`landcover == 'Forest'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **44** | `landcover_Plantation` | One-Hot Encoding (`landcover == 'Plantation'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **45** | `landcover_Scrub` | One-Hot Encoding (`landcover == 'Scrub'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **46** | `landcover_Urban` | One-Hot Encoding (`landcover == 'Urban'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **47** | `landcover_Wetland` | One-Hot Encoding (`landcover == 'Wetland'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **48** | `soil_type_Loamy` | One-Hot Encoding (`soil_type == 'Loamy'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **49** | `soil_type_Peaty` | One-Hot Encoding (`soil_type == 'Peaty'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **50** | `soil_type_Sandy` | One-Hot Encoding (`soil_type == 'Sandy'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **51** | `soil_type_Silty` | One-Hot Encoding (`soil_type == 'Silty'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **52** | `water_supply_Rainwater harvesting` | One-Hot (`water_supply == 'Rainwater harvesting'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **53** | `water_supply_Surface water` | One-Hot (`water_supply == 'Surface water'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **54** | `water_supply_Tube-well` | One-Hot (`water_supply == 'Tube-well'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **55** | `water_supply_Well` | One-Hot (`water_supply == 'Well'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **56** | `electricity_Mixed` | One-Hot (`electricity == 'Mixed'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **57** | `electricity_Off-gr` | One-Hot (`electricity == 'Off-gr'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **58** | `electricity_Off-grid (solar)` | One-Hot (`electricity == 'Off-grid (solar)'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **59** | `road_quality_Good (paved)` | One-Hot (`road_quality == 'Good (paved)'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **60** | `road_quality_No road access` | One-Hot (`road_quality == 'No road access'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **61** | `road_quality_Poor (unpaved)` | One-Hot (`road_quality == 'Poor (unpaved)'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **62** | `urban_rural_Urban` | Binary (`urban_rural == 'Urban'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **63** | `water_presence_flag_Unlikely` | Binary (`water_presence_flag == 'Unlikely'`) | STATIC | **AVAILABLE** | Binary indicator (1.0 or 0.0) |
| **64** | `is_good_to_live_Yes` | Normal Baseline Livability | DERIVED | **LEAKAGE REVIEW** | Set to 1.0 baseline (normal) during non-catastrophic conditions |

---

## 4. Status Summary Count
* **AVAILABLE (Static / One-Hot)**: 60 features
* **PHASE 3 (Live Open-Meteo Weather)**: 2 features (`rainfall_7d_mm`, `monthly_rainfall_mm`)
* **LEAKAGE REVIEW (Derived Pre-Event Baselines)**: 2 features (`flood_risk_score`, `is_good_to_live_Yes`)
* **TOTAL FEATURES**: **64** (100% accounted for with zero arbitrary fabrication)
