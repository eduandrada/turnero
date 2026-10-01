"""
app/api/admin/appointments.py - Endpoints de Gestión Administrativa de Turnos y Lista de Espera
HiddenSYNC AI 2026
"""
import logging
from datetime import datetime, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models import AdminUser, Appointment, Barber, AppointmentHistory, AuditLog, WaitlistEntry
from app.schemas import AppointmentRead, AppointmentUpdate, WaitlistEntryRead
from app.core.dependencies import require_admin_role, require_encargado_or_admin, require_any_staff_role

logger = logging.getLogger("hiddensync.admin.appointments")

router = APIRouter(tags=["Admin Appointments"])

from datetime import datetime, time, timedelta

@router.get("/api/admin/appointments", response_model=List[AppointmentRead])
def get_admin_appointments(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_preset: Optional[str] = None,
    barber_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 500,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """Consulta de turnos con filtros avanzados por fecha, rango, profesional y estado."""
    # Resolver presets si no se proporcionó fecha explícita
    if not date and date_preset:
        dp = date_preset.strip().lower()
        now = datetime.now()
        if dp == "today":
            date = now.strftime("%Y-%m-%d")
        elif dp == "tomorrow":
            date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    query = db.query(Appointment)
    if date:
        try:
            t_date = datetime.strptime(date, "%Y-%m-%d").date()
            s_day = datetime.combine(t_date, time.min)
            e_day = datetime.combine(t_date, time.max)
            query = query.filter(Appointment.appointment_time >= s_day, Appointment.appointment_time <= e_day)
            query = query.order_by(Appointment.appointment_time.asc())
        except ValueError:
            query = query.order_by(Appointment.appointment_time.desc())
    elif start_date and end_date:
        try:
            s_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_d = datetime.strptime(end_date, "%Y-%m-%d").date()
            s_day = datetime.combine(s_d, time.min)
            e_day = datetime.combine(e_d, time.max)
            query = query.filter(Appointment.appointment_time >= s_day, Appointment.appointment_time <= e_day)
            query = query.order_by(Appointment.appointment_time.desc())
        except ValueError:
            query = query.order_by(Appointment.appointment_time.desc())
    else:
        query = query.order_by(Appointment.appointment_time.desc())

    user_role = (admin.role or "").strip().lower()
    if user_role == "barbero":
        matched_b = db.query(Barber).filter(Barber.name.ilike(f"%{admin.username}%")).first()
        target_b_id = matched_b.id if matched_b else -1
        query = query.filter(Appointment.barber_id == target_b_id)
    elif barber_id:
        query = query.filter(Appointment.barber_id == barber_id)

    if status:
        st = status.strip().lower()
        if st in ["activos", "active", "pendientes_atencion"]:
            query = query.filter(
                Appointment.status.in_(["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"]),
                Appointment.canceled == False
            )
        elif st in ["completados", "completed", "atendidos"]:
            query = query.filter(Appointment.status.in_(["COMPLETADO", "ATENDIDO", "FINALIZADO"]))
        elif st in ["cancelados", "canceled"]:
            query = query.filter(or_(Appointment.status.in_(["CANCELADO", "NO_SHOW"]), Appointment.canceled == True))
        elif st not in ["todos", "all", ""]:
            query = query.filter(Appointment.status == status.upper())

    return query.limit(limit).all()

@router.put("/api/admin/appointments/{appointment_id}", response_model=AppointmentRead)
@router.put("/api/admin/appointments/{appointment_id}/status", response_model=AppointmentRead)
@router.post("/api/admin/appointments/{appointment_id}/status", response_model=AppointmentRead)
def update_admin_appointment(
    appointment_id: int,
    appt_in: AppointmentUpdate,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """Actualización integral de datos, horario y estado del turno."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    user_role = (admin.role or "").strip().lower()
    if user_role == "barbero":
        matched_b = db.query(Barber).filter(Barber.name.ilike(f"%{admin.username}%")).first()
        if not matched_b or appt.barber_id != matched_b.id:
            raise HTTPException(status_code=403, detail="Un barbero solo puede gestionar sus propios turnos.")

    old_status = appt.status or "PENDIENTE"
    for k, v in appt_in.model_dump(exclude_unset=True).items():
        setattr(appt, k, v)

    # Sincronización robusta de estados y banderas booleanas
    if appt_in.status:
        st = appt_in.status.upper().strip()
        appt.status = st
        if st == "CANCELADO":
            appt.canceled = True
            appt.confirmed = False
        elif st == "COMPLETADO":
            appt.canceled = False
            appt.confirmed = True
            # Barber Club: Acreditar puntos automáticamente por el servicio
            from app.api.loyalty import credit_client_loyalty_points
            amount = appt.service_price_snapshot or (appt.service_rel.price if appt.service_rel else 0.0)
            if amount > 0 and appt.client_phone:
                credit_client_loyalty_points(
                    db,
                    client_phone=appt.client_phone,
                    amount=amount,
                    reason=f"Corte/Servicio: {appt.service or 'Barbería'}",
                    reference_id=str(appt.id)
                )

        elif st in ["CONFIRMADO", "EN_SILLA", "EN_ATENCION"]:
            appt.canceled = False
            appt.confirmed = True
        elif st == "PENDIENTE":
            appt.canceled = False
            appt.confirmed = False

    db.commit()
    db.refresh(appt)

    # Registro en historial de auditoría de turnos
    if appt.status != old_status:
        try:
            db.add(AppointmentHistory(
                appointment_id=appt.id,
                previous_status=old_status,
                new_status=appt.status,
                changed_by=admin.username,
                change_reason=appt_in.notes or f"Estado cambiado a {appt.status}"
            ))
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar historial de turno: {e}")

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Turnos",
        action="Actualizar Turno",
        record_id=str(appt.id),
        old_value=f"Estado: {old_status}",
        new_value=f"Estado: {appt.status}",
        description=f"Turno #{appt.id} ({appt.client_name}) actualizado a {appt.status}"
    ))
    db.commit()
    return appt

@router.delete("/api/admin/appointments/{appointment_id}")
def delete_admin_appointment(
    appointment_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina definitivamente un turno del sistema."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    db.delete(appt)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Turnos", action="Eliminar Turno", record_id=str(appointment_id)))
    db.commit()
    return {"message": "Turno eliminado correctamente."}

@router.get("/api/admin/waitlist", response_model=List[WaitlistEntryRead])
def list_admin_waitlist(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Lista las entradas registradas en la lista de espera."""
    query = db.query(WaitlistEntry)
    if status:
        query = query.filter(WaitlistEntry.status == status)
    return query.order_by(WaitlistEntry.created_at.desc()).all()

@router.delete("/api/admin/waitlist/{entry_id}")
def delete_waitlist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Elimina una entrada de la lista de espera."""
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada en lista de espera.")
    db.delete(entry)
    db.commit()
    return {"status": "success", "message": "Entrada eliminada de la lista de espera."}
