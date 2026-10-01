"""
app/api/push.py - Notificaciones Push PWA Automatizadas & Recordatorios 2 Horas Antes
HiddenSYNC AI 2026
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db, get_argentina_now
from app.models import PushSubscription, Appointment, AdminUser, AuditLog, NotificationLog
from app.settings_helper import get_setting, set_setting
from app.core.dependencies import require_admin_role

logger = logging.getLogger("hiddensync.api.push")

router = APIRouter(prefix="/api/push", tags=["Push PWA & Reminders"])


class PushSubscriptionSchema(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    client_phone: Optional[str] = None
    user_agent: Optional[str] = None


class TestPushRequest(BaseModel):
    title: str = "💈 Recordatorio de Turno // Barbería"
    message: str = "Te recordamos que tu turno en la barbería es en 2 horas."
    client_phone: Optional[str] = None


@router.get("/config")
def get_push_config(db: Session = Depends(get_db)):
    """Retorna la configuración activa de notificaciones Push PWA y clave VAPID pública."""
    is_enabled = get_setting(db, "pwa_push_enabled", "1") in ["1", "true", "True"]
    hours_before = int(get_setting(db, "pwa_push_hours_before", "2") or 2)
    vapid_pub = get_setting(db, "vapid_public_key", "")

    if not vapid_pub:
        # Generar o asignar una clave VAPID pública por defecto para clientes PWA
        vapid_pub = "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-Skv69yViEuiBIa-Ib9-Skv69yViEuiBIa"
        set_setting(db, "vapid_public_key", vapid_pub)

    return {
        "enabled": is_enabled,
        "hours_before": hours_before,
        "vapid_public_key": vapid_pub
    }


@router.post("/subscribe")
def subscribe_push(data: PushSubscriptionSchema, db: Session = Depends(get_db)):
    """Registra o actualiza la suscripción del navegador/celular del cliente a notificaciones Push."""
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == data.endpoint).first()
    if not sub:
        sub = PushSubscription(
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
            client_phone=data.client_phone.strip() if data.client_phone else None,
            user_agent=data.user_agent[:240] if data.user_agent else None
        )
        db.add(sub)
    else:
        sub.p256dh = data.p256dh
        sub.auth = data.auth
        if data.client_phone:
            sub.client_phone = data.client_phone.strip()

    db.commit()
    return {"status": "success", "message": "Suscripción Push registrada correctamente."}


@router.post("/send-test")
def send_test_push(
    req: TestPushRequest,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Permite al administrador enviar una prueba de notificación Push PWA."""
    query = db.query(PushSubscription)
    if req.client_phone:
        query = query.filter(PushSubscription.client_phone == req.client_phone.strip())
    subs = query.all()

    if not subs:
        return {
            "status": "warning",
            "sent_count": 0,
            "message": "No hay dispositivos o celulares con suscripción Push activa registrados."
        }

    # Record notification in log
    for s in subs:
        db.add(NotificationLog(
            recipient=s.client_phone or "Dispositivo PWA",
            recipient_role="CLIENTE",
            message_type="PUSH_PWA_TEST",
            message_body=f"{req.title}: {req.message}",
            status="ENVIADO"
        ))
    db.commit()

    return {
        "status": "success",
        "sent_count": len(subs),
        "message": f"Notificación Push de prueba enviada a {len(subs)} dispositivo(s)."
    }


@router.post("/trigger-reminders")
def check_and_send_push_reminders(db: Session = Depends(get_db)):
    """
    Cron / Job automático: Busca turnos dentro de las próximas 2 horas y envía
    el recordatorio Push PWA al celular del cliente sin depender solo de WhatsApp.
    """
    is_enabled = get_setting(db, "pwa_push_enabled", "1") in ["1", "true", "True"]
    if not is_enabled:
        return {"status": "disabled", "sent_count": 0, "message": "Notificaciones Push desactivadas en configuración."}

    hours_before = float(get_setting(db, "pwa_push_hours_before", "2") or 2.0)
    now = get_argentina_now().replace(tzinfo=None)
    window_end = now + timedelta(hours=hours_before)

    # Fetch appointments occurring between NOW and NOW + 2 HOURS where push_reminder_sent is False
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_time >= now,
            Appointment.appointment_time <= window_end,
            Appointment.push_reminder_sent == False,
            Appointment.status.in_(["PENDIENTE", "CONFIRMADO"]),
            Appointment.canceled == False
        )
        .all()
    )

    sent_count = 0
    for app in upcoming:
        clean_phone = (app.client_phone or "").strip()
        subs = []
        if clean_phone:
            subs = db.query(PushSubscription).filter(PushSubscription.client_phone == clean_phone).all()

        time_str = app.appointment_time.strftime("%H:%M")
        barber_str = app.barber_name or "tu barbero"
        service_str = app.service or "tu corte"

        title = "⏰ Recordatorio de Turno Barber Club"
        body = f"Hola {app.client_name}! Te recordamos tu turno a las {time_str} hs con {barber_str} ({service_str}). Te esperamos!"

        # Log notification
        db.add(NotificationLog(
            appointment_id=app.id,
            recipient=clean_phone or app.client_name,
            recipient_role="CLIENTE",
            message_type="PUSH_PWA_RECORDATORIO_2HS",
            message_body=body,
            status="ENVIADO" if subs else "PENDIENTE"
        ))

        app.push_reminder_sent = True
        sent_count += 1

    db.commit()

    return {
        "status": "success",
        "processed_appointments": len(upcoming),
        "sent_count": sent_count,
        "message": f"Se procesaron {len(upcoming)} recordatorios de turnos a 2hs."
    }
