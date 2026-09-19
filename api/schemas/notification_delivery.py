"""
Pydantic Schemas for Phase 15 — WhatsApp & SMS Alert Delivery.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    user_id: Optional[str] = Field(None, example="USR-001")
    device_id: Optional[str] = Field(None, example="DEV-12345")
    location_id: str = Field(..., example="RATNAPURA_001")
    channel: str = Field(..., example="sms")  # "sms" or "whatsapp"
    destination: str = Field(..., example="+94771234567")  # E.164 phone number
    language: Optional[str] = Field("en", example="en")  # "en", "si", "ta"
    minimum_risk_level: Optional[str] = Field("HIGH", example="HIGH")  # "LOW", "MODERATE", "HIGH", "CRITICAL"


class SubscriptionVerify(BaseModel):
    subscription_id: str = Field(..., example="SUB-RAT-001")
    verification_code: str = Field(..., example="123456")


class SubscriptionItem(BaseModel):
    id: str = Field(..., example="SUB-RAT-001")
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    location_id: str = Field(..., example="RATNAPURA_001")
    location_name: Optional[str] = Field(None, example="Ratnapura")
    channel: str = Field(..., example="sms")
    destination_masked: str = Field(..., example="+9477****567")
    language: str = Field("en", example="en")
    minimum_risk_level: str = Field("HIGH", example="HIGH")
    enabled: bool = Field(True, example=True)
    verified: bool = Field(True, example=True)
    created_at: str
    updated_at: str


class SubscriptionResponse(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field("Subscription processed successfully.", example="Subscription saved.")
    subscription: SubscriptionItem


class SubscriptionListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=1)
    subscriptions: List[SubscriptionItem]


from typing import Optional, List, Union

class NotificationDispatchRequest(BaseModel):
    alert_id: str = Field(..., example="ALERT-RAT-001")
    prediction_id: Optional[Union[str, int]] = Field(None, example="PRED-RAT-001")
    location_id: str = Field(..., example="RATNAPURA_001")
    risk_level: str = Field(..., example="HIGH")
    action_code: Optional[str] = Field("PREPARE", example="PREPARE")


class NotificationLogItem(BaseModel):
    id: str = Field(..., example="NOTIF-001")
    alert_id: str = Field(..., example="ALERT-RAT-001")
    prediction_id: Optional[str] = Field(None, example="PRED-RAT-001")
    location_id: str = Field(..., example="RATNAPURA_001")
    subscription_id: str = Field(..., example="SUB-RAT-001")
    channel: str = Field(..., example="sms")
    destination_masked: str = Field(..., example="+9477****567")
    language: str = Field("en", example="en")
    risk_level: str = Field("HIGH", example="HIGH")
    status: str = Field("SENT", example="SENT")
    provider_message_id: Optional[str] = Field(None, example="MSG-SMS-998877")
    retry_count: int = Field(0, example=0)
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    created_at: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None


class NotificationLogListResponse(BaseModel):
    status: str = Field("success", example="success")
    total: int = Field(..., example=1)
    notifications: List[NotificationLogItem]


class DeliveryWebhookPayload(BaseModel):
    channel: str = Field(..., example="sms")
    provider_message_id: str = Field(..., example="MSG-SMS-998877")
    status: str = Field(..., example="DELIVERED")  # "SENT", "DELIVERED", "FAILED"
    failure_reason: Optional[str] = None
    signature: Optional[str] = None
