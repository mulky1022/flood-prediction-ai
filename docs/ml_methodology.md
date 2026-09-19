# Machine Learning Methodology & Feature Contract

## 1. Overview
The Flood Risk Prediction Engine uses a trained **RandomForestClassifier v1.0.0** coupled with a 64-feature pipeline to estimate localized flood risk probability across Sri Lankan hydrological monitoring stations.

---

## 2. ML Artifact Specification

| Artifact | File Path | Description |
| :--- | :--- | :--- |
| **Model Classifier** | `model/flood_model.pkl` | Scikit-Learn `RandomForestClassifier` (100 Estimators) |
| **Feature Scaler** | `model/preprocessor.pkl` | `StandardScaler` (64-dimensional normalization) |
| **Feature Schema** | `model/feature_columns.json` | Exact list & ordering of 64 contract features |
| **Metadata** | `model/model_metadata.json` | Training metrics & version metadata |

---

## 3. Evaluation Metrics

```text
  Accuracy:    92.63% (0.9263)
  ROC-AUC:     0.9632
  Precision:   0.6057
  Recall:      0.7450
  F1 Score:    0.6682
```

---

## 4. 64-Feature Contract Definition

The model consumes an exact 64-feature vector categorized into two main groups:

### Group A: Meteorological & Temporal Features (32 Features)
- `temperature_c`, `humidity_percent`, `precipitation_mm`, `rain_mm`, `weather_code`, `wind_speed_kmh`
- `rainfall_7d_mm`, `monthly_rainfall_mm`, `rainfall_3d_mm`, `rainfall_24h_mm`
- Rolling statistics (max, mean, std over 24h, 72h, 168h windows)
- Temporal sin/cos cyclical encodings for day-of-year and hour-of-day

### Group B: Geospatial & Hydrography Static Baselines (32 Features)
- `elevation_m`, `distance_to_river_m`, `population_density_per_km2`, `built_up_percent`
- `drainage_index`, `historical_flood_count`, `infrastructure_score`, `nearest_hospital_km`
- Soil permeability encodings (`soil_silty`, `soil_clay`, `soil_sandy`)
- Landcover encodings (`landcover_urban`, `landcover_forest`, `landcover_agriculture`)

---

## 5. Inference Workflow

```text
Telemetry (Open-Meteo) + Spatial Registry (locations.json)
                         │
                         ▼
             [ feature_builder.py ]
          Synthesizes 64 Feature Array
                         │
                         ▼
            [ StandardScaler Transform ]
           Normalizes input vector (1, 64)
                         │
                         ▼
        [ RandomForestClassifier.predict_proba ]
       Yields P(Non-Flood=0) and P(Flood=1)
                         │
                         ▼
             [ Canonical Risk Engine ]
  Assigns LOW (<25%), MODERATE (25-50%), HIGH (50-75%), CRITICAL (>=75%)
```
