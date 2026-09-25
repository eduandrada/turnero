import os
import logging
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_argentina_now
from app.models import Appointment

logger = logging.getLogger("bladesync.scheduler")
logging.basicConfig(level=logging.INFO)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_CLOUD_API_TOKEN", "EAAG_MOCK_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "109876543210")
WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
except ImportError:
    scheduler = None
    logger.warning("apscheduler no está instalado. El planificador de recordatorios por WhatsApp estará en modo manual.")

async def send_whatsapp_interactive_reminder(
    phone: str,
    appointment_id: int,
    client_name: str,
    service: str,
    app_time: datetime
) -> bool:
    """
    Envía un mensaje interactivo con botones de Confirmar / Cancelar
    a través de WhatsApp Cloud API (Meta Graph API).
    """
    formatted_time = app_time.strftime("%H:%M hs")
    formatted_date = app_time.strftime("%d/%m")

    clean_phone = "".join(filter(str.isdigit, phone))

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": "💈 Barbería // Recordatorio"
            },
            "body": {
                "text": (
                    f"¡Hola *{client_name}*! Te recordamos tu cita para *{service}* "
                    f"el día *{formatted_date}* a las *{formatted_time}*.\n\n"
                    f"Por favor confirma o cancela tu turno."
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"CONFIRM_{appointment_id}",
                            "title": "✅ Confirmar"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"CANCEL_{appointment_id}",
                            "title": "❌ Cancelar"
                        }
                    }
                ]
            }
        }
    }

    if not WHATSAPP_TOKEN or WHATSAPP_TOKEN.startswith("EAAG_MOCK") or WHATSAPP_TOKEN == "your_whatsapp_permanent_or_temp_token_here":
        logger.info(
            f"[MOCK WHATSAPP NOTIFICATION] A {clean_phone} para Turno #{appointment_id} "
            f"({client_name} - {service} a las {formatted_time})."
        )
        return True

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(WHATSAPP_API_URL, json=payload, headers=headers)
            if response.status_code in (200, 201):
                logger.info(f"WhatsApp Cloud API enviado a {clean_phone} para cita #{appointment_id}")
                return True
            else:
                logger.error(f"WhatsApp API Error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.exception(f"Excepción al conectar con WhatsApp Cloud API: {e}")
        return False


async def check_upcoming_appointments():
    """
    Cron Job ejecutado cada 5 minutos.
    Busca citas programadas entre [now] y [now + 2h] que aún no hayan recibido recordatorio.
    """
    logger.info("Verificando citas próximas para envío de recordatorios...")
    db: Session = SessionLocal()
    try:
        now = get_argentina_now().replace(tzinfo=None)
        window_end = now + timedelta(hours=2, minutes=5)

        appointments = db.query(Appointment).filter(
            Appointment.appointment_time >= now,
            Appointment.appointment_time <= window_end,
            Appointment.reminder_sent == False,
            Appointment.canceled == False
        ).all()

        for appt in appointments:
            service_title = appt.service or (appt.service_rel.name if appt.service_rel else "Servicio de Barbería")
            success = await send_whatsapp_interactive_reminder(
                phone=appt.client_phone,
                appointment_id=appt.id,
                client_name=appt.client_name,
                service=service_title,
                app_time=appt.appointment_time
            )
            if success:
                appt.reminder_sent = True
                db.commit()
    except Exception as e:
        logger.exception(f"Error en check_upcoming_appointments: {e}")
    finally:
        db.close()


def start_scheduler():
    """Inicializa el planificador si está disponible."""
    if scheduler and not scheduler.running:
        scheduler.add_job(
            check_upcoming_appointments,
            "interval",
            minutes=5,
            id="whatsapp_reminder_job",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler iniciado correctamente.")


def shutdown_scheduler():
    """Detiene el planificador si está en ejecución."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler detenido.")
