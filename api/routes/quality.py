"""
Phase 20 — Data Quality, Prediction Quality & Monitoring API Routes.

Exposes telemetry endpoints for system monitoring, quality metrics,
data source health, station health, and data lineage tracing.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_db, get_quality_service, SupabaseService, DataQualityService

logger = logging.getLogger("QualityAPI")
router = APIRouter(prefix="/quality", tags=["Data & Prediction Quality"])


@router.get(
    "/status",
    summary="Get aggregated data quality, prediction quality & system monitoring telemetry"
)
def get_quality_status(
    db: SupabaseService = Depends(get_db),
    quality_service: DataQualityService = Depends(get_quality_service)
):
    """
    Returns production-grade technical quality telemetry:
    - Data source health (healthy, degraded, stale, unavailable)
    - Prediction freshness & completeness metrics
    - Station health summary
    - Verification of non-negotiable quality invariants
    """
    return quality_service.get_quality_status_overview(db)


@router.get(
    "/lineage/{prediction_id}",
    summary="Trace end-to-end data lineage for a specific prediction ID"
)
def get_prediction_lineage(
    prediction_id: str,
    db: SupabaseService = Depends(get_db),
    quality_service: DataQualityService = Depends(get_quality_service)
):
    """
    Traces prediction back to its input sources, weather telemetry, feature preparation,
    ML model inference version, triggered alert, and recipient notifications.
    """
    lineage_res = quality_service.get_data_lineage(prediction_id, db)
    if lineage_res.get("status") == "LINEAGE_NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "code": "PREDICTION_NOT_FOUND", "message": f"Prediction record '{prediction_id}' not found."}
        )
    return lineage_res


@router.get(
    "/sources",
    summary="Get diagnostic status of external data sources"
)
def get_data_sources_telemetry(
    quality_service: DataQualityService = Depends(get_quality_service)
):
    """
    Retrieves operational metrics and SLAs for external telemetry feeds.
    """
    return {
        "status": "success",
        "sources": list(quality_service.data_sources.values())
    }
