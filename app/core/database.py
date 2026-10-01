"""
app/core/database.py - Database engine, session management, and schema migration utilities.
Fully compatible with both SQLite and PostgreSQL.
"""
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import DATABASE_URL, TIMEZONE_NAME

ARGENTINA_OFFSET = timezone(timedelta(hours=-3))

try:
    APP_TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except Exception:
    APP_TIMEZONE = ARGENTINA_OFFSET

def get_argentina_now() -> datetime:
    """Retorna la fecha y hora actual en la zona horaria oficial del negocio (Catamarca UTC-3)."""
    try:
        return datetime.now(APP_TIMEZONE)
    except Exception:
        return datetime.now(ARGENTINA_OFFSET)

def get_catamarca_now() -> datetime:
    """Alias explícito para la zona horaria de Catamarca (UTC-3)."""
    return get_argentina_now()

def get_utc_now() -> datetime:
    """Retorna la fecha y hora actual en UTC usando objetos timezone-aware."""
    return datetime.now(timezone.utc)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
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
                conn.execute(text("ALTER TABLE appointments ADD COLUMN end_time TIMESTAMP"))
                conn.commit()
            if "client_id" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN client_id INTEGER"))
                conn.commit()
            if "notes" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN notes TEXT"))
                conn.commit()
            if "idempotency_key" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN idempotency_key VARCHAR(100)"))
                conn.commit()
            if "service_price_snapshot" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN service_price_snapshot FLOAT"))
                conn.commit()
            if "deposit_required" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN deposit_required BOOLEAN DEFAULT FALSE"))
                conn.commit()
            if "deposit_amount" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN deposit_amount FLOAT DEFAULT 0.0"))
                conn.commit()
            if "deposit_paid" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN deposit_paid BOOLEAN DEFAULT FALSE"))
                conn.commit()
            if "deposit_payment_id" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN deposit_payment_id VARCHAR(100)"))
                conn.commit()
            if "payment_status" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN payment_status VARCHAR(30) DEFAULT 'SIN_SEÑA'"))
                conn.commit()
            if "push_reminder_sent" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN push_reminder_sent BOOLEAN DEFAULT FALSE"))
                conn.commit()
            if "actual_duration_min" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN actual_duration_min INTEGER"))
                conn.commit()
            if "tip_amount" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN tip_amount FLOAT DEFAULT 0.0"))
                conn.commit()
            if "is_checked_in" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN is_checked_in BOOLEAN DEFAULT FALSE"))
                conn.commit()
            if "checked_in_at" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN checked_in_at TIMESTAMP"))
                conn.commit()
            if "checkin_token" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN checkin_token VARCHAR(50)"))
                conn.commit()
            if "extras_snapshot" not in columns:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN extras_snapshot TEXT"))
                conn.commit()

        # 2. Migration for barbers
        if "barbers" in tables:
            columns = [c["name"] for c in inspector.get_columns("barbers")]
            if "phone" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN phone VARCHAR(50)"))
                conn.commit()
            if "experience" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN experience VARCHAR(200)"))
                conn.commit()
            if "instagram" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN instagram VARCHAR(100)"))
                conn.commit()
            if "facebook" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN facebook VARCHAR(100)"))
                conn.commit()
            if "featured_styles" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN featured_styles VARCHAR(200)"))
                conn.commit()
            if "description" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN description TEXT"))
                conn.commit()
            if "working_days" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN working_days VARCHAR(100) DEFAULT 'Lunes,Martes,Miércoles,Jueves,Viernes,Sábado'"))
                conn.commit()
            if "display_order" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN display_order INTEGER DEFAULT 0"))
                conn.commit()
            if "commission_services_percent" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN commission_services_percent FLOAT DEFAULT 50.0"))
                conn.commit()
            if "commission_products_percent" not in columns:
                conn.execute(text("ALTER TABLE barbers ADD COLUMN commission_products_percent FLOAT DEFAULT 10.0"))
                conn.commit()

        # 2.1 Migration for clients
        if "clients" in tables:
            columns = [c["name"] for c in inspector.get_columns("clients")]
            if "points" not in columns:
                conn.execute(text("ALTER TABLE clients ADD COLUMN points INTEGER DEFAULT 0"))
                conn.commit()
            if "total_spent" not in columns:
                conn.execute(text("ALTER TABLE clients ADD COLUMN total_spent FLOAT DEFAULT 0.0"))
                conn.commit()
            if "tier" not in columns:
                conn.execute(text("ALTER TABLE clients ADD COLUMN tier VARCHAR(30) DEFAULT 'BRONCE'"))
                conn.commit()

        # 3. Migration for services
        if "services" in tables:
            columns = [c["name"] for c in inspector.get_columns("services")]
            if "previous_price" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN previous_price FLOAT"))
                conn.commit()
            if "prep_buffer_min" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN prep_buffer_min INTEGER DEFAULT 0"))
                conn.commit()
            if "clean_buffer_min" not in columns:
                conn.execute(text("ALTER TABLE services ADD COLUMN clean_buffer_min INTEGER DEFAULT 5"))
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

        # 3.1 Migration for orders
        if "orders" in tables:
            columns = [c["name"] for c in inspector.get_columns("orders")]
            if "idempotency_key" not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(100)"))
                conn.commit()

        # 4. Migration for products
        if "products" in tables:
            columns = [c["name"] for c in inspector.get_columns("products")]
            if "cost_price" not in columns:
                conn.execute(text("ALTER TABLE products ADD COLUMN cost_price FLOAT DEFAULT 0.0"))
                conn.commit()
            if "category" not in columns:
                conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR(50) DEFAULT 'reventa'"))
                conn.commit()
            if "created_at" not in columns:
                conn.execute(text("ALTER TABLE products ADD COLUMN created_at TIMESTAMP"))
                conn.commit()

        # 5. Migration for audit_logs
        if "audit_logs" in tables:
            columns = [c["name"] for c in inspector.get_columns("audit_logs")]
            if "actor" not in columns:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN actor VARCHAR(80) DEFAULT 'Encargado / Recepción'"))
                conn.commit()
            if "description" not in columns:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN description TEXT"))
                conn.commit()
            if "ip_address" not in columns:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(50)"))
                conn.commit()

        # 6. Migration for admin_users
        if "admin_users" in tables:
            columns = [c["name"] for c in inspector.get_columns("admin_users")]
            if "role" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN role VARCHAR(30) DEFAULT 'admin'"))
                conn.commit()
            if "can_edit_stock" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN can_edit_stock BOOLEAN DEFAULT TRUE"))
                conn.commit()
            if "can_view_finances" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN can_view_finances BOOLEAN DEFAULT FALSE"))
                conn.commit()
            if "can_cancel_appointments" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN can_cancel_appointments BOOLEAN DEFAULT TRUE"))
                conn.commit()
            if "can_manage_shop" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN can_manage_shop BOOLEAN DEFAULT TRUE"))
                conn.commit()

        # 7. Migration for notification_logs
        if "notification_logs" in tables:
            columns = [c["name"] for c in inspector.get_columns("notification_logs")]
            if "whatsapp_message_id" not in columns:
                conn.execute(text("ALTER TABLE notification_logs ADD COLUMN whatsapp_message_id VARCHAR(100)"))
                conn.commit()
            if "retry_count" not in columns:
                conn.execute(text("ALTER TABLE notification_logs ADD COLUMN retry_count INTEGER DEFAULT 0"))
                conn.commit()
            if "response_payload" not in columns:
                conn.execute(text("ALTER TABLE notification_logs ADD COLUMN response_payload TEXT"))
                conn.commit()

        # 8. Migration for idempotency_records
        if "idempotency_records" in tables:
            columns = [c["name"] for c in inspector.get_columns("idempotency_records")]
            if "expires_at" not in columns:
                conn.execute(text("ALTER TABLE idempotency_records ADD COLUMN expires_at TIMESTAMP"))
                conn.commit()

        # 9. Migration for vouchers
        if "vouchers" in tables:
            columns = [c["name"] for c in inspector.get_columns("vouchers")]
            if "allowed_start_time" not in columns:
                conn.execute(text("ALTER TABLE vouchers ADD COLUMN allowed_start_time VARCHAR(10)"))
                conn.commit()
            if "allowed_end_time" not in columns:
                conn.execute(text("ALTER TABLE vouchers ADD COLUMN allowed_end_time VARCHAR(10)"))
                conn.commit()

        # 10. Migration for sales_records
        if "sales_records" in tables:
            columns = [c["name"] for c in inspector.get_columns("sales_records")]
            if "items_detail" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN items_detail TEXT"))
                conn.commit()
            if "client_id" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN client_id INTEGER"))
                conn.commit()
            if "voucher_code" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN voucher_code VARCHAR(50)"))
                conn.commit()
            if "original_amount" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN original_amount FLOAT DEFAULT 0.0"))
                conn.commit()
            if "tip_amount" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN tip_amount FLOAT DEFAULT 0.0"))
                conn.commit()
            if "commission_amount" not in columns:
                conn.execute(text("ALTER TABLE sales_records ADD COLUMN commission_amount FLOAT DEFAULT 0.0"))
                conn.commit()

    # Sembrado inicial de ServiceExtra y Corte General si no existen
    try:
        from app.models import ServiceExtra, Service
        db_session = SessionLocal()
        if db_session.query(ServiceExtra).count() == 0:
            default_extras = [
                ServiceExtra(name="Perfilado con Navaja", description="Definición nítida de líneas con navaja tradicional y toalla tibia", price=1500.0, duration_min=15, icon="✂️", display_order=1),
                ServiceExtra(name="Alineado & Cejas Clean", description="Limpieza y perfilado de cejas al detalle", price=1000.0, duration_min=10, icon="✨", display_order=2),
                ServiceExtra(name="Barba Ritual Completa", description="Vapor ozonizado, recorte con máquina y tijera, bálsamo hidratante", price=2500.0, duration_min=20, icon="🧔", display_order=3),
                ServiceExtra(name="Color / Platinado / Mechas", description="Colorimetría, mechas o platinado profesional de autor", price=4500.0, duration_min=40, icon="🎨", display_order=4),
                ServiceExtra(name="Degradé Especial / Freestyle", description="Diseño personalizado o degradé marcado a elección", price=1500.0, duration_min=15, icon="💈", display_order=5),
                ServiceExtra(name="Lavado & Masaje Capilar", description="Lavado profundo con masaje relajante y tónico revitalizante", price=1200.0, duration_min=10, icon="💆", display_order=6),
            ]
            db_session.add_all(default_extras)
            db_session.commit()

        corte_gen = db_session.query(Service).filter(Service.name.ilike("%corte general%")).first()
        if not corte_gen:
            corte_gen = Service(
                name="Corte General",
                description="Corte de cabello completo a máquina y tijera con acabado y peinado profesional.",
                duration_min=30,
                price=6000.0,
                previous_price=7000.0,
                category="Cortes",
                display_order=-1,
                is_active=True
            )
            db_session.add(corte_gen)
            db_session.commit()
        else:
            if corte_gen.display_order >= 0:
                corte_gen.display_order = -1
                db_session.commit()
        db_session.close()
    except Exception as e:
        pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
