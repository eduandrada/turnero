"""
app/main.py - Aplicación Central y Composición Modular de HiddenSYNC AI 2026
Turnero & Shop Barber Digital Ecosystem
"""
import os
import json
import logging
import secrets
import threading
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import verify_production_secrets, ENABLE_SCHEDULER
from app.core.database import Base, engine, get_db, SessionLocal, init_db_and_migrate, get_argentina_now
from app.core.seed import seed_initial_data
from app.settings_helper import get_setting, DEFAULT_SETTINGS
from app.scheduler import start_scheduler, shutdown_scheduler

# Routers de la Capa API
from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.api.appointments import router as appointments_router
from app.api.live import router as live_router
from app.api.style_advisor import router as style_advisor_router
from app.api.whatsapp import router as whatsapp_router
from app.api.shop import router as shop_router
from app.api.vouchers import router as vouchers_router
from app.api.inventory import router as inventory_router
from app.api.admin.dashboard import router as admin_dashboard_router
from app.api.admin.appointments import router as admin_appointments_router
from app.api.admin.staff import router as admin_staff_router
from app.api.admin.services import router as admin_services_router
from app.api.admin.clients import router as admin_clients_router
from app.api.admin.products import router as admin_products_router
from app.api.admin.finance import router as admin_finance_router
from app.api.admin.vouchers import router as admin_vouchers_router
from app.api.admin.settings import router as admin_settings_router
from app.api.admin.backups import router as admin_backups_router
from app.api.payments import router as payments_router
from app.api.loyalty import router as loyalty_router
from app.api.push import router as push_router
from app.api.admin.productivity import router as admin_productivity_router

logger = logging.getLogger("hiddensync.main")
logging.basicConfig(level=logging.INFO)

# Cerrojo de concurrencia para retrocompatibilidad
APPOINTMENT_LOCK = threading.Lock()

ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_STR.split(",") if o.strip()]
if "*" in ALLOWED_ORIGINS or os.getenv("ENV") == "development":
    ALLOWED_ORIGINS = ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: verificaciones, migraciones, siembra y scheduler."""
    verify_production_secrets()
    init_db_and_migrate()
    seed_initial_data()
    if ENABLE_SCHEDULER:
        start_scheduler()
    yield
    if ENABLE_SCHEDULER:
        shutdown_scheduler()


app = FastAPI(
    title="Turnero & Shop Barber Digital Ecosystem 2026",
    description="Sistema Digital Integral para Barberías (Turnos + Agenda en Vivo + Shop Barber + Admin)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Seguro
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if "*" not in ALLOWED_ORIGINS else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de Seguridad, Request ID y Modo Mantenimiento
@app.middleware("http")
async def security_and_maintenance_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"REQ-2026-{secrets.token_hex(4).upper()}"
    request.state.request_id = req_id

    # Modo mantenimiento para endpoints de reserva y compra pública
    path = request.url.path
    if request.method in ["POST", "PUT", "PATCH"] and (path.startswith("/api/appointments") or path.startswith("/api/shop/orders")):
        db = SessionLocal()
        try:
            m_mode = get_setting(db, "maintenance_mode", "0")
            if str(m_mode).lower() in ["1", "true"]:
                m_msg = get_setting(db, "maintenance_message", "Sistema en mantenimiento programado. Por favor intente más tarde.")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "maintenance",
                        "detail": m_msg,
                        "success": False,
                        "error": {
                            "code": "MAINTENANCE_MODE",
                            "message": m_msg
                        }
                    },
                    headers={"X-Request-ID": req_id}
                )
        finally:
            db.close()

    response = await call_next(request)

    # Inyección de headers de seguridad
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    return response


# Manejo global de excepciones
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    code = f"HTTP_{exc.status_code}"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "APPOINTMENT_CONFLICT"
    elif exc.status_code == 400:
        code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "success": False,
            "error": {
                "code": code,
                "message": detail
            }
        },
        headers=getattr(exc, "headers", None)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msgs = []
    for err in exc.errors():
        loc = " -> ".join([str(l) for l in err.get("loc", []) if l != "body"])
        msg = err.get("msg", "Dato inválido")
        error_msgs.append(f"{loc}: {msg}" if loc else msg)
    message = "; ".join(error_msgs) or "Datos de solicitud inválidos."
    return JSONResponse(
        status_code=422,
        content={
            "detail": message,
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"[CRITICAL_ERROR] Excepción no controlada procesando {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ha ocurrido un error interno en el servidor. Por favor, intente más tarde.",
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Ha ocurrido un error interno en el servidor. Por favor, intente más tarde."
            }
        }
    )


# Archivos estáticos
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Probes de Liveness y Readiness
@app.get("/health")
def health_check():
    """Liveness Probe: Retorna estado del proceso y hora oficial."""
    return {
        "status": "ok",
        "app": "hiddensync",
        "timezone": "America/Argentina/Catamarca",
        "timestamp": get_argentina_now().isoformat()
    }

@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness Probe: Comprueba conectividad con el motor de base de datos."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": get_argentina_now().isoformat()
        }
    except Exception as e:
        logger.error(f"[READINESS_PROBE_ERROR] Falla al conectar a la base de datos: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "disconnected",
                "detail": "Base de datos no disponible o sobrecargada."
            }
        )


# Rutas de Vistas Web y PWA
@app.get("/", include_in_schema=False)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Turnero API está corriendo."}

@app.get("/index.html", include_in_schema=False)
def serve_index_html():
    return serve_index()

@app.get("/admin", include_in_schema=False)
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

@app.get("/turnolive.html", include_in_schema=False)
@app.get("/turnolive", include_in_schema=False)
@app.get("/live.html", include_in_schema=False)
@app.get("/agenda.html", include_in_schema=False)
@app.get("/agenda-en-vivo.html", include_in_schema=False)
@app.get("/turnos.html", include_in_schema=False)
@app.get("/turnos", include_in_schema=False)
def serve_turnolive():
    tl_path = os.path.join(STATIC_DIR, "turnolive.html")
    if os.path.exists(tl_path):
        return FileResponse(tl_path)
    t_path = os.path.join(STATIC_DIR, "turnos.html")
    if os.path.exists(t_path):
        return FileResponse(t_path)
    live_path = os.path.join(STATIC_DIR, "live.html")
    if os.path.exists(live_path):
        return FileResponse(live_path)
    raise HTTPException(status_code=404, detail="Página turnolive.html no encontrada.")

@app.get("/display.html", include_in_schema=False)
@app.get("/tv.html", include_in_schema=False)
def serve_display():
    disp_path = os.path.join(STATIC_DIR, "display.html")
    if os.path.exists(disp_path):
        return FileResponse(disp_path)
    tl_path = os.path.join(STATIC_DIR, "turnolive.html")
    if os.path.exists(tl_path):
        return FileResponse(tl_path)
    raise HTTPException(status_code=404, detail="Página display.html no encontrada.")

@app.get("/inventario.html", include_in_schema=False)
@app.get("/inventario", include_in_schema=False)
def serve_inventario():
    inv_path = os.path.join(STATIC_DIR, "inventario.html")
    if os.path.exists(inv_path):
        return FileResponse(inv_path)
    raise HTTPException(status_code=404, detail="Página inventario.html no encontrada.")

@app.get("/voucher.html", include_in_schema=False)
@app.get("/voucher", include_in_schema=False)
def serve_voucher():
    v_path = os.path.join(STATIC_DIR, "voucher.html")
    if os.path.exists(v_path):
        return FileResponse(v_path)
    raise HTTPException(status_code=404, detail="Página voucher.html no encontrada.")

@app.get("/gestion.html", include_in_schema=False)
@app.get("/gestion", include_in_schema=False)
def serve_gestion():
    g_path = os.path.join(STATIC_DIR, "gestion.html")
    if os.path.exists(g_path):
        return FileResponse(g_path)
    raise HTTPException(status_code=404, detail="Página gestion.html no encontrada.")

@app.get("/checkin.html", include_in_schema=False)
@app.get("/checkin", include_in_schema=False)
def serve_checkin():
    ch_path = os.path.join(STATIC_DIR, "checkin.html")
    if os.path.exists(ch_path):
        return FileResponse(ch_path)
    raise HTTPException(status_code=404, detail="Página checkin.html no encontrada.")




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
            {"src": icon_192, "sizes": "192x192", "type": "image/png"},
            {"src": icon_512, "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.get("/service-worker.js", include_in_schema=False)
def serve_sw():
    sw_path = os.path.join(STATIC_DIR, "service-worker.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="service-worker.js no encontrado.")


# Registro de Routers Modulares
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(appointments_router)
app.include_router(live_router)
app.include_router(style_advisor_router)
app.include_router(whatsapp_router)
app.include_router(shop_router)
app.include_router(vouchers_router)
app.include_router(inventory_router)

# Routers de Administración
app.include_router(admin_dashboard_router)
app.include_router(admin_appointments_router)
app.include_router(admin_staff_router)
app.include_router(admin_services_router)
app.include_router(admin_clients_router)
app.include_router(admin_products_router)
app.include_router(admin_finance_router)
app.include_router(admin_vouchers_router)
app.include_router(admin_settings_router)
app.include_router(admin_backups_router)

# Routers de la Nueva Hoja de Ruta (Pagos, Fidelización, Push PWA, Productividad)
app.include_router(payments_router)
app.include_router(loyalty_router)
app.include_router(push_router)
app.include_router(admin_productivity_router)

