"""
app/core/logging.py - Configuración y obtención de loggers especializados del sistema.
"""
import logging
import os
import re

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Patrones sensibles para sanitización de logs
SENSITIVE_PATTERNS = [
    (re.compile(r'(password|token|secret|authorization|key)[\s:=]+["\']?([^"\'\s,]+)', re.IGNORECASE), r'\1=***REDACTED***')
]

class SensitiveDataFilter(logging.Filter):
    """Filtra y oculta tokens, contraseñas y secretos de las trazas de logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True

# Formateador estructurado
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def setup_logger(name: str) -> logging.Logger:
    """Crea o retorna un logger configurado con filtro de datos sensibles."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.addFilter(SensitiveDataFilter())
        logger.addHandler(ch)
    return logger

# Loggers especializados requeridos por la arquitectura
app_logger = setup_logger("hiddensync.app")
security_logger = setup_logger("hiddensync.security")
audit_logger = setup_logger("hiddensync.audit")
scheduler_logger = setup_logger("hiddensync.scheduler")
whatsapp_logger = setup_logger("hiddensync.whatsapp")
backup_logger = setup_logger("hiddensync.backup")
