"""
app/api/whatsapp.py - Endpoints de Webhook de WhatsApp Cloud API
HiddenSYNC AI 2026
"""
import os
import json
import logging
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import Appointment, AppointmentHistory, IdempotencyRecord
from app.services.whatsapp_service import (
    verify_whatsapp_signature,
    process_whatsapp_status_update,
    clean_phone_number,
)

logger = logging.getLogger("hiddensync.whatsapp")

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "hiddensync_webhook_secret_token_2026")

router = APIRouter(tags=["WhatsApp Webhook"])

@router.get("/api/whatsapp-webhook")
@router.get("/api/whatsapp/webhook", deprecated=True)
def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """Verificación de suscripción al webhook de WhatsApp Cloud API."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/api/whatsapp-webhook")
@router.post("/api/whatsapp/webhook", deprecated=True)
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Recepción de eventos, estados de entrega y respuestas de clientes vía WhatsApp Cloud API."""
    body_bytes = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")

    # 1. Verificación estricta de firma criptográfica HMAC-SHA256
    if not verify_whatsapp_signature(body_bytes, sig_header):
        logger.warning("[SECURITY] Firma de WhatsApp Webhook inválida o ausente.")
        raise HTTPException(status_code=403, detail="Firma de WhatsApp Webhook inválida.")

    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception as e:
        logger.error(f"Error decodificando payload de WhatsApp: {e}")
        return {"status": "invalid_json"}

    try:
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                val = change.get("value", {})

                # A. Actualizaciones de estado de entrega (SENT, DELIVERED, READ, FAILED) con deduplicación
                for status_obj in val.get("statuses", []):
                    s_id = status_obj.get("id")
                    s_val = status_obj.get("status")
                    if s_id and s_val:
                        s_key = f"wa_stat_{s_id}_{s_val}"
                        if db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == s_key).first():
                            logger.info(f"[WHATSAPP] Webhook de estado duplicado ignorado: {s_key}")
                            continue
                        db.add(IdempotencyRecord(
                            idempotency_key=s_key,
                            request_path="/api/whatsapp-webhook",
                            response_json="{}",
                            expires_at=get_argentina_now() + timedelta(days=7)
                        ))
                        db.commit()
                    process_whatsapp_status_update(db, status_obj)

                # B. Mensajes entrantes / Respuestas interactivas con deduplicación
                for msg in val.get("messages", []):
                    m_id = msg.get("id")
                    if m_id:
                        m_key = f"wa_msg_{m_id}"
                        if db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == m_key).first():
                            logger.info(f"[WHATSAPP] Webhook de mensaje duplicado ignorado: {m_key}")
                            continue
                        db.add(IdempotencyRecord(
                            idempotency_key=m_key,
                            request_path="/api/whatsapp-webhook",
                            response_json="{}",
                            expires_at=get_argentina_now() + timedelta(days=7)
                        ))
                        db.commit()

                    sender_phone = clean_phone_number(msg.get("from", ""))
                    action_payload = ""
                    if msg.get("type") == "interactive":
                        action_payload = msg.get("interactive", {}).get("button_reply", {}).get("id", "")
                    elif msg.get("type") == "text" or "text" in msg:
                        action_payload = msg.get("text", {}).get("body", "").strip()

                    if "_" in action_payload:
                        action, appt_id_str = action_payload.split("_", 1)
                        if action in ("CONFIRM", "CANCEL") and appt_id_str.isdigit():
                            appt = db.query(Appointment).filter(Appointment.id == int(appt_id_str)).first()
                            if appt:
                                client_p = clean_phone_number(appt.client_phone)
                                barber_p = clean_phone_number(appt.barber.phone) if appt.barber else ""
                                phone_matches = False
                                if sender_phone:
                                    if client_p and (sender_phone.endswith(client_p[-8:]) or client_p.endswith(sender_phone[-8:])):
                                        phone_matches = True
                                    elif barber_p and (sender_phone.endswith(barber_p[-8:]) or barber_p.endswith(sender_phone[-8:])):
                                        phone_matches = True

                                if phone_matches:
                                    old_s = appt.status
                                    if action == "CONFIRM":
                                        appt.status = "CONFIRMADO"
                                        appt.confirmed = True
                                        appt.canceled = False
                                        db.add(AppointmentHistory(
                                            appointment_id=appt.id,
                                            old_status=old_s,
                                            new_status="CONFIRMADO",
                                            changed_by="WHATSAPP_BOT",
                                            change_reason=f"Confirmado vía WhatsApp ({sender_phone})"
                                        ))
                                        logger.info(f"[WHATSAPP] Turno #{appt.id} confirmado por WhatsApp ({sender_phone})")
                                    elif action == "CANCEL":
                                        appt.status = "CANCELADO"
                                        appt.canceled = True
                                        db.add(AppointmentHistory(
                                            appointment_id=appt.id,
                                            old_status=old_s,
                                            new_status="CANCELADO",
                                            changed_by="WHATSAPP_BOT",
                                            change_reason=f"Cancelado vía WhatsApp ({sender_phone})"
                                        ))
                                        logger.info(f"[WHATSAPP] Turno #{appt.id} cancelado por WhatsApp ({sender_phone})")
                                    db.commit()
                                else:
                                    logger.warning(
                                        f"[SECURITY] Intento no autorizado de acción {action} sobre turno #{appt.id} "
                                        f"desde remitente no verificado ({sender_phone}). Ignorado."
                                    )
    except Exception as e:
        logger.exception(f"Error procesando WhatsApp Webhook: {e}")
    return {"status": "received"}
