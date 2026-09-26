import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import ShopSetting

DEFAULT_SETTINGS = {
    # Identidad Central
    "barber_name": "Turnero",
    "app_name": "Turnero",
    "short_name": "Turnero",
    "browser_title": "Turnero // Sistema de Reservas & Shop",
    "description": "Sistema de reservas de turnos y control de inventario en tiempo real.",
    "phone": "5493834123456",
    "whatsapp": "5493834123456",
    "email": "contacto@turnero.app",
    "address": "Av. Belgrano 1234",
    "city": "Catamarca",
    "province": "Catamarca",
    "instagram": "@turnero",
    "facebook": "turnero.oficial",
    "tiktok": "@turnero",
    "website": "https://turnero.app",
    "google_maps": "https://maps.google.com",
    
    # Textos Principales
    "welcome_title": "TURNERO & SHOP",
    "welcome_sub": "Experiencia premium en reservas de barbería y gestión de productos.",
    "text_welcome": "Bienvenido a Turnero.",
    "text_services": "Conoce nuestros servicios de autor, duración y precio transparente.",
    "text_barbers": "Selecciona al profesional para tu atención.",
    "text_appointments": "Agenda tu día y horario disponible.",
    "text_contact": "Contactanos directamente por WhatsApp o visítanos.",
    "text_shop": "Productos profesionales para el cuidado de tu barba y cabello.",
    "text_cart": "Revisa los productos seleccionados antes de confirmar tu pedido.",
    "text_confirm": "Revisa el resumen de tu reserva antes de confirmar.",
    "text_footer": "TURNERO // RESERVAS & SHOP © 2026",
    
    # WhatsApp & Notificaciones
    "wa_notify_client": "true",
    "wa_notify_barber": "true",
    "wa_template_client": "Hola, {cliente}. Te confirmamos tu turno en {barberia}. Te atenderá {barbero} el {fecha} a las {hora} para {servicio}. Te esperamos en {direccion}.",
    "wa_template_barber": "Hola, {barbero}. Tenés un nuevo turno confirmado: {cliente} — {servicio} — {fecha} — {hora}. Lugar: {direccion}.",
    "wa_signature": "Equipo de {barberia}",
    "msg_success": "Reserva confirmada exitosamente. Recibirás recordatorio por WhatsApp.",
    "msg_cancel": "Tu turno ha sido cancelado.",
    "msg_confirm": "Tu turno ha sido confirmado.",
    "msg_error": "No pudimos completar la operación. Por favor reintenta.",
    "msg_maintenance": "El sistema se encuentra en mantenimiento programado.",

    # Logo & Assets
    "logo_url": "",
    "logo_dark_url": "",
    "favicon_url": "",
    "app_icon_url": "",
    "cover_image_url": "",
    "splash_image_url": "",
    "splash_title": "TURNERO",
    "splash_subtitle": "Tu estilo comienza acá.",
    "splash_welcome": "Reservá tu turno o explora nuestro shop.",
    "splash_duration": "3",
    "show_splash": "true",

    # Apariencia & Tema Visual (CSS Variables Globals)
    "color_primary": "#d4ff00",
    "color_secondary": "#00f2fe",
    "color_accent": "#ff007f",
    "color_background": "#0a0a0c",
    "color_surface": "#121216",
    "color_surface_elevated": "#1a1a22",
    "color_text": "#ffffff",
    "color_muted": "#94a3b8",
    "color_button": "#d4ff00",
    "color_button_text": "#0a0a0c",
    "color_button_secondary": "#1e293b",
    "color_border": "rgba(255, 255, 255, 0.08)",
    "color_success": "#10b981",
    "color_warning": "#f59e0b",
    "color_error": "#ef4444",
    "border_radius": "16px",
    "box_shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
    "font_family": "Plus Jakarta Sans",
    "theme_mode": "dark",

    # Créditos
    "developed_by": "Eduardo Andrada",
    "designed_by": "Eduardo Andrada",
    "version": "2.0.0",
    "year": "2026",
    "copyright": "Todos los derechos reservados.",
    "dev_website": "https://turnero.app",
    "dev_contact": "eduandoandrada@gmail.com",
    "show_credits": "true",

    # PWA
    "pwa_name": "Turnero",
    "pwa_short_name": "Turnero",
    "pwa_description": "Turnero y Shop Barber",
    "pwa_theme_color": "#0a0a0c",
    "pwa_bg_color": "#0a0a0c",
    "pwa_start_url": "/",
    "pwa_display": "standalone",

    # Música de Fondo
    "bg_music_url": "/static/musica punchi/punchi.mp4",
    "bg_music_enabled": "true",

    # Agenda en Vivo & Pantalla TV
    "live_tv_title": "SALA DE ESPERA // TURNERO EN VIVO",
    "live_tv_subtitle": "ATENCIÓN POR SILLÓN",
    "live_tv_marquee": "💈 Bienvenido a la Barbería • Turnos en Tiempo Real • Wi-Fi Disponible • Consulta nuestros productos en el Shop Barber",
    "live_voice_enabled": "true",
    "live_chime_enabled": "true",
    "live_auto_refresh_sec": "10",
    "live_current_called_id": "",

    # Horarios de Atención (JSON)
    "business_hours": json.dumps({
        "Lunes": {"active": True, "open": "09:00", "close": "20:00", "pause_start": "13:00", "pause_end": "14:00"},
        "Martes": {"active": True, "open": "09:00", "close": "20:00", "pause_start": "13:00", "pause_end": "14:00"},
        "Miércoles": {"active": True, "open": "09:00", "close": "20:00", "pause_start": "13:00", "pause_end": "14:00"},
        "Jueves": {"active": True, "open": "09:00", "close": "20:00", "pause_start": "13:00", "pause_end": "14:00"},
        "Viernes": {"active": True, "open": "09:00", "close": "20:00", "pause_start": "13:00", "pause_end": "14:00"},
        "Sábado": {"active": True, "open": "09:00", "close": "18:00", "pause_start": "", "pause_end": ""},
        "Domingo": {"active": False, "open": "09:00", "close": "14:00", "pause_start": "", "pause_end": ""}
    })
}

def get_all_settings(db: Session) -> Dict[str, Any]:
    rows = db.query(ShopSetting).all()
    settings = dict(DEFAULT_SETTINGS)
    for r in rows:
        settings[r.key] = r.value
    return settings

def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.query(ShopSetting).filter(ShopSetting.key == key).first()
    if row and row.value is not None:
        return row.value
    return DEFAULT_SETTINGS.get(key, default)

def set_setting(db: Session, key: str, value: Any) -> None:
    val_str = str(value) if not isinstance(value, str) else value
    row = db.query(ShopSetting).filter(ShopSetting.key == key).first()
    if row:
        row.value = val_str
    else:
        db.add(ShopSetting(key=key, value=val_str))
    db.commit()

def bulk_set_settings(db: Session, settings_dict: Dict[str, Any]) -> None:
    # If barber_name is being updated, auto-sync splash_title and footer if they aren't explicitly provided
    if "barber_name" in settings_dict and settings_dict["barber_name"]:
        new_name = str(settings_dict["barber_name"]).strip()
        if "splash_title" not in settings_dict or not settings_dict["splash_title"]:
            settings_dict["splash_title"] = new_name.upper()
        if "browser_title" not in settings_dict or not settings_dict["browser_title"]:
            settings_dict["browser_title"] = f"{new_name} // Turnero & Shop"
        if "text_footer" not in settings_dict or not settings_dict["text_footer"]:
            settings_dict["text_footer"] = f"{new_name.upper()} // RESERVAS & SHOP © 2026"
        if "app_name" not in settings_dict:
            settings_dict["app_name"] = new_name
        if "pwa_name" not in settings_dict:
            settings_dict["pwa_name"] = new_name

    for k, v in settings_dict.items():
        val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        row = db.query(ShopSetting).filter(ShopSetting.key == k).first()
        if row:
            row.value = val_str
        else:
            db.add(ShopSetting(key=k, value=val_str))
    db.commit()
