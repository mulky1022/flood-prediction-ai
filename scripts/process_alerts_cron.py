"""
Scheduled Alert & Sentry Processing Cron.

Periodically evaluates all 33 monitored hydrological stations in Sri Lanka:
1. Ingests weather & generates ML inference
2. Evaluates operational alert policy
3. Creates, updates, or auto-resolves active alerts
4. Dispatches multi-channel notifications
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.alert_service import get_alert_service
from config.alert_config import SCHEDULED_PROCESSING_INTERVAL_MINUTES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AlertProcessingCron")


def run_cycle():
    logger.info("=== Starting Sri Lanka FloodWatch Scheduled Alert Evaluation Cycle ===")
    service = get_alert_service()
    start_time = time.time()
    
    result = service.process_all_monitored_locations()
    duration = time.time() - start_time

    logger.info(
        f"Cycle completed in {duration:.2f}s: "
        f"Processed {result.get('total_locations_processed')} stations | "
        f"Created: {result.get('alerts_created')} | "
        f"Updated: {result.get('alerts_updated')} | "
        f"Resolved: {result.get('alerts_resolved')} | "
        f"Total Active Alerts: {result.get('active_alerts_total')}"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Sri Lanka FloodWatch Alert Processing Engine")
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle and exit.")
    parser.add_argument(
        "--interval",
        type=int,
        default=SCHEDULED_PROCESSING_INTERVAL_MINUTES,
        help=f"Processing interval in minutes (default: {SCHEDULED_PROCESSING_INTERVAL_MINUTES})"
    )
    args = parser.parse_args()

    if args.once:
        run_cycle()
        return

    logger.info(f"Starting continuous alert daemon. Interval: {args.interval} minutes.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            logger.error(f"Error in alert processing cycle: {e}", exc_info=True)

        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
