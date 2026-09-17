"""
Supabase PostgreSQL Database Service.

Handles persistence and queries for:
- locations (static GIS profiles)
- weather_observations (Open-Meteo ingestion telemetry)
- predictions (ML inference audits and history)

Includes automatic fallback to verified local static data / in-memory store
if Supabase credentials are not set in .env.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("SupabaseService")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# Local in-memory storage fallback for local development / testing
_LOCAL_WEATHER_OBSERVATIONS: List[Dict[str, Any]] = []
_LOCAL_PREDICTIONS: List[Dict[str, Any]] = []
_LOCAL_ALERTS: List[Dict[str, Any]] = []
_LOCAL_ALERT_PREFERENCES: List[Dict[str, Any]] = []
_LOCAL_TRIGGERED_ALERTS: List[Dict[str, Any]] = []
_ALERT_ID_COUNTER: int = 1
_PREFERENCE_ID_COUNTER: int = 1
_TRIGGERED_ALERT_ID_COUNTER: int = 1



class SupabaseService:
    """
    Encapsulates database operations against Supabase with local fallback.
    """

    def __init__(self):
        self.client = None
        self.is_connected = False
        self._init_client()

    def _init_client(self) -> None:
        """Initializes Supabase client if credentials are configured."""
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and "your-project" not in SUPABASE_URL:
            try:
                from supabase import create_client, Client
                clean_url = SUPABASE_URL.strip().rstrip('/')
                if clean_url.endswith('/rest/v1'):
                    clean_url = clean_url[:-8].rstrip('/')
                self.client: Client = create_client(clean_url, SUPABASE_SERVICE_ROLE_KEY)
                self.is_connected = True
                logger.info("Supabase client connected successfully.")
            except Exception as e:
                logger.warning(f"Could not connect to remote Supabase: {e}. Using local storage fallback.")
                self.is_connected = False
        else:
            logger.info("Supabase credentials not configured in .env. Operating in local fallback mode.")
            self.is_connected = False

    def get_locations(self) -> List[Dict[str, Any]]:
        """
        Retrieves all locations from Supabase or fallback location_service.
        """
        if self.is_connected and self.client:
            try:
                response = self.client.table("locations").select("*").order("id").execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase get_locations query failed: {e}. Falling back to local data.")

        # Fallback to Phase 2 static location service
        from services.location_service import get_all_locations
        return get_all_locations()

    def get_location(self, location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieves a location by its integer 'id' or 'record_id'.
        """
        if self.is_connected and self.client:
            try:
                if str(location_id).isdigit():
                    resp = self.client.table("locations").select("*").eq("id", int(location_id)).execute()
                else:
                    resp = self.client.table("locations").select("*").eq("record_id", str(location_id)).execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase get_location query failed: {e}. Falling back to local data.")

        from services.location_service import get_location_by_id
        return get_location_by_id(location_id)

    def upsert_locations(self, locations_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upserts location records into the Supabase database.
        """
        if not self.is_connected or not self.client:
            return {
                "status": "local_fallback",
                "message": "Supabase not connected. Locations loaded from local locations.json.",
                "count": len(locations_list)
            }

        try:
            resp = self.client.table("locations").upsert(locations_list, on_conflict="record_id").execute()
            return {
                "status": "success",
                "count": len(resp.data) if resp.data else len(locations_list),
                "message": f"Successfully upserted {len(locations_list)} locations into Supabase."
            }
        except Exception as e:
            logger.error(f"Failed to upsert locations into Supabase: {e}")
            return {
                "status": "error",
                "message": f"Supabase upsert failed: {str(e)}"
            }

    def save_weather_observation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a normalized weather observation into database.
        """
        record = {
            "location_id": weather_data.get("location", {}).get("id") or weather_data.get("location_id"),
            "observed_at": weather_data.get("current", {}).get("observed_at") or datetime.now(timezone.utc).isoformat(),
            "temperature_c": weather_data.get("current", {}).get("temperature_c"),
            "humidity_percent": weather_data.get("current", {}).get("humidity_percent"),
            "precipitation_mm": weather_data.get("current", {}).get("precipitation_mm"),
            "rain_mm": weather_data.get("current", {}).get("rain_mm"),
            "weather_code": weather_data.get("current", {}).get("weather_code"),
            "wind_speed_kmh": weather_data.get("current", {}).get("wind_speed_kmh"),
            "rainfall_7d_mm": weather_data.get("rainfall", {}).get("rainfall_7d_mm"),
            "monthly_rainfall_mm": weather_data.get("rainfall", {}).get("monthly_rainfall_mm"),
            "source": weather_data.get("source", {}).get("provider", "Open-Meteo"),
            "data_quality_status": weather_data.get("rainfall", {}).get("data_quality", "GOOD"),
            "window_start": weather_data.get("rainfall", {}).get("window_start"),
            "window_end": weather_data.get("rainfall", {}).get("window_end"),
            "expected_hours": weather_data.get("rainfall", {}).get("expected_hours", 168),
            "received_hours": weather_data.get("rainfall", {}).get("received_hours", 168),
            "missing_hours": weather_data.get("rainfall", {}).get("missing_hours", 0)
        }

        if self.is_connected and self.client:
            try:
                resp = self.client.table("weather_observations").insert(record).execute()
                return {"status": "success", "persisted_to": "supabase", "data": resp.data}
            except Exception as e:
                logger.warning(f"Supabase weather save failed: {e}. Storing locally.")

        _LOCAL_WEATHER_OBSERVATIONS.append(record)
        return {"status": "success", "persisted_to": "local_memory", "record_count": len(_LOCAL_WEATHER_OBSERVATIONS)}

    def save_prediction(self, prediction_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists an ML prediction result into database.
        """
        loc = prediction_payload.get("location", {})
        pred = prediction_payload.get("prediction", {})
        model = prediction_payload.get("model", {})
        audit = prediction_payload.get("input_audit", {})
        quality = prediction_payload.get("data_quality", {})

        record = {
            "location_id": loc.get("id"),
            "created_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
            "prediction_class": pred.get("class", 0),
            "flood_probability": pred.get("flood_probability", 0.0),
            "non_flood_probability": pred.get("non_flood_probability", 1.0),
            "model_name": model.get("name", "RandomForestClassifier"),
            "model_version": model.get("version", "1.0.0"),
            "feature_count": model.get("feature_count", 64),
            "weather_observed_at": audit.get("weather_retrieved_at"),
            "data_source": audit.get("weather_source", "Open-Meteo"),
            "data_quality_status": quality.get("weather_quality", "GOOD"),
            "ready_for_prediction": prediction_payload.get("ready_for_prediction", True),
            "prediction_status": prediction_payload.get("status", "success"),
            "error_message": prediction_payload.get("message"),
            "audit_metadata": {
                "rainfall_7d_mm": audit.get("rainfall_7d_mm"),
                "monthly_rainfall_mm": audit.get("monthly_rainfall_mm"),
                "missing_features": quality.get("missing_features", []),
                "invalid_features": quality.get("invalid_features", []),
                "unknown_categories": quality.get("unknown_categories", [])
            }
        }

        if self.is_connected and self.client:
            try:
                resp = self.client.table("predictions").insert(record).execute()
                return {"status": "success", "persisted_to": "supabase", "data": resp.data}
            except Exception as e:
                logger.warning(f"Supabase prediction save failed: {e}. Storing locally.")

        _LOCAL_PREDICTIONS.append(record)
        return {"status": "success", "persisted_to": "local_memory", "record_count": len(_LOCAL_PREDICTIONS)}

    def get_prediction_history(
        self,
        location_id: Union[int, str],
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves historical prediction records for a location.
        """
        loc_id = int(location_id) if str(location_id).isdigit() else location_id

        if self.is_connected and self.client:
            try:
                resp = (
                    self.client.table("predictions")
                    .select("*")
                    .eq("location_id", loc_id)
                    .order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase history query failed: {e}. Returning local records.")

        # Local memory filter
        matching = [p for p in _LOCAL_PREDICTIONS if p.get("location_id") == loc_id]
        sorted_matching = sorted(matching, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_matching[offset: offset + limit]

    def get_latest_prediction(self, location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent prediction record for a location.
        """
        history = self.get_prediction_history(location_id, limit=1)
        return history[0] if history else None

    # --------------------------------------------------------------------
    # Alerts Operations (Phase 7)
    # --------------------------------------------------------------------
    def save_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a new alert into database or local fallback store.
        """
        global _ALERT_ID_COUNTER
        loc_id = alert_data.get("location_id")
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

        record = {
            "location_id": int(loc_id) if str(loc_id).isdigit() else loc_id,
            "risk_level": alert_data.get("risk_level", "LOW"),
            "flood_probability": float(alert_data.get("flood_probability", 0.0)),
            "prediction_class": int(alert_data.get("prediction_class", 0)),
            "title": alert_data.get("title", ""),
            "message": alert_data.get("message", ""),
            "recommendation": alert_data.get("recommendation", ""),
            "status": alert_data.get("status", "ACTIVE"),
            "notification_status": alert_data.get("notification_status", "NOT_REQUIRED"),
            "data_source": alert_data.get("data_source", "Open-Meteo / RandomForest v1.0.0"),
            "created_at": alert_data.get("created_at") or now_iso,
            "updated_at": alert_data.get("updated_at") or now_iso,
            "acknowledged_at": alert_data.get("acknowledged_at"),
            "resolved_at": alert_data.get("resolved_at")
        }

        if self.is_connected and self.client:
            try:
                resp = self.client.table("alerts").insert(record).execute()
                if resp.data and len(resp.data) > 0:
                    return {"status": "success", "persisted_to": "supabase", "data": resp.data[0]}
            except Exception as e:
                logger.warning(f"Supabase alert save failed: {e}. Storing locally.")

        record["id"] = _ALERT_ID_COUNTER
        _ALERT_ID_COUNTER += 1
        _LOCAL_ALERTS.append(record)
        return {"status": "success", "persisted_to": "local_memory", "data": record}

    def update_alert(self, alert_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing alert record by its primary ID.
        """
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        if "updated_at" not in updates:
            updates["updated_at"] = now_iso

        if self.is_connected and self.client:
            try:
                resp = self.client.table("alerts").update(updates).eq("id", alert_id).execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase update_alert failed: {e}. Updating in local store.")

        for alert in _LOCAL_ALERTS:
            if alert.get("id") == alert_id:
                alert.update(updates)
                return alert
        return None

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single alert by its ID.
        """
        if self.is_connected and self.client:
            try:
                resp = self.client.table("alerts").select("*").eq("id", alert_id).execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase get_alert_by_id failed: {e}. Searching local store.")

        for alert in _LOCAL_ALERTS:
            if alert.get("id") == alert_id:
                return alert
        return None

    def get_active_alert_for_location(self, location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieves an ongoing ACTIVE or ACKNOWLEDGED alert for a given location.
        """
        loc_id = int(location_id) if str(location_id).isdigit() else location_id

        if self.is_connected and self.client:
            try:
                resp = (
                    self.client.table("alerts")
                    .select("*")
                    .eq("location_id", loc_id)
                    .in_("status", ["ACTIVE", "ACKNOWLEDGED"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase active alert query failed: {e}. Searching local store.")

        for alert in reversed(_LOCAL_ALERTS):
            if alert.get("location_id") == loc_id and alert.get("status") in ["ACTIVE", "ACKNOWLEDGED"]:
                return alert
        return None

    def get_alerts(
        self,
        status: Optional[str] = None,
        location_id: Optional[Union[int, str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves alert history filtered by status and/or location with pagination.
        """
        loc_id = int(location_id) if location_id is not None and str(location_id).isdigit() else location_id

        if self.is_connected and self.client:
            try:
                query = self.client.table("alerts").select("*")
                if status:
                    query = query.eq("status", status)
                if loc_id is not None:
                    query = query.eq("location_id", loc_id)
                resp = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_alerts query failed: {e}. Returning local store alerts.")

        results = _LOCAL_ALERTS
        if status:
            results = [a for a in results if a.get("status") == status]
        if loc_id is not None:
            results = [a for a in results if a.get("location_id") == loc_id]

        sorted_results = sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_results[offset: offset + limit]

    def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves all currently ACTIVE and ACKNOWLEDGED alerts.
        """
        if self.is_connected and self.client:
            try:
                resp = (
                    self.client.table("alerts")
                    .select("*")
                    .in_("status", ["ACTIVE", "ACKNOWLEDGED"])
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_active_alerts failed: {e}. Returning local store active alerts.")

        active = [a for a in _LOCAL_ALERTS if a.get("status") in ["ACTIVE", "ACKNOWLEDGED"]]
        sorted_active = sorted(active, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_active[:limit]

    def acknowledge_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Transitions an alert from ACTIVE to ACKNOWLEDGED.
        """
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        return self.update_alert(alert_id, {
            "status": "ACKNOWLEDGED",
            "acknowledged_at": now_iso
        })

    def resolve_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Transitions an alert to RESOLVED status.
        """
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        return self.update_alert(alert_id, {
            "status": "RESOLVED",
            "resolved_at": now_iso
        })

    def resolve_active_alerts_for_location(self, location_id: Union[int, str]) -> List[Dict[str, Any]]:
        """
        Resolves any active alerts for a given location when conditions return to safe baseline.
        """
        loc_id = int(location_id) if str(location_id).isdigit() else location_id
        resolved_list = []
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

        if self.is_connected and self.client:
            try:
                resp = (
                    self.client.table("alerts")
                    .update({"status": "RESOLVED", "resolved_at": now_iso, "updated_at": now_iso})
                    .eq("location_id", loc_id)
                    .in_("status", ["ACTIVE", "ACKNOWLEDGED"])
                    .execute()
                )
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase resolve_active_alerts_for_location failed: {e}.")

        for alert in _LOCAL_ALERTS:
            if alert.get("location_id") == loc_id and alert.get("status") in ["ACTIVE", "ACKNOWLEDGED"]:
                alert["status"] = "RESOLVED"
                alert["resolved_at"] = now_iso
                alert["updated_at"] = now_iso
                resolved_list.append(alert)
        return resolved_list

    # --------------------------------------------------------------------
    # Alert Preferences Operations
    # --------------------------------------------------------------------
    def save_alert_preference(self, preference_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates or updates a user alert preference record.
        """
        global _PREFERENCE_ID_COUNTER
        device_id = preference_data.get("device_id")
        loc_id = preference_data.get("location_id")
        if loc_id is not None and str(loc_id).isdigit():
            loc_id = int(loc_id)
        elif loc_id is not None and str(loc_id).lower() in ["null", "all", ""]:
            loc_id = None

        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        record = {
            "device_id": device_id,
            "location_id": loc_id,
            "risk_threshold": float(preference_data.get("risk_threshold", 35.0)),
            "notification_channels": preference_data.get("notification_channels", ["in_app"]),
            "is_active": bool(preference_data.get("is_active", True)),
            "created_at": preference_data.get("created_at") or now_iso,
            "updated_at": now_iso
        }

        # Enrich location names if location_id is present
        if loc_id:
            loc = self.get_location(loc_id)
            if loc:
                record["location_name"] = loc.get("place_name")
                record["district"] = loc.get("district")
        else:
            record["location_name"] = "All Monitored Stations"
            record["district"] = "Island-wide"

        if self.is_connected and self.client:
            try:
                # Check for existing matching preference for this device + location
                query = self.client.table("alert_preferences").select("*").eq("device_id", device_id)
                if loc_id is None:
                    query = query.is_("location_id", "null")
                else:
                    query = query.eq("location_id", loc_id)
                
                existing = query.execute()
                if existing.data and len(existing.data) > 0:
                    pref_id = existing.data[0]["id"]
                    resp = self.client.table("alert_preferences").update({
                        "risk_threshold": record["risk_threshold"],
                        "notification_channels": record["notification_channels"],
                        "is_active": record["is_active"],
                        "updated_at": now_iso
                    }).eq("id", pref_id).execute()
                    if resp.data:
                        merged = {**record, **resp.data[0]}
                        return {"status": "success", "persisted_to": "supabase", "data": merged}
                else:
                    resp = self.client.table("alert_preferences").insert(record).execute()
                    if resp.data:
                        merged = {**record, **resp.data[0]}
                        return {"status": "success", "persisted_to": "supabase", "data": merged}
            except Exception as e:
                logger.warning(f"Supabase save_alert_preference failed: {e}. Persisting to local memory.")

        # Local in-memory fallback
        for pref in _LOCAL_ALERT_PREFERENCES:
            if pref.get("device_id") == device_id and pref.get("location_id") == loc_id:
                pref["risk_threshold"] = record["risk_threshold"]
                pref["notification_channels"] = record["notification_channels"]
                pref["is_active"] = record["is_active"]
                pref["updated_at"] = now_iso
                return {"status": "success", "persisted_to": "local_memory", "data": pref}

        record["id"] = _PREFERENCE_ID_COUNTER
        _PREFERENCE_ID_COUNTER += 1
        _LOCAL_ALERT_PREFERENCES.append(record)
        return {"status": "success", "persisted_to": "local_memory", "data": record}

    def get_alert_preferences(
        self,
        device_id: Optional[str] = None,
        location_id: Optional[Union[int, str]] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves matching alert preferences.
        """
        loc_id = int(location_id) if location_id is not None and str(location_id).isdigit() else location_id

        if self.is_connected and self.client:
            try:
                query = self.client.table("alert_preferences").select("*")
                if device_id:
                    query = query.eq("device_id", device_id)
                if loc_id is not None:
                    query = query.eq("location_id", loc_id)
                if is_active is not None:
                    query = query.eq("is_active", is_active)
                
                resp = query.order("created_at", desc=True).execute()
                if resp.data:
                    # Enrich location details
                    for item in resp.data:
                        if item.get("location_id"):
                            loc = self.get_location(item["location_id"])
                            if loc:
                                item["location_name"] = loc.get("place_name")
                                item["district"] = loc.get("district")
                        else:
                            item["location_name"] = "All Monitored Stations"
                            item["district"] = "Island-wide"
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_alert_preferences failed: {e}. Using local store.")

        results = _LOCAL_ALERT_PREFERENCES
        if device_id:
            results = [p for p in results if p.get("device_id") == device_id]
        if loc_id is not None:
            results = [p for p in results if p.get("location_id") == loc_id]
        if is_active is not None:
            results = [p for p in results if p.get("is_active") == is_active]

        for p in results:
            if p.get("location_id"):
                loc = self.get_location(p["location_id"])
                if loc:
                    p["location_name"] = loc.get("place_name")
                    p["district"] = loc.get("district")
            else:
                p["location_name"] = "All Monitored Stations"
                p["district"] = "Island-wide"

        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

    def delete_alert_preference(
        self,
        preference_id: Optional[int] = None,
        device_id: Optional[str] = None,
        location_id: Optional[Union[int, str]] = None
    ) -> bool:
        """
        Deletes or deactivates an alert preference.
        """
        if self.is_connected and self.client:
            try:
                if preference_id:
                    self.client.table("alert_preferences").delete().eq("id", preference_id).execute()
                    return True
                elif device_id:
                    query = self.client.table("alert_preferences").delete().eq("device_id", device_id)
                    if location_id is not None:
                        query = query.eq("location_id", location_id)
                    query.execute()
                    return True
            except Exception as e:
                logger.warning(f"Supabase delete_alert_preference failed: {e}.")

        global _LOCAL_ALERT_PREFERENCES
        if preference_id:
            _LOCAL_ALERT_PREFERENCES = [p for p in _LOCAL_ALERT_PREFERENCES if p.get("id") != preference_id]
            return True
        elif device_id:
            if location_id is not None:
                _LOCAL_ALERT_PREFERENCES = [
                    p for p in _LOCAL_ALERT_PREFERENCES 
                    if not (p.get("device_id") == device_id and p.get("location_id") == location_id)
                ]
            else:
                _LOCAL_ALERT_PREFERENCES = [p for p in _LOCAL_ALERT_PREFERENCES if p.get("device_id") != device_id]
            return True
        return False

    # --------------------------------------------------------------------
    # Triggered Alerts Operations
    # --------------------------------------------------------------------
    def save_triggered_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a triggered alert created when an inference crosses a user threshold.
        """
        global _TRIGGERED_ALERT_ID_COUNTER
        loc_id = alert_data.get("location_id")
        loc_id = int(loc_id) if str(loc_id).isdigit() else loc_id
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

        prob = float(alert_data.get("flood_probability", 0.0))
        record = {
            "preference_id": alert_data.get("preference_id"),
            "device_id": alert_data.get("device_id"),
            "location_id": loc_id,
            "prediction_id": alert_data.get("prediction_id"),
            "flood_probability": prob,
            "risk_level": alert_data.get("risk_level", "LOW"),
            "threshold_crossed": float(alert_data.get("threshold_crossed", 35.0)),
            "title": alert_data.get("title", ""),
            "message": alert_data.get("message", ""),
            "status": alert_data.get("status", "UNREAD"),
            "created_at": alert_data.get("created_at") or now_iso
        }

        loc = self.get_location(loc_id)
        if loc:
            record["location_name"] = loc.get("place_name")
            record["district"] = loc.get("district")

        if self.is_connected and self.client:
            try:
                resp = self.client.table("triggered_alerts").insert(record).execute()
                if resp.data:
                    merged = {**record, **resp.data[0]}
                    merged["flood_probability_percent"] = round(prob * 100, 2)
                    return {"status": "success", "persisted_to": "supabase", "data": merged}
            except Exception as e:
                logger.warning(f"Supabase save_triggered_alert failed: {e}. Persisting to local memory.")

        record["id"] = _TRIGGERED_ALERT_ID_COUNTER
        _TRIGGERED_ALERT_ID_COUNTER += 1
        _LOCAL_TRIGGERED_ALERTS.append(record)
        res = {**record, "flood_probability_percent": round(prob * 100, 2)}
        return {"status": "success", "persisted_to": "local_memory", "data": res}

    def get_triggered_alerts(
        self,
        device_id: Optional[str] = None,
        location_id: Optional[Union[int, str]] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves triggered alert records.
        """
        loc_id = int(location_id) if location_id is not None and str(location_id).isdigit() else location_id

        if self.is_connected and self.client:
            try:
                query = self.client.table("triggered_alerts").select("*")
                if device_id:
                    query = query.eq("device_id", device_id)
                if loc_id is not None:
                    query = query.eq("location_id", loc_id)
                if status:
                    query = query.eq("status", status)

                resp = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
                if resp.data:
                    for item in resp.data:
                        if item.get("location_id"):
                            loc = self.get_location(item["location_id"])
                            if loc:
                                item["location_name"] = loc.get("place_name")
                                item["district"] = loc.get("district")
                        prob = float(item.get("flood_probability", 0.0))
                        item["flood_probability_percent"] = round(prob * 100, 2)
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_triggered_alerts failed: {e}. Using local store.")

        results = _LOCAL_TRIGGERED_ALERTS
        if device_id:
            results = [a for a in results if a.get("device_id") == device_id]
        if loc_id is not None:
            results = [a for a in results if a.get("location_id") == loc_id]
        if status:
            results = [a for a in results if a.get("status") == status]

        for a in results:
            if a.get("location_id"):
                loc = self.get_location(a["location_id"])
                if loc:
                    a["location_name"] = loc.get("place_name")
                    a["district"] = loc.get("district")
            prob = float(a.get("flood_probability", 0.0))
            a["flood_probability_percent"] = round(prob * 100, 2)

        sorted_results = sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)
        return sorted_results[offset: offset + limit]

    def update_triggered_alert_status(self, alert_id: int, status: str) -> Optional[Dict[str, Any]]:
        """
        Updates the read/dismissed status of a triggered alert.
        """
        if self.is_connected and self.client:
            try:
                resp = self.client.table("triggered_alerts").update({"status": status}).eq("id", alert_id).execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase update_triggered_alert_status failed: {e}.")

        for a in _LOCAL_TRIGGERED_ALERTS:
            if a.get("id") == alert_id:
                a["status"] = status
                return a
        return None


# Global singleton instance
_SUPABASE_SERVICE: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    global _SUPABASE_SERVICE
    if _SUPABASE_SERVICE is None:
        _SUPABASE_SERVICE = SupabaseService()
    return _SUPABASE_SERVICE

