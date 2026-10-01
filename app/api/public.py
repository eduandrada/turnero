"""
app/api/public.py - Endpoints Públicos de Catálogo, Configuración, Slots y Lista de Espera
HiddenSYNC AI 2026
"""
import json
from datetime import datetime, timedelta, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import Barber, Service, ServiceExtra, Style, WaitlistEntry, Appointment, AuditLog
from app.schemas import (
    BarberRead,
    ServiceRead,
    ServiceExtraRead,
    StyleRead,
    AvailableSlotsResponse,
    AvailableSlotItem,
    WaitlistEntryCreate,
)
from app.settings_helper import get_public_settings_dict, get_setting, set_setting
from app.services.availability_service import calculate_available_slots, parse_time_str
from app.utils import normalize_phone

router = APIRouter(tags=["Public"])

@router.get("/api/public/settings")
def get_public_settings(db: Session = Depends(get_db)):
    """Retorna la configuración central pública de la barbería (sin credenciales ni secretos)."""
    return get_public_settings_dict(db)

@router.get("/api/barbers", response_model=List[BarberRead])
def list_public_barbers(db: Session = Depends(get_db)):
    """Retorna los barberos activos."""
    return db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).all()

@router.get("/api/services", response_model=List[ServiceRead])
def list_public_services(db: Session = Depends(get_db)):
    """Retorna los servicios activos."""
    return db.query(Service).filter(Service.is_active == True).order_by(Service.display_order.asc(), Service.id.asc()).all()

@router.get("/api/styles", response_model=List[StyleRead])
def list_public_styles(db: Session = Depends(get_db)):
    """Retorna los estilos de corte activos."""
    return db.query(Style).filter(Style.is_active == True).order_by(Style.display_order.asc()).all()

@router.get("/api/service-extras", response_model=List[ServiceExtraRead])
def list_public_service_extras(db: Session = Depends(get_db)):
    """Retorna las opciones y servicios adicionales (extras tildables) activos."""
    return db.query(ServiceExtra).filter(ServiceExtra.is_active == True).order_by(ServiceExtra.display_order.asc(), ServiceExtra.id.asc()).all()

@router.get("/api/available-slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    barber_id: Optional[int] = None,
    barber_name: Optional[str] = None,
    service_id: Optional[int] = None,
    duration_min: Optional[int] = Query(None, description="Duración total estimada incluyendo agregados"),
    date: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Calcula slots dinámicos mediante el motor de disponibilidad (calculate_available_slots)
    evaluando ventanas laborales por barbero, pausas, feriados, excepciones,
    duración real del servicio y buffers de preparación y limpieza.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Utilice YYYY-MM-DD.")

    # Resolver barbero
    query_barber = None
    if barber_id:
        query_barber = db.query(Barber).filter(Barber.id == barber_id).first()
    elif barber_name:
        query_barber = db.query(Barber).filter(Barber.name.ilike(f"%{barber_name}%")).first()

    resolved_name = query_barber.name if query_barber else (barber_name or "General")
    resolved_id = query_barber.id if query_barber else barber_id

    # Si no se pasó barbero, usar el primer barbero activo
    if not resolved_id:
        first_b = db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).first()
        if first_b:
            resolved_id = first_b.id
            resolved_name = first_b.name
        else:
            resolved_id = 1

    # Duración de servicio (acumulada con extras si fue provista)
    effective_duration = duration_min if (duration_min and duration_min > 0) else 45
    if not duration_min or duration_min <= 0:
        if service_id:
            srv = db.query(Service).filter(Service.id == service_id).first()
            if srv and srv.duration_min:
                effective_duration = srv.duration_min

    # Configuración de horarios comerciales
    bh_json = get_setting(db, "business_hours", "{}")
    try:
        bh_config = json.loads(bh_json)
    except Exception:
        bh_config = {}

    days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    day_name = days_es[target_date.weekday()]
    day_setting = bh_config.get(day_name, {"active": True, "open": "09:00", "close": "20:00"})

    # Si el día está marcado inactivo en business_hours o domingo por defecto cerrado
    if not day_setting.get("active", True) or (target_date.weekday() == 6 and not bh_config.get("Domingo", {}).get("active", False)):
        return AvailableSlotsResponse(
            barber_id=resolved_id,
            barber_name=resolved_name,
            date=date,
            slots=[]
        )

    # Invocar el motor de disponibilidad configurable con la duración acumulada
    calc_res = calculate_available_slots(db, date, resolved_id, service_id, duration_min=effective_duration)
    avail_set = set(calc_res.get("slots", []))

    open_t = parse_time_str(day_setting.get("open", "09:00")) or time(9, 0)
    close_t = parse_time_str(day_setting.get("close", "20:00")) or time(20, 0)

    slots: List[AvailableSlotItem] = []
    current_dt = datetime.combine(target_date, open_t)
    limit_dt = datetime.combine(target_date, close_t)
    step_minutes = 15

    while current_dt + timedelta(minutes=effective_duration) <= limit_dt:
        time_str = current_dt.strftime("%H:%M")
        is_avail = (time_str in avail_set)
        slots.append(AvailableSlotItem(time=time_str, available=is_avail))
        current_dt += timedelta(minutes=step_minutes)

    return AvailableSlotsResponse(
        barber_id=resolved_id,
        barber_name=resolved_name,
        date=date,
        slots=slots
    )

@router.post("/api/waitlist", response_model=dict)
def add_to_waitlist(data: WaitlistEntryCreate, db: Session = Depends(get_db)):
    """Registra a un cliente en la lista de espera cuando un horario no está disponible."""
    norm_phone = normalize_phone(data.client_phone)
    entry = WaitlistEntry(
        client_name=data.client_name.strip(),
        client_phone=norm_phone,
        service_id=data.service_id,
        barber_id=data.barber_id,
        preferred_date=data.preferred_date,
        preferred_time_range=data.preferred_time_range,
        status="ACTIVA",
        notes=data.notes
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "status": "success",
        "message": "Te hemos registrado en la lista de espera. Te avisaremos si se libera un turno.",
        "id": entry.id
    }


@router.post("/api/public/checkin")
def process_client_checkin(
    data: dict,
    db: Session = Depends(get_db)
):
    """
    Procesa el check-in express de un cliente al llegar a la barbería (vía QR o PIN/Teléfono).
    Marca 'is_checked_in = True' y notifica automáticamente en pantalla TV Vivo y Gestión.
    """
    # Inputs unificados
    identifier = str(data.get("identifier") or "").strip()
    raw_pin = str(data.get("pin") or "").strip()
    token_or_code = str(data.get("code") or data.get("token") or raw_pin or data.get("appointment_id") or identifier or "").strip()
    phone_input = str(data.get("phone") or identifier or "").strip()

    search_terms = list(dict.fromkeys([t for t in [identifier, raw_pin, token_or_code, phone_input] if t]))
    if not search_terms:
        raise HTTPException(status_code=400, detail="Debes ingresar tu código PIN, número de turno o teléfono.")

    now_arg = get_argentina_now()
    today_start = datetime.combine(now_arg.date(), datetime.min.time())
    today_end = datetime.combine(now_arg.date(), datetime.max.time())

    query = db.query(Appointment).filter(
        Appointment.appointment_time >= today_start,
        Appointment.appointment_time <= today_end,
        Appointment.canceled == False,
        Appointment.status != "CANCELADO"
    )

    appt = None

    # 1. Búsqueda prioritaria por PIN de Check-in (checkin_token)
    for term in search_terms:
        appt = query.filter(Appointment.checkin_token == term).first()
        if appt:
            break

    # 2. Búsqueda por ID de Turno
    if not appt:
        for term in search_terms:
            if term.isdigit() and len(term) <= 6:
                appt = query.filter(Appointment.id == int(term)).first()
                if appt:
                    break

    # 3. Búsqueda por Teléfono completo o normalizado
    if not appt:
        for term in search_terms:
            norm_p = normalize_phone(term)
            appt = query.filter(Appointment.client_phone.ilike(f"%{term}%") | (Appointment.client_phone == norm_p)).first()
            if appt:
                break

    # 4. Búsqueda por últimos 4 o más dígitos del teléfono
    if not appt:
        all_today = query.all()
        for term in search_terms:
            if len(term) >= 4:
                suffix = term[-4:]
                for candidate in all_today:
                    if candidate.client_phone and candidate.client_phone.endswith(suffix):
                        appt = candidate
                        break
            if appt:
                break

    if not appt:
        raise HTTPException(status_code=404, detail="No encontramos ningún turno activo registrado para hoy con ese PIN o teléfono.")

    # Marcar Check-in y confirmar presencia
    now_naive = now_arg.replace(tzinfo=None)
    appt.is_checked_in = True
    appt.checked_in_at = now_naive
    if appt.status == "PENDIENTE":
        appt.confirmed = True
        appt.status = "CONFIRMADO"

    # Disparar alerta en live settings para TV y Moderador
    set_setting(db, "live_last_checkin_id", str(appt.id))
    set_setting(db, "live_last_checkin_name", appt.client_name)
    set_setting(db, "live_last_checkin_barber", appt.barber_name or "General")
    set_setting(db, "live_last_checkin_time", now_arg.strftime("%H:%M:%S"))

    db.add(AuditLog(
        user_name=appt.client_name,
        actor="Totem Check-in Entrada",
        module="Check-in QR",
        action="Check-in Registrado",
        description=f"Cliente {appt.client_name} (Turno #{appt.id}) realizó check-in en el Totem de entrada.",
        record_id=str(appt.id)
    ))
    db.commit()

    return {
        "status": "success",
        "message": f"¡Bienvenido {appt.client_name}! Tu check-in se registró correctamente.",
        "appointment_id": appt.id,
        "client_name": appt.client_name,
        "is_checked_in": True,
        "checked_in_at": appt.checked_in_at.strftime("%H:%M"),
        "appointment": {
            "id": appt.id,
            "turn_code": f"T-{appt.id:03d}" if appt.id < 1000 else f"T-{appt.id}",
            "client_name": appt.client_name,
            "barber_name": appt.barber_name or "General",
            "service": appt.service or "Corte de Autor",
            "appointment_time": appt.appointment_time.strftime("%H:%M"),
            "checked_in_at": appt.checked_in_at.strftime("%H:%M")
        }
    }

