"""
app/config.py - Backward compatibility facade. Re-exports configuration from app.core.config.
"""
from app.core.config import (
    APP_ENV,
    IS_PRODUCTION,
    DEFAULT_SECRET_KEY,
    INSECURE_SECRETS,
    DATABASE_URL,
    TIMEZONE_NAME,
    ADMIN_INITIAL_PASSWORD,
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_ACCESS_TOKEN,
    ALLOWED_ORIGINS,
    ENABLE_SCHEDULER,
    BACKUP_DIR,
    get_secret_key,
    verify_production_secrets,
)

__all__ = [
    "APP_ENV",
    "IS_PRODUCTION",
    "DEFAULT_SECRET_KEY",
    "INSECURE_SECRETS",
    "DATABASE_URL",
    "TIMEZONE_NAME",
    "ADMIN_INITIAL_PASSWORD",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ACCESS_TOKEN",
    "ALLOWED_ORIGINS",
    "ENABLE_SCHEDULER",
    "BACKUP_DIR",
    "get_secret_key",
    "verify_production_secrets",
]
