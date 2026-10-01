"""
app/api/appointments.py - Endpoints Públicos de Turnos
HiddenSYNC AI 2026
"""
import json
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import IdempotencyRecord
from app.schemas import AppointmentCreate
from app.settings_helper import get_setting
from app.rate_limiter import check_rate_limit
from app.services.appointment_service import appointment_service

logger = logging.getLogger("hiddensync.appointments")

router = APIRouter(tags=["Appointments"])

@router.post("/api/appointments", response_model=dict)
def create_public_appointment(request: Request, data: AppointmentCreate, db: Session = Depends(get_db)):
    """Crea un nuevo turno verificando disponibilidad en tiempo real, idempotencia y rate limiting."""
    # 1. Rate Limiting de reservas
    check_rate_limit(request, "appointments", max_requests=20, window_seconds=60)

    # 2. Idempotencia: Verificar si esta solicitud ya fue procesada
    idem_key = request.headers.get("X-Idempotency-Key") or data.idempotency_key
    if idem_key:
        cached = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idem_key,
            IdempotencyRecord.expires_at > get_argentina_now().replace(tzinfo=None)
        ).first()
        if cached:
            logger.info(f"[IDEMPOTENCY] Turno repetido con clave '{idem_key}'. Retornando respuesta en caché.")
            return json.loads(cached.response_json)

    # 3. Delegar al servicio central de turnos
    appt_data = appointment_service.create_appointment(
        db=db,
        client_name=data.client_name,
        client_phone=data.client_phone,
        appointment_time=data.appointment_time,
        barber_id=data.barber_id,
        barber_name=data.barber_name,
        service_id=data.service_id,
        service=data.service,
        extras_ids=data.extras_ids,
        extras=data.extras,
        notes=data.notes,
        idempotency_key=idem_key
    )

    response_payload = {
        "status": "success",
        "message": get_setting(db, "msg_success", "Turno reservado exitosamente."),
        "appointment": appt_data
    }

    # 4. Guardar registro de idempotencia si se proveyó clave
    if idem_key:
        try:
            db.add(IdempotencyRecord(
                idempotency_key=idem_key,
                response_json=json.dumps(response_payload),
                request_path="/api/appointments",
                expires_at=get_argentina_now().replace(tzinfo=None) + timedelta(hours=24)
            ))
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo guardar registro de idempotencia: {e}")
            db.rollback()

    return response_payload
