"""
app/database.py - Backward compatibility facade. Re-exports database components from app.core.database.
"""
from app.core.database import (
    DATABASE_URL,
    TIMEZONE_NAME,
    ARGENTINA_OFFSET,
    APP_TIMEZONE,
    get_argentina_now,
    get_catamarca_now,
    get_utc_now,
    connect_args,
    engine,
    SessionLocal,
    Base,
    init_db_and_migrate,
    get_db,
)

__all__ = [
    "DATABASE_URL",
    "TIMEZONE_NAME",
    "ARGENTINA_OFFSET",
    "APP_TIMEZONE",
    "get_argentina_now",
    "get_catamarca_now",
    "get_utc_now",
    "connect_args",
    "engine",
    "SessionLocal",
    "Base",
    "init_db_and_migrate",
    "get_db",
]
