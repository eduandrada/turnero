import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
import httpx
from sqlalchemy.orm import Session

from app.models import Appointment, Barber, NotificationLog
from app.settings_helper import get_setting
from app.utils import normalize_phone

logger = logging.getLogger("bladesync.whatsapp")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_CLOUD_API_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
APP_ENV = os.getenv("ENV", "development").lower()

def get_whatsapp_api_url() -> str:
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_ID)
    return f"https://graph.facebook.com/v20.0/{phone_id}/messages"

def verify_whatsapp_signature(body_bytes: bytes, signature_header: Optional[str], secret: Optional[str] = None) -> bool:
    """
    Verifica la firma criptográfica HMAC-SHA256 enviada por Meta en la cabecera X-Hub-Signature-256.
    """
    app_secret = secret or os.getenv("WHATSAPP_APP_SECRET", WHATSAPP_APP_SECRET)
    if not app_secret:
        if APP_ENV == "production":
            logger.error("SEGURIDAD: WHATSAPP_APP_SECRET no está configurado en producción. Webhook rechazado.")
            return False
        # En desarrollo, si no hay secreto configurado y no hay firma, se permite para pruebas locales
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
        return False, None, "Número de teléfono destinatario inválido o vacío."

    token = os.getenv("WHATSAPP_CLOUD_API_TOKEN", WHATSAPP_TOKEN)
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_ID)

    # Si estamos en modo mock/test sin token real configurado
    if not token or token.startswith("EAAG_MOCK") or token == "your_whatsapp_cloud_api_token_here":
        mock_msg_id = f"wamid_mock_{int(datetime.utcnow().timestamp())}_{clean_to[-4:]}"
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
                "header": {"type": "text", "text": header_text or "💈 Barbería"},
                "body": {"text": text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": btn["id"], "title": btn["title"]}
                        }
                        for btn in interactive_buttons[:3]  # WhatsApp soporta hasta 3 botones reply
                    ]
                }
            }
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
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(api_url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                data = resp.json()
                msg_id = None
                messages = data.get("messages", [])
                if messages:
                    msg_id = messages[0].get("id")
                return True, msg_id, json.dumps(data)
            else:
                err_detail = f"Status {resp.status_code}: {resp.text}"
                logger.error(f"WhatsApp Cloud API Error al enviar a {clean_to}: {err_detail}")
                return False, None, err_detail
    except Exception as exc:
        err_msg = f"Excepción de conexión con WhatsApp API: {str(exc)}"
        logger.exception(err_msg)
        return False, None, err_msg

def build_client_appointment_message(db: Session, appointment: Appointment) -> Tuple[str, List[Dict[str, str]]]:
    """
    Construye un mensaje profesional, inteligente y claro para el cliente.
    """
    shop_name = get_setting(db, "barber_name", "Turnero")
    shop_address = get_setting(db, "address", "Av. Belgrano 1234")
    shop_phone = get_setting(db, "phone", "")
    
    date_str = appointment.appointment_time.strftime("%d/%m/%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")
    duration = appointment.duration_min or 45
    barber_name = appointment.barber_name or "Profesional de Autor"
    service_name = appointment.service or "Corte de Autor"

    msg = (
        f"💈 *¡Hola {appointment.client_name}! Tu turno en {shop_name} está reservado.* 💈\n\n"
        f"📅 *Fecha:* {date_str}\n"
        f"⏰ *Hora:* {time_str} hs (Duración aprox: {duration} min)\n"
        f"✂️ *Servicio:* {service_name}\n"
        f"👤 *Atención por:* {barber_name}\n"
        f"📍 *Dirección:* {shop_address}\n\n"
        f"ℹ️ *Instrucciones:* Te recomendamos llegar 5 minutos antes. "
        f"Si necesitás modificar o cancelar, podés hacerlo respondiendo a este mensaje.\n"
        f"¡Te esperamos para brindarte la mejor experiencia!"
    )

    buttons = [
        {"id": f"CONFIRM_{appointment.id}", "title": "✅ Confirmar Asistencia"},
        {"id": f"CANCEL_{appointment.id}", "title": "❌ Cancelar Turno"}
    ]
    return msg, buttons

def build_barber_appointment_message(db: Session, appointment: Appointment) -> str:
    """
    Construye el mensaje interno privado para el barbero.
    """
    shop_name = get_setting(db, "barber_name", "Turnero")
    date_str = appointment.appointment_time.strftime("%d/%m/%Y")
    time_str = appointment.appointment_time.strftime("%H:%M")
    duration = appointment.duration_min or 45
    barber_name = appointment.barber_name or "Profesional"
    service_name = appointment.service or "Corte"
    notes = appointment.notes or "Sin observaciones."

    return (
        f"🔔 *Nuevo turno agendado - {shop_name}*\n\n"
        f"Hola *{barber_name}*, tenés una nueva reserva:\n"
        f"• *Cliente:* {appointment.client_name}\n"
        f"• *Fecha y Hora:* {date_str} a las {time_str} hs ({duration} min)\n"
        f"• *Servicio:* {service_name}\n"
        f"• *Notas:* {notes}\n"
        f"• *Turno ID:* #{appointment.id}"
    )

def send_appointment_whatsapp_notifications(db: Session, appointment: Appointment) -> None:
    """
    Envía notificaciones de WhatsApp tanto al cliente como al barbero al confirmarse o crearse un turno.
    Registra el estado en NotificationLog (SENT / ERROR / PENDING) con ID de mensaje.
    No bloquea ni hace fallar la transacción del turno si WhatsApp tiene problemas.
    """
    notify_client = get_setting(db, "wa_notify_client", "true") == "true"
    notify_barber = get_setting(db, "wa_notify_barber", "true") == "true"
    shop_name = get_setting(db, "barber_name", "Turnero")

    # 1. Notificación al Cliente
    if notify_client and appointment.client_phone:
        try:
            client_msg, buttons = build_client_appointment_message(db, appointment)
            success, msg_id, response_details = send_whatsapp_message(
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

    # 2. Notificación al Barbero (número privado en DB, nunca expuesto en API pública)
    if notify_barber and appointment.barber_id:
        try:
            barber = db.query(Barber).filter(Barber.id == appointment.barber_id).first()
            if barber and barber.phone:
                barber_msg = build_barber_appointment_message(db, appointment)
                success, msg_id, response_details = send_whatsapp_message(
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
    """
    Procesa actualizaciones de estado de entrega de mensajes recibidas en el webhook de WhatsApp.
    (sent -> SENT, delivered -> DELIVERED, read -> READ, failed -> ERROR)
    """
    wamid = status_obj.get("id")
    raw_status = status_obj.get("status", "").lower()
    if not wamid:
        return

    status_map = {
        "sent": "SENT",
        "delivered": "DELIVERED",
        "read": "READ",
        "failed": "ERROR"
    }
    new_status = status_map.get(raw_status)
    if not new_status:
        return

    log_entry = db.query(NotificationLog).filter(NotificationLog.whatsapp_message_id == wamid).first()
    if log_entry:
        log_entry.status = new_status
        if raw_status == "failed":
            errors = status_obj.get("errors", [])
            log_entry.error_details = json.dumps(errors)
        db.commit()
        logger.info(f"NotificationLog #{log_entry.id} actualizado a estado {new_status} para mensaje {wamid}")

def retry_failed_whatsapp_notifications(db: Session, max_retries: int = 3) -> int:
    """
    Reintenta el envío de notificaciones de WhatsApp en estado ERROR o PENDING que no hayan superado max_retries.
    Retorna la cantidad de notificaciones reintentadas exitosamente.
    """
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

