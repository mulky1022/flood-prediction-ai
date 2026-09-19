# Project Overview — Sri Lanka ML Early Flood Risk Prediction & Notification System

## 1. Problem Statement
Sri Lanka faces frequent seasonal monsoons causing severe localized riverine flooding along major river basins including Kalu Ganga, Kelani River, Gin Ganga, and Nilwala Ganga. Traditional flood warnings often rely on manual river gauge observations or regional weather forecasts that lack fine-grained location specificity and machine-learning risk probability estimation.

## 2. Motivation & Significance
Early detection and hyper-local risk warnings save human lives, reduce property damage, and empower emergency management agencies (Disaster Management Centre - DMC) and citizens to take timely precautionary actions. By coupling live meteorological telemetry with geospatial hydrography and a trained machine learning classifier, this system provides 6-to-24 hour early flood risk predictions.

## 3. Core Objectives
1. **Automated Meteorological Telemetry**: Ingest real-time and historical rainfall telemetry from Open-Meteo across 33 hydrological monitoring stations in all 25 administrative districts.
2. **64-Feature Machine Learning Inference**: Predict flood risk probability using a trained `RandomForestClassifier` v1.0.0 and `StandardScaler` feature pipeline (92.63% Accuracy, 0.9632 ROC-AUC).
3. **Canonical Risk & Action Assignment**: Classify risk into discrete categories (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) and generate standardized emergency action guidelines.
4. **Resilient Persistence**: Store canonical predictions in a remote Supabase PostgreSQL database with seamless in-memory fallback if network connectivity drops.
5. **Unified Public Web Application**: Provide an accessible, mobile-responsive SPA featuring live GIS flood maps, district analytics, active alerts feed, low-bandwidth emergency mode (< 2KB), and direct **DMC Hotline 117** integration.
6. **Government Warning Matrix**: Explicitly distinguish ML flood-risk probability estimates from official government evacuation orders (DMC / Irrigation Department).

## 4. System Invariants
- **Location Isolation**: `RATNAPURA_DATA != KOLONNAWA_DATA` (Zero cross-location contamination).
- **Master Location Invariant**: `REQUESTED_LOCATION_ID = AUTHORIZED_LOCATION_ID = RETURNED_LOCATION_ID = DISPLAYED_LOCATION_ID`.
- **Multilingual Preservation**: Changing language (English, Sinhala, Tamil) preserves identical prediction data (`LANGUAGE_CHANGE != PREDICTION_CHANGE`).
- **Safety Principles**: `MISSING_DATA != LOW_RISK` and `SERVICE_FAILURE != LOW_RISK`.
