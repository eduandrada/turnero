import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barberia.db")
TIMEZONE_NAME = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")

ARGENTINA_OFFSET = timezone(timedelta(hours=-3))

try:
    APP_TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except Exception:
    APP_TIMEZONE = ARGENTINA_OFFSET

def get_argentina_now() -> datetime:
    """Retorna la fecha y hora actual en la zona horaria oficial del negocio (Argentina UTC-3)."""
    try:
        return datetime.now(APP_TIMEZONE)
    except Exception:
        return datetime.now(ARGENTINA_OFFSET)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db_and_migrate():
    """Crea las tablas y realiza migraciones no destructivas si faltan columnas."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # 1. Migration for appointments
        if "appointments" in tables:
            columns = [c["name"] for c in inspector.get_columns("appointments")]
            if "duration_min" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN duration_min INTEGER DEFAULT 45"))
                conn.commit()
            if "status" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN status VARCHAR(20) DEFAULT 'PENDIENTE'"))
                conn.commit()
            if "end_time" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN end_time DATETIME"))
                conn.commit()
            if "client_id" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN client_id INTEGER"))
                conn.commit()
            if "notes" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN notes TEXT"))
                conn.commit()

        # 2. Migration for barbers
        if "barbers" in tables:
            columns = [c["name"] for c in inspector.get_columns("barbers")]
            if "description" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN description TEXT"))
                conn.commit()
            if "working_days" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN working_days VARCHAR(100) DEFAULT 'Lunes,Martes,Miércoles,Jueves,Viernes,Sábado'"))
                conn.commit()
            if "display_order" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN display_order INTEGER DEFAULT 0"))
                conn.commit()

        # 3. Migration for services
        if "services" in tables:
            columns = [c["name"] for c in inspector.get_columns("services")]
            if "previous_price" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN previous_price FLOAT"))
                conn.commit()
            if "category" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN category VARCHAR(50) DEFAULT 'Cortes'"))
                conn.commit()
            if "image_url" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN image_url VARCHAR(500)"))
                conn.commit()
            if "display_order" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN display_order INTEGER DEFAULT 0"))
                conn.commit()

def get_db():
    """Dependency for obtaining a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
