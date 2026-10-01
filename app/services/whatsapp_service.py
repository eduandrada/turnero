"""
app/services/whatsapp_service.py - WhatsApp Cloud API integration (Meta Graph API).
Handles message sending, webhook signature verification (HMAC-SHA256), idempotency,
status callbacks, interactive button responses, and notification logging.
"""
import os
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
import httpx
from sqlalchemy.orm import Session

from app.core.config import (
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_ACCESS_TOKEN,
    APP_ENV
)
from app.core.logging import whatsapp_logger
from app.models import Appointment, Barber, NotificationLog
from app.settings_helper import get_setting
from app.utils import normalize_phone

logger = whatsapp_logger

WHATSAPP_TOKEN = WHATSAPP_ACCESS_TOKEN or os.getenv("WHATSAPP_CLOUD_API_TOKEN", "")
WHATSAPP_PHONE_ID = WHATSAPP_PHONE_NUMBER_ID or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

def get_whatsapp_api_url() -> str:
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_ID)
    return f"https://graph.facebook.com/v20.0/{phone_id}/messages"

def verify_whatsapp_signature(body_bytes: bytes, signature_header: Optional[str], secret: Optional[str] = None) -> bool:
    """Verifica la firma criptográfica HMAC-SHA256 enviada por Meta en la cabecera X-Hub-Signature-256."""
    app_secret = secret or os.getenv("WHATSAPP_APP_SECRET", WHATSAPP_APP_SECRET)
    if not app_secret:
        if APP_ENV == "production":
            logger.error("SEGURIDAD: WHATSAPP_APP_SECRET no está configurado en producción. Webhook rechazado.")
            return False
        if not signature_header:
            return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    received_hash = signature_header.split("sha256=", 1)[1].strip()
    expected_hash = hmac.new(
        app_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(received_hash, expected_hash)

def clean_phone_number(phone: str) -> str:
    """Limpia y normaliza el número telefónico para WhatsApp Cloud API."""
    return normalize_phone(phone)

def send_whatsapp_message(
    to_phone: str,
    text: str,
    interactive_buttons: Optional[List[Dict[str, str]]] = None,
    header_text: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Envía un mensaje real o interactivo mediante WhatsApp Cloud API (Meta Graph API).
    Retorna: (éxito, whatsapp_message_id, detalles/error)
    """
    clean_to = clean_phone_number(to_phone)
    if not clean_to:
        logger.warning(f"Intento de envío de WhatsApp a teléfono vacío o inválido: '{to_phone}'")
        return False, None, "Número de teléfono inválido"

    token = os.getenv("WHATSAPP_CLOUD_API_TOKEN", WHATSAPP_TOKEN)
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_ID)

    # Si estamos en modo mock/test sin token real configurado
    if not token or token.startswith("EAAG_MOCK") or token == "your_whatsapp_cloud_api_token_here":
        mock_msg_id = f"wamid_mock_{int(datetime.now(timezone.utc).timestamp())}_{clean_to[-4:]}"
        logger.info(f"[WHATSAPP MOCK / DEV] Enviado a {clean_to}: '{text[:60]}...' (ID: {mock_msg_id})")
        return True, mock_msg_id, "Enviado en modo mock de desarrollo/testing."

    api_url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if interactive_buttons:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn["id"],
                                "title": btn["title"]
                            }
                        }
                        for btn in interactive_buttons
                    ]
                }
            }
        }
        if header_text:
            payload["interactive"]["header"] = {
                "type": "text",
                "text": header_text
            }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(api_url, headers=headers, json=payload)
            if resp.status_code in [200, 201]:
                resp_data = resp.json()
                msg_id = None
                messages = resp_data.get("messages", [])
                if messages and len(messages) > 0:
                    msg_id = messages[0].get("id")
                logger.info(f"WhatsApp enviado exitosamente a {clean_to} (Status {resp.status_code}, ID: {msg_id})")
                return True, msg_id, resp.text
            else:
                error_msg = f"Error Meta API ({resp.status_code}): {resp.text}"
                logger.error(f"Fallo envío WhatsApp a {clean_to}: {error_msg}")
                return False, None, error_msg
    except Exception as e:
        error_detail = f"Excepción de conexión enviando WhatsApp: {str(e)}"
        logger.error(error_detail)
        return False, None, error_detail

def build_client_appointment_message(db: Session, appointment: Appointment) -> Tuple[str, List[Dict[str, str]]]:
    """Genera el texto amigable y botones interactivos para la confirmación del turno del cliente."""
    shop_name = get_setting(db, "barber_name", "Turnero")
    date_str = appointment.appointment_time.strftime("%d/%m/%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")
    barber_name = appointment.barber_name or (appointment.barber.name if appointment.barber else "Profesional asignado")
    service_name = appointment.service or (appointment.service_rel.name if appointment.service_rel else "Servicio")
    address = get_setting(db, "address", "Av. Principal 123")
    pin_code = appointment.checkin_token or f"{appointment.id:04d}"

    msg = (
        f"💈 *¡Hola {appointment.client_name}!* Tu turno en *{shop_name}* ha sido registrado.\n\n"
        f"📅 *Fecha:* {date_str}\n"
        f"⏰ *Hora:* {time_str} hs\n"
        f"✂️ *Servicio:* {service_name}\n"
        f"👤 *Barbero:* {barber_name}\n"
        f"📍 *Dirección:* {address}\n\n"
        f"🔑 *TU PIN DE LLEGADA / TOTEM:* `{pin_code}`\n"
        f"📲 *Al llegar a la barbería:* Ingresá tu PIN o tu teléfono en el Totem de recepción para anunciar tu llegada y sentarte en la sala de espera.\n\n"
        f"Por favor confirma tu asistencia presionando el botón abajo 👇"
    )

    buttons = [
        {"id": f"CONFIRM_{appointment.id}", "title": "✅ Confirmar"},
        {"id": f"CANCEL_{appointment.id}", "title": "❌ Cancelar"}
    ]
    return msg, buttons

def build_barber_appointment_message(db: Session, appointment: Appointment) -> str:
    """Genera el mensaje informativo para el barbero cuando se agenda un nuevo turno con él."""
    shop_name = get_setting(db, "barber_name", "Turnero")
    date_str = appointment.appointment_time.strftime("%d/%m/%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")
    service_name = appointment.service or (appointment.service_rel.name if appointment.service_rel else "Servicio")
    duration = appointment.duration_min or 45
    barber_name = appointment.barber_name or (appointment.barber.name if appointment.barber else "Barbero")
    notes = appointment.notes or "Sin notas adicionales"

    return (
        f"🔔 *Nuevo turno agendado - {shop_name}*\n\n"
        f"Hola *{barber_name}*, tenés una nueva reserva:\n"
        f"• *Cliente:* {appointment.client_name}\n"
        f"• *Fecha y Hora:* {date_str} a las {time_str} hs ({duration} min)\n"
        f"• *Servicio:* {service_name}\n"
        f"• *Notas:* {notes}\n"
        f"• *Turno ID:* #{appointment.id}"
    )

import sys

def send_appointment_whatsapp_notifications(db: Session, appointment: Appointment) -> None:
    """Envía notificaciones de WhatsApp tanto al cliente como al barbero al confirmarse o crearse un turno."""
    notify_client = get_setting(db, "wa_notify_client", "true") == "true"
    notify_barber = get_setting(db, "wa_notify_barber", "true") == "true"
    shop_name = get_setting(db, "barber_name", "Turnero")
    sender_fn = getattr(sys.modules.get("app.whatsapp_service"), "send_whatsapp_message", send_whatsapp_message)

    # 1. Notificación al Cliente
    if notify_client and appointment.client_phone:
        try:
            client_msg, buttons = build_client_appointment_message(db, appointment)
            success, msg_id, response_details = sender_fn(
                to_phone=appointment.client_phone,
                text=client_msg,
                interactive_buttons=buttons,
                header_text=f"💈 {shop_name} // Turnos"
            )

            status_val = "SENT" if success else "ERROR"
            db.add(NotificationLog(
                appointment_id=appointment.id,
                recipient=appointment.client_phone,
                recipient_role="CLIENTE",
                message_type="WHATSAPP_CONFIRMACION",
                message_body=client_msg,
                status=status_val,
                whatsapp_message_id=msg_id,
                response_payload=response_details if success else None,
                error_details=response_details if not success else None,
                retry_count=0
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Fallo no crítico enviando WhatsApp a cliente para turno #{appointment.id}: {e}")

    # 2. Notificación al Barbero
    if notify_barber and appointment.barber_id:
        try:
            barber = db.query(Barber).filter(Barber.id == appointment.barber_id).first()
            if barber and barber.phone:
                barber_msg = build_barber_appointment_message(db, appointment)
                success, msg_id, response_details = sender_fn(
                    to_phone=barber.phone,
                    text=barber_msg
                )

                status_val = "SENT" if success else "ERROR"
                db.add(NotificationLog(
                    appointment_id=appointment.id,
                    recipient=barber.phone,
                    recipient_role="BARBERO",
                    message_type="WHATSAPP_CONFIRMACION",
                    message_body=barber_msg,
                    status=status_val,
                    whatsapp_message_id=msg_id,
                    response_payload=response_details if success else None,
                    error_details=response_details if not success else None,
                    retry_count=0
                ))
                db.commit()
        except Exception as e:
            logger.error(f"Fallo no crítico enviando WhatsApp a barbero para turno #{appointment.id}: {e}")

def process_whatsapp_status_update(db: Session, status_obj: Dict[str, Any]) -> None:
    """Procesa actualizaciones de estado de entrega de mensajes recibidas en el webhook de WhatsApp."""
    try:
        wamid = status_obj.get("id")
        new_status = status_obj.get("status")
        if not wamid or not new_status:
            return

        status_mapping = {
            "sent": "SENT",
            "delivered": "DELIVERED",
            "read": "READ",
            "failed": "ERROR"
        }
        mapped_status = status_mapping.get(new_status, new_status.upper())

        log_entry = db.query(NotificationLog).filter(NotificationLog.whatsapp_message_id == wamid).first()
        if log_entry:
            log_entry.status = mapped_status
            if mapped_status == "ERROR":
                errors = status_obj.get("errors", [])
                log_entry.error_details = json.dumps(errors) if errors else "Error devuelto por WhatsApp API"
            db.commit()
            logger.info(f"Estado de WhatsApp actualizado para wamid {wamid}: {mapped_status}")
    except Exception as e:
        logger.error(f"Error procesando callback de estado de WhatsApp: {e}")

def retry_failed_whatsapp_notifications(db: Session, max_retries: int = 3) -> int:
    """Reintenta el envío de notificaciones registradas como fallidas o pendientes."""
    failed_logs = db.query(NotificationLog).filter(
        NotificationLog.status.in_(["ERROR", "PENDIENTE"]),
        NotificationLog.retry_count < max_retries
    ).limit(20).all()

    success_count = 0
    for log in failed_logs:
        log.retry_count = (log.retry_count or 0) + 1
        success, msg_id, response_details = send_whatsapp_message(
            to_phone=log.recipient,
            text=log.message_body
        )
        if success:
            log.status = "SENT"
            log.whatsapp_message_id = msg_id
            log.response_payload = response_details
            log.error_details = None
            success_count += 1
        else:
            log.status = "ERROR"
            log.error_details = response_details
        db.commit()
    return success_count

async def send_whatsapp_interactive_reminder(
    phone: str,
    appointment_id: int,
    client_name: str,
    service: str,
    app_time: datetime
) -> bool:
    """Envía un mensaje interactivo con botones de Confirmar / Cancelar para recordatorio de turno."""
    formatted_time = app_time.strftime("%H:%M hs")
    formatted_date = app_time.strftime("%d/%m")

    body_text = (
        f"¡Hola *{client_name}*! Te recordamos tu cita para *{service}* "
        f"el día *{formatted_date}* a las *{formatted_time}*.\n\n"
        f"Por favor confirma o cancela tu turno."
    )
    buttons = [
        {"id": f"CONFIRM_{appointment_id}", "title": "✅ Confirmar"},
        {"id": f"CANCEL_{appointment_id}", "title": "❌ Cancelar"}
    ]

    success, msg_id, details = send_whatsapp_message(
        to_phone=phone,
        text=body_text,
        interactive_buttons=buttons,
        header_text="💈 Barbería // Recordatorio"
    )
    return success
