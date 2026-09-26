import os
import io
import json
import logging
import threading
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query, Form, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.database import Base, engine, get_db, SessionLocal, init_db_and_migrate, get_argentina_now
from app.models import (
    AdminUser, ShopSetting, Barber, Service, Style, Client, Appointment,
    Category, Product, StockMovement, DeliveryZone, Order, OrderItem, Promotion, AppNotification, AuditLog, NotificationLog
)
from app.schemas import (
    LoginRequest, LoginResponse, PasswordChangeRequest,
    BarberRead, BarberAdminRead, BarberCreate, BarberUpdate,
    ServiceRead, ServiceCreate, ServiceUpdate,
    StyleRead, StyleCreate, StyleUpdate,
    ClientRead, ClientCreate, ClientUpdate,
    AppointmentRead, AppointmentCreate, AppointmentUpdate,
    AvailableSlotsResponse, AvailableSlotItem,
    CategoryRead, CategoryCreate,
    ProductRead, ProductCreate, ProductUpdate, ProductResponse, StockAdjustment,
    StockMovementCreate, StockMovementRead, InventoryAnalyticsResponse,
    OrderRead, OrderCreate, OrderStatusUpdate,
    DeliveryZoneRead, DeliveryZoneCreate,
    PromotionRead, PromotionCreate,
    AppNotificationRead, AppNotificationCreate,
    AuditLogRead, AuditLogResponse, NotificationLogRead, DashboardStatsResponse,
    StyleAdviceRequest, StyleAdviceResponse, BulkSettingsUpdate
)
from app.auth import get_current_admin, create_admin_token, hash_password, verify_password, revoke_token, security_bearer
from app.settings_helper import get_all_settings, get_setting, bulk_set_settings, DEFAULT_SETTINGS
from app.backup_helper import create_database_backup, list_backups, restore_database_backup, BACKUP_DIR
from app.scheduler import start_scheduler, shutdown_scheduler

logger = logging.getLogger("bladesync.main")
logging.basicConfig(level=logging.INFO)

APPOINTMENT_LOCK = threading.Lock()


WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "bladesync_webhook_secret_token_2026")
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_STR.split(",") if o.strip()]
if "*" in ALLOWED_ORIGINS or os.getenv("ENV") == "development":
    ALLOWED_ORIGINS = ["*"]


def seed_initial_data():
    """Siembra usuario administrador, barberos, servicios, productos y configuraciones iniciales."""
    db: Session = SessionLocal()
    try:
        # 1. Admin User
        if db.query(AdminUser).count() == 0:
            initial_password = os.getenv("ADMIN_INITIAL_PASSWORD", "admin123")
            default_admin = AdminUser(
                username="admin",
                password_hash=hash_password(initial_password),
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            logger.info(f"Usuario administrador inicial creado ('admin').")

        # 2. Settings iniciales
        for k, v in DEFAULT_SETTINGS.items():
            if not db.query(ShopSetting).filter(ShopSetting.key == k).first():
                db.add(ShopSetting(key=k, value=str(v)))
        db.commit()

        # 3. Barberos iniciales
        if db.query(Barber).count() == 0:
            barbers = [
                Barber(
                    name="Misael Fade",
                    specialties="Master Barber // Skin Fade & Visagismo",
                    description="Especialista en degradados a navaja y morfolología facial.",
                    avatar_url="https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80",
                    working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
                    is_active=True,
                    display_order=1
                ),
                Barber(
                    name="Lucas Blade",
                    specialties="Stylist & Beard // Ritual de Navaja",
                    description="Experto en barboterapia, vapor ozonizado y toalla caliente.",
                    avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
                    working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
                    is_active=True,
                    display_order=2
                ),
                Barber(
                    name="Mateo Razor",
                    specialties="Urban Textures & Freestyle Crop",
                    description="Cortes urbanos desestructurados y acabados mate de autor.",
                    avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
                    working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
                    is_active=True,
                    display_order=3
                )
            ]
            db.add_all(barbers)
            db.commit()

        # 4. Servicios iniciales
        if db.query(Service).count() == 0:
            services = [
                Service(
                    name="Corte Signature Fade",
                    description="Degradado milimétrico a elección (Low/Mid/High) + Lavado exfoliante y textura mate.",
                    duration_min=45,
                    price=4500.0,
                    previous_price=5000.0,
                    category="Cortes",
                    is_active=True,
                    display_order=1
                ),
                Service(
                    name="Barba Ritual + Toalla Caliente",
                    description="Vapor ozonizado, perfilado a navaja japonesa con aceites esenciales orgánicos.",
                    duration_min=30,
                    price=3000.0,
                    previous_price=3500.0,
                    category="Barba",
                    is_active=True,
                    display_order=2
                ),
                Service(
                    name="Combo BladeSync Total (Corte + Barba)",
                    description="Servicio completo de autor: Asesoría morfológica, Fade, Barboterapia y styling.",
                    duration_min=60,
                    price=6800.0,
                    previous_price=7500.0,
                    category="Combos",
                    is_active=True,
                    display_order=3
                ),
                Service(
                    name="Perfilado de Barba & Líneas Clean",
                    description="Definición nítida de contornos con navaja tradicional y bálsamo hidratante.",
                    duration_min=20,
                    price=2200.0,
                    previous_price=2500.0,
                    category="Barba",
                    is_active=True,
                    display_order=4
                )
            ]
            db.add_all(services)
            db.commit()

        # 5. Estilos de Corte iniciales
        if db.query(Style).count() == 0:
            styles = [
                Style(name="Low Skin Fade", description="Degradado sutil desde la base de la nuca con acabado a cero nítido.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=1),
                Style(name="Mid Fade Clásico", description="Degradado equilibrado a media altura con textura superior.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=2),
                Style(name="High Drop Fade", description="Caída pronunciada en la parte posterior para un contraste agresivo.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=3),
                Style(name="Taper Fade", description="Degradado sutil centrado en patillas y nuca manteniendo longitud.", approx_duration=40, suggested_price=4200, category="Taper", is_active=True, display_order=4),
                Style(name="French Crop", description="Flequillo recto con textura caótica en coronilla y laterales rasurados.", approx_duration=45, suggested_price=4500, category="Crop", is_active=True, display_order=5),
                Style(name="Pompadour Moderno", description="Tupé voluminoso peinado hacia atrás con fijación mate duradera.", approx_duration=50, suggested_price=4800, category="Clásico", is_active=True, display_order=6)
            ]
            db.add_all(styles)
            db.commit()

        # 6. Categorías del Shop iniciales
        if db.query(Category).count() == 0:
            categories = [
                Category(name="Pomadas & Ceras", slug="pomadas-ceras", description="Fijadores, arcillas mate y cereales modeladores.", is_active=True, display_order=1),
                Category(name="Cuidado de Barba", slug="cuidado-barba", description="Aceites, bálsamos hidratantes y jabones de barboterapia.", is_active=True, display_order=2),
                Category(name="Shampoo & Acondicionador", slug="shampoo-acondicionador", description="Limpieza profunda y fortalecimiento capilar.", is_active=True, display_order=3),
                Category(name="Herramientas & Accesorios", slug="herramientas-accesorios", description="Peines de carbono, cepillos pulidores y navajas.", is_active=True, display_order=4)
            ]
            db.add_all(categories)
            db.commit()

        # 7. Productos iniciales del Shop
        if db.query(Product).count() == 0:
            cat_pomada = db.query(Category).filter(Category.slug == "pomadas-ceras").first()
            cat_barba = db.query(Category).filter(Category.slug == "cuidado-barba").first()

            products = [
                Product(
                    name="Pomada Arcilla Mate Matte Clay",
                    description="Fijación fuerte de acabado 100% mate sin residuos grasos. 100g.",
                    price=12500.0,
                    previous_price=14000.0,
                    sku="POM-CLAY-01",
                    stock=15,
                    min_stock=3,
                    image_url="https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_pomada.id if cat_pomada else 1,
                    is_featured=True,
                    is_active=True,
                    display_order=1
                ),
                Product(
                    name="Aceite Esencial para Barba Ritual Navaja",
                    description="Mezcla orgánica de argán, jojoba y cedro para hidratar piel y vello facial. 50ml.",
                    price=9800.0,
                    previous_price=11000.0,
                    sku="ACE-BARB-02",
                    stock=10,
                    min_stock=2,
                    image_url="https://images.unsplash.com/photo-1608248597379-397505553599?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_barba.id if cat_barba else 2,
                    is_featured=True,
                    is_active=True,
                    display_order=2
                ),
                Product(
                    name="Bálsamo Perfilador & Hidratante de Barba",
                    description="Suaviza el vello duro y protege la piel contra irritación tras el afeitado. 80g.",
                    price=8500.0,
                    previous_price=9500.0,
                    sku="BAL-BARB-03",
                    stock=8,
                    min_stock=2,
                    image_url="https://images.unsplash.com/photo-1626285861696-9f0bf5a49c6d?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_barba.id if cat_barba else 2,
                    is_featured=False,
                    is_active=True,
                    display_order=3
                )
            ]
            db.add_all(products)
            db.commit()

        # 8. Zonas de Delivery iniciales
        if db.query(DeliveryZone).count() == 0:
            dz = [
                DeliveryZone(name="Retiro en Barbería (Gratis)", cost=0.0, min_order_amount=0.0, is_active=True),
                DeliveryZone(name="Zona Centro / Macrocentro", cost=1500.0, min_order_amount=5000.0, is_active=True),
                DeliveryZone(name="Zonas Periféricas / Barrios", cost=2500.0, min_order_amount=8000.0, is_active=True)
            ]
            db.add_all(dz)
            db.commit()

    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_and_migrate()
    seed_initial_data()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Turnero & Shop Barber Digital Ecosystem 2026",
    description="Sistema Digital Integral para una Barbería (Turnos + Admin + Shop Barber)",
    version="2.0.0",
    lifespan=lifespan
)

# Configuración de CORS segura
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if "*" not in ALLOWED_ORIGINS else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = os.path.join(static_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)


# ==========================================
# APIS PÚBLICAS (CONFIGURACIÓN, BARBEROS, SERVICIOS, SLOTS, RESERVA)
# ==========================================
@app.get("/api/public/settings")
def get_public_settings(db: Session = Depends(get_db)):
    """Retorna la configuración central pública de la barbería."""
    return get_all_settings(db)

@app.get("/api/barbers", response_model=List[BarberRead])
def list_public_barbers(db: Session = Depends(get_db)):
    """Retorna los barberos activos."""
    return db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).all()

@app.get("/api/services", response_model=List[ServiceRead])
def list_public_services(db: Session = Depends(get_db)):
    """Retorna los servicios activos."""
    return db.query(Service).filter(Service.is_active == True).order_by(Service.display_order.asc()).all()

@app.get("/api/styles", response_model=List[StyleRead])
def list_public_styles(db: Session = Depends(get_db)):
    """Retorna los estilos de corte activos."""
    return db.query(Style).filter(Style.is_active == True).order_by(Style.display_order.asc()).all()


# ==========================================
# MOTOR DE SLOTS & DISPONIBILIDAD DE TURNOS
# ==========================================
def parse_time_str(t_str: str) -> time:
    parts = t_str.split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]))

@app.get("/api/available-slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    barber_id: Optional[int] = None,
    barber_name: Optional[str] = None,
    service_id: Optional[int] = None,
    date: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Calcula slots dinámicos evaluando duración real del servicio,
    horarios de atención del día y solapamientos exactos (start < existing_end AND end > existing_start).
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Utilice YYYY-MM-DD.")

    # Barber
    query_barber = None
    if barber_id:
        query_barber = db.query(Barber).filter(Barber.id == barber_id).first()
    elif barber_name:
        query_barber = db.query(Barber).filter(Barber.name.ilike(f"%{barber_name}%")).first()

    resolved_name = query_barber.name if query_barber else (barber_name or "General")
    resolved_id = query_barber.id if query_barber else barber_id

    # Service Duration
    duration_min = 45
    if service_id:
        srv = db.query(Service).filter(Service.id == service_id).first()
        if srv:
            duration_min = srv.duration_min

    # Obtener configuración de Horarios de Atención
    bh_json = get_setting(db, "business_hours", "{}")
    try:
        bh_config = json.loads(bh_json)
    except Exception:
        bh_config = {}

    days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    day_name = days_es[target_date.weekday()]
    day_setting = bh_config.get(day_name, {"active": True, "open": "09:00", "close": "20:00"})

    slots: List[AvailableSlotItem] = []

    # Si el día está cerrado, retornar grilla vacía
    if not day_setting.get("active", True):
        return AvailableSlotsResponse(
            barber_id=resolved_id,
            barber_name=resolved_name,
            date=date,
            slots=slots
        )

    open_t = parse_time_str(day_setting.get("open", "09:00"))
    close_t = parse_time_str(day_setting.get("close", "20:00"))
    pause_start_str = day_setting.get("pause_start", "")
    pause_end_str = day_setting.get("pause_end", "")
    has_pause = bool(pause_start_str and pause_end_str)
    
    pause_start_t = parse_time_str(pause_start_str) if has_pause else None
    pause_end_t = parse_time_str(pause_end_str) if has_pause else None

    # Consultar citas existentes del barbero para el día objetivo (no canceladas)
    start_day = datetime.combine(target_date, datetime.min.time())
    end_day = datetime.combine(target_date, datetime.max.time())

    appt_filter = [
        Appointment.canceled == False,
        Appointment.appointment_time >= start_day,
        Appointment.appointment_time <= end_day
    ]
    if query_barber:
        appt_filter.append(
            or_(
                Appointment.barber_id == query_barber.id,
                Appointment.barber_name == query_barber.name
            )
        )

    existing_appts = db.query(Appointment).filter(*appt_filter).all()

    # Generar intervalos de 15 minutos desde apertura hasta cierre
    current_dt = datetime.combine(target_date, open_t)
    limit_dt = datetime.combine(target_date, close_t)
    now_arg = get_argentina_now().replace(tzinfo=None)
    is_today = (target_date == now_arg.date())

    step_minutes = 15
    while current_dt + timedelta(minutes=duration_min) <= limit_dt:
        slot_start = current_dt
        slot_end = current_dt + timedelta(minutes=duration_min)
        time_str = slot_start.strftime("%H:%M")

        # 1. Past check
        if is_today and slot_start < now_arg:
            slots.append(AvailableSlotItem(time=time_str, available=False))
            current_dt += timedelta(minutes=step_minutes)
            continue

        # 2. Pause check
        if has_pause:
            slot_s_t = slot_start.time()
            slot_e_t = slot_end.time()
            if not (slot_e_t <= pause_start_t or slot_s_t >= pause_end_t):
                slots.append(AvailableSlotItem(time=time_str, available=False))
                current_dt += timedelta(minutes=step_minutes)
                continue

        # 3. Overlap check: new_start < existing_end AND new_end > existing_start
        has_overlap = False
        for ex in existing_appts:
            ex_start = ex.appointment_time
            ex_dur = ex.duration_min or 45
            ex_end = ex.end_time or (ex_start + timedelta(minutes=ex_dur))

            if slot_start < ex_end and slot_end > ex_start:
                has_overlap = True
                break

        slots.append(AvailableSlotItem(time=time_str, available=not has_overlap))
        current_dt += timedelta(minutes=step_minutes)

    return AvailableSlotsResponse(
        barber_id=resolved_id,
        barber_name=resolved_name,
        date=date,
        slots=slots
    )


# ==========================================
# CREACIÓN PÚBLICA DE TURNOS
# ==========================================
@app.post("/api/appointments", response_model=dict)
def create_public_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    """Crea un nuevo turno verificando disponibilidad en tiempo real."""
    now_arg = get_argentina_now().replace(tzinfo=None)
    appt_time_naive = data.appointment_time.replace(tzinfo=None)
    if appt_time_naive < now_arg:
        raise HTTPException(status_code=400, detail="No es posible reservar en fechas u horarios transcurridos.")

    # Resolver barbero
    barber_obj = None
    if data.barber_id:
        barber_obj = db.query(Barber).filter(Barber.id == data.barber_id).first()
    elif data.barber_name:
        barber_obj = db.query(Barber).filter(Barber.name.ilike(f"%{data.barber_name}%")).first()

    resolved_b_name = barber_obj.name if barber_obj else (data.barber_name or "Misael Fade")
    resolved_b_id = barber_obj.id if barber_obj else 1

    # Resolver servicio
    service_obj = None
    if data.service_id:
        service_obj = db.query(Service).filter(Service.id == data.service_id).first()
    elif data.service:
        service_obj = db.query(Service).filter(Service.name.ilike(f"%{data.service}%")).first()

    resolved_s_name = service_obj.name if service_obj else (data.service or "Corte Signature Fade")
    resolved_s_id = service_obj.id if service_obj else 1
    duration_min = service_obj.duration_min if service_obj else 45

    slot_start = appt_time_naive
    slot_end = slot_start + timedelta(minutes=duration_min)

    # Validar colisión de horario y crear turno de forma atómica (thread-safe)
    with APPOINTMENT_LOCK:
        existing = db.query(Appointment).filter(
            Appointment.canceled == False,
            or_(
                Appointment.barber_id == resolved_b_id,
                Appointment.barber_name == resolved_b_name
            )
        ).all()

        for ex in existing:
            ex_start = ex.appointment_time
            ex_dur = ex.duration_min or 45
            ex_end = ex.end_time or (ex_start + timedelta(minutes=ex_dur))

            if slot_start < ex_end and slot_end > ex_start:
                raise HTTPException(
                    status_code=400,
                    detail="El horario seleccionado ya se encuentra ocupado. Por favor elige otro horario."
                )

        # Buscar o crear cliente
        client_obj = db.query(Client).filter(Client.phone == data.client_phone).first()
        if not client_obj:
            client_obj = Client(
                name=data.client_name,
                phone=data.client_phone,
                is_active=True
            )
            db.add(client_obj)
            db.commit()
            db.refresh(client_obj)

        new_appt = Appointment(
            client_id=client_obj.id if client_obj else None,
            client_name=data.client_name,
            client_phone=data.client_phone,
            barber_id=resolved_b_id,
            barber_name=resolved_b_name,
            service_id=resolved_s_id,
            service=resolved_s_name,
            appointment_time=slot_start,
            end_time=slot_end,
            duration_min=duration_min,
            status="PENDIENTE",
            confirmed=False,
            canceled=False,
            reminder_sent=False,
            notes=data.notes
        )
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)

        # Disparar notificaciones WhatsApp automáticas (cliente + barbero)
        send_appointment_whatsapp_notifications(db, new_appt)

    logger.info(f"Nuevo turno creado #{new_appt.id} para {new_appt.client_name} a las {slot_start}")

    return {
        "status": "success",
        "message": get_setting(db, "msg_success", "Turno reservado exitosamente."),
        "appointment": {
            "id": new_appt.id,
            "client_name": new_appt.client_name,
            "client_phone": new_appt.client_phone,
            "barber_name": new_appt.barber_name,
            "service": new_appt.service,
            "appointment_time": new_appt.appointment_time.isoformat(),
            "status": new_appt.status
        }
    }


def send_appointment_whatsapp_notifications(db: Session, appointment: Appointment):
    """
    Registra y envía notificaciones de WhatsApp para Cliente y Barbero al confirmar turno.
    No interrumpe el flujo ni rompe la transacción si falla.
    """
    try:
        notify_client = get_setting(db, "wa_notify_client", "true") == "true"
        notify_barber = get_setting(db, "wa_notify_barber", "true") == "true"
        tmpl_client = get_setting(db, "wa_template_client", "Hola, {cliente}. Te confirmamos tu turno en {barberia}. Te atenderá {barbero} el {fecha} a las {hora} para {servicio}. Te esperamos en {direccion}.")
        tmpl_barber = get_setting(db, "wa_template_barber", "Hola, {barbero}. Tenés un nuevo turno confirmado: {cliente} — {servicio} — {fecha} — {hora}. Lugar: {direccion}.")
        
        shop_name = get_setting(db, "barber_name", "Turnero")
        shop_address = get_setting(db, "address", "Av. Principal 123")
        
        date_str = appointment.appointment_time.strftime("%d/%m/%Y")
        time_str = appointment.appointment_time.strftime("%H:%M")
        
        vars_map = {
            "cliente": appointment.client_name,
            "barbero": appointment.barber_name or "Profesional de Autor",
            "servicio": appointment.service or "Servicio de Barbería",
            "fecha": date_str,
            "hora": time_str,
            "direccion": shop_address,
            "barberia": shop_name
        }

        # 1. Notificación al Cliente
        if notify_client and appointment.client_phone:
            body_c = tmpl_client
            for k, v in vars_map.items():
                body_c = body_c.replace(f"{{{k}}}", str(v))
            
            db.add(NotificationLog(
                appointment_id=appointment.id,
                recipient=appointment.client_phone,
                recipient_role="CLIENTE",
                message_type="WHATSAPP_CONFIRMACION",
                message_body=body_c,
                status="ENVIADO"
            ))

        # 2. Notificación al Barbero (Usando teléfono privado del barbero)
        if notify_barber and appointment.barber_id:
            barber = db.query(Barber).filter(Barber.id == appointment.barber_id).first()
            if barber and barber.phone:
                body_b = tmpl_barber
                for k, v in vars_map.items():
                    body_b = body_b.replace(f"{{{k}}}", str(v))

                db.add(NotificationLog(
                    appointment_id=appointment.id,
                    recipient=barber.phone,
                    recipient_role="BARBERO",
                    message_type="WHATSAPP_CONFIRMACION",
                    message_body=body_b,
                    status="ENVIADO"
                ))
        
        db.commit()
    except Exception as e:
        logger.error(f"Error procesando notificaciones WhatsApp para turno #{appointment.id}: {e}")


# ==========================================
# ASESOR DE ESTILO (VISAGISMO)
# ==========================================
@app.post("/api/ai-advisor", response_model=StyleAdviceResponse)
@app.post("/api/ai-style-advisor", response_model=StyleAdviceResponse)
def get_ai_style_advice(req: StyleAdviceRequest):
    face = req.face_shape.strip().lower()
    density = (req.hair_density or "media").lower()

    recs = {
        "ovalada": ("Low Skin Fade con Texturizado French Crop", "Corte Signature Fade", "Low Skin Fade", "Tu rostro es simétrico. Mantené textura arriba."),
        "cuadrada": ("Mid Fade Clásico con Pompadour", "Combo BladeSync Total (Corte + Barba)", "Mid Fade Rasurado", "Resalta tu mandíbula manteniendo laterales limpios."),
        "redonda": ("High Drop Fade con Quiff voluminoso", "Corte Signature Fade", "High Drop Fade", "Concentra altura en la coronilla para elongación vertical."),
        "diamante": ("Taper Fade Medio con barba esculpida", "Combo BladeSync Total (Corte + Barba)", "Taper Fade", "Suaviza pómulos manteniendo caída natural."),
        "triangular": ("Mid Skin Fade con Crop despuntado", "Corte Signature Fade", "Mid Fade Gradual", "Añade textura en la zona superior."),
        "corazón": ("Low Taper con barba perfilada", "Barba Ritual + Toalla Caliente", "Low Taper Fade", "Barba tupida pero delimitada para equilibrar mentón.")
    }

    cut, srv, fade, tip = recs.get(face, ("Taper Fade Moderno", "Corte Signature Fade", "Taper Fade 2026", "Aplica pomada con arcilla mate."))
    if "baja" in density:
        tip += " Recomendamos corte en bloque con menor entresacado."
    elif "alta" in density:
        tip += " Aligeraremos peso en zonas clave para mayor soltura."

    return StyleAdviceResponse(
        face_shape=req.face_shape,
        recommendation=cut,
        styling_tips=tip,
        recommended_service=srv,
        fade_type=fade,
        confidence_score=0.95
    )


# ==========================================
# AGENDA EN VIVO / PANTALLA EN TIEMPO REAL
# ==========================================
@app.get("/api/live-agenda")
def get_live_agenda(
    barber_id: Optional[int] = None,
    target_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna la agenda en vivo para hoy (o fecha especificada),
    calculando en tiempo real quién está en atención ahora, quién sigue,
    y la lista de turnos ordenada con estadísticas para pantalla o móvil.
    """
    now_dt = get_argentina_now()
    if target_date:
        try:
            curr_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            curr_date = now_dt.date()
    else:
        curr_date = now_dt.date()

    start_day = datetime.combine(curr_date, datetime.min.time())
    end_day = datetime.combine(curr_date, datetime.max.time())

    query = db.query(Appointment).filter(
        Appointment.appointment_time >= start_day,
        Appointment.appointment_time <= end_day,
        Appointment.canceled == False,
        Appointment.status != "CANCELADO"
    )
    if barber_id:
        query = query.filter(Appointment.barber_id == barber_id)

    appts = query.order_by(Appointment.appointment_time.asc()).all()
    now_naive = now_dt.replace(tzinfo=None) if curr_date == now_dt.date() else datetime.combine(curr_date, datetime.min.time())

    in_service_list = []
    next_up_list = []
    upcoming_list = []
    completed_list = []

    for a in appts:
        start_t = a.appointment_time
        dur = a.duration_min or 45
        end_t = a.end_time or (start_t + timedelta(minutes=dur))

        # Calcular progreso si está en horario
        progress_pct = 0
        if start_t <= now_naive <= end_t and (end_t > start_t):
            total_sec = (end_t - start_t).total_seconds()
            elapsed_sec = (now_naive - start_t).total_seconds()
            progress_pct = min(100, max(0, int((elapsed_sec / total_sec) * 100)))

        item = {
            "id": a.id,
            "client_name": a.client_name,
            "barber_id": a.barber_id,
            "barber_name": a.barber_name or "General",
            "service": a.service or "Corte de Autor",
            "duration_min": dur,
            "appointment_time": start_t.isoformat(),
            "time_str": start_t.strftime("%H:%M"),
            "end_time_str": end_t.strftime("%H:%M"),
            "status": a.status,
            "is_now": False,
            "progress_pct": progress_pct
        }

        if a.status == "COMPLETADO":
            completed_list.append(item)
        elif a.status in ["EN_ATENCION", "EN_SILLON"] or (curr_date == now_dt.date() and start_t <= now_naive < end_t and a.status in ["PENDIENTE", "CONFIRMADO"]):
            item["is_now"] = True
            item["status"] = "EN SILLÓN"
            in_service_list.append(item)
        elif curr_date == now_dt.date() and end_t <= now_naive and a.status != "COMPLETADO":
            item["status"] = "FINALIZADO"
            completed_list.append(item)
        else:
            upcoming_list.append(item)

    # Identificar siguiente en turno
    if upcoming_list:
        next_up_list.append(upcoming_list[0])

    barbers = db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).all()
    barbers_data = [{"id": b.id, "name": b.name, "avatar_url": b.avatar_url, "specialties": b.specialties} for b in barbers]
    bName = get_setting(db, "barber_name", "BARBERÍA")

    # Settings de Live TV / Sala de espera
    tv_title = get_setting(db, "live_tv_title", "SALA DE ESPERA // TURNERO EN VIVO")
    tv_subtitle = get_setting(db, "live_tv_subtitle", "ATENCIÓN POR SILLÓN")
    tv_marquee = get_setting(db, "live_tv_marquee", "💈 Bienvenido • Turnos en Tiempo Real • Wi-Fi Disponible • Shop Barber")
    voice_enabled = get_setting(db, "live_voice_enabled", "true") == "true"
    chime_enabled = get_setting(db, "live_chime_enabled", "true") == "true"
    auto_refresh_sec = int(get_setting(db, "live_auto_refresh_sec", "10") or 10)
    current_called_id_str = get_setting(db, "live_current_called_id", "")

    called_appointment = None
    if current_called_id_str and current_called_id_str.isdigit():
        c_appt = db.query(Appointment).filter(Appointment.id == int(current_called_id_str)).first()
        if c_appt:
            called_appointment = {
                "id": c_appt.id,
                "client_name": c_appt.client_name,
                "barber_name": c_appt.barber_name or "General",
                "service": c_appt.service or "Corte",
                "time_str": c_appt.appointment_time.strftime("%H:%M")
            }

    return {
        "server_time": now_dt.strftime("%H:%M:%S"),
        "server_date": curr_date.strftime("%Y-%m-%d"),
        "barber_name": bName,
        "tv_title": tv_title,
        "tv_subtitle": tv_subtitle,
        "tv_marquee": tv_marquee,
        "voice_enabled": voice_enabled,
        "chime_enabled": chime_enabled,
        "auto_refresh_sec": auto_refresh_sec,
        "called_appointment": called_appointment,
        "total_today": len(appts),
        "in_service": in_service_list,
        "next_up": next_up_list,
        "upcoming": upcoming_list,
        "completed": completed_list,
        "barbers": barbers_data
    }

@app.post("/api/live-agenda/{appointment_id}/call")
def call_live_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Llama al cliente a pantalla TV y emite timbre/chime sincronizado."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    appt.status = "LLAMANDO"
    set_setting(db, "live_current_called_id", str(appt.id))
    db.commit()
    return {
        "message": f"Turno #{appt.id} de {appt.client_name} llamado a pantalla.",
        "appointment": {
            "id": appt.id,
            "client_name": appt.client_name,
            "barber_name": appt.barber_name or "General",
            "service": appt.service or "Corte",
            "time_str": appt.appointment_time.strftime("%H:%M")
        }
    }

@app.post("/api/live-agenda/walk-in")
def create_live_walk_in(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Agrega un cliente espontáneo / en espera directamente a la cola de hoy."""
    name = str(data.get("client_name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del cliente es obligatorio.")
    phone = str(data.get("client_phone", "")).strip() or "5493834000000"
    barber_id = data.get("barber_id")
    barber_name = "General"
    if barber_id:
        b = db.query(Barber).filter(Barber.id == barber_id).first()
        if b:
            barber_name = b.name
    service_name = data.get("service_name") or "Corte Espontáneo / En Espera"
    dur = int(data.get("duration_min") or 30)

    now_arg = get_argentina_now().replace(tzinfo=None)

    new_appt = Appointment(
        client_name=name,
        client_phone=phone,
        barber_id=barber_id,
        barber_name=barber_name,
        service=service_name,
        appointment_time=now_arg,
        end_time=now_arg + timedelta(minutes=dur),
        duration_min=dur,
        status="PENDIENTE",
        confirmed=True
    )
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)
    return {"message": "Cliente agregado a la cola en vivo exitosamente.", "appointment_id": new_appt.id}

@app.put("/api/live-agenda/{appointment_id}")
def update_live_appointment(appointment_id: int, data: Dict[str, Any], db: Session = Depends(get_db)):
    """Permite editar cliente, barbero o servicio directamente desde la pantalla de moderación."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    if "client_name" in data and data["client_name"]:
        appt.client_name = data["client_name"]
    if "service" in data and data["service"]:
        appt.service = data["service"]
    if "barber_id" in data:
        appt.barber_id = data["barber_id"]
        if appt.barber_id:
            b = db.query(Barber).filter(Barber.id == appt.barber_id).first()
            if b:
                appt.barber_name = b.name
    if "status" in data and data["status"]:
        appt.status = data["status"]
    if "time_str" in data and data["time_str"]:
        try:
            parts = data["time_str"].split(":")
            h, m = int(parts[0]), int(parts[1])
            appt.appointment_time = appt.appointment_time.replace(hour=h, minute=m)
            appt.end_time = appt.appointment_time + timedelta(minutes=appt.duration_min or 45)
        except Exception:
            pass
    db.commit()
    return {"message": "Turno actualizado correctamente.", "id": appt.id}

@app.post("/api/live-agenda/{appointment_id}/status")
def update_live_status(
    appointment_id: int,
    status_data: Dict[str, str],
    db: Session = Depends(get_db)
):
    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Falta el estado.")
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    appt.status = new_status
    if new_status == "COMPLETADO":
        appt.confirmed = True
    elif new_status == "CANCELADO":
        appt.canceled = True
    db.commit()
    return {"message": "Estado actualizado exitosamente.", "id": appt.id, "status": appt.status}

@app.get("/api/live-agenda/settings")
def get_live_settings(db: Session = Depends(get_db)):
    """Retorna las configuraciones actuales de la pantalla TV y agenda en vivo."""
    return {
        "live_tv_title": get_setting(db, "live_tv_title", DEFAULT_SETTINGS.get("live_tv_title", "SALA DE ESPERA // TURNERO EN VIVO")),
        "live_tv_subtitle": get_setting(db, "live_tv_subtitle", DEFAULT_SETTINGS.get("live_tv_subtitle", "ATENCIÓN POR SILLÓN")),
        "live_tv_marquee": get_setting(db, "live_tv_marquee", DEFAULT_SETTINGS.get("live_tv_marquee", "💈 Bienvenido a la Barbería • Turnos en Tiempo Real • Wi-Fi Disponible")),
        "live_voice_enabled": str(get_setting(db, "live_voice_enabled", DEFAULT_SETTINGS.get("live_voice_enabled", "true"))).lower() in ["true", "1", "yes"],
        "live_chime_enabled": str(get_setting(db, "live_chime_enabled", DEFAULT_SETTINGS.get("live_chime_enabled", "true"))).lower() in ["true", "1", "yes"],
        "live_auto_refresh_sec": int(get_setting(db, "live_auto_refresh_sec", DEFAULT_SETTINGS.get("live_auto_refresh_sec", "8")) or 8)
    }

@app.post("/api/live-agenda/settings")
@app.put("/api/live-agenda/settings")
def save_live_settings(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Guarda las configuraciones de la pantalla TV y cartelera directamente desde live.html o admin."""
    allowed = ["live_tv_title", "live_tv_subtitle", "live_tv_marquee", "live_voice_enabled", "live_chime_enabled", "live_auto_refresh_sec"]
    for k in allowed:
        if k in data:
            set_setting(db, k, str(data[k]))
    db.commit()
    return {"message": "Configuraciones de pantalla TV guardadas exitosamente."}



# ==========================================
# APIS DEL SHOP BARBER (CATÁLOGO, CHECKOUT)
# ==========================================
@app.get("/api/shop/categories", response_model=List[CategoryRead])
def list_shop_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).order_by(Category.display_order.asc()).all()

@app.get("/api/shop/products", response_model=List[ProductRead])
def list_shop_products(
    category_id: Optional[int] = None,
    featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if featured:
        query = query.filter(Product.is_featured == True)
    
    products = query.order_by(Product.display_order.asc()).all()
    result = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        result.append(p_read)
    return result

@app.get("/api/shop/delivery-zones", response_model=List[DeliveryZoneRead])
def list_delivery_zones(db: Session = Depends(get_db)):
    return db.query(DeliveryZone).filter(DeliveryZone.is_active == True).all()

@app.post("/api/shop/orders", response_model=OrderRead)
def create_shop_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Crea un pedido en el shop recalculando los precios en backend y
    descontando el stock de los productos.
    """
    if not order_in.items:
        raise HTTPException(status_code=400, detail="El carrito de compras no contiene productos.")

    subtotal = 0.0
    items_to_create = []

    for item in order_in.items:
        prod = db.query(Product).filter(Product.id == item.product_id, Product.is_active == True).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Producto ID #{item.product_id} no disponible.")
        
        if prod.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{prod.name}'. Stock disponible: {prod.stock} un."
            )

        item_subtotal = prod.price * item.quantity
        subtotal += item_subtotal

        # Descontar stock
        prod.stock -= item.quantity

        items_to_create.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "unit_price": prod.price,
            "quantity": item.quantity,
            "subtotal": item_subtotal
        })

    delivery_cost = 0.0
    if order_in.delivery_type == "delivery":
        if not order_in.delivery_zone_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar una zona de envío para entregas a domicilio."
            )
        dz = db.query(DeliveryZone).filter(
            DeliveryZone.id == order_in.delivery_zone_id,
            DeliveryZone.is_active == True
        ).first()
        if not dz:
            raise HTTPException(
                status_code=400,
                detail="La zona de envío seleccionada no existe o no se encuentra activa."
            )
        if dz.min_order_amount and subtotal < dz.min_order_amount:
            raise HTTPException(
                status_code=400,
                detail=f"El monto mínimo de productos para la zona '{dz.name}' es de ${dz.min_order_amount:,.2f}. Tu subtotal es ${subtotal:,.2f}."
            )
        delivery_cost = dz.cost

    total = subtotal + delivery_cost

    # Generar código de pedido único #PED-YYYYMMDD-HHMMSS-XXXX
    unique_suffix = secrets.token_hex(2).upper()
    order_num = f"PED-{get_argentina_now().strftime('%Y%m%d-%H%M%S')}-{unique_suffix}"

    # Buscar o crear cliente
    client_obj = db.query(Client).filter(Client.phone == order_in.client_phone).first()
    if not client_obj:
        client_obj = Client(
            name=order_in.client_name,
            phone=order_in.client_phone,
            email=order_in.client_email,
            is_active=True
        )
        db.add(client_obj)
        db.commit()
        db.refresh(client_obj)

    new_order = Order(
        order_number=order_num,
        client_id=client_obj.id if client_obj else None,
        client_name=order_in.client_name,
        client_phone=order_in.client_phone,
        client_email=order_in.client_email,
        address=order_in.address,
        neighborhood=order_in.neighborhood,
        city=order_in.city,
        notes=order_in.notes,
        subtotal=subtotal,
        delivery_cost=delivery_cost,
        total=total,
        delivery_type=order_in.delivery_type,
        payment_method=order_in.payment_method,
        status="NUEVO"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for it in items_to_create:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=it["product_id"],
            product_name=it["product_name"],
            unit_price=it["unit_price"],
            quantity=it["quantity"],
            subtotal=it["subtotal"]
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    logger.info(f"Nuevo pedido creado {new_order.order_number} por ${total}")
    return new_order


# ==========================================
# WHATSAPP WEBHOOK
# ==========================================
@app.get("/api/whatsapp-webhook")
def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/api/whatsapp-webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []):
                    if msg.get("type") == "interactive":
                        button_id = msg["interactive"].get("button_reply", {}).get("id", "")
                        if "_" in button_id:
                            action, appt_id_str = button_id.split("_", 1)
                            if appt_id_str.isdigit():
                                appt = db.query(Appointment).filter(Appointment.id == int(appt_id_str)).first()
                                if appt:
                                    if action == "CONFIRM":
                                        appt.status = "CONFIRMADO"
                                        appt.confirmed = True
                                        appt.canceled = False
                                    elif action == "CANCEL":
                                        appt.status = "CANCELADO"
                                        appt.canceled = True
                                    db.commit()
    except Exception as e:
        logger.exception(f"Error procesando WhatsApp Webhook: {e}")
    return {"status": "received"}


# ==============================================================================
# RUTAS DE ADMINISTRACIÓN PROTEGIDAS (/api/admin/*)
# ==============================================================================

# 1. AUTH ADMIN
@app.post("/api/admin/login", response_model=LoginResponse)
def admin_login(creds: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == creds.username, AdminUser.is_active == True).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    # Auto-actualizar hash si el usuario aún tenía la versión legada
    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(creds.password)
        db.commit()

    token = create_admin_token(user.username)
    return LoginResponse(
        token=token,
        username=user.username,
        message="Autenticación exitosa."
    )

@app.post("/api/admin/logout")
def admin_logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    admin: AdminUser = Depends(get_current_admin)
):
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    return {"message": "Sesión cerrada correctamente."}

@app.get("/api/admin/me")
def get_admin_me(admin: AdminUser = Depends(get_current_admin)):
    return {"username": admin.username, "id": admin.id}

@app.post("/api/admin/change-password")
def change_admin_password(
    data: PasswordChangeRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if admin.password_hash and not verify_password(data.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    
    admin.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña de administrador actualizada con éxito."}


# 2. DASHBOARD & REPORTES
@app.get("/api/admin/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    now_arg = get_argentina_now().date()
    start_today = datetime.combine(now_arg, time.min)
    end_today = datetime.combine(now_arg, time.max)

    today_appts = db.query(Appointment).filter(Appointment.appointment_time >= start_today, Appointment.appointment_time <= end_today).count()
    pending_appts = db.query(Appointment).filter(Appointment.status == "PENDIENTE").count()
    confirmed_appts = db.query(Appointment).filter(Appointment.status == "CONFIRMADO").count()
    completed_appts = db.query(Appointment).filter(Appointment.status == "COMPLETADO").count()
    canceled_appts = db.query(Appointment).filter(Appointment.status == "CANCELADO").count()

    total_clients = db.query(Client).count()
    total_barbers = db.query(Barber).count()
    total_services = db.query(Service).count()
    total_products = db.query(Product).count()

    low_stock_prods = db.query(Product).filter(Product.stock <= Product.min_stock).count()
    pending_orders = db.query(Order).filter(Order.status.in_(["NUEVO", "CONFIRMADO", "PREPARANDO"])).count()

    orders_rev = db.query(func.sum(Order.total)).filter(Order.status != "CANCELADO").scalar() or 0.0
    
    # Recent appointments
    rec_appts = db.query(Appointment).order_by(Appointment.appointment_time.desc()).limit(8).all()
    rec_appts_list = [
        {
            "id": a.id,
            "client_name": a.client_name,
            "service": a.service,
            "barber_name": a.barber_name,
            "time": a.appointment_time.isoformat(),
            "status": a.status
        } for a in rec_appts
    ]

    # Recent orders
    rec_orders = db.query(Order).order_by(Order.created_at.desc()).limit(8).all()
    rec_orders_list = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "client_name": o.client_name,
            "total": o.total,
            "status": o.status,
            "created_at": o.created_at.isoformat()
        } for o in rec_orders
    ]

    # Low stock list
    low_stock = db.query(Product).filter(Product.stock <= Product.min_stock).all()
    low_stock_list = [
        {
            "id": p.id,
            "name": p.name,
            "stock": p.stock,
            "min_stock": p.min_stock,
            "price": p.price
        } for p in low_stock
    ]

    return DashboardStatsResponse(
        today_appointments=today_appts,
        pending_appointments=pending_appts,
        confirmed_appointments=confirmed_appts,
        completed_appointments=completed_appts,
        canceled_appointments=canceled_appts,
        total_clients=total_clients,
        total_barbers=total_barbers,
        total_services=total_services,
        total_products=total_products,
        low_stock_products=low_stock_prods,
        pending_orders=pending_orders,
        total_orders_revenue=round(orders_rev, 2),
        estimated_turnover_revenue=0.0,
        recent_appointments=rec_appts_list,
        recent_orders=rec_orders_list,
        low_stock_list=low_stock_list
    )


# 3. SETTINGS & CONFIGURACIÓN CENTRAL
@app.get("/api/admin/settings")
def get_admin_settings(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return get_all_settings(db)

@app.put("/api/admin/settings")
def update_admin_settings(
    data: BulkSettingsUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    old_sets = get_all_settings(db)
    bulk_set_settings(db, data.settings)
    
    # Audit log
    db.add(AuditLog(
        user_name=admin.username,
        module="Configuración",
        action="Actualizar Ajustes",
        old_value="Valores previos actualizados",
        new_value=json.dumps(data.settings, default=str)[:300]
    ))
    db.commit()

    return {"message": "Configuración actualizada correctamente.", "settings": get_all_settings(db)}


# 4. SUBIDA DE ARCHIVOS / RECURSOS VISUALES
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(uploads_dir, exist_ok=True)

@app.post("/api/admin/upload")
async def upload_asset(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo no válido.")
    
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg", ".mp3", ".mp4"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Formato de archivo no permitido. Permitidos: {allowed_exts}")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo supera el tamaño máximo permitido (5 MB).")

    filename = f"asset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename.replace(' ', '_')}"
    filepath = os.path.join(uploads_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    file_url = f"/static/uploads/{filename}"
    return {"status": "success", "file_url": file_url, "filename": filename}

@app.post("/api/admin/logo/upload")
async def upload_logo(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se seleccionó ningún archivo.")
    
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".png", ".jpg", ".jpeg", ".webp", ".svg"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Formato no permitido ({ext}). Formatos aceptados: PNG (con transparencia), JPG, WebP, SVG.")
    
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El logo supera el tamaño máximo permitido (5 MB).")

    filename = f"logo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
    filepath = os.path.join(uploads_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    logo_url = f"/static/uploads/{filename}"
    bulk_set_settings(db, {"logo_url": logo_url})

    db.add(AuditLog(
        user_name=admin.username,
        module="Identidad",
        action="Subir Logo",
        new_value=logo_url
    ))
    db.commit()

    return {"status": "success", "logo_url": logo_url, "message": "Logo actualizado y guardado correctamente."}

@app.delete("/api/admin/logo/delete")
def delete_logo(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    bulk_set_settings(db, {"logo_url": ""})
    db.add(AuditLog(
        user_name=admin.username,
        module="Identidad",
        action="Eliminar Logo",
        old_value="Logo eliminado"
    ))
    db.commit()
    return {"status": "success", "logo_url": "", "message": "Logo eliminado correctamente."}


# 5. GESTIÓN DE BARBEROS
@app.get("/api/admin/barbers", response_model=List[BarberAdminRead])
def get_admin_barbers(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Barber).order_by(Barber.display_order.asc()).all()

@app.post("/api/admin/barbers", response_model=BarberAdminRead)
def create_admin_barber(
    barber_in: BarberCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    b = Barber(**barber_in.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    
    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Crear Barbero", record_id=str(b.id), new_value=b.name))
    db.commit()
    return b

@app.put("/api/admin/barbers/{barber_id}", response_model=BarberAdminRead)
def update_admin_barber(
    barber_id: int,
    barber_in: BarberUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    b = db.query(Barber).filter(Barber.id == barber_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")
    
    old_name = b.name
    for k, v in barber_in.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)

    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Editar Barbero", record_id=str(b.id), old_value=old_name, new_value=b.name))
    db.commit()
    return b

@app.delete("/api/admin/barbers/{barber_id}")
def delete_admin_barber(
    barber_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    b = db.query(Barber).filter(Barber.id == barber_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")
    
    name = b.name
    db.delete(b)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Eliminar Barbero", record_id=str(barber_id), old_value=name))
    db.commit()
    return {"message": f"Barbero '{name}' eliminado."}

@app.post("/api/admin/barbers/{barber_id}/reassign-turnos")
def reassign_absent_barber_turnos(
    barber_id: int,
    date_str: str = Query(..., description="Fecha YYYY-MM-DD"),
    target_barber_id: Optional[int] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Reasigna turnos pendientes de un barbero ausente a otro barbero y genera links de aviso por WhatsApp.
    """
    absent_barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not absent_barber:
        raise HTTPException(status_code=404, detail="Barbero ausente no encontrado.")

    target_barber = None
    if target_barber_id:
        target_barber = db.query(Barber).filter(Barber.id == target_barber_id).first()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Utilice YYYY-MM-DD.")

    start_d = datetime.combine(target_date, time.min)
    end_d = datetime.combine(target_date, time.max)

    appts = db.query(Appointment).filter(
        Appointment.barber_id == barber_id,
        Appointment.appointment_time >= start_d,
        Appointment.appointment_time <= end_d,
        Appointment.status.in_(["PENDIENTE", "CONFIRMADO"])
    ).all()

    affected_list = []
    shop_name = get_setting(db, "barber_name", "Turnero")

    for a in appts:
        old_bname = a.barber_name
        if target_barber:
            a.barber_id = target_barber.id
            a.barber_name = target_barber.name
            new_bname = target_barber.name
            msg = f"Hola {a.client_name}, te informamos desde {shop_name} que tu turno del {target_date.strftime('%d/%m')} a las {a.appointment_time.strftime('%H:%M')} hs ha sido reasignado al profesional {new_bname}. ¡Te esperamos!"
        else:
            new_bname = "Sin asignar"
            msg = f"Hola {a.client_name}, te contactamos desde {shop_name} para reprogramar tu turno del {target_date.strftime('%d/%m')} a las {a.appointment_time.strftime('%H:%M')} hs por imprevisto de tu barbero. ¡Escribinos!"

        clean_phone = "".join(filter(str.isdigit, a.client_phone))
        affected_list.append({
            "appointment_id": a.id,
            "client_name": a.client_name,
            "client_phone": a.client_phone,
            "time": a.appointment_time.strftime("%H:%M"),
            "old_barber": old_bname,
            "new_barber": new_bname,
            "wa_message": msg,
            "wa_url": f"https://wa.me/{clean_phone}?text={msg.replace(' ', '%20')}"
        })

    db.commit()
    return {
        "status": "success",
        "count": len(appts),
        "absent_barber": absent_barber.name,
        "target_barber": target_barber.name if target_barber else None,
        "affected": affected_list
    }


# 6. GESTIÓN DE SERVICIOS Y PRECIOS
@app.get("/api/admin/services", response_model=List[ServiceRead])
def get_admin_services(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Service).order_by(Service.display_order.asc()).all()

@app.post("/api/admin/services", response_model=ServiceRead)
def create_admin_service(
    service_in: ServiceCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    s = Service(**service_in.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Crear Servicio", record_id=str(s.id), new_value=f"{s.name} - ${s.price}"))
    db.commit()
    return s

@app.put("/api/admin/services/{service_id}", response_model=ServiceRead)
def update_admin_service(
    service_id: int,
    service_in: ServiceUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    
    old_info = f"{s.name} - ${s.price} ({s.duration_min}m)"
    for k, v in service_in.model_dump(exclude_unset=True).items():
        if k == "price" and v != s.price:
            s.previous_price = s.price
        setattr(s, k, v)
    db.commit()
    db.refresh(s)

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Editar Servicio", record_id=str(s.id), old_value=old_info, new_value=f"{s.name} - ${s.price} ({s.duration_min}m)"))
    db.commit()
    return s

@app.delete("/api/admin/services/{service_id}")
def delete_admin_service(
    service_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    
    name = s.name
    db.delete(s)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Eliminar Servicio", record_id=str(service_id), old_value=name))
    db.commit()
    return {"message": f"Servicio '{name}' eliminado."}


# 7. GESTIÓN DE ESTILOS DE CORTE
@app.get("/api/admin/styles", response_model=List[StyleRead])
def get_admin_styles(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Style).order_by(Style.display_order.asc()).all()

@app.post("/api/admin/styles", response_model=StyleRead)
def create_admin_style(
    style_in: StyleCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    st = Style(**style_in.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Crear Estilo", record_id=str(st.id), new_value=st.name))
    db.commit()
    return st

@app.put("/api/admin/styles/{style_id}", response_model=StyleRead)
def update_admin_style(
    style_id: int,
    style_in: StyleUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    st = db.query(Style).filter(Style.id == style_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Estilo no encontrado.")
    
    old_name = st.name
    for k, v in style_in.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    db.commit()
    db.refresh(st)

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Editar Estilo", record_id=str(st.id), old_value=old_name, new_value=st.name))
    db.commit()
    return st

@app.delete("/api/admin/styles/{style_id}")
def delete_admin_style(
    style_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    st = db.query(Style).filter(Style.id == style_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Estilo no encontrado.")
    
    name = st.name
    db.delete(st)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Eliminar Estilo", record_id=str(style_id), old_value=name))
    db.commit()
    return {"message": f"Estilo '{name}' eliminado."}


# 8. GESTIÓN COMPLETA DE TURNOS
@app.get("/api/admin/appointments", response_model=List[AppointmentRead])
def get_admin_appointments(
    date: Optional[str] = None,
    barber_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 200,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Appointment).order_by(Appointment.appointment_time.desc())
    if date:
        try:
            t_date = datetime.strptime(date, "%Y-%m-%d").date()
            s_day = datetime.combine(t_date, time.min)
            e_day = datetime.combine(t_date, time.max)
            query = query.filter(Appointment.appointment_time >= s_day, Appointment.appointment_time <= e_day)
        except ValueError:
            pass

    if barber_id:
        query = query.filter(Appointment.barber_id == barber_id)
    if status:
        query = query.filter(Appointment.status == status)

    return query.limit(limit).all()

@app.put("/api/admin/appointments/{appointment_id}", response_model=AppointmentRead)
def update_admin_appointment(
    appointment_id: int,
    appt_in: AppointmentUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    old_status = appt.status
    for k, v in appt_in.model_dump(exclude_unset=True).items():
        setattr(appt, k, v)

    # Sync flags
    if appt_in.status:
        if appt_in.status == "CANCELADO":
            appt.canceled = True
        elif appt_in.status == "CONFIRMADO":
            appt.confirmed = True
            appt.canceled = False

    db.commit()
    db.refresh(appt)

    db.add(AuditLog(
        user_name=admin.username,
        module="Turnos",
        action="Actualizar Turno",
        record_id=str(appt.id),
        old_value=f"Estado: {old_status}",
        new_value=f"Estado: {appt.status}"
    ))
    db.commit()
    return appt

@app.delete("/api/admin/appointments/{appointment_id}")
def delete_admin_appointment(
    appointment_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    db.delete(appt)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Turnos", action="Eliminar Turno", record_id=str(appointment_id)))
    db.commit()
    return {"message": "Turno eliminado correctamente."}


# 9. DIRECTORIO DE CLIENTES
@app.get("/api/admin/clients", response_model=List[ClientRead])
def get_admin_clients(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.id.desc()).all()

@app.post("/api/admin/clients", response_model=ClientRead)
def create_admin_client(
    client_in: ClientCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    c = Client(**client_in.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.delete("/api/admin/clients/{client_id}")
@app.delete("/api/clients/{client_id}")
def delete_admin_client(
    client_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    
    name = c.name
    # Desvincular turnos y pedidos asociados para preservar integridad de BD
    db.query(Appointment).filter(Appointment.client_id == client_id).update({"client_id": None})
    db.query(Order).filter(Order.client_id == client_id).update({"client_id": None})
    
    db.delete(c)
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        module="Clientes",
        action="Eliminar Cliente",
        record_id=str(client_id),
        old_value=name
    ))
    db.commit()
    return {"message": f"Cliente '{name}' eliminado exitosamente."}



# 10. GESTIÓN DEL SHOP (PRODUCTOS Y CATEGORÍAS)
@app.get("/api/admin/categories", response_model=List[CategoryRead])
def get_admin_categories(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.display_order.asc()).all()

@app.post("/api/admin/categories", response_model=CategoryRead)
def create_admin_category(
    cat_in: CategoryCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    cat = Category(**cat_in.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@app.get("/api/admin/products", response_model=List[ProductRead])
def get_admin_products(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.display_order.asc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        res.append(p_read)
    return res

@app.post("/api/admin/products", response_model=ProductRead)
def create_admin_product(
    prod_in: ProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = Product(**prod_in.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Crear Producto", record_id=str(p.id), new_value=f"{p.name} (${p.price}, stock: {p.stock})"))
    db.commit()
    return p

@app.put("/api/admin/products/{product_id}", response_model=ProductRead)
def update_admin_product(
    product_id: int,
    prod_in: ProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    old_info = f"{p.name} (${p.price}, stock: {p.stock})"
    for k, v in prod_in.model_dump(exclude_unset=True).items():
        if k == "price" and v != p.price:
            p.previous_price = p.price
        setattr(p, k, v)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Editar Producto", record_id=str(p.id), old_value=old_info, new_value=f"{p.name} (${p.price}, stock: {p.stock})"))
    db.commit()
    return p

@app.delete("/api/admin/products/{product_id}")
def delete_admin_product(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    
    name = p.name
    db.delete(p)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Eliminar Producto", record_id=str(product_id), old_value=name))
    db.commit()
    return {"message": f"Producto '{name}' eliminado."}


# ==============================================================================
# MÓDULO DE INVENTARIO EN TIEMPO REAL & ALERTAS DE STOCK (/api/inventory/*)
# ==============================================================================
@app.get("/api/inventory/products", response_model=List[ProductRead])
def get_inventory_products(
    category: Optional[str] = Query(None, description="reventa o insumo"),
    alert_only: bool = Query(False, description="Solo productos con stock <= min_stock"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre"),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    if alert_only:
        query = query.filter(Product.stock <= Product.min_stock)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.order_by(Product.display_order.asc(), Product.name.asc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        res.append(p_read)
    return res

@app.post("/api/inventory/products", response_model=ProductRead)
def create_inventory_product(
    prod_in: ProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    data = prod_in.model_dump()
    if data.get("sale_price") is not None:
        data["price"] = data["sale_price"]
    if data.get("current_stock") is not None:
        data["stock"] = data["current_stock"]
    data.pop("sale_price", None)
    data.pop("current_stock", None)

    p = Product(**data)
    db.add(p)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(
        user_name=admin.username,
        module="Inventario",
        action="Crear Producto",
        record_id=str(p.id),
        new_value=f"{p.name} ({p.category}, Costo: ${p.cost_price}, Venta: ${p.price}, Stock: {p.stock})"
    ))
    db.commit()

    p_read = ProductRead.model_validate(p)
    p_read.cost_price = p.cost_price or 0.0
    p_read.sale_price = p.price or 0.0
    p_read.current_stock = p.stock or 0
    p_read.category = p.category or "reventa"
    return p_read

@app.put("/api/inventory/products/{product_id}", response_model=ProductRead)
def update_inventory_product(
    product_id: int,
    prod_in: ProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    data = prod_in.model_dump(exclude_unset=True)
    if "sale_price" in data and data["sale_price"] is not None:
        data["price"] = data["sale_price"]
    if "current_stock" in data and data["current_stock"] is not None:
        data["stock"] = data["current_stock"]
    data.pop("sale_price", None)
    data.pop("current_stock", None)

    old_info = f"{p.name} (Stock: {p.stock}, Costo: ${p.cost_price}, Venta: ${p.price})"
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(
        user_name=admin.username,
        module="Inventario",
        action="Editar Producto",
        record_id=str(p.id),
        old_value=old_info,
        new_value=f"{p.name} (Stock: {p.stock}, Costo: ${p.cost_price}, Venta: ${p.price})"
    ))
    db.commit()

    p_read = ProductRead.model_validate(p)
    p_read.cost_price = p.cost_price or 0.0
    p_read.sale_price = p.price or 0.0
    p_read.current_stock = p.stock or 0
    p_read.category = p.category or "reventa"
    return p_read

@app.delete("/api/inventory/products/{product_id}")
def delete_inventory_product(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    p.is_active = False # Borrado lógico
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        module="Inventario",
        action="Borrado Lógico Producto",
        record_id=str(product_id),
        old_value=p.name
    ))
    db.commit()
    return {"message": f"Producto '{p.name}' deshabilitado del inventario (borrado lógico)."}

@app.post("/api/inventory/movements", response_model=StockMovementRead)
def create_stock_movement(
    mov_in: StockMovementCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    p = db.query(Product).filter(Product.id == mov_in.product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    qty = mov_in.quantity
    m_type = mov_in.movement_type.lower()

    if m_type in ["ingreso_compra"]:
        qty = abs(qty)
        p.stock += qty
    elif m_type in ["venta", "uso_interno"]:
        qty = -abs(qty)
        if p.stock + qty < 0:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para el producto '{p.name}'. Stock actual: {p.stock}.")
        p.stock += qty
    elif m_type == "ajuste":
        p.stock += qty
        if p.stock < 0:
            p.stock = 0

    mov = StockMovement(
        product_id=p.id,
        movement_type=m_type,
        quantity=qty,
        notes=mov_in.notes,
        registered_by=mov_in.registered_by or admin.username
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)

    db.add(AuditLog(
        user_name=admin.username,
        module="Inventario",
        action=f"Movimiento {m_type.upper()}",
        record_id=str(p.id),
        new_value=f"Variación: {qty} un. Nuevo stock: {p.stock}"
    ))
    db.commit()

    res = StockMovementRead.model_validate(mov)
    res.product_name = p.name
    return res

@app.get("/api/inventory/alerts", response_model=List[ProductRead])
def get_inventory_alerts(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.is_active == True, Product.stock <= Product.min_stock).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        res.append(p_read)
    return res

@app.get("/api/inventory/analytics", response_model=InventoryAnalyticsResponse)
def get_inventory_analytics(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    active_prods = db.query(Product).filter(Product.is_active == True).all()

    total_cost = sum((p.stock or 0) * (p.cost_price or 0.0) for p in active_prods)
    total_sale = sum((p.stock or 0) * (p.price or 0.0) for p in active_prods if (p.category or 'reventa') == 'reventa')

    # Net profit total from completed orders
    completed_items = db.query(OrderItem).join(Order).filter(Order.status != "CANCELADO").all()
    net_profit = 0.0
    for item in completed_items:
        prod = item.product
        c_price = prod.cost_price if prod and prod.cost_price else 0.0
        net_profit += (item.unit_price - c_price) * item.quantity

    # Top rotating products in past 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    top_items = (
        db.query(OrderItem.product_id, OrderItem.product_name, func.sum(OrderItem.quantity).label("total_sold"))
        .join(Order)
        .filter(Order.status != "CANCELADO", Order.created_at >= thirty_days_ago)
        .group_by(OrderItem.product_id, OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    top_rotating = [
        {"product_id": t[0], "name": t[1], "quantity_sold": t[2]} for t in top_items
    ]

    # Critical products
    critical_list = [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category or "reventa",
            "current_stock": p.stock,
            "min_stock": p.min_stock,
            "cost_price": p.cost_price or 0.0,
            "sale_price": p.price or 0.0
        } for p in active_prods if (p.stock or 0) <= (p.min_stock or 0)
    ]

    # Dead stock products (> 60 days without movements/sales)
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    recent_mov_prod_ids = [m.product_id for m in db.query(StockMovement.product_id).filter(StockMovement.date >= sixty_days_ago).distinct().all()]
    recent_order_prod_ids = [it.product_id for it in db.query(OrderItem.product_id).join(Order).filter(Order.created_at >= sixty_days_ago).distinct().all() if it.product_id]
    active_prod_ids = set(recent_mov_prod_ids + recent_order_prod_ids)

    dead_stock = [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category or "reventa",
            "current_stock": p.stock,
            "cost_price": p.cost_price or 0.0
        } for p in active_prods if p.id not in active_prod_ids and (p.stock or 0) > 0
    ]

    return InventoryAnalyticsResponse(
        total_inventory_cost=round(total_cost, 2),
        total_inventory_sale_value=round(total_sale, 2),
        net_profit_total=round(net_profit, 2),
        critical_count=len(critical_list),
        top_rotating_products=top_rotating,
        critical_products=critical_list,
        dead_stock_products=dead_stock
    )



# 11. GESTIÓN DE PEDIDOS Y ESTADOS CON CONTROL DE STOCK
@app.get("/api/admin/orders", response_model=List[OrderRead])
def get_admin_orders(
    status: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Order).order_by(Order.created_at.desc())
    if status:
        query = query.filter(Order.status == status)
    return query.all()

@app.put("/api/admin/orders/{order_id}/status", response_model=OrderRead)
def update_admin_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    ord_obj = db.query(Order).filter(Order.id == order_id).first()
    if not ord_obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    old_status = ord_obj.status
    new_status = status_in.status

    # Si pasa a CANCELADO y no estaba cancelado previamente -> Restaurar stock
    if new_status == "CANCELADO" and old_status != "CANCELADO":
        for item in ord_obj.items:
            if item.product_id:
                prod = db.query(Product).filter(Product.id == item.product_id).first()
                if prod:
                    prod.stock += item.quantity

    ord_obj.status = new_status
    db.commit()
    db.refresh(ord_obj)

    db.add(AuditLog(
        user_name=admin.username,
        module="Pedidos",
        action="Cambio Estado Pedido",
        record_id=ord_obj.order_number,
        old_value=old_status,
        new_value=new_status
    ))
    db.commit()
    return ord_obj


# 12. GESTIÓN DE ZONAS DE DELIVERY
@app.get("/api/admin/delivery-zones", response_model=List[DeliveryZoneRead])
def get_admin_delivery_zones(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(DeliveryZone).all()

@app.post("/api/admin/delivery-zones", response_model=DeliveryZoneRead)
def create_admin_delivery_zone(
    dz_in: DeliveryZoneCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    dz = DeliveryZone(**dz_in.model_dump())
    db.add(dz)
    db.commit()
    db.refresh(dz)
    return dz

@app.delete("/api/admin/delivery-zones/{zone_id}")
def delete_admin_delivery_zone(
    zone_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    dz = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not dz:
        raise HTTPException(status_code=404, detail="Zona de delivery no encontrada")
    db.delete(dz)
    db.commit()
    return {"message": "Zona eliminada correctamente"}



# 13. AUDITORÍA Y COPIAS DE SEGURIDAD
@app.get("/api/admin/audit-logs", response_model=List[AuditLogRead])
def get_admin_audit_logs(
    limit: int = 100,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()

@app.get("/api/admin/backups")
def get_admin_backups(admin: AdminUser = Depends(get_current_admin)):
    return list_backups()

@app.post("/api/admin/backups/create")
def create_admin_backup(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    fname = create_database_backup(db, user_name=admin.username)
    return {"message": "Copia de seguridad creada correctamente.", "filename": fname}

@app.post("/api/admin/backups/restore")
def restore_admin_backup(
    filename: str = Query(...),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    ok = restore_database_backup(db, filename, user_name=admin.username)
    if not ok:
        raise HTTPException(status_code=400, detail="No se pudo restaurar el archivo de backup especificado.")
    return {"message": f"Base de datos restaurada exitosamente desde '{filename}'."}

@app.get("/api/admin/backups/download/{filename}")
def download_admin_backup(
    filename: str,
    admin: AdminUser = Depends(get_current_admin)
):
    fpath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(fpath, media_type="application/json", filename=filename)


# 14. GESTIÓN DE CLIENTES Y NOTIFICACIONES
@app.get("/api/admin/clients", response_model=List[ClientRead])
def get_admin_clients(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.created_at.desc()).all()

@app.delete("/api/admin/clients/{client_id}")
def delete_admin_client(
    client_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    client_name = client.name
    
    # Desvincular turnos y pedidos para preservar integridad referencial sin romper SQLite
    db.query(Appointment).filter(Appointment.client_id == client_id).update({"client_id": None})
    db.query(Order).filter(Order.client_id == client_id).update({"client_id": None})
    
    db.delete(client)
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        module="Clientes",
        action="Eliminar Cliente",
        record_id=str(client_id),
        old_value=client_name
    ))
    db.commit()

    return {"message": f"Cliente '{client_name}' eliminado correctamente."}

@app.get("/api/admin/notifications/logs", response_model=List[NotificationLogRead])
def get_admin_notification_logs(
    limit: int = 100,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit).all()


# ==========================================
# GESTIÓN DE PRODUCTOS, FOTOS Y AUDITORÍA DE STOCK
# ==========================================
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
UPLOAD_PRODUCTS_DIR = os.path.join(STATIC_DIR, "uploads", "products")
os.makedirs(UPLOAD_PRODUCTS_DIR, exist_ok=True)

@app.get("/api/products", response_model=List[ProductRead])
def get_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    if search:
        s_term = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(s_term), Product.description.ilike(s_term)))
    
    products = query.order_by(Product.display_order.asc(), Product.id.desc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        res.append(p_read)
    return res

@app.post("/api/products", response_model=ProductRead)
async def create_product_with_photo(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    stock: int = Form(0),
    category: Optional[str] = Form("reventa"),
    cost_price: Optional[float] = Form(0.0),
    min_stock: Optional[int] = Form(2),
    file: Optional[UploadFile] = File(None),
    actor: Optional[str] = Form("Encargado / Recepción"),
    db: Session = Depends(get_db)
):
    image_url = None
    if file and file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if not file_ext or file_ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            file_ext = ".jpg"
        
        safe_filename = f"prod_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}{file_ext}"
        file_path = os.path.join(UPLOAD_PRODUCTS_DIR, safe_filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        image_url = f"/static/uploads/products/{safe_filename}"

    new_prod = Product(
        name=name.strip(),
        description=description.strip() if description else None,
        price=price,
        stock=stock,
        cost_price=cost_price or 0.0,
        category=category or "reventa",
        min_stock=min_stock or 2,
        image_url=image_url,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)

    client_ip = request.client.host if (request and request.client) else None
    actor_name = actor or "Encargado / Recepción"
    
    db.add(AuditLog(
        user_name=actor_name,
        actor=actor_name,
        module="Productos",
        action="CREAR_PRODUCTO",
        description=f"Nuevo producto creado: '{name}' (${price:.2f}) - Stock Inicial: {stock}",
        record_id=str(new_prod.id),
        new_value=f"Precio: ${price:.2f}, Stock: {stock}",
        ip_address=client_ip
    ))
    
    if stock > 0:
        db.add(StockMovement(
            product_id=new_prod.id,
            movement_type="ingreso_compra",
            quantity=stock,
            notes="Carga inicial al crear producto",
            registered_by=actor_name
        ))

    db.commit()

    p_read = ProductRead.model_validate(new_prod)
    p_read.cost_price = new_prod.cost_price or 0.0
    p_read.sale_price = new_prod.price or 0.0
    p_read.current_stock = new_prod.stock or 0
    p_read.category = new_prod.category or "reventa"
    return p_read

@app.patch("/api/products/{product_id}/stock", response_model=ProductRead)
def adjust_product_stock(
    product_id: int,
    request: Request,
    adj: StockAdjustment,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    old_stock = product.stock or 0
    
    if adj.stock is not None:
        new_stock = max(0, adj.stock)
        delta = new_stock - old_stock
    elif adj.quantity is not None:
        delta = adj.quantity
        new_stock = max(0, old_stock + delta)
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'quantity' (variación) o 'stock' (valor absoluto).")

    product.stock = new_stock
    
    actor_name = adj.actor or "Encargado / Recepción"
    action_type = adj.action_type or ("VENTA_PRODUCTO" if delta < 0 else "MODIFICAR_STOCK")
    
    client_ip = request.client.host if (request and request.client) else None
    
    sign = f"+{delta}" if delta > 0 else str(delta)
    desc = f"Ajuste de stock en '{product.name}': {old_stock} -> {new_stock} ({sign})"
    if adj.notes:
        desc += f" - Notas: {adj.notes}"

    db.add(AuditLog(
        user_name=actor_name,
        actor=actor_name,
        module="Productos",
        action=action_type,
        description=desc,
        record_id=str(product.id),
        old_value=str(old_stock),
        new_value=str(new_stock),
        ip_address=client_ip
    ))

    m_type = "venta" if action_type == "VENTA_PRODUCTO" else ("ingreso_compra" if delta > 0 else "ajuste")
    db.add(StockMovement(
        product_id=product.id,
        movement_type=m_type,
        quantity=delta,
        notes=adj.notes or f"Ajuste rápido ({sign})",
        registered_by=actor_name
    ))

    db.commit()
    db.refresh(product)

    p_read = ProductRead.model_validate(product)
    p_read.cost_price = product.cost_price or 0.0
    p_read.sale_price = product.price or 0.0
    p_read.current_stock = product.stock or 0
    p_read.category = product.category or "reventa"
    return p_read

@app.get("/api/admin/audit-logs", response_model=List[AuditLogRead])
@app.get("/api/audit-logs", response_model=List[AuditLogRead])
def get_audit_logs(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if actor:
        query = query.filter(or_(AuditLog.actor.ilike(f"%{actor}%"), AuditLog.user_name.ilike(f"%{actor}%")))
    if search:
        s_term = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.description.ilike(s_term),
                AuditLog.action.ilike(s_term),
                AuditLog.actor.ilike(s_term),
                AuditLog.user_name.ilike(s_term),
                AuditLog.module.ilike(s_term)
            )
        )
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    res = []
    for l in logs:
        item = AuditLogRead.model_validate(l)
        item.actor = l.actor or l.user_name or "Encargado / Recepción"
        item.description = l.description or f"{l.action} en módulo {l.module}"
        res.append(item)
    return res


# ==========================================
# RUTAS DE ARCHIVOS ESTÁTICOS Y VISTAS HTML
# ==========================================
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Turnero API está corriendo."}

@app.get("/index.html", include_in_schema=False)
def serve_index_html():
    return serve_index()

@app.get("/admin.html", include_in_schema=False)
def serve_admin():
    admin_path = os.path.join(STATIC_DIR, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    raise HTTPException(status_code=404, detail="Página admin.html no encontrada.")

@app.get("/shop.html", include_in_schema=False)
def serve_shop():
    shop_path = os.path.join(STATIC_DIR, "shop.html")
    if os.path.exists(shop_path):
        return FileResponse(shop_path)
    raise HTTPException(status_code=404, detail="Página shop.html no encontrada.")

@app.get("/live.html", include_in_schema=False)
@app.get("/agenda.html", include_in_schema=False)
@app.get("/agenda-en-vivo.html", include_in_schema=False)
def serve_live():
    live_path = os.path.join(STATIC_DIR, "live.html")
    if os.path.exists(live_path):
        return FileResponse(live_path)
    raise HTTPException(status_code=404, detail="Página live.html no encontrada.")

@app.get("/display.html", include_in_schema=False)
@app.get("/tv.html", include_in_schema=False)
def serve_display():
    disp_path = os.path.join(STATIC_DIR, "display.html")
    if os.path.exists(disp_path):
        return FileResponse(disp_path)
    # Fallback to live.html if display not created yet
    live_path = os.path.join(STATIC_DIR, "live.html")
    if os.path.exists(live_path):
        return FileResponse(live_path)
    raise HTTPException(status_code=404, detail="Página display.html no encontrada.")

@app.get("/turnos.html", include_in_schema=False)
@app.get("/turnos", include_in_schema=False)
def serve_turnos():
    t_path = os.path.join(STATIC_DIR, "turnos.html")
    if os.path.exists(t_path):
        return FileResponse(t_path)
    raise HTTPException(status_code=404, detail="Página turnos.html no encontrada.")

@app.get("/inventario.html", include_in_schema=False)
@app.get("/inventario", include_in_schema=False)
def serve_inventario():
    inv_path = os.path.join(STATIC_DIR, "inventario.html")
    if os.path.exists(inv_path):
        return FileResponse(inv_path)
    raise HTTPException(status_code=404, detail="Página inventario.html no encontrada.")

@app.get("/manifest.json", include_in_schema=False)
def serve_manifest(db: Session = Depends(get_db)):
    """Genera manifest.json PWA dinámico desde configuración o static fallback."""
    app_name = get_setting(db, "pwa_name", DEFAULT_SETTINGS.get("pwa_name", "Barbería Digital"))
    short_name = get_setting(db, "pwa_short_name", DEFAULT_SETTINGS.get("pwa_short_name", "Barbería"))
    desc = get_setting(db, "pwa_description", "Reservas y Shop Barber")
    theme_color = get_setting(db, "pwa_theme_color", "#0a0a0c")
    bg_color = get_setting(db, "pwa_bg_color", "#0a0a0c")
    custom_icon = get_setting(db, "app_icon_url", None)
    
    icon_192 = custom_icon if custom_icon else "/static/icon-192.png"
    icon_512 = custom_icon if custom_icon else "/static/icon-512.png"

    return JSONResponse({
        "name": app_name,
        "short_name": short_name,
        "description": desc,
        "start_url": "/",
        "display": "standalone",
        "background_color": bg_color,
        "theme_color": theme_color,
        "icons": [
            {
                "src": icon_192,
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": icon_512,
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.get("/service-worker.js", include_in_schema=False)
def serve_sw():
    sw_path = os.path.join(STATIC_DIR, "service-worker.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="service-worker.js no encontrado.")

