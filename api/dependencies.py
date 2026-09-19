"""
FastAPI Dependency Injections.
"""

from services.supabase_service import get_supabase_service, SupabaseService
from services.predictor import get_predictor, PredictorService
from services.alert_service import get_alert_service as get_alert_service_instance, AlertService
from services.notification_service import get_notification_service as get_notification_service_instance, NotificationService



from services.official_warning_service import get_official_warning_service as get_official_warning_service_instance, OfficialWarningService
from services.data_quality_service import get_data_quality_service as get_data_quality_service_instance, DataQualityService


def get_db() -> SupabaseService:
    """Returns database service instance."""
    return get_supabase_service()


def get_prediction_engine() -> PredictorService:
    """Returns ML predictor service instance."""
    return get_predictor()


def get_alert_service() -> AlertService:
    """Returns AlertService instance."""
    return get_alert_service_instance()


def get_notification_service() -> NotificationService:
    """Returns NotificationService instance."""
    return get_notification_service_instance()


def get_official_warning_service() -> OfficialWarningService:
    """Returns OfficialWarningService instance."""
    return get_official_warning_service_instance()


def get_quality_service() -> DataQualityService:
    """Returns DataQualityService instance."""
    return get_data_quality_service_instance()




