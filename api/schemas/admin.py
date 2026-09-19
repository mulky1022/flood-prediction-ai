"""
Phase 17 — Admin & Technical Dashboard Pydantic Schemas.
Defines request/response models for authentication, system health, prediction records,
data sources, station feeds, pipeline jobs, alert/notification logs, errors, and audit trails.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class AdminAuthRequest(BaseModel):
    token: str = Field(..., example="admin-secret-token-v17")


class AdminAuthResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field("Authentication successful.", example="Authentication successful.")
    token_valid: bool = Field(True, example=True)


class SystemHealthStatus(BaseModel):
    overall_status: str = Field("HEALTHY", example="HEALTHY")
    database_status: str = Field("CONNECTED", example="CONNECTED")
    telemetry_api_status: str = Field("ONLINE", example="ONLINE")
    model_engine_status: str = Field("LOADED", example="LOADED")
    scheduler_status: str = Field("ACTIVE", example="ACTIVE")
    warning_service_status: str = Field("SYNCED", example="SYNCED")
    notification_service_status: str = Field("READY", example="READY")
    checked_at: str


class DataSourceHealthItem(BaseModel):
    source_id: str = Field(..., example="openmeteo-rain-v1")
    name: str = Field(..., example="Open-Meteo Global Precipitation Telemetry")
    status: str = Field("ONLINE", example="ONLINE")
    last_fetch_at: Optional[str] = None
    latency_ms: Optional[float] = Field(45.2, example=45.2)
    error_count_24h: int = Field(0, example=0)


class StationMappingItem(BaseModel):
    station_id: Union[int, str] = Field(..., example=7)
    station_name: str = Field(..., example="Ratnapura Hydro station")
    location_id: str = Field(..., example="RATNAPURA_001")
    location_name: str = Field(..., example="Ratnapura")
    district: str = Field(..., example="Ratnapura")
    status: str = Field("ACTIVE", example="ACTIVE")
    last_updated: Optional[str] = None


class AdminOverviewResponse(BaseModel):
    status: str = Field("success", example="success")
    system_health: SystemHealthStatus
    monitored_locations_count: int = Field(7, example=7)
    active_predictions_count: int = Field(7, example=7)
    stale_predictions_count: int = Field(0, example=0)
    missing_predictions_count: int = Field(0, example=0)
    active_alerts_count: int = Field(1, example=1)
    notifications_sent_24h: int = Field(12, example=12)
    official_warnings_active_count: int = Field(1, example=1)
    recent_errors_count: int = Field(0, example=0)
    data_sources: List[DataSourceHealthItem]
    model_metadata: Dict[str, Any]
    generated_at: str


class AdminPredictionItem(BaseModel):
    prediction_id: Union[str, int] = Field(..., example="TEST-RAT-004")
    location_id: str = Field(..., example="RATNAPURA_001")
    location_name: str = Field(..., example="Ratnapura")
    station_id: Optional[Union[int, str]] = Field(7, example=7)
    risk_level: str = Field(..., example="HIGH")
    flood_probability: float = Field(..., example=0.85)
    prediction_time: str
    valid_from: str
    valid_until: str
    freshness_status: str = Field("CURRENT", example="CURRENT")  # CURRENT, STALE, MISSING, FAILED
    model_version: str = Field("v1.2.0-xgboost-prod", example="v1.2.0-xgboost-prod")
    created_at: str


class AdminPredictionListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=7)
    predictions: List[AdminPredictionItem]


class AdminJobItem(BaseModel):
    job_id: str = Field(..., example="JOB-20260918-001")
    job_type: str = Field("CANONICAL_PREDICTION_CRON", example="CANONICAL_PREDICTION_CRON")
    status: str = Field("SUCCESS", example="SUCCESS")  # RUNNING, SUCCESS, PARTIAL_SUCCESS, FAILED
    started_at: str
    completed_at: Optional[str] = None
    locations_requested: int = Field(7, example=7)
    locations_processed: int = Field(7, example=7)
    failed_count: int = Field(0, example=0)
    model_version: str = Field("v1.2.0-xgboost-prod", example="v1.2.0-xgboost-prod")
    error_summary: Optional[str] = None


class AdminJobListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=10)
    jobs: List[AdminJobItem]


class AdminJobRetryRequest(BaseModel):
    location_id: Optional[str] = Field(None, example="RATNAPURA_001")


class AdminJobRetryResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field("Canonical prediction pipeline triggered successfully.", example="Pipeline triggered.")
    job: AdminJobItem


class AdminErrorItem(BaseModel):
    id: str = Field(..., example="ERR-99128")
    service: str = Field(..., example="PredictorService")
    error_code: str = Field(..., example="TELEMETRY_FETCH_TIMEOUT")
    message: str = Field(..., example="Open-Meteo API connection timed out.")
    location_id: Optional[str] = Field(None, example="RATNAPURA_001")
    created_at: str


class AdminErrorListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=0)
    errors: List[AdminErrorItem]


class AdminAuditLogItem(BaseModel):
    id: str = Field(..., example="AUDIT-1002")
    actor: str = Field("admin", example="admin")
    action: str = Field("TRIGGER_PIPELINE_RETRY", example="TRIGGER_PIPELINE_RETRY")
    target: str = Field("RATNAPURA_001", example="RATNAPURA_001")
    details: Optional[str] = None
    timestamp: str


class AdminAuditLogListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=5)
    logs: List[AdminAuditLogItem]
