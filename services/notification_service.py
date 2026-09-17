"""
Notification Service.

Provides multi-channel operational notification delivery for Sri Lanka FloodWatch alerts:
1. Web / Dashboard Telemetry (application-level)
2. Email Alert Dispatch (SMTP - if configured)
3. SMS Alert Dispatch (SMS Gateway - if configured)

Maintains truthful delivery tracking without fabricating provider success.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from config.alert_config import (
    NOTIFICATION_CONFIG,
    NOTIFICATION_STATUS_PENDING,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_NOT_REQUIRED,
    NOTIFICATION_STATUS_NOT_CONFIGURED,
)

logger = logging.getLogger("NotificationService")


class NotificationService:
    """
    Orchestrates alert notification delivery across supported channels.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or NOTIFICATION_CONFIG

    def get_channel_status(self) -> Dict[str, Any]:
        """Returns the configured status of each notification delivery channel."""
        email_cfg = self.config.get("email", {})
        sms_cfg = self.config.get("sms", {})
        return {
            "web_dashboard": {"configured": True, "enabled": True},
            "email": {
                "configured": bool(email_cfg.get("smtp_host") and email_cfg.get("sender")),
                "enabled": bool(email_cfg.get("enabled", False))
            },
            "sms": {
                "configured": bool(sms_cfg.get("api_key") and sms_cfg.get("provider")),
                "enabled": bool(sms_cfg.get("enabled", False))
            }
        }

    def send_notification(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches alert notifications across configured channels and records truthful status.
        """
        alert_id = alert.get("id")
        risk_level = alert.get("risk_level", "LOW")
        title = alert.get("title", "Flood Risk Alert")
        message = alert.get("message", "")
        rec = alert.get("recommendation", "")
        loc_id = alert.get("location_id")

        results: Dict[str, Any] = {
            "web_dashboard": {"status": NOTIFICATION_STATUS_SENT, "channel": "web_dashboard"},
            "email": {"status": NOTIFICATION_STATUS_NOT_CONFIGURED, "channel": "email"},
            "sms": {"status": NOTIFICATION_STATUS_NOT_CONFIGURED, "channel": "sms"},
        }

        # 1. Web/Dashboard Alert (in-app telemetry is always ready)
        logger.info(f"Web/Dashboard alert broadcast ready for Alert #{alert_id} (Location {loc_id}, {risk_level})")

        # 2. Email Dispatch (if configured)
        email_cfg = self.config.get("email", {})
        if email_cfg.get("enabled") and email_cfg.get("smtp_host"):
            try:
                self._send_email(email_cfg, title, message, rec, alert)
                results["email"]["status"] = NOTIFICATION_STATUS_SENT
                logger.info(f"Email notification successfully sent for Alert #{alert_id}")
            except Exception as e:
                logger.error(f"Email notification failed for Alert #{alert_id}: {e}")
                results["email"]["status"] = NOTIFICATION_STATUS_FAILED
                results["email"]["error"] = str(e)
        else:
            results["email"]["status"] = NOTIFICATION_STATUS_NOT_CONFIGURED
            results["email"]["message"] = "Email notification provider not configured in environment."

        # 3. SMS Dispatch (if configured)
        sms_cfg = self.config.get("sms", {})
        if sms_cfg.get("enabled") and sms_cfg.get("api_key"):
            try:
                self._send_sms(sms_cfg, title, message, alert)
                results["sms"]["status"] = NOTIFICATION_STATUS_SENT
                logger.info(f"SMS notification successfully sent for Alert #{alert_id}")
            except Exception as e:
                logger.error(f"SMS notification failed for Alert #{alert_id}: {e}")
                results["sms"]["status"] = NOTIFICATION_STATUS_FAILED
                results["sms"]["error"] = str(e)
        else:
            results["sms"]["status"] = NOTIFICATION_STATUS_NOT_CONFIGURED
            results["sms"]["message"] = "SMS gateway provider not configured in environment."

        # Aggregate Overall Notification Status
        overall_status = NOTIFICATION_STATUS_NOT_REQUIRED
        if email_cfg.get("enabled") or sms_cfg.get("enabled"):
            has_success = (results["email"]["status"] == NOTIFICATION_STATUS_SENT) or (results["sms"]["status"] == NOTIFICATION_STATUS_SENT)
            has_failure = (results["email"]["status"] == NOTIFICATION_STATUS_FAILED) or (results["sms"]["status"] == NOTIFICATION_STATUS_FAILED)
            if has_success:
                overall_status = NOTIFICATION_STATUS_SENT
            elif has_failure:
                overall_status = NOTIFICATION_STATUS_FAILED
            else:
                overall_status = NOTIFICATION_STATUS_NOT_CONFIGURED
        else:
            overall_status = NOTIFICATION_STATUS_NOT_REQUIRED

        return {
            "overall_status": overall_status,
            "channels": results,
            "dispatched_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        }

    def _send_email(self, cfg: Dict[str, Any], title: str, message: str, recommendation: str, alert: Dict[str, Any]) -> None:
        """Sends email via standard smtplib."""
        import smtplib
        from email.mime.text import MIMEText

        smtp_host = cfg.get("smtp_host")
        smtp_port = cfg.get("smtp_port", 587)
        sender = cfg.get("sender")
        recipients = cfg.get("recipients", [])

        if not smtp_host or not sender or not recipients:
            raise ValueError("Incomplete SMTP settings in configuration.")

        body = f"{title}\n\n{message}\n\nOperational Recommendation:\n{recommendation}\n\nSri Lanka FloodWatch Early Warning System"
        msg = MIMEText(body)
        msg["Subject"] = f"[FloodWatch Alert] {title}"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.sendmail(sender, recipients, msg.as_string())

    def _send_sms(self, cfg: Dict[str, Any], title: str, message: str, alert: Dict[str, Any]) -> None:
        """Sends SMS via configured HTTP Gateway."""
        import urllib.request
        import json

        api_key = cfg.get("api_key")
        provider_url = cfg.get("provider")
        sender_id = cfg.get("sender_id", "FLOODWATCH")
        recipients = cfg.get("recipients", [])

        if not api_key or not provider_url or not recipients:
            raise ValueError("Incomplete SMS gateway settings in configuration.")

        payload = json.dumps({
            "api_key": api_key,
            "sender": sender_id,
            "recipients": recipients,
            "message": f"{title}: {message}"[:160]
        }).encode("utf-8")

        req = urllib.request.Request(provider_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status not in (200, 201, 202):
                raise RuntimeError(f"SMS Gateway returned HTTP {response.status}")


# Global singleton instance
_NOTIFICATION_SERVICE: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _NOTIFICATION_SERVICE
    if _NOTIFICATION_SERVICE is None:
        _NOTIFICATION_SERVICE = NotificationService()
    return _NOTIFICATION_SERVICE
