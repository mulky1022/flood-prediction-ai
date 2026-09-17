# 64-Feature Production Readiness & Source Audit

This document provides a granular, feature-by-feature audit of all 64 variables expected by the Random Forest Model (`v1.0.0`).

---

## 1. Complete 64-Feature Audit Matrix

| # | Feature | Training Role | Production Source | Type | Available | Validated | Status | Notes |
| :-: | :--- | :--- | :--- | :--- | :-: | :-: | :-: | :--- |
| **1** | `latitude` | Geographic coordinate | `locations.json` | STATIC | Yes | Yes | **READY** | Validated Sri Lanka range ($5.8^\circ\text{N} - 10.0^\circ\text{N}$) |
| **2** | `longitude` | Geographic coordinate | `locations.json` | STATIC | Yes | Yes | **READY** | Validated Sri Lanka range ($79.4^\circ\text{E} - 82.0^\circ\text{E}$) |
| **3** | `elevation_m` | Topographic height | `locations.json` | STATIC | Yes | Yes | **READY** | Digital Elevation Model baseline |
| **4** | `distance_to_river_m` | Hydrological proximity | `locations.json` | STATIC | Yes | Yes | **READY** | Distance to major stream/river channel in meters |
| **5** | `population_density_per_km2` | Exposure / Vulnerability | `locations.json` | STATIC | Yes | Yes | **READY** | Census Department district population density |
| **6** | `built_up_percent` | Impervious surface | `locations.json` | STATIC | Yes | Yes | **READY** | Urban land coverage percentage |
| **7** | `rainfall_7d_mm` | Trigger / Antecedent moisture | Open-Meteo Forecast API | LIVE | Yes | Yes | **READY** | Rolling 168-hour cumulative precipitation sum |
| **8** | `monthly_rainfall_mm` | Seasonal saturation | Open-Meteo Archive API | LIVE | Yes | Yes | **PROVISIONAL** | Rolling 30-day cumulative precipitation sum |
| **9** | `drainage_index` | Soil / Stormwater drainage | `locations.json` | STATIC | Yes | Yes | **READY** | Scaled index from 0.0 (poor) to 1.0 (excellent) |
| **10** | `ndvi` | Vegetation density | `locations.json` | PERIODIC | Yes | Yes | **READY** | Normalized Difference Vegetation Index (-1 to +1) |
| **11** | `ndwi` | Surface water content | `locations.json` | PERIODIC | Yes | Yes | **READY** | Normalized Difference Water Index (-1 to +1) |
| **12** | `historical_flood_count` | Historical susceptibility | `locations.json` | HISTORICAL | Yes | Yes | **READY** | DMC historical flood event count |
| **13** | `infrastructure_score` | Civic resilience | `locations.json` | STATIC | Yes | Yes | **READY** | Civic infrastructure quality index (0–100) |
| **14** | `nearest_hospital_km` | Emergency proximity | `locations.json` | STATIC | Yes | Yes | **READY** | Distance to nearest tertiary/district hospital |
| **15** | `nearest_evac_km` | Evacuation proximity | `locations.json` | STATIC | Yes | Yes | **READY** | Distance to designated disaster relief safe center |
| **16** | `flood_risk_score` | Synthetic hydrological index | Hydrological baseline formula | DERIVED | Yes | Yes | **LEAKAGE_REVIEW** | Top model feature (64.03% importance); derived via pre-event formula |
| **17** | `inundation_area_sqm` | Post-disaster flood footprint | Pre-event baseline (0.0) | DERIVED | Yes | Yes | **LEAKAGE_REVIEW** | Pre-event early warning baseline set to 0.0 (Scaler mean=0, std=1) |
| **18** | `district_Anuradhapura` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Anuradhapura, 0.0 otherwise |
| **19** | `district_Badulla` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Badulla, 0.0 otherwise |
| **20** | `district_Batticaloa` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Batticaloa, 0.0 otherwise |
| **21** | `district_Colombo` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Colombo, 0.0 otherwise |
| **22** | `district_Galle` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Galle, 0.0 otherwise |
| **23** | `district_Gampaha` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Gampaha, 0.0 otherwise |
| **24** | `district_Hambantota` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Hambantota, 0.0 otherwise |
| **25** | `district_Jaffna` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Jaffna, 0.0 otherwise |
| **26** | `district_Kalutara` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Kalutara, 0.0 otherwise |
| **27** | `district_Kandy` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Kandy, 0.0 otherwise |
| **28** | `district_Kegalle` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Kegalle, 0.0 otherwise |
| **29** | `district_Kilinochchi` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Kilinochchi, 0.0 otherwise |
| **30** | `district_Kurunegala` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Kurunegala, 0.0 otherwise |
| **31** | `district_Mannar` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Mannar, 0.0 otherwise |
| **32** | `district_Matale` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Matale, 0.0 otherwise |
| **33** | `district_Matara` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Matara, 0.0 otherwise |
| **34** | `district_Monaragala` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Monaragala, 0.0 otherwise |
| **35** | `district_Mullaitivu` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Mullaitivu, 0.0 otherwise |
| **36** | `district_Nuwara Eliya` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Nuwara Eliya, 0.0 otherwise |
| **37** | `district_Polonnaruwa` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Polonnaruwa, 0.0 otherwise |
| **38** | `district_Puttalam` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Puttalam, 0.0 otherwise |
| **39** | `district_Ratnapura` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Ratnapura, 0.0 otherwise |
| **40** | `district_Trincomalee` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Trincomalee, 0.0 otherwise |
| **41** | `district_Vavuniya` | Spatial one-hot | One-hot encoding (`district`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Vavuniya, 0.0 otherwise |
| **42** | `landcover_Bare Soil` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Bare Soil, 0.0 otherwise |
| **43** | `landcover_Forest` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Forest, 0.0 otherwise |
| **44** | `landcover_Plantation` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Plantation, 0.0 otherwise |
| **45** | `landcover_Scrub` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Scrub, 0.0 otherwise |
| **46** | `landcover_Urban` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Urban, 0.0 otherwise |
| **47** | `landcover_Wetland` | Land surface one-hot | One-hot encoding (`landcover`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Wetland, 0.0 otherwise |
| **48** | `soil_type_Loamy` | Soil composition one-hot | One-hot encoding (`soil_type`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Loamy, 0.0 otherwise |
| **49** | `soil_type_Peaty` | Soil composition one-hot | One-hot encoding (`soil_type`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Peaty, 0.0 otherwise |
| **50** | `soil_type_Sandy` | Soil composition one-hot | One-hot encoding (`soil_type`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Sandy, 0.0 otherwise |
| **51** | `soil_type_Silty` | Soil composition one-hot | One-hot encoding (`soil_type`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Silty, 0.0 otherwise |
| **52** | `water_supply_Rainwater harvesting` | Water source one-hot | One-hot (`water_supply`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Rainwater harvesting, 0.0 otherwise |
| **53** | `water_supply_Surface water` | Water source one-hot | One-hot (`water_supply`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Surface water, 0.0 otherwise |
| **54** | `water_supply_Tube-well` | Water source one-hot | One-hot (`water_supply`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Tube-well, 0.0 otherwise |
| **55** | `water_supply_Well` | Water source one-hot | One-hot (`water_supply`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Well, 0.0 otherwise |
| **56** | `electricity_Mixed` | Utility grid one-hot | One-hot (`electricity`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Mixed, 0.0 otherwise |
| **57** | `electricity_Off-gr` | Utility grid one-hot | One-hot (`electricity`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Off-gr, 0.0 otherwise |
| **58** | `electricity_Off-grid (solar)` | Utility grid one-hot | One-hot (`electricity`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Off-grid (solar), 0.0 otherwise |
| **59** | `road_quality_Good (paved)` | Access quality one-hot | One-hot (`road_quality`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Good (paved), 0.0 otherwise |
| **60** | `road_quality_No road access` | Access quality one-hot | One-hot (`road_quality`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if No road access, 0.0 otherwise |
| **61** | `road_quality_Poor (unpaved)` | Access quality one-hot | One-hot (`road_quality`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Poor (unpaved), 0.0 otherwise |
| **62** | `urban_rural_Urban` | Demography binary | Binary flag (`urban_rural`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Urban, 0.0 if Rural |
| **63** | `water_presence_flag_Unlikely` | Hydrological flag | Binary flag (`water_presence_flag`) | CATEGORICAL | Yes | Yes | **READY** | 1.0 if Unlikely, 0.0 if Likely |
| **64** | `is_good_to_live_Yes` | Normal baseline livability | Pre-event baseline (1.0) | DERIVED | Yes | Yes | **LEAKAGE_REVIEW** | Pre-event baseline livability set to 1.0 |

---

## 2. Summary Status Counts
* **READY**: **60 / 64** features (Fully supported by static DB, live Open-Meteo weather, and one-hot encoders).
* **PROVISIONAL**: **1 / 64** feature (`monthly_rainfall_mm` based on rolling 30-day archive sum).
* **LEAKAGE_REVIEW**: **3 / 64** features (`flood_risk_score`, `inundation_area_sqm`, `is_good_to_live_Yes` supported via deterministic pre-event baseline derivations).
* **MISSING / BLOCKED**: **0 / 64** features (100% of the contract is mathematically satisfied without arbitrary random imputation).
