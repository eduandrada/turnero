"""
app/core/config.py - Centralized configuration and environment settings for HiddenSYNC / Turnero.
Enforces strict secret validation for production and clean defaults for development/testing.
"""
import os
import logging
from typing import List, Optional, Set
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("hiddensync.config")

import sys

# Environment detection
APP_ENV: str = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()
IS_PRODUCTION: bool = APP_ENV in ["production", "prod"]
IS_TESTING: bool = APP_ENV in ["test", "testing"] or any("pytest" in arg for arg in sys.argv)

# Secrets and credentials
DEFAULT_SECRET_KEY: str = "hiddensync_secret_key_barberia_2026_x99"
INSECURE_SECRETS: Set[str] = {
    "",
    "default",
    "secret",
    "changeme",
    "admin123",
    "hiddensync_secret_key_barberia_2026_x99",
    "bladesync_secret_key_barberia_2026_x99",
    "change_this_to_a_secure_random_32_character_secret_key",
}

def get_secret_key() -> str:
    """Devuelve la clave secreta activa o fallback seguro en desarrollo."""
    secret = (os.getenv("APP_SECRET_KEY") or os.getenv("SECRET_KEY") or "").strip()
    env = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()
    is_prod = env in ["production", "prod"]
    if not secret or secret in INSECURE_SECRETS:
        if is_prod:
            verify_production_secrets()
        return DEFAULT_SECRET_KEY
    return secret

def verify_production_secrets() -> None:
    """Verifica que las variables críticas de producción estén correctamente configuradas."""
    secret = (os.getenv("APP_SECRET_KEY") or os.getenv("SECRET_KEY") or "").strip()
    env = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()
    is_prod = env in ["production", "prod"]

    if is_prod:
        if not secret:
            logger.critical("FATAL: APP_SECRET_KEY no está definida en entorno de producción.")
            raise RuntimeError(
                "CRÍTICO DE SEGURIDAD: Debe definir la variable de entorno 'APP_SECRET_KEY' en producción."
            )
        if secret in INSECURE_SECRETS or len(secret) < 16:
            logger.critical("FATAL: APP_SECRET_KEY contiene un valor inseguro o insuficiente en producción.")
            raise RuntimeError(
                "CRÍTICO DE SEGURIDAD: La variable 'APP_SECRET_KEY' en producción debe tener al menos 16 caracteres "
                "y no puede ser un valor por defecto o plantilla."
            )
        logger.info("Verificación de producción: APP_SECRET_KEY segura y válida.")
    else:
        if not secret or secret in INSECURE_SECRETS:
            logger.warning(
                "MODO DESARROLLO: Utilizando APP_SECRET_KEY por defecto. "
                "Recuerde configurar una clave segura para despliegues en producción."
            )

# Database URL
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./barberia.db")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Timezone settings
TIMEZONE_NAME: str = os.getenv("TIMEZONE", "America/Argentina/Catamarca")

# Initial Admin Password (STRICT: no insecure default fallback in production)
ADMIN_INITIAL_PASSWORD: Optional[str] = os.getenv("ADMIN_INITIAL_PASSWORD")

# WhatsApp Integration Secrets & Config
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "hiddensync_webhook_secret_token_2026")
WHATSAPP_APP_SECRET: Optional[str] = os.getenv("WHATSAPP_APP_SECRET")
WHATSAPP_PHONE_NUMBER_ID: Optional[str] = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN: Optional[str] = os.getenv("WHATSAPP_ACCESS_TOKEN")

# CORS and Network
ALLOWED_ORIGINS_STR: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in ALLOWED_ORIGINS_STR.split(",") if o.strip()]
if "*" in ALLOWED_ORIGINS or APP_ENV == "development":
    ALLOWED_ORIGINS = ["*"]

# Scheduler Decoupling Configuration
ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").strip().lower() in ["true", "1", "yes"]

# Backup directory
BACKUP_DIR: str = os.path.abspath(os.getenv("BACKUP_DIR", "backups"))
