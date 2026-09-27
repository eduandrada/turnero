import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Carga limpia de variables de entorno desde .env
load_dotenv()

logger = logging.getLogger("bladesync.config")

# Detección de entorno
APP_ENV = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()
IS_PRODUCTION = APP_ENV in ["production", "prod"]

# Secret key de la aplicación
DEFAULT_SECRET_KEY = "bladesync_secret_key_barberia_2026_x99"
INSECURE_SECRETS = {
    "",
    "default",
    "secret",
    "changeme",
    "bladesync_secret_key_barberia_2026_x99",
    "change_this_to_a_secure_random_32_character_secret_key",
}


def verify_production_secrets() -> None:
    """
    Verifica que en entornos de producción la clave secreta APP_SECRET_KEY
    esté configurada de forma explícita, segura y no utilice valores por defecto.
    Aborta el arranque con una excepción crítica (RuntimeError) si no cumple los requisitos.
    """
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
        logger.info("Verificación de seguridad en producción: APP_SECRET_KEY válida.")
    else:
        if not secret or secret in INSECURE_SECRETS:
            logger.warning(
                "MODO DESARROLLO: Utilizando APP_SECRET_KEY por defecto. "
                "Recuerde configurar una clave segura para despliegues en producción."
            )


def get_secret_key() -> str:
    """Devuelve la clave secreta activa o el fallback seguro para desarrollo."""
    secret = (os.getenv("APP_SECRET_KEY") or os.getenv("SECRET_KEY") or "").strip()
    if not secret or secret in INSECURE_SECRETS:
        if IS_PRODUCTION:
            verify_production_secrets()
        return DEFAULT_SECRET_KEY
    return secret
