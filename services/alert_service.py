"""
Alert Service.

Orchestrates the operational flood alert lifecycle:
1. Policy evaluation on ML predictions (probabilistic tiers -> operational risk levels)
2. Alert generation, deduplication, updating, and resolution
3. Integration with Supabase persistence and Notification Service
4. Enrichment of alert payloads with geospatial location profiles
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union

from config.alert_config import (
    RISK_LEVEL_LOW,
    RISK_LEVEL_MODERATE,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_CRITICAL,
    ALERT_POLICY,
    PROBABILITY_THRESHOLDS,
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
    NOTIFICATION_STATUS_NOT_REQUIRED,
    NOTIFICATION_STATUS_SENT,
    SIGNIFICANT_PROBABILITY_DELTA,
)
from services.location_service import get_location_by_id, get_all_locations
from services.supabase_service import get_supabase_service, SupabaseService
from services.predictor import get_predictor, PredictorService
from services.notification_service import get_notification_service, NotificationService

logger = logging.getLogger("AlertService")


class AlertService:
    """
    Central operational alert management service.
    """

    def __init__(
        self,
        db: Optional[SupabaseService] = None,
        predictor: Optional[PredictorService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.db = db or get_supabase_service()
        self.predictor = predictor or get_predictor()
        self.notification_service = notification_service or get_notification_service()

    def evaluate_prediction_for_alert(self, prediction_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates an ML prediction against centralized operational policies.
        Does NOT recalculate ML probabilities; operates strictly on inference output.
        """
        pred = prediction_payload.get("prediction", {})
        loc = prediction_payload.get("location", {})
        model = prediction_payload.get("model", {})
        audit = prediction_payload.get("input_audit", {})

        prob = float(pred.get("flood_probability", 0.0))
        pred_class = int(pred.get("class", 0))

        # Determine operational risk level from continuous probability
        if prob >= PROBABILITY_THRESHOLDS[RISK_LEVEL_CRITICAL]["min"]:
            risk_level = RISK_LEVEL_CRITICAL
        elif prob >= PROBABILITY_THRESHOLDS[RISK_LEVEL_HIGH]["min"]:
            risk_level = RISK_LEVEL_HIGH
        elif prob >= PROBABILITY_THRESHOLDS[RISK_LEVEL_MODERATE]["min"]:
            risk_level = RISK_LEVEL_MODERATE
        else:
            risk_level = RISK_LEVEL_LOW

        policy = ALERT_POLICY.get(risk_level, ALERT_POLICY[RISK_LEVEL_LOW])
        is_alertable = bool(policy.get("is_alertable", False))
        auto_resolve = bool(policy.get("auto_resolve_active", False))

        place_name = loc.get("place_name", "Monitored Station")
        district = loc.get("district", "Sri Lanka")
        prob_pct = round(prob * 100, 2)

        # Generate factual operational titles and descriptions without fabricating authorities
        if risk_level == RISK_LEVEL_CRITICAL:
            title = f"Critical Flood Risk Warning — {place_name}"
            message = (
                f"Continuous hydrological model indicates critical flood inundation probability of {prob_pct}% "
                f"at {place_name} ({district} Catchment). High precipitation accumulation observed."
            )
        elif risk_level == RISK_LEVEL_HIGH:
            title = f"High Flood Risk Warning — {place_name}"
            message = (
                f"Continuous hydrological model indicates elevated flood probability of {prob_pct}% "
                f"at {place_name} ({district} Catchment). Runoff capacity nearing threshold."
            )
        elif risk_level == RISK_LEVEL_MODERATE:
            title = f"Moderate Flood Risk Advisory — {place_name}"
            message = (
                f"Hydrological sentry detects moderate probability of {prob_pct}% at {place_name} ({district} Catchment). "
                f"Heightened telemetry monitoring active."
            )
        else:
            title = f"Normal Hydrological Baseline — {place_name}"
            message = f"Hydrological sentry detects normal baseline conditions ({prob_pct}%) at {place_name} ({district})."

        recommendation = policy.get("default_recommendation", "Maintain routine monitoring.")
        data_source = f"{audit.get('weather_source', 'Open-Meteo')} / {model.get('name', 'RandomForest')} v{model.get('version', '1.0.0')}"

        return {
            "risk_level": risk_level,
            "is_alertable": is_alertable,
            "auto_resolve": auto_resolve,
            "flood_probability": prob,
            "flood_probability_percent": prob_pct,
            "prediction_class": pred_class,
            "title": title,
            "message": message,
            "recommendation": recommendation,
            "data_source": data_source,
            "location": loc
        }

    def process_location_alert(
        self,
        location_id: Union[int, str],
        prediction_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end alert evaluation for a location with robust duplicate prevention:
        1. Obtains or uses latest ML inference
        2. Evaluates operational alert policy
        3. Creates, updates, or resolves active alerts
        4. Dispatches notifications when appropriate
        """
        loc = self.db.get_location(location_id)
        if not loc:
            return {
                "status": "error",
                "action_taken": "LOCATION_NOT_FOUND",
                "location_id": location_id,
                "message": f"Location '{location_id}' not found.",
                "alert": None
            }

        numeric_loc_id = loc.get("id")

        # 1. Obtain prediction if not provided
        if prediction_payload is None:
            prediction_payload = self.predictor.predict_location(numeric_loc_id, use_cache=True)
            if prediction_payload.get("status") != "success":
                return {
                    "status": "error",
                    "action_taken": "PREDICTION_UNAVAILABLE",
                    "location_id": numeric_loc_id,
                    "message": prediction_payload.get("message", "Prediction could not be generated."),
                    "alert": None
                }
            # Save prediction audit
            self.db.save_prediction(prediction_payload)

        # 2. Evaluate Policy
        evaluation = self.evaluate_prediction_for_alert(prediction_payload)
        risk_level = evaluation["risk_level"]
        is_alertable = evaluation["is_alertable"]
        auto_resolve = evaluation["auto_resolve"]
        prob = evaluation["flood_probability"]
        pred_class = evaluation["prediction_class"]

        now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

        # 3. Check for existing ongoing alert
        existing_alert = self.db.get_active_alert_for_location(numeric_loc_id)

        # 4. Handle Alertable Scenarios (HIGH or CRITICAL)
        if is_alertable:
            if existing_alert:
                # Duplicate Prevention: update existing active alert instead of creating a new one
                prev_prob = float(existing_alert.get("flood_probability", 0.0))
                prev_risk = existing_alert.get("risk_level")
                alert_id = existing_alert["id"]

                updates = {
                    "flood_probability": prob,
                    "risk_level": risk_level,
                    "title": evaluation["title"],
                    "message": evaluation["message"],
                    "recommendation": evaluation["recommendation"],
                    "updated_at": now_iso
                }

                # If risk escalated (e.g. HIGH -> CRITICAL) or significant delta, trigger notification
                if risk_level != prev_risk and risk_level == RISK_LEVEL_CRITICAL:
                    notif_res = self.notification_service.send_notification({
                        **existing_alert,
                        **updates
                    })
                    updates["notification_status"] = notif_res.get("overall_status", NOTIFICATION_STATUS_SENT)
                    logger.info(f"Risk escalated for Alert #{alert_id} ({prev_risk} -> {risk_level}); notification dispatched.")

                updated_record = self.db.update_alert(alert_id, updates)
                enriched = self._enrich_alert_with_location(updated_record or existing_alert, loc)

                logger.info(f"Updated existing active Alert #{alert_id} for Location {numeric_loc_id} (P: {prev_prob:.4f} -> {prob:.4f})")
                return {
                    "status": "success",
                    "action_taken": "ALERT_UPDATED",
                    "location_id": numeric_loc_id,
                    "message": f"Existing active alert for {loc.get('place_name')} updated with latest probability ({evaluation['flood_probability_percent']}%).",
                    "alert": enriched
                }
            else:
                # Create NEW Active Alert
                new_alert_data = {
                    "location_id": numeric_loc_id,
                    "risk_level": risk_level,
                    "flood_probability": prob,
                    "prediction_class": pred_class,
                    "title": evaluation["title"],
                    "message": evaluation["message"],
                    "recommendation": evaluation["recommendation"],
                    "status": ALERT_STATUS_ACTIVE,
                    "notification_status": NOTIFICATION_STATUS_NOT_REQUIRED,
                    "data_source": evaluation["data_source"],
                    "created_at": now_iso,
                    "updated_at": now_iso
                }

                # Save initially to acquire ID
                save_res = self.db.save_alert(new_alert_data)
                created_record = save_res.get("data", new_alert_data)
                alert_id = created_record.get("id")

                # Dispatch Notification
                notif_res = self.notification_service.send_notification(created_record)
                notif_status = notif_res.get("overall_status", NOTIFICATION_STATUS_NOT_REQUIRED)

                # Update notification status on created record
                if alert_id:
                    self.db.update_alert(alert_id, {"notification_status": notif_status})
                    created_record["notification_status"] = notif_status

                enriched = self._enrich_alert_with_location(created_record, loc)
                logger.info(f"Created new {risk_level} Alert #{alert_id} for Location {numeric_loc_id} ({loc.get('place_name')})")

                return {
                    "status": "success",
                    "action_taken": "ALERT_CREATED",
                    "location_id": numeric_loc_id,
                    "message": f"New {risk_level} alert created for {loc.get('place_name')}.",
                    "alert": enriched
                }

        # 5. Handle Non-Alertable Scenarios (LOW or MODERATE)
        else:
            if existing_alert and auto_resolve:
                # Auto-resolve existing active alert as conditions returned to normal baseline
                alert_id = existing_alert["id"]
                resolved_record = self.db.resolve_alert(alert_id)
                enriched = self._enrich_alert_with_location(resolved_record or existing_alert, loc)

                logger.info(f"Auto-resolved Alert #{alert_id} for Location {numeric_loc_id} as risk decreased to {risk_level}.")
                return {
                    "status": "success",
                    "action_taken": "ALERT_RESOLVED",
                    "location_id": numeric_loc_id,
                    "message": f"Active alert for {loc.get('place_name')} resolved as flood risk dropped to {risk_level}.",
                    "alert": enriched
                }
            elif existing_alert:
                # If MODERATE risk and policy preserves active alert, keep it active with updated telemetry
                alert_id = existing_alert["id"]
                updates = {
                    "flood_probability": prob,
                    "risk_level": risk_level,
                    "title": evaluation["title"],
                    "message": evaluation["message"],
                    "recommendation": evaluation["recommendation"],
                    "updated_at": now_iso
                }
                updated_record = self.db.update_alert(alert_id, updates)
                enriched = self._enrich_alert_with_location(updated_record or existing_alert, loc)
                return {
                    "status": "success",
                    "action_taken": "ALERT_UPDATED",
                    "location_id": numeric_loc_id,
                    "message": f"Active alert for {loc.get('place_name')} maintained in advisory status.",
                    "alert": enriched
                }
            else:
                return {
                    "status": "success",
                    "action_taken": "NO_ALERT_REQUIRED",
                    "location_id": numeric_loc_id,
                    "message": f"No alert required for {loc.get('place_name')} (Risk: {risk_level}, P: {evaluation['flood_probability_percent']}%).",
                    "alert": None
                }

    def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves all currently active / acknowledged alerts enriched with location metadata.
        """
        raw_alerts = self.db.get_active_alerts(limit=limit)
        return [self._enrich_alert(a) for a in raw_alerts]

    def get_alert_history(
        self,
        status: Optional[str] = None,
        location_id: Optional[Union[int, str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves alert history filtered by status and/or location with pagination.
        """
        raw_alerts = self.db.get_alerts(status=status, location_id=location_id, limit=limit, offset=offset)
        return [self._enrich_alert(a) for a in raw_alerts]

    def get_alert_by_id(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single alert by ID enriched with location details.
        """
        raw_alert = self.db.get_alert_by_id(alert_id)
        if not raw_alert:
            return None
        return self._enrich_alert(raw_alert)

    def acknowledge_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Acknowledges an active alert.
        """
        alert = self.db.get_alert_by_id(alert_id)
        if not alert:
            return None
        updated = self.db.acknowledge_alert(alert_id)
        return self._enrich_alert(updated or alert)

    def resolve_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Resolves an alert.
        """
        alert = self.db.get_alert_by_id(alert_id)
        if not alert:
            return None
        updated = self.db.resolve_alert(alert_id)
        return self._enrich_alert(updated or alert)

    def evaluate_and_trigger_user_preferences(
        self,
        location_id: Union[int, str],
        prediction_payload: Dict[str, Any],
        previous_prediction: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Checks current inference against all active user alert preferences.
        Triggers an alert if current probability crosses a preference threshold
        on transition from below threshold (or first evaluation) to avoid spam.
        """
        loc = self.db.get_location(location_id)
        if not loc:
            return []

        numeric_loc_id = loc.get("id")
        pred = prediction_payload.get("prediction", {})
        curr_prob = float(pred.get("flood_probability", 0.0))
        curr_prob_pct = round(curr_prob * 100, 2)
        risk_level = pred.get("risk_level", "LOW")
        prediction_id = prediction_payload.get("prediction_id") or prediction_payload.get("id")

        prev_prob = float(previous_prediction.get("flood_probability", 0.0)) if previous_prediction else 0.0
        prev_prob_pct = round(prev_prob * 100, 2)

        # Get active preferences for this specific station or global (all stations)
        active_prefs = self.db.get_alert_preferences(is_active=True)
        station_prefs = [
            p for p in active_prefs 
            if p.get("location_id") == numeric_loc_id or p.get("location_id") is None
        ]

        triggered_records = []
        for pref in station_prefs:
            threshold = float(pref.get("risk_threshold", 35.0))
            # Transition check: current >= threshold AND (prev < threshold OR no prev)
            if curr_prob_pct >= threshold:
                is_transition = (prev_prob_pct < threshold) or (previous_prediction is None)
                if is_transition:
                    alert_title = f"{risk_level} Flood Risk Alert: {loc.get('place_name')}"
                    alert_msg = (
                        f"Station {loc.get('place_name')} ({loc.get('district')}) has exceeded your {threshold:.0f}% threshold. "
                        f"Current flood risk is {curr_prob_pct}% ({risk_level})."
                    )
                    triggered_data = {
                        "preference_id": pref.get("id"),
                        "device_id": pref.get("device_id"),
                        "location_id": numeric_loc_id,
                        "prediction_id": prediction_id,
                        "flood_probability": curr_prob,
                        "risk_level": risk_level,
                        "threshold_crossed": threshold,
                        "title": alert_title,
                        "message": alert_msg,
                        "status": "UNREAD"
                    }
                    save_res = self.db.save_triggered_alert(triggered_data)
                    if save_res.get("data"):
                        triggered_records.append(save_res.get("data"))
                        logger.info(f"Triggered alert saved for Device {pref.get('device_id')} at Location {numeric_loc_id} (Threshold: {threshold}%, Prob: {curr_prob_pct}%)")

        return triggered_records

    def process_all_monitored_locations(self) -> Dict[str, Any]:
        """
        Batch-evaluates alerts for all 33 monitoring stations across Sri Lanka.
        """
        locations = self.db.get_locations()
        created_count = 0
        updated_count = 0
        resolved_count = 0
        triggered_alerts_total = 0
        results = []

        for loc in locations:
            loc_id = loc.get("id")
            try:
                res = self.process_location_alert(loc_id)
                action = res.get("action_taken")
                if action == "ALERT_CREATED":
                    created_count += 1
                elif action == "ALERT_UPDATED":
                    updated_count += 1
                elif action == "ALERT_RESOLVED":
                    resolved_count += 1
                results.append(res)
            except Exception as e:
                logger.error(f"Failed processing alert for location {loc_id}: {e}")
                results.append({
                    "status": "error",
                    "action_taken": "PROCESSING_ERROR",
                    "location_id": loc_id,
                    "message": str(e),
                    "alert": None
                })

        return {
            "status": "success",
            "total_locations_processed": len(locations),
            "alerts_created": created_count,
            "alerts_updated": updated_count,
            "alerts_resolved": resolved_count,
            "active_alerts_total": len(self.get_active_alerts()),
            "details": results
        }

    def _enrich_alert(self, alert_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches an alert record with full location GIS metadata."""
        loc_id = alert_dict.get("location_id")
        loc = self.db.get_location(loc_id) if loc_id is not None else None
        return self._enrich_alert_with_location(alert_dict, loc)

    def _enrich_alert_with_location(
        self,
        alert_dict: Dict[str, Any],
        location: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Formats alert and attaches location attributes and percentage helper."""
        prob = float(alert_dict.get("flood_probability", 0.0))
        enriched = dict(alert_dict)
        enriched["flood_probability_percent"] = round(prob * 100, 2)

        if location:
            enriched["location"] = {
                "id": location.get("id"),
                "record_id": location.get("record_id"),
                "district": location.get("district"),
                "place_name": location.get("place_name"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude")
            }
        else:
            enriched["location"] = None

        return enriched


# Global singleton instance
_ALERT_SERVICE: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    global _ALERT_SERVICE
    if _ALERT_SERVICE is None:
        _ALERT_SERVICE = AlertService()
    return _ALERT_SERVICE
