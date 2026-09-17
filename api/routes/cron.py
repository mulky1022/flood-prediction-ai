"""
Scheduled Background Monitoring Router.

Provides secure endpoints for automated scheduled execution of the end-to-end
flood monitoring, prediction, risk evaluation, and alert dispatch pipeline across
all monitored locations in Sri Lanka.
"""

import os
import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from services.alert_service import get_alert_service, AlertService

logger = logging.getLogger("CronMonitoring")

router = APIRouter(prefix="/cron", tags=["Scheduled Monitoring"])

CRON_SECRET = os.getenv("CRON_SECRET", "")


def verify_cron_auth(
    authorization: Optional[str] = Header(None),
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    x_vercel_cron: Optional[str] = Header(None, alias="x-vercel-cron"),
    secret: Optional[str] = Query(None)
) -> bool:
    """
    Validates that the invocation originated from an authorized scheduler.
    Accepts:
    1. Authorization: Bearer <CRON_SECRET>
    2. X-Cron-Secret: <CRON_SECRET>
    3. ?secret=<CRON_SECRET>
    4. Vercel Cron header (when deployed on Vercel)
    If CRON_SECRET is not configured in local development, allows execution with a warning.
    """
    expected_secret = CRON_SECRET.strip() if CRON_SECRET else ""

    # If secret is configured in environment, strictly enforce authentication
    if expected_secret:
        # Check Bearer token
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected_secret:
                return True

        # Check custom headers
        if x_cron_secret == expected_secret or secret == expected_secret:
            return True

        # Check Vercel Cron signature header
        if x_vercel_cron:
            return True

        logger.warning("Unauthorized cron monitoring invocation attempt blocked.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "code": "UNAUTHORIZED_CRON", "message": "Invalid or missing cron authentication secret."}
        )

    # Local development warning
    logger.info("CRON_SECRET not configured; permitting local scheduled execution.")
    return True


@router.get(
    "/monitor",
    summary="Execute automated scheduled monitoring across all Sri Lanka locations",
    description="Processes all 25 calibrated monitoring locations: fetches live Open-Meteo weather, runs 64-feature ML prediction, evaluates operational alert policies, handles deduplication, and records alert state."
)
@router.post(
    "/monitor",
    summary="Execute automated scheduled monitoring across all Sri Lanka locations"
)
def run_scheduled_monitoring(
    request: Request,
    is_authorized: bool = Depends(verify_cron_auth),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Automated backend monitoring entrypoint.
    """
    start_time = time.time()
    logger.info("Starting automated background monitoring run across all locations...")

    try:
        results = alert_service.process_all_monitored_locations()
        elapsed_seconds = round(time.time() - start_time, 2)
        results["execution_time_seconds"] = elapsed_seconds
        logger.info(
            f"Automated monitoring complete in {elapsed_seconds}s. "
            f"Processed: {results.get('total_locations_processed')}, "
            f"Created: {results.get('alerts_created')}, "
            f"Updated: {results.get('alerts_updated')}, "
            f"Resolved: {results.get('alerts_resolved')}"
        )
        return results

    except Exception as e:
        logger.error(f"Error during scheduled monitoring execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "code": "CRON_MONITORING_FAILED",
                "message": f"Scheduled monitoring failed: {str(e)}"
            }
        )
