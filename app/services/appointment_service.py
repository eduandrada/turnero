"""
app/services/appointment_service.py - Core appointment lifecycle management.
Handles transactional creation with concurrency lock (BEGIN IMMEDIATE), collision validation,
snapshots (barber_name, service, service_price), status transitions, audit history, and notifications.
"""
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from fastapi import HTTPException

from app.core.database import engine, get_argentina_now
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import audit_logger, app_logger
from app.models import (
    Appointment,
    AppointmentHistory,
    AuditLog,
    Barber,
    Service,
    Client,
    IdempotencyRecord
)
from app.utils import normalize_phone
from app.services.whatsapp_service import send_appointment_whatsapp_notifications

logger = app_logger

# Cerrojo global en memoria para serializar reservas concurrentes
APPOINTMENT_LOCK = threading.Lock()


class AppointmentService:
    """Encapsulates all appointment business rules, concurrency safeguards, and history."""

    @staticmethod
    def create_appointment(
        db: Session,
        client_name: str,
        client_phone: str,
        appointment_time: datetime,
        barber_id: Optional[int] = None,
        barber_name: Optional[str] = None,
        service_id: Optional[int] = None,
        service: Optional[str] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        request_path: str = "/api/appointments"
    ) -> Dict[str, Any]:
        """
        Crea un nuevo turno de forma atómica y segura contra colisiones:
        1. Normaliza teléfono.
        2. Bloquea concurrencia con APPOINTMENT_LOCK y BEGIN IMMEDIATE.
        3. Verifica solapamiento de horarios con turnos activos.
        4. Resuelve o crea registro de cliente.
        5. Guarda snapshots históricos (nombre del barbero, nombre del servicio, precio del servicio).
        6. Registra entrada en historial inmutable de estados.
        7. Despacha notificaciones de WhatsApp asíncronas / seguras.
        """
        # 1. Normalizar y validar teléfono
        normalized_phone = normalize_phone(client_phone)

        now_arg = get_argentina_now().replace(tzinfo=None)
        appt_time_naive = appointment_time.replace(tzinfo=None)
        if appt_time_naive < now_arg:
            raise HTTPException(status_code=400, detail="No es posible reservar en fechas u horarios transcurridos.")

        # Resolver barbero
        barber_obj = None
        if barber_id:
            barber_obj = db.query(Barber).filter(Barber.id == barber_id).first()
        elif barber_name:
            barber_obj = db.query(Barber).filter(Barber.name.ilike(f"%{barber_name}%")).first()

        resolved_b_name = barber_obj.name if barber_obj else (barber_name or "Misael Fade")
        resolved_b_id = barber_obj.id if barber_obj else 1

        # Resolver servicio
        service_obj = None
        if service_id:
            service_obj = db.query(Service).filter(Service.id == service_id).first()
        elif service:
            service_obj = db.query(Service).filter(Service.name.ilike(f"%{service}%")).first()

        resolved_s_name = service_obj.name if service_obj else (service or "Corte Signature Fade")
        resolved_s_id = service_obj.id if service_obj else 1
        duration_min = service_obj.duration_min if service_obj else 45
        service_price = service_obj.price if service_obj else 0.0

        slot_start = appt_time_naive
        slot_end = slot_start + timedelta(minutes=duration_min)

        # 2. Concurrencia atómica
        with APPOINTMENT_LOCK:
            try:
                if str(engine.url).startswith("sqlite"):
                    db.execute(text("BEGIN IMMEDIATE"))
            except Exception:
                pass

            existing = db.query(Appointment).filter(
                Appointment.canceled == False,
                Appointment.status != "CANCELADO",
                or_(
                    Appointment.barber_id == resolved_b_id,
                    Appointment.barber_name == resolved_b_name
                )
            ).all()

            for ex in existing:
                ex_start = ex.appointment_time
                ex_dur = ex.duration_min or 45
                ex_end = ex.end_time or (ex_start + timedelta(minutes=ex_dur))

                if slot_start < ex_end and slot_end > ex_start:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail="El horario seleccionado ya se encuentra ocupado. Por favor elige otro horario."
                    )

            # Buscar o crear cliente
            client_obj = db.query(Client).filter(Client.phone == normalized_phone).first()
            if not client_obj:
                client_obj = Client(
                    name=client_name,
                    phone=normalized_phone,
                    is_active=True
                )
                db.add(client_obj)
                db.commit()
                db.refresh(client_obj)

            import random
            checkin_pin = f"{random.randint(1000, 9999)}"

            new_appt = Appointment(
                client_id=client_obj.id if client_obj else None,
                client_name=client_name,
                client_phone=normalized_phone,
                barber_id=resolved_b_id,
                barber_name=resolved_b_name,
                service_id=resolved_s_id,
                service=resolved_s_name,
                service_price_snapshot=service_price,
                appointment_time=slot_start,
                end_time=slot_end,
                duration_min=duration_min,
                status="PENDIENTE",
                confirmed=False,
                canceled=False,
                reminder_sent=False,
                checkin_token=checkin_pin,
                is_checked_in=False,
                idempotency_key=idempotency_key,
                notes=notes
            )
            db.add(new_appt)
            db.commit()
            db.refresh(new_appt)

            # Registrar historial
            db.add(AppointmentHistory(
                appointment_id=new_appt.id,
                old_status=None,
                new_status="PENDIENTE",
                changed_by="CLIENTE",
                change_reason="Reserva web pública inicial"
            ))
            db.commit()

            # Disparar notificaciones WhatsApp
            send_appointment_whatsapp_notifications(db, new_appt)

        logger.info(f"Turno #{new_appt.id} creado para {new_appt.client_name} ({slot_start}) - PIN: {new_appt.checkin_token}")
        return {
            "id": new_appt.id,
            "checkin_pin": new_appt.checkin_token,
            "checkin_token": new_appt.checkin_token,
            "client_name": new_appt.client_name,
            "client_phone": new_appt.client_phone,
            "barber_name": new_appt.barber_name,
            "service": new_appt.service,
            "appointment_time": new_appt.appointment_time.isoformat(),
            "status": new_appt.status,
            "duration_min": new_appt.duration_min
        }

    @staticmethod
    def update_status(
        db: Session,
        appointment_id: int,
        new_status: str,
        actor: str = "Admin",
        reason: Optional[str] = None
    ) -> Appointment:
        """Actualiza el estado de un turno registrando historial y banderas de confirmación/cancelación."""
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Turno no encontrado.")

        old_status = appt.status
        st = new_status.upper().strip()
        appt.status = st

        if st == "CANCELADO":
            appt.canceled = True
            appt.confirmed = False
        elif st in ["CONFIRMADO", "COMPLETADO", "EN_ATENCION", "EN_SILLA", "LLAMANDO"]:
            appt.canceled = False
            appt.confirmed = True
        elif st == "PENDIENTE":
            appt.canceled = False
            appt.confirmed = False

        db.commit()
        db.refresh(appt)

        if old_status != st:
            db.add(AppointmentHistory(
                appointment_id=appt.id,
                previous_status=old_status,
                new_status=st,
                changed_by=actor,
                change_reason=reason or f"Estado actualizado a {st}"
            ))
            db.add(AuditLog(
                user_name=actor,
                actor=actor,
                module="Turnos",
                action="Actualizar Estado",
                record_id=str(appt.id),
                old_value=f"Estado: {old_status}",
                new_value=f"Estado: {st}",
                description=f"Turno #{appt.id} ({appt.client_name}) actualizado a {st}"
            ))
            db.commit()

        return appt

    @staticmethod
    def cancel_appointment(db: Session, appointment_id: int, actor: str = "Cliente", reason: str = "Cancelación voluntaria") -> Appointment:
        return AppointmentService.update_status(db, appointment_id, "CANCELADO", actor=actor, reason=reason)

    @staticmethod
    def confirm_appointment(db: Session, appointment_id: int, actor: str = "Cliente", reason: str = "Confirmado") -> Appointment:
        return AppointmentService.update_status(db, appointment_id, "CONFIRMADO", actor=actor, reason=reason)

    @staticmethod
    def mark_no_show(db: Session, appointment_id: int, actor: str = "Admin", reason: str = "Cliente no asistió") -> Appointment:
        return AppointmentService.update_status(db, appointment_id, "NO_SHOW", actor=actor, reason=reason)


appointment_service = AppointmentService()
