"""
app/whatsapp_service.py - Backward compatibility facade. Re-exports from app.services.whatsapp_service.
"""
from app.services.whatsapp_service import (
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_ID,
    get_whatsapp_api_url,
    verify_whatsapp_signature,
    clean_phone_number,
    send_whatsapp_message,
    build_client_appointment_message,
    build_barber_appointment_message,
    send_appointment_whatsapp_notifications,
    process_whatsapp_status_update,
    retry_failed_whatsapp_notifications,
    send_whatsapp_interactive_reminder,
)

__all__ = [
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_ID",
    "get_whatsapp_api_url",
    "verify_whatsapp_signature",
    "clean_phone_number",
    "send_whatsapp_message",
    "build_client_appointment_message",
    "build_barber_appointment_message",
    "send_appointment_whatsapp_notifications",
    "process_whatsapp_status_update",
    "retry_failed_whatsapp_notifications",
    "send_whatsapp_interactive_reminder",
]
