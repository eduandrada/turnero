"""
app/api/live.py - Endpoints de Agenda en Vivo, Turnero en Pantalla TV y Walk-in
HiddenSYNC AI 2026
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import AdminUser, Appointment, Barber, AuditLog, AppointmentHistory
from app.core.dependencies import require_encargado_or_admin
from app.settings_helper import get_setting, set_setting, DEFAULT_SETTINGS
from app.utils import build_speech_announcement, format_turn_for_speech
from app.services.live_queue_service import live_queue_service

router = APIRouter(tags=["Live Queue & TV Display"])

def save_live_settings_service(db: Session, data: Dict[str, Any], actor_name: str = "Encargado / Admin") -> Dict[str, str]:
    """Servicio centralizado para guardar configuraciones de pantalla TV y Live Agenda."""
    allowed = [
        "live_tv_title", "live_tv_subtitle", "live_tv_marquee", "live_voice_enabled", "live_chime_enabled", "live_auto_refresh_sec",
        "voice_communication_style", "voice_pitch", "voice_rate", "voice_volume", "voice_chime_volume", "voice_double_call", "voice_custom_template"
    ]
    saved_items = {}
    for k in allowed:
        if k in data:
            set_setting(db, k, str(data[k]))
            saved_items[k] = str(data[k])
    db.commit()

    if saved_items:
        db.add(AuditLog(
            user_name=actor_name,
            actor=actor_name,
            module="Live Agenda",
            action="Actualizar Configuración Live TV",
            description="Ajustes de pantalla TV actualizados",
            new_value=json.dumps(saved_items)
        ))
        db.commit()
    return {"status": "success", "message": "Configuraciones de pantalla TV guardadas exitosamente."}

@router.get("/api/live-agenda")
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
    return live_queue_service.get_live_agenda(db, barber_id, target_date)

@router.get("/api/live-agenda/settings")
def get_live_settings(db: Session = Depends(get_db)):
    """Retorna las configuraciones actuales de la pantalla TV y agenda en vivo (público)."""
    return {
        "live_tv_title": get_setting(db, "live_tv_title", DEFAULT_SETTINGS.get("live_tv_title", "SALA DE ESPERA // TURNERO EN VIVO")),
        "live_tv_subtitle": get_setting(db, "live_tv_subtitle", DEFAULT_SETTINGS.get("live_tv_subtitle", "ATENCIÓN POR SILLÓN")),
        "live_tv_marquee": get_setting(db, "live_tv_marquee", DEFAULT_SETTINGS.get("live_tv_marquee", "💈 Bienvenido a la Barbería • Turnos en Tiempo Real • Wi-Fi Disponible")),
        "live_voice_enabled": str(get_setting(db, "live_voice_enabled", DEFAULT_SETTINGS.get("live_voice_enabled", "true"))).lower() in ["true", "1", "yes"],
        "live_chime_enabled": str(get_setting(db, "live_chime_enabled", DEFAULT_SETTINGS.get("live_chime_enabled", "true"))).lower() in ["true", "1", "yes"],
        "live_auto_refresh_sec": int(get_setting(db, "live_auto_refresh_sec", DEFAULT_SETTINGS.get("live_auto_refresh_sec", "8")) or 8)
    }

@router.post("/api/live-agenda/settings")
@router.put("/api/live-agenda/settings")
def save_live_settings(
    data: Dict[str, Any],
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Guarda las configuraciones de la pantalla TV y cartelera directamente desde live.html o admin."""
    return save_live_settings_service(db, data, current_user.username)

@router.post("/api/live-agenda/walk-in")
def create_live_walk_in(
    data: Dict[str, Any],
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
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

    db.add(AuditLog(
        user_name=current_user.username,
        actor=current_user.username,
        module="Live Agenda",
        action="Walk-in Agregado",
        description=f"Cliente espontáneo: {name} ({service_name}) - Barbero: {barber_name}",
        record_id=str(new_appt.id)
    ))
    db.commit()

    return {"message": "Cliente agregado a la cola en vivo exitosamente.", "appointment_id": new_appt.id}

@router.put("/api/live-agenda/{appointment_id}")
def update_live_appointment(
    appointment_id: int,
    data: Dict[str, Any],
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
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

    db.add(AuditLog(
        user_name=current_user.username,
        actor=current_user.username,
        module="Live Agenda",
        action="Editar Turno en Vivo",
        description=f"Turno #{appt.id} modificado en pantalla de moderación",
        record_id=str(appt.id)
    ))
    db.commit()

    return {"message": "Turno actualizado correctamente.", "id": appt.id}

@router.post("/api/live-agenda/{appointment_id}/call")
def call_live_appointment(
    appointment_id: int,
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Llama al cliente a pantalla TV y emite timbre/chime sincronizado."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    appt.status = "LLAMANDO"
    set_setting(db, "live_current_called_id", str(appt.id))
    db.commit()

    db.add(AppointmentHistory(
        appointment_id=appt.id,
        old_status="CONFIRMADO",
        new_status="LLAMANDO",
        changed_by=current_user.username,
        change_reason="Llamado a pantalla TV desde Live Agenda"
    ))
    db.add(AuditLog(
        user_name=current_user.username,
        actor=current_user.username,
        module="Live Agenda",
        action="Llamar Turno a Pantalla TV",
        description=f"Llamado a pantalla: Turno #{appt.id} ({appt.client_name})",
        record_id=str(appt.id)
    ))
    db.commit()

    turn_code = f"T-{appt.id:03d}" if appt.id < 1000 else f"T-{appt.id}"
    speech_text = build_speech_announcement(
        style=get_setting(db, "voice_communication_style", "moderno"),
        turn_code=turn_code,
        client_name=appt.client_name,
        barber_name=appt.barber_name or "General",
        station_name=f"Sillón {appt.barber_id or 1}",
        service_name=appt.service or "Corte",
        custom_template=get_setting(db, "voice_custom_template", "")
    )
    call_info = {
        "id": appt.id,
        "turn_code": turn_code,
        "client_name": appt.client_name,
        "barber_name": appt.barber_name or "General",
        "service": appt.service or "Corte",
        "time_str": appt.appointment_time.strftime("%H:%M"),
        "speech_text": speech_text
    }
    return {
        "status": "success",
        "message": f"Turno #{appt.id} de {appt.client_name} llamado a pantalla.",
        "appointment": call_info,
        "current_call": call_info
    }

@router.post("/api/live-agenda/{appointment_id}/status")
def update_live_status(
    appointment_id: int,
    status_data: Dict[str, str],
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Actualiza el estado de un turno desde la pantalla de agenda en vivo."""
    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Falta el estado.")
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    old_status = appt.status
    appt.status = new_status
    if new_status == "COMPLETADO":
        appt.confirmed = True
    elif new_status == "CANCELADO":
        appt.canceled = True
    db.commit()

    db.add(AuditLog(
        user_name=current_user.username,
        actor=current_user.username,
        module="Live Agenda",
        action="Cambio Estado en Vivo",
        description=f"Turno #{appt.id} ({appt.client_name}) pasó de {old_status} a {new_status}",
        record_id=str(appt.id)
    ))
    db.commit()

    return {"message": "Estado actualizado correctamente.", "status": new_status}

@router.get("/api/live/speech-format")
def get_live_speech_format(
    turn_code: str = Query("A-125"),
    barber_name: str = Query("Martín"),
    service_name: str = Query("Corte Clásico"),
    station_name: str = Query("Sillón 1"),
    style: str = Query("moderno")
):
    """Endpoint de utilidad para probar en vivo la locución y formateo fonético."""
    speech = build_speech_announcement(
        style=style,
        turn_code=turn_code,
        barber_name=barber_name,
        station_name=station_name,
        service_name=service_name
    )
    phonetic_turn = format_turn_for_speech(turn_code)
    return {
        "turn_code": turn_code,
        "phonetic_turn": phonetic_turn,
        "style": style,
        "speech_text": speech
    }

@router.post("/api/live-agenda/finish-and-next")
def finish_and_next_appointment(
    data: Optional[Dict[str, Any]] = None,
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """
    Endpoint de 1-Click: '⚡ Finalizar Corte y Llamar al Próximo'.
    Realiza el cierre ágil del corte actual, otorga puntos Barber Club, y llama automáticamente al siguiente en cola.
    """
    body = data or {}
    appointment_id = body.get("appointment_id")
    barber_id = body.get("barber_id")
    payment_method = body.get("payment_method")
    tip_amount = float(body.get("tip_amount") or 0.0)

    return live_queue_service.finish_and_next(
        db=db,
        appointment_id=appointment_id,
        barber_id=barber_id,
        payment_method=payment_method,
        tip_amount=tip_amount,
        actor_name=current_user.username
    )

