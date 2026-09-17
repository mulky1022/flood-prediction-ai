"""
Alert System Centralized Configuration.

Defines operational thresholds, risk tiers, duplicate-prevention parameters,
cooldown periods, notification channels, and retention rules for Sri Lanka FloodWatch.
"""

from typing import Dict, Any, List
import os

# Supported Operational Risk Levels
RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MODERATE = "MODERATE"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_CRITICAL = "CRITICAL"

SUPPORTED_RISK_LEVELS: List[str] = [
    RISK_LEVEL_LOW,
    RISK_LEVEL_MODERATE,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_CRITICAL,
]

# Supported Alert Statuses
ALERT_STATUS_ACTIVE = "ACTIVE"
ALERT_STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
ALERT_STATUS_RESOLVED = "RESOLVED"
ALERT_STATUS_EXPIRED = "EXPIRED"

SUPPORTED_ALERT_STATUSES: List[str] = [
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
    ALERT_STATUS_EXPIRED,
]

# Supported Notification Statuses
NOTIFICATION_STATUS_PENDING = "PENDING"
NOTIFICATION_STATUS_SENT = "SENT"
NOTIFICATION_STATUS_FAILED = "FAILED"
NOTIFICATION_STATUS_NOT_REQUIRED = "NOT_REQUIRED"
NOTIFICATION_STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"

# Operational Thresholds (Probability Bounds)
# Note: These represent operational early-warning tiers for emergency sentry dispatch,
# separated cleanly from underlying ML probability output.
PROBABILITY_THRESHOLDS: Dict[str, Dict[str, float]] = {
    RISK_LEVEL_LOW: {"min": 0.0, "max": 0.35},
    RISK_LEVEL_MODERATE: {"min": 0.35, "max": 0.60},
    RISK_LEVEL_HIGH: {"min": 0.60, "max": 0.80},
    RISK_LEVEL_CRITICAL: {"min": 0.80, "max": 1.0},
}

# Operational Alert Policy
ALERT_POLICY: Dict[str, Dict[str, Any]] = {
    RISK_LEVEL_LOW: {
        "is_alertable": False,
        "auto_resolve_active": True,
        "urgency": "NORMAL",
        "description": "Standard hydrological baseline. No flood hazard detected.",
        "default_recommendation": "Maintain standard routine catchment monitoring.",
    },
    RISK_LEVEL_MODERATE: {
        "is_alertable": False,  # Advisory telemetry tier; does not generate standalone alarm unless configured
        "auto_resolve_active": False,
        "urgency": "ADVISORY",
        "description": "Elevated runoff or antecedent precipitation detected in catchment.",
        "default_recommendation": "Heighten sensor monitoring frequency and inspect local drainage infrastructure.",
    },
    RISK_LEVEL_HIGH: {
        "is_alertable": True,
        "auto_resolve_active": False,
        "urgency": "HIGH",
        "description": "High flood probability identified. Basin runoff exceeds typical thresholds.",
        "default_recommendation": "Alert local emergency response units, prepare low-lying drainage channels, and monitor vulnerable communities.",
    },
    RISK_LEVEL_CRITICAL: {
        "is_alertable": True,
        "auto_resolve_active": False,
        "urgency": "CRITICAL",
        "description": "Critical flood risk identified. Inundation conditions highly probable.",
        "default_recommendation": "Activate emergency evacuation readiness protocols, notify district disaster management centers, and restrict access to low-lying riverbanks.",
    },
}

# Duplicate Prevention and Cooldown Rules
ALERT_COOLDOWN_SECONDS: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "1800"))  # 30 minutes
MAX_ACTIVE_ALERTS_PER_LOCATION: int = 1
SIGNIFICANT_PROBABILITY_DELTA: float = 0.05  # 5% change threshold to record updated telemetry

# Scheduled Processing Configuration
SCHEDULED_PROCESSING_INTERVAL_MINUTES: int = int(os.getenv("SCHEDULED_ALERT_INTERVAL_MINUTES", "15"))

# Notification Providers Configuration
NOTIFICATION_CONFIG: Dict[str, Any] = {
    "web_dashboard": {
        "enabled": True,
        "name": "Web/Dashboard Live Stream",
    },
    "email": {
        "enabled": bool(os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"),
        "smtp_host": os.getenv("SMTP_HOST"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "sender": os.getenv("ALERT_EMAIL_SENDER"),
        "recipients": [r.strip() for r in os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",") if r.strip()],
    },
    "sms": {
        "enabled": bool(os.getenv("ALERT_SMS_ENABLED", "false").lower() == "true"),
        "provider": os.getenv("SMS_PROVIDER"),
        "api_key": os.getenv("SMS_API_KEY"),
        "sender_id": os.getenv("SMS_SENDER_ID", "FLOODWATCH"),
        "recipients": [r.strip() for r in os.getenv("ALERT_SMS_RECIPIENTS", "").split(",") if r.strip()],
    },
}
