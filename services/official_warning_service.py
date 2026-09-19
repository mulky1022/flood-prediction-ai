"""
Official Warning Service.

Manages business logic, status evaluation, source attribution,
and ingestion for official government flood warnings.

CORE ARCHITECTURAL INVARIANT:
- Official Warning System IS SEPARATE from ML Flood-Risk Estimates.
- Official warnings originate from verified government authorities (DMC, Irrigation Dept, Met Dept).
- ML predictions do not fabricate official warnings.
- Absence of official warnings does not override or reduce ML risk scores.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from services.supabase_service import SupabaseService, get_supabase_service

logger = logging.getLogger("OfficialWarningService")


class OfficialWarningService:
    """
    Manages official government flood warnings.
    """

    def __init__(self, db_service: Optional[SupabaseService] = None):
        self.db = db_service or get_supabase_service()

    def get_current_warning(
        self,
        location_id: Union[int, str]
    ) -> Dict[str, Any]:
        """
        Retrieves the current official warning status for a location.
        Enforces location isolation.
        Returns a structured dictionary with state: ACTIVE, NO_ACTIVE_WARNING, EXPIRED, or UNAVAILABLE.
        """
        location = self.db.get_location(location_id)
        if not location:
            return {
                "status": "UNAVAILABLE",
                "state": "LOCATION_NOT_FOUND",
                "location_id": location_id,
                "warning": None,
                "message": f"Location '{location_id}' not found."
            }

        canonical_loc_id = location.get("id")

        try:
            warnings = self.db.get_official_warnings(canonical_loc_id)
            if not warnings or len(warnings) == 0:
                return {
                    "status": "success",
                    "state": "NO_ACTIVE_WARNING",
                    "location_id": canonical_loc_id,
                    "location_name": location.get("place_name") or location.get("name"),
                    "district": location.get("district"),
                    "warning": None,
                    "message": "No active official government warning for this location."
                }

            latest = warnings[0]
            st = str(latest.get("status") or "ACTIVE").upper()
            valid_until_str = latest.get("valid_until")
            is_expired = False

            if valid_until_str:
                try:
                    vul_dt = datetime.fromisoformat(str(valid_until_str).replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > vul_dt:
                        is_expired = True
                        latest["status"] = "EXPIRED"
                except Exception:
                    pass

            if st == "EXPIRED" or is_expired:
                return {
                    "status": "success",
                    "state": "EXPIRED",
                    "location_id": canonical_loc_id,
                    "location_name": location.get("place_name") or location.get("name"),
                    "district": location.get("district"),
                    "warning": latest,
                    "message": "Official warning for this location has expired."
                }

            if st == "ACTIVE":
                return {
                    "status": "success",
                    "state": "ACTIVE",
                    "location_id": canonical_loc_id,
                    "location_name": location.get("place_name") or location.get("name"),
                    "district": location.get("district"),
                    "warning": latest,
                    "message": "Active official government warning found."
                }

            return {
                "status": "success",
                "state": st,
                "location_id": canonical_loc_id,
                "location_name": location.get("place_name") or location.get("name"),
                "district": location.get("district"),
                "warning": latest,
                "message": f"Official warning status: '{st}'."
            }

        except Exception as e:
            logger.error(f"Error fetching official warning for location '{location_id}': {e}")
            return {
                "status": "error",
                "state": "UNAVAILABLE",
                "location_id": canonical_loc_id,
                "warning": None,
                "message": "Official warning information is temporarily unavailable."
            }

    def get_warning_history(
        self,
        location_id: Union[int, str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the full official warning history log for a location.
        """
        return self.db.get_official_warnings(location_id)

    def ingest_warning(
        self,
        warning_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates, normalizes, and persists an official government warning.
        Performs deduplication by warning_id.
        """
        location_id = warning_data.get("location_id")
        loc = self.db.get_location(location_id)
        if not loc:
            raise ValueError(f"Invalid location_id '{location_id}'. Location does not exist.")

        # Timestamp validation
        v_from = warning_data.get("valid_from") or datetime.now(timezone.utc).isoformat()
        v_until = warning_data.get("valid_until")
        if not v_until:
            raise ValueError("valid_until timestamp is required for official warnings.")

        try:
            vf_dt = datetime.fromisoformat(str(v_from).replace("Z", "+00:00"))
            vu_dt = datetime.fromisoformat(str(v_until).replace("Z", "+00:00"))
            if vu_dt < vf_dt:
                raise ValueError("valid_until cannot be earlier than valid_from timestamp.")
        except ValueError as e:
            if "valid_until cannot be earlier" in str(e):
                raise
            raise ValueError(f"Malformed timestamp format: {e}")

        # Default source attribution to Disaster Management Centre if not provided
        warning_data["source_id"] = warning_data.get("source_id") or "DMC-SL"
        warning_data["source_name"] = warning_data.get("source_name") or "Disaster Management Centre (DMC) Sri Lanka"
        warning_data["source_type"] = warning_data.get("source_type") or "GOVERNMENT_AGENCY"
        warning_data["location_id"] = loc.get("id")

        saved = self.db.save_official_warning(warning_data)
        logger.info(f"Ingested official warning '{saved.get('warning_id')}' for location '{loc.get('id')}'.")
        return saved

    def get_all_active_warnings(self) -> List[Dict[str, Any]]:
        """Retrieves all active official warnings."""
        return self.db.get_official_warnings(location_id=None, status_filter="ACTIVE")


# Singleton factory helper
_OFFICIAL_WARNING_SERVICE: Optional[OfficialWarningService] = None


def get_official_warning_service() -> OfficialWarningService:
    global _OFFICIAL_WARNING_SERVICE
    if _OFFICIAL_WARNING_SERVICE is None:
        _OFFICIAL_WARNING_SERVICE = OfficialWarningService()
    return _OFFICIAL_WARNING_SERVICE
