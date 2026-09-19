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
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from services.risk_engine import RiskEngine

logger = logging.getLogger("SupabaseService")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# Local in-memory storage fallback for local development / testing
_LOCAL_WEATHER_OBSERVATIONS: List[Dict[str, Any]] = []
_LOCAL_PREDICTIONS: List[Dict[str, Any]] = []
_LOCAL_ALERTS: List[Dict[str, Any]] = []
_LOCAL_ALERT_PREFERENCES: List[Dict[str, Any]] = []
_LOCAL_TRIGGERED_ALERTS: List[Dict[str, Any]] = []
_LOCAL_OFFICIAL_WARNINGS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "warning_id": "TEST-WARN-RAT-001",
        "location_id": 7,
        "source_id": "DMC-SL",
        "source_name": "Disaster Management Centre (DMC) Sri Lanka",
        "source_type": "GOVERNMENT_AGENCY",
        "source_url": "https://www.dmc.gov.lk/warnings/2026-ratnapura",
        "official_reference": "DMC/FL/2026/09/18/RAT01",
        "warning_type": "FLOOD_WARNING",
        "severity": "MAJOR",
        "title": "Official Flood Warning — Kalu Ganga Basin (Ratnapura)",
        "message": "Irrigation Department & DMC report severe river overflow risk. Evacuate low-lying areas in Ratnapura Town immediately.",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
        "status": "ACTIVE",
        "language": "en",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
]
_PREDICTION_ID_COUNTER: int = 1
_ALERT_ID_COUNTER: int = 1
_PREFERENCE_ID_COUNTER: int = 1
_TRIGGERED_ALERT_ID_COUNTER: int = 1
_OFFICIAL_WARNING_ID_COUNTER: int = 2
_LOCAL_SUBSCRIPTIONS: List[Dict[str, Any]] = []
_LOCAL_NOTIFICATION_LOGS: List[Dict[str, Any]] = []
_LOCAL_SYSTEM_ERRORS: List[Dict[str, Any]] = []
_LOCAL_AUDIT_LOGS: List[Dict[str, Any]] = []
_LOCAL_PREDICTION_JOBS: List[Dict[str, Any]] = []




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

    def get_all_locations(self) -> List[Dict[str, Any]]:
        """Retrieves static locations dataset via LocationService."""
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

    def save_prediction(
        self,
        prediction_payload: Dict[str, Any],
        deduplicate_window_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Persists an ML prediction result into database with idempotency & deduplication checks.
        Prevents creating duplicate identical records if run repeatedly within a short window.
        """
        global _PREDICTION_ID_COUNTER
        loc = prediction_payload.get("location", {})
        pred = prediction_payload.get("prediction", {})
        model = prediction_payload.get("model", {})
        audit = prediction_payload.get("input_audit", {})
        quality = prediction_payload.get("data_quality", {})

        loc_id = loc.get("id")
        prob = pred.get("flood_probability", 0.0)
        pred_cls = pred.get("class", 0)

        # Idempotency Check: Look for recent identical prediction record for this location
        latest_existing = self.get_latest_prediction(loc_id)
        if latest_existing and deduplicate_window_minutes > 0:
            existing_created_str = latest_existing.get("created_at")
            if existing_created_str:
                try:
                    now_utc = datetime.now(timezone.utc)
                    if existing_created_str.endswith("Z"):
                        ex_dt = datetime.fromisoformat(existing_created_str.replace("Z", "+00:00"))
                    else:
                        ex_dt = datetime.fromisoformat(existing_created_str)
                    if ex_dt.tzinfo is None:
                        ex_dt = ex_dt.replace(tzinfo=timezone.utc)

                    age_minutes = (now_utc - ex_dt).total_seconds() / 60.0
                    ex_prob = float(latest_existing.get("flood_probability", -1.0))
                    ex_cls = int(latest_existing.get("prediction_class", -1))

                    if age_minutes <= deduplicate_window_minutes and abs(ex_prob - prob) < 0.001 and ex_cls == pred_cls:
                        logger.info(f"Duplicate prediction avoided for location '{loc_id}'. Returning existing prediction ID '{latest_existing.get('id')}'.")
                        return {
                            "status": "success",
                            "deduplicated": True,
                            "persisted_to": "idempotency_cache",
                            "data": latest_existing,
                            "prediction_id": latest_existing.get("id")
                        }
                except Exception as e:
                    logger.warning(f"Error evaluating prediction idempotency: {e}")

        pred_id = prediction_payload.get("prediction_id") or prediction_payload.get("id") or pred.get("prediction_id")
        risk_lvl = pred.get("risk_level", "LOW")
        action_mapping = RiskEngine.get_canonical_action(risk_lvl)

        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        record = {
            "prediction_id": pred_id,
            "location_id": loc_id,
            "created_at": now_iso,
            "prediction_time": pred.get("valid_from") or now_iso,
            "valid_from": pred.get("valid_from") or now_iso,
            "valid_until": pred.get("expires_at") or pred.get("valid_until"),
            "prediction_class": pred_cls,
            "flood_probability": prob,
            "flood_probability_percent": round(prob * 100, 2),
            "non_flood_probability": pred.get("non_flood_probability", 1.0),
            "risk_level": risk_lvl,
            "action_code": action_mapping["code"],
            "action_message": action_mapping["message"],
            "confidence": 0.90,
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
                supabase_record = {k: v for k, v in record.items() if k not in ["prediction_id", "valid_from", "valid_until", "action_code", "action_message", "confidence"]}
                resp = self.client.table("predictions").insert(supabase_record).execute()
                if resp.data and len(resp.data) > 0:
                    saved_row = resp.data[0]
                    merged_row = {**record, **saved_row}
                    return {"status": "success", "persisted_to": "supabase", "data": merged_row, "prediction_id": merged_row.get("id")}
            except Exception as e:
                logger.warning(f"Supabase prediction save failed: {e}. Storing locally.")

        record["id"] = _PREDICTION_ID_COUNTER
        _PREDICTION_ID_COUNTER += 1
        _LOCAL_PREDICTIONS.append(record)
        return {"status": "success", "persisted_to": "local_memory", "data": record, "prediction_id": record["id"]}

    def get_prediction_by_id(self, prediction_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single prediction record by its primary ID.
        Searches local in-memory records first, then remote database.
        """
        pred_id = int(prediction_id) if str(prediction_id).isdigit() else prediction_id

        for pred in _LOCAL_PREDICTIONS:
            if pred.get("id") == pred_id or str(pred.get("id")) == str(pred_id) or str(pred.get("prediction_id")) == str(pred_id):
                return pred

        if self.is_connected and self.client:
            try:
                resp = self.client.table("predictions").select("*").eq("id", pred_id).execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase get_prediction_by_id failed: {e}.")

        return None

    def get_prediction_history(
        self,
        location_id: Union[int, str],
        risk_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves historical prediction records for a location with optional filtering.
        Merges remote database records and local memory records, sorted by creation timestamp.
        """
        loc_id = int(location_id) if str(location_id).isdigit() else location_id
        combined: List[Dict[str, Any]] = []

        # Local memory records for this location
        matching_local = [p for p in _LOCAL_PREDICTIONS if p.get("location_id") == loc_id]
        combined.extend(matching_local)

        if self.is_connected and self.client:
            try:
                query = self.client.table("predictions").select("*").eq("location_id", loc_id)
                if risk_level and isinstance(risk_level, str):
                    query = query.eq("risk_level", risk_level.upper())
                if start_date and isinstance(start_date, str):
                    query = query.gte("created_at", start_date)
                if end_date and isinstance(end_date, str):
                    query = query.lte("created_at", end_date)

                resp = query.order("created_at", desc=True).range(0, offset + limit + 50).execute()
                if resp.data:
                    combined.extend(resp.data)
            except Exception as e:
                logger.warning(f"Supabase history query failed: {e}. Returning local records.")

        def _parse_ts(rec: Dict[str, Any]) -> float:
            c = rec.get("created_at") or rec.get("prediction_time")
            if not c:
                return 0.0
            try:
                s = str(c)
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except Exception:
                return 0.0

        # Filter local & merged records by risk_level, start_date, end_date if present
        filtered_records = []
        for rec in combined:
            if risk_level and str(rec.get("risk_level", "")).upper() != str(risk_level).upper():
                continue

            ts = _parse_ts(rec)
            if start_date:
                try:
                    s_str = str(start_date)
                    if s_str.endswith("Z"):
                        s_str = s_str[:-1] + "+00:00"
                    s_dt = datetime.fromisoformat(s_str)
                    if s_dt.tzinfo is None:
                        s_dt = s_dt.replace(tzinfo=timezone.utc)
                    if ts < s_dt.timestamp():
                        continue
                except Exception:
                    pass

            if end_date:
                try:
                    e_str = str(end_date)
                    if e_str.endswith("Z"):
                        e_str = e_str[:-1] + "+00:00"
                    e_dt = datetime.fromisoformat(e_str)
                    if e_dt.tzinfo is None:
                        e_dt = e_dt.replace(tzinfo=timezone.utc)
                    if ts > e_dt.timestamp():
                        continue
                except Exception:
                    pass

            filtered_records.append(rec)

        # Deduplicate records by ID / prediction_id
        seen_ids = set()
        unique_records = []
        for rec in filtered_records:
            r_id = rec.get("id") or rec.get("prediction_id")
            if r_id is not None:
                if r_id in seen_ids:
                    continue
                seen_ids.add(r_id)
            unique_records.append(rec)

        sorted_records = sorted(unique_records, key=_parse_ts, reverse=True)
        return sorted_records[offset: offset + limit]

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
            "prediction_id": alert_data.get("prediction_id"),
            "action_code": alert_data.get("action_code"),
            "action_message": alert_data.get("action_message"),
            "valid_from": alert_data.get("valid_from"),
            "expires_at": alert_data.get("expires_at"),
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

        if self.is_connected and self.client:
            try:
                # Strip keys not present in Supabase table schema if needed
                supabase_record = {k: v for k, v in record.items() if k not in ["action_code", "action_message"]}
                resp = self.client.table("alerts").insert(supabase_record).execute()
                if resp.data and len(resp.data) > 0:
                    merged = {**record, **resp.data[0]}
                    return {"status": "success", "persisted_to": "supabase", "data": merged}
            except Exception as e:
                logger.warning(f"Supabase alert save failed: {e}. Storing locally.")

        return {"status": "success", "persisted_to": "local_memory", "data": record}

    def update_alert(self, alert_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing alert record by its primary ID.
        """
        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        if "updated_at" not in updates:
            updates["updated_at"] = now_iso

        local_record = None
        for alert in _LOCAL_ALERTS:
            if alert.get("id") == alert_id:
                alert.update(updates)
                local_record = alert
                break

        if self.is_connected and self.client:
            try:
                supabase_updates = {k: v for k, v in updates.items() if k not in ["action_code", "action_message"]}
                resp = self.client.table("alerts").update(supabase_updates).eq("id", alert_id).execute()
                if resp.data and len(resp.data) > 0:
                    return {**(local_record or {}), **resp.data[0]}
            except Exception as e:
                logger.warning(f"Supabase update_alert failed: {e}. Updating in local store.")

        return local_record

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single alert by its ID.
        """
        local_match = next((a for a in _LOCAL_ALERTS if a.get("id") == alert_id), None)

        if self.is_connected and self.client:
            try:
                resp = self.client.table("alerts").select("*").eq("id", alert_id).execute()
                if resp.data and len(resp.data) > 0:
                    remote_rec = resp.data[0]
                    if local_match:
                        return {**local_match, **remote_rec, **{k: v for k, v in local_match.items() if k not in remote_rec or remote_rec[k] is None}}
                    return remote_rec
            except Exception as e:
                logger.warning(f"Supabase get_alert_by_id failed: {e}. Searching local store.")

        return local_match

    def get_active_alert_for_location(self, location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieves an ongoing ACTIVE or ACKNOWLEDGED alert for a given location.
        """
        loc_id = int(location_id) if str(location_id).isdigit() else location_id
        local_match = next((a for a in reversed(_LOCAL_ALERTS) if a.get("location_id") == loc_id and a.get("status") in ["ACTIVE", "ACKNOWLEDGED"]), None)

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
                    remote_rec = resp.data[0]
                    if local_match:
                        return {**local_match, **remote_rec, **{k: v for k, v in local_match.items() if k not in remote_rec or remote_rec[k] is None}}
                    return remote_rec
            except Exception as e:
                logger.warning(f"Supabase active alert query failed: {e}. Searching local store.")

        return local_match

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
        global _LOCAL_ALERT_PREFERENCES
        if self.is_connected and self.client:
            try:
                if preference_id:
                    self.client.table("alert_preferences").delete().eq("id", preference_id).execute()
                elif device_id:
                    query = self.client.table("alert_preferences").delete().eq("device_id", device_id)
                    if location_id is not None:
                        query = query.eq("location_id", location_id)
                    query.execute()
            except Exception as e:
                logger.warning(f"Supabase delete_alert_preference failed: {e}.")

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

    def get_official_warnings(
        self,
        location_id: Optional[Union[int, str]] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves official government warnings for a canonical location_id or all locations.
        Enforces location isolation when location_id is provided.
        """
        canonical_id = None
        if location_id is not None:
            loc = self.get_location(location_id)
            if not loc:
                return []
            canonical_id = loc.get("id")

        if self.is_connected and self.client:
            try:
                q = self.client.table("official_warnings").select("*")
                if canonical_id is not None:
                    q = q.eq("location_id", canonical_id)
                if status_filter:
                    q = q.eq("status", status_filter.upper())
                resp = q.order("issued_at", desc=True).execute()
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_official_warnings query failed: {e}. Falling back to local data.")

        now = datetime.now(timezone.utc)
        results = []
        for w in _LOCAL_OFFICIAL_WARNINGS:
            if canonical_id is None or str(w.get("location_id")) == str(canonical_id):
                # Update status if expired
                vul = w.get("valid_until")
                if vul:
                    try:
                        vul_dt = datetime.fromisoformat(str(vul).replace("Z", "+00:00"))
                        if now > vul_dt and w.get("status") == "ACTIVE":
                            w["status"] = "EXPIRED"
                    except Exception:
                        pass

                if status_filter:
                    if w.get("status", "").upper() == status_filter.upper():
                        results.append(w)
                else:
                    results.append(w)

        return sorted(results, key=lambda x: str(x.get("issued_at", "")), reverse=True)

    def get_active_official_warning(
        self,
        location_id: Union[int, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the single currently active official warning for a location_id.
        Returns None if no active warning exists.
        """
        warnings = self.get_official_warnings(location_id, status_filter="ACTIVE")
        if warnings and len(warnings) > 0:
            return warnings[0]
        return None

    def save_official_warning(self, warning_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists or updates an official government warning record.
        Deduplicates based on warning_id.
        """
        global _OFFICIAL_WARNING_ID_COUNTER

        w_id = warning_dict.get("warning_id")
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "warning_id": w_id or f"WARN-DMC-{int(datetime.now(timezone.utc).timestamp())}",
            "location_id": int(warning_dict.get("location_id", 7)),
            "source_id": warning_dict.get("source_id", "DMC-SL"),
            "source_name": warning_dict.get("source_name", "Disaster Management Centre (DMC) Sri Lanka"),
            "source_type": warning_dict.get("source_type", "GOVERNMENT_AGENCY"),
            "source_url": warning_dict.get("source_url"),
            "official_reference": warning_dict.get("official_reference"),
            "warning_type": warning_dict.get("warning_type", "FLOOD_WARNING"),
            "severity": warning_dict.get("severity", "MAJOR"),
            "title": warning_dict.get("title", "Official Warning"),
            "message": warning_dict.get("message", ""),
            "issued_at": warning_dict.get("issued_at") or now_iso,
            "valid_from": warning_dict.get("valid_from") or now_iso,
            "valid_until": warning_dict.get("valid_until") or (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
            "status": warning_dict.get("status", "ACTIVE").upper(),
            "language": warning_dict.get("language", "en"),
            "updated_at": now_iso
        }

        if self.is_connected and self.client:
            try:
                resp = self.client.table("official_warnings").upsert(record, on_conflict="warning_id").execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase save_official_warning failed: {e}. Using local storage.")

        # Local fallback with deduplication
        existing_idx = None
        for idx, item in enumerate(_LOCAL_OFFICIAL_WARNINGS):
            if item.get("warning_id") == record["warning_id"]:
                existing_idx = idx
                break

        if existing_idx is not None:
            record["id"] = _LOCAL_OFFICIAL_WARNINGS[existing_idx]["id"]
            record["created_at"] = _LOCAL_OFFICIAL_WARNINGS[existing_idx].get("created_at", now_iso)
            _LOCAL_OFFICIAL_WARNINGS[existing_idx] = record
        else:
            record["id"] = _OFFICIAL_WARNING_ID_COUNTER
            record["created_at"] = now_iso
            _OFFICIAL_WARNING_ID_COUNTER += 1
            _LOCAL_OFFICIAL_WARNINGS.append(record)

        return record

    def save_subscription(self, sub_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves or updates a Phase 15 SMS/WhatsApp subscription record.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        sub_id = sub_data.get("id") or f"SUB-{uuid.uuid4().hex[:8].upper()}"

        record = {
            "id": sub_id,
            "user_id": sub_data.get("user_id"),
            "device_id": sub_data.get("device_id"),
            "location_id": str(sub_data.get("location_id")),
            "channel": str(sub_data.get("channel", "sms")).lower(),
            "destination": sub_data.get("destination"),
            "destination_masked": sub_data.get("destination_masked"),
            "language": sub_data.get("language", "en"),
            "minimum_risk_level": sub_data.get("minimum_risk_level", "HIGH").upper(),
            "enabled": bool(sub_data.get("enabled", True)),
            "verified": bool(sub_data.get("verified", True)),
            "verification_code": sub_data.get("verification_code", "123456"),
            "created_at": sub_data.get("created_at", now_iso),
            "updated_at": now_iso
        }

        if self.is_connected and self.client:
            try:
                resp = self.client.table("subscriptions").upsert(record, on_conflict="id").execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase save_subscription query failed: {e}. Using local storage.")

        # Always maintain local memory sync
        global _LOCAL_SUBSCRIPTIONS
        existing_idx = None
        for idx, item in enumerate(_LOCAL_SUBSCRIPTIONS):
            if item.get("id") == sub_id:
                existing_idx = idx
                break

        if existing_idx is not None:
            _LOCAL_SUBSCRIPTIONS[existing_idx] = record
        else:
            _LOCAL_SUBSCRIPTIONS.append(record)

        if self.is_connected and self.client:
            try:
                resp = self.client.table("subscriptions").upsert(record, on_conflict="id").execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase save_subscription query failed: {e}. Using local storage.")

        return record

    def get_subscriptions(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        location_id: Optional[str] = None,
        channel: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves matching active subscriptions filtered by location_id, channel, user_id, or device_id.
        """
        if self.is_connected and self.client:
            try:
                q = self.client.table("subscriptions").select("*")
                if enabled_only:
                    q = q.eq("enabled", True)
                if location_id:
                    q = q.eq("location_id", str(location_id))
                if channel:
                    q = q.eq("channel", channel.lower())
                if user_id:
                    q = q.eq("user_id", user_id)
                if device_id:
                    q = q.eq("device_id", device_id)
                resp = q.execute()
                if resp.data is not None and len(resp.data) > 0:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_subscriptions query failed: {e}. Using local storage.")

        global _LOCAL_SUBSCRIPTIONS
        results = []
        for s in _LOCAL_SUBSCRIPTIONS:
            if enabled_only and not s.get("enabled", True):
                continue
            if location_id and str(s.get("location_id")) != str(location_id):
                continue
            if channel and str(s.get("channel")).lower() != str(channel).lower():
                continue
            if user_id and s.get("user_id") != user_id:
                continue
            if device_id and s.get("device_id") != device_id:
                continue
            results.append(s)
        return results

    def verify_subscription(self, subscription_id: str, code: str) -> Optional[Dict[str, Any]]:
        """
        Verifies subscription OTP and sets verified status to True.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        global _LOCAL_SUBSCRIPTIONS
        for s in _LOCAL_SUBSCRIPTIONS:
            if s.get("id") == subscription_id and s.get("verification_code") == code:
                s["verified"] = True
                s["enabled"] = True
                s["updated_at"] = now_iso
                return s
        return None

    def delete_subscription(self, subscription_id: str) -> bool:
        """
        Disables or deletes a subscription (unsubscribe).
        """
        global _LOCAL_SUBSCRIPTIONS
        for s in _LOCAL_SUBSCRIPTIONS:
            if s.get("id") == subscription_id:
                s["enabled"] = False
                return True
        return False

    def save_notification_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a Phase 15 notification delivery log.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        notif_id = log_data.get("id") or f"NOTIF-{uuid.uuid4().hex[:10].upper()}"

        record = {
            "id": notif_id,
            "alert_id": str(log_data.get("alert_id")),
            "prediction_id": log_data.get("prediction_id"),
            "location_id": str(log_data.get("location_id")),
            "subscription_id": str(log_data.get("subscription_id")),
            "channel": str(log_data.get("channel", "sms")).lower(),
            "destination_masked": log_data.get("destination_masked"),
            "language": log_data.get("language", "en"),
            "risk_level": log_data.get("risk_level", "HIGH"),
            "status": log_data.get("status", "PENDING").upper(),
            "provider_message_id": log_data.get("provider_message_id"),
            "retry_count": log_data.get("retry_count", 0),
            "failure_code": log_data.get("failure_code"),
            "failure_message": log_data.get("failure_message"),
            "created_at": log_data.get("created_at", now_iso),
            "sent_at": log_data.get("sent_at"),
            "delivered_at": log_data.get("delivered_at")
        }

        # Sync local memory
        global _LOCAL_NOTIFICATION_LOGS
        _LOCAL_NOTIFICATION_LOGS.append(record)

        if self.is_connected and self.client:
            try:
                resp = self.client.table("notification_logs").upsert(record, on_conflict="id").execute()
                if resp.data and len(resp.data) > 0:
                    return resp.data[0]
            except Exception as e:
                logger.warning(f"Supabase save_notification_log failed: {e}. Using local storage.")

        return record

    def update_notification_status(
        self,
        provider_message_id: str,
        new_status: str,
        failure_reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Updates delivery status of a notification by provider message ID.
        Ensures safe state transition (e.g. DELIVERED is preserved).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        global _LOCAL_NOTIFICATION_LOGS
        for log in _LOCAL_NOTIFICATION_LOGS:
            if log.get("provider_message_id") == provider_message_id:
                curr_status = log.get("status")
                # Do not overwrite DELIVERED with FAILED or older status
                if curr_status == "DELIVERED" and new_status != "DELIVERED":
                    return log

                log["status"] = new_status.upper()
                if new_status.upper() == "DELIVERED":
                    log["delivered_at"] = now_iso
                elif new_status.upper() == "FAILED" and failure_reason:
                    log["failure_message"] = failure_reason
                return log
        return None

    def get_notification_logs(
        self,
        alert_id: Optional[str] = None,
        location_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent notification logs.
        """
        if self.is_connected and self.client:
            try:
                q = self.client.table("notification_logs").select("*")
                if alert_id:
                    q = q.eq("alert_id", str(alert_id))
                if location_id:
                    q = q.eq("location_id", str(location_id))
                resp = q.order("created_at", desc=True).limit(limit).execute()
                if resp.data is not None and len(resp.data) > 0:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_notification_logs query failed: {e}. Using local storage.")

        global _LOCAL_NOTIFICATION_LOGS
        results = []
        for log in reversed(_LOCAL_NOTIFICATION_LOGS):
            if alert_id and str(log.get("alert_id")) != str(alert_id):
                continue
            if location_id and str(log.get("location_id")) != str(location_id):
                continue
            results.append(log)
            if len(results) >= limit:
                break
        return results

    def save_system_error(self, service: str, error_code: str, message: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Records a system exception or telemetry failure diagnostic log."""
        now_iso = datetime.now(timezone.utc).isoformat()
        err_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "id": err_id,
            "service": service,
            "error_code": error_code,
            "message": message,
            "location_id": str(location_id) if location_id else None,
            "created_at": now_iso
        }
        global _LOCAL_SYSTEM_ERRORS
        _LOCAL_SYSTEM_ERRORS.append(record)
        return record

    def get_system_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent system error diagnostic logs."""
        global _LOCAL_SYSTEM_ERRORS
        return list(reversed(_LOCAL_SYSTEM_ERRORS))[:limit]

    def save_admin_audit_log(self, actor: str, action: str, target: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Records an admin operation audit trail entry."""
        now_iso = datetime.now(timezone.utc).isoformat()
        audit_id = f"AUDIT-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "id": audit_id,
            "actor": actor,
            "action": action,
            "target": target,
            "details": details,
            "timestamp": now_iso
        }
        global _LOCAL_AUDIT_LOGS
        _LOCAL_AUDIT_LOGS.append(record)
        return record

    def get_admin_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent admin operation audit logs."""
        global _LOCAL_AUDIT_LOGS
        return list(reversed(_LOCAL_AUDIT_LOGS))[:limit]

    def save_job_log(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Records a prediction generation job execution log."""
        now_iso = datetime.now(timezone.utc).isoformat()
        job_id = job_data.get("job_id") or f"JOB-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "job_id": job_id,
            "job_type": job_data.get("job_type", "CANONICAL_PREDICTION_CRON"),
            "status": job_data.get("status", "SUCCESS"),
            "started_at": job_data.get("started_at", now_iso),
            "completed_at": job_data.get("completed_at", now_iso),
            "locations_requested": job_data.get("locations_requested", 7),
            "locations_processed": job_data.get("locations_processed", 7),
            "failed_count": job_data.get("failed_count", 0),
            "model_version": job_data.get("model_version", "v1.2.0-xgboost-prod"),
            "error_summary": job_data.get("error_summary")
        }
        global _LOCAL_PREDICTION_JOBS
        _LOCAL_PREDICTION_JOBS.append(record)
        return record

    def get_job_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves prediction pipeline job logs."""
        global _LOCAL_PREDICTION_JOBS
        if not _LOCAL_PREDICTION_JOBS:
            # Seed default historical job run if empty
            now_iso = datetime.now(timezone.utc).isoformat()
            default_job = {
                "job_id": f"JOB-{datetime.now().strftime('%Y%m%d')}-SYSTEM01",
                "job_type": "CANONICAL_PREDICTION_CRON",
                "status": "SUCCESS",
                "started_at": now_iso,
                "completed_at": now_iso,
                "locations_requested": 7,
                "locations_processed": 7,
                "failed_count": 0,
                "model_version": "v1.2.0-xgboost-prod",
                "error_summary": None
            }
            _LOCAL_PREDICTION_JOBS.append(default_job)
        return list(reversed(_LOCAL_PREDICTION_JOBS))[:limit]


# Global singleton instance

_SUPABASE_SERVICE: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    global _SUPABASE_SERVICE
    if _SUPABASE_SERVICE is None:
        _SUPABASE_SERVICE = SupabaseService()
    return _SUPABASE_SERVICE

