"""
app/api/admin/staff.py - Endpoints de Gestión de Personal, Barberos, Horarios y Bloqueos
HiddenSYNC AI 2026
"""
from datetime import datetime, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models import AdminUser, Barber, Appointment, BarberSchedule, ScheduleException, WaitlistEntry, AuditLog
from app.schemas import (
    StaffUserRead,
    StaffUserCreate,
    StaffUserUpdate,
    StaffPasswordUpdate,
    BarberAdminRead,
    BarberCreate,
    BarberUpdate,
    BarberScheduleItem,
    BarberScheduleBulkUpdate,
    ScheduleExceptionRead,
    ScheduleExceptionCreate,
)
from app.core.security import hash_password
from app.core.dependencies import require_admin_role, require_encargado_or_admin, require_any_staff_role
from app.settings_helper import get_setting
from app.image_service import delete_orphan_file

router = APIRouter(tags=["Admin Staff & Barbers"])

# 1. GESTIÓN DE PERSONAL Y PERMISOS
@router.get("/api/admin/staff", response_model=List[StaffUserRead])
def list_staff_users(
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Lista los usuarios encargados y administradores del sistema."""
    return db.query(AdminUser).all()

@router.post("/api/admin/staff", response_model=StaffUserRead)
def create_staff_user(
    staff_in: StaffUserCreate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Crea un nuevo usuario encargado o administrador."""
    existing = db.query(AdminUser).filter(AdminUser.username == staff_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe.")

    new_user = AdminUser(
        username=staff_in.username,
        password_hash=hash_password(staff_in.password),
        role=staff_in.role,
        is_active=staff_in.is_active,
        can_edit_stock=staff_in.can_edit_stock,
        can_view_finances=staff_in.can_view_finances,
        can_cancel_appointments=staff_in.can_cancel_appointments,
        can_manage_shop=staff_in.can_manage_shop
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    db.add(AuditLog(
        user_name=admin.username,
        module="Gestión de Personal",
        action="Crear Personal",
        record_id=str(new_user.id),
        new_value=f"{new_user.username} ({new_user.role})"
    ))
    db.commit()
    return new_user

@router.put("/api/admin/staff/{user_id}/permissions", response_model=StaffUserRead)
def update_staff_permissions(
    user_id: int,
    staff_in: StaffUserUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza rol, estado activo y switches de permisos de un usuario."""
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    for k, v in staff_in.model_dump(exclude_unset=True).items():
        setattr(target, k, v)

    db.commit()
    db.refresh(target)

    db.add(AuditLog(
        user_name=admin.username,
        module="Gestión de Personal",
        action="Actualizar Permisos",
        record_id=str(target.id),
        new_value=f"Permisos actualizados para {target.username}"
    ))
    db.commit()
    return target

@router.put("/api/admin/staff/{user_id}/password")
def update_staff_password(
    user_id: int,
    data: StaffPasswordUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Cambia la contraseña de un encargado/administrador desde el panel."""
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    target.password_hash = hash_password(data.new_password)
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        module="Gestión de Personal",
        action="Cambiar Contraseña",
        record_id=str(target.id),
        new_value=f"Contraseña modificada para {target.username}"
    ))
    db.commit()
    return {"message": "Contraseña actualizada exitosamente."}

# 2. GESTIÓN DE BARBEROS
@router.get("/api/admin/barbers", response_model=List[BarberAdminRead])
def get_admin_barbers(admin: AdminUser = Depends(require_any_staff_role), db: Session = Depends(get_db)):
    """Lista todos los profesionales de la barbería."""
    return db.query(Barber).order_by(Barber.display_order.asc()).all()

@router.post("/api/admin/barbers", response_model=BarberAdminRead)
def create_admin_barber(
    barber_in: BarberCreate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Crea un nuevo profesional en el sistema."""
    b = Barber(**barber_in.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)

    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Crear Barbero", record_id=str(b.id), new_value=b.name))
    db.commit()
    return b

@router.put("/api/admin/barbers/{barber_id}", response_model=BarberAdminRead)
def update_admin_barber(
    barber_id: int,
    barber_in: BarberUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza datos, horarios o foto de un profesional."""
    b = db.query(Barber).filter(Barber.id == barber_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")

    old_name = b.name
    old_avatar = b.avatar_url
    updates = barber_in.model_dump(exclude_unset=True)

    if "avatar_url" in updates and updates["avatar_url"] != old_avatar and old_avatar:
        delete_orphan_file(old_avatar)

    for k, v in updates.items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)

    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Editar Barbero", record_id=str(b.id), old_value=old_name, new_value=b.name))
    db.commit()
    return b

@router.delete("/api/admin/barbers/{barber_id}")
def delete_admin_barber(
    barber_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina a un profesional y limpia sus archivos huérfanos."""
    b = db.query(Barber).filter(Barber.id == barber_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")

    name = b.name
    old_avatar = b.avatar_url

    # Desvincular y limpiar registros relacionados para no violar constraints en PostgreSQL
    db.query(BarberSchedule).filter(BarberSchedule.barber_id == barber_id).delete(synchronize_session=False)
    db.query(ScheduleException).filter(ScheduleException.barber_id == barber_id).delete(synchronize_session=False)
    db.query(WaitlistEntry).filter(WaitlistEntry.barber_id == barber_id).update({WaitlistEntry.barber_id: None}, synchronize_session=False)
    db.query(Appointment).filter(Appointment.barber_id == barber_id).update({Appointment.barber_id: None}, synchronize_session=False)

    db.delete(b)
    db.commit()

    if old_avatar:
        delete_orphan_file(old_avatar)

    db.add(AuditLog(user_name=admin.username, module="Barberos", action="Eliminar Barbero", record_id=str(barber_id), old_value=name))
    db.commit()
    return {"message": f"Barbero '{name}' eliminado."}

@router.post("/api/admin/barbers/{barber_id}/reassign-turnos")
def reassign_absent_barber_turnos(
    barber_id: int,
    date_str: str = Query(..., description="Fecha YYYY-MM-DD"),
    target_barber_id: Optional[int] = Query(None),
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Reasigna turnos pendientes de un barbero ausente a otro barbero y genera links de aviso por WhatsApp."""
    absent_barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not absent_barber:
        raise HTTPException(status_code=404, detail="Barbero ausente no encontrado.")

    target_barber = None
    if target_barber_id:
        target_barber = db.query(Barber).filter(Barber.id == target_barber_id).first()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Utilice YYYY-MM-DD.")

    start_d = datetime.combine(target_date, time.min)
    end_d = datetime.combine(target_date, time.max)

    appts = db.query(Appointment).filter(
        Appointment.barber_id == barber_id,
        Appointment.appointment_time >= start_d,
        Appointment.appointment_time <= end_d,
        Appointment.status.in_(["PENDIENTE", "CONFIRMADO"])
    ).all()

    affected_list = []
    shop_name = get_setting(db, "barber_name", "Turnero")

    for a in appts:
        old_bname = a.barber_name
        if target_barber:
            a.barber_id = target_barber.id
            a.barber_name = target_barber.name
            new_bname = target_barber.name
            msg = f"Hola {a.client_name}, te informamos desde {shop_name} que tu turno del {target_date.strftime('%d/%m')} a las {a.appointment_time.strftime('%H:%M')} hs ha sido reasignado al profesional {new_bname}. ¡Te esperamos!"
        else:
            new_bname = "Sin asignar"
            msg = f"Hola {a.client_name}, te contactamos desde {shop_name} para reprogramar tu turno del {target_date.strftime('%d/%m')} a las {a.appointment_time.strftime('%H:%M')} hs por imprevisto de tu barbero. ¡Escribinos!"

        clean_phone = "".join(filter(str.isdigit, a.client_phone))
        affected_list.append({
            "appointment_id": a.id,
            "client_name": a.client_name,
            "client_phone": a.client_phone,
            "time": a.appointment_time.strftime("%H:%M"),
            "old_barber": old_bname,
            "new_barber": new_bname,
            "wa_message": msg,
            "wa_url": f"https://wa.me/{clean_phone}?text={msg.replace(' ', '%20')}"
        })

    db.commit()
    return {
        "status": "success",
        "count": len(appts),
        "reassigned_to": target_barber.name if target_barber else None,
        "affected_appointments": affected_list
    }

# 3. HORARIOS BASE POR BARBERO Y EXCEPCIONES
@router.get("/api/admin/schedules/barbers/{barber_id}", response_model=List[BarberScheduleItem])
def get_barber_schedules(
    barber_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Obtiene la configuración semanal de horarios del barbero (0=Lunes, 6=Domingo)."""
    schedules = db.query(BarberSchedule).filter(BarberSchedule.barber_id == barber_id).all()
    sched_map = {s.day_of_week: s for s in schedules}
    result = []
    for d in range(7):
        if d in sched_map:
            s = sched_map[d]
            result.append(BarberScheduleItem(
                day_of_week=d,
                is_working=s.is_working,
                start_time_1=s.start_time_1,
                end_time_1=s.end_time_1,
                start_time_2=s.start_time_2,
                end_time_2=s.end_time_2
            ))
        else:
            result.append(BarberScheduleItem(
                day_of_week=d,
                is_working=True if d < 6 else False,
                start_time_1="09:00",
                end_time_1="13:00",
                start_time_2="16:00",
                end_time_2="21:00"
            ))
    return result

@router.post("/api/admin/schedules/barbers/{barber_id}", response_model=dict)
def update_barber_schedules(
    barber_id: int,
    data: BarberScheduleBulkUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Actualiza o crea la grilla de disponibilidad semanal para un barbero."""
    b = db.query(Barber).filter(Barber.id == barber_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")

    for item in data.schedules:
        s = db.query(BarberSchedule).filter(
            BarberSchedule.barber_id == barber_id,
            BarberSchedule.day_of_week == item.day_of_week
        ).first()
        if not s:
            s = BarberSchedule(barber_id=barber_id, day_of_week=item.day_of_week)
            db.add(s)
        s.is_working = item.is_working
        s.start_time_1 = item.start_time_1
        s.end_time_1 = item.end_time_1
        s.start_time_2 = item.start_time_2
        s.end_time_2 = item.end_time_2

    db.commit()
    db.add(AuditLog(
        user_name=admin.username,
        module="Disponibilidad",
        action="Actualizar Horarios Barbero",
        record_id=str(barber_id),
        new_value=f"Horarios actualizados para {b.name}"
    ))
    db.commit()
    return {"status": "success", "message": f"Horarios de {b.name} actualizados exitosamente."}

@router.get("/api/admin/schedules/exceptions", response_model=List[ScheduleExceptionRead])
def list_schedule_exceptions(
    barber_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Lista las excepciones, licencias o feriados registrados."""
    query = db.query(ScheduleException)
    if barber_id:
        query = query.filter(or_(ScheduleException.barber_id == barber_id, ScheduleException.barber_id.is_(None)))
    return query.order_by(ScheduleException.date.asc()).all()

@router.post("/api/admin/schedules/exceptions", response_model=ScheduleExceptionRead)
def create_schedule_exception(
    data: ScheduleExceptionCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Crea una excepción de horario, feriado o bloqueo para uno o todos los barberos."""
    exc = ScheduleException(
        barber_id=data.barber_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
        exception_type=data.exception_type
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    db.add(AuditLog(
        user_name=admin.username,
        module="Disponibilidad",
        action="Crear Bloqueo/Feriado",
        record_id=str(exc.id),
        new_value=f"{exc.exception_type} el {exc.date}: {exc.reason}"
    ))
    db.commit()
    return exc

@router.delete("/api/admin/schedules/exceptions/{exception_id}")
def delete_schedule_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Elimina una excepción o bloqueo programado."""
    exc = db.query(ScheduleException).filter(ScheduleException.id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Excepción o bloqueo no encontrado.")
    db.delete(exc)
    db.commit()
    return {"status": "success", "message": "Bloqueo eliminado correctamente."}


# 5. LÍMITES Y CONFIGURACIÓN ROL ENCARGADO (GESTION.HTML)
@router.get("/api/encargado/limits")
def get_encargado_limits(
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Retorna los límites actuales y la cuota consumida hoy para el operador o encargado."""
    from app.core.database import get_argentina_now
    from app.models import Service, Style, Client
    from app.settings_helper import set_setting

    is_admin = (current_user.role == "admin")
    
    max_appts = int(get_setting(db, "encargado_max_appointments_per_day", "6"))
    max_clients = int(get_setting(db, "encargado_max_clients_per_day", "6"))
    max_services = int(get_setting(db, "encargado_max_services", "3"))
    max_styles = int(get_setting(db, "encargado_max_styles", "3"))
    allow_full_admin = get_setting(db, "encargado_allow_full_admin", "false").lower() == "true"

    now_ar = get_argentina_now()
    start_today = datetime.combine(now_ar.date(), time.min)
    end_today = datetime.combine(now_ar.date(), time.max)

    today_appts = db.query(Appointment).filter(
        Appointment.appointment_time >= start_today,
        Appointment.appointment_time <= end_today
    ).count()
    today_clients = db.query(Appointment).filter(
        Appointment.appointment_time >= start_today,
        Appointment.appointment_time <= end_today,
        Appointment.status.in_(["atendiendo", "atendido", "confirmado", "COMPLETADO", "CONFIRMADO"])
    ).count()
    if today_clients == 0:
        today_clients = db.query(Client).count()
        today_clients = min(today_clients, today_appts or today_clients)

    current_services = db.query(Service).count()
    current_styles = db.query(Style).count()

    return {
        "username": current_user.username,
        "role": current_user.role,
        "is_master_admin": is_admin,
        "allow_full_admin": allow_full_admin or is_admin,
        "limits": {
            "max_appointments_per_day": 9999 if (is_admin or allow_full_admin) else max_appts,
            "today_appointments_count": today_appts,
            "max_clients_per_day": 9999 if (is_admin or allow_full_admin) else max_clients,
            "today_clients_count": today_clients,
            "max_services": 9999 if (is_admin or allow_full_admin) else max_services,
            "current_services_count": current_services,
            "max_styles": 9999 if (is_admin or allow_full_admin) else max_styles,
            "current_styles_count": current_styles,
        }
    }


@router.get("/api/admin/encargado-settings")
def get_admin_encargado_settings(
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Retorna la configuración de cuotas y permisos del rol Encargado."""
    return {
        "encargado_max_appointments_per_day": int(get_setting(db, "encargado_max_appointments_per_day", "6")),
        "encargado_max_clients_per_day": int(get_setting(db, "encargado_max_clients_per_day", "6")),
        "encargado_max_services": int(get_setting(db, "encargado_max_services", "3")),
        "encargado_max_styles": int(get_setting(db, "encargado_max_styles", "3")),
        "encargado_allow_full_admin": get_setting(db, "encargado_allow_full_admin", "false").lower() == "true"
    }


@router.post("/api/admin/encargado-settings")
def update_admin_encargado_settings(
    payload: dict,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza la configuración de cuotas y permisos del rol Encargado (Llave Maestra)."""
    from app.settings_helper import set_setting

    if "encargado_max_appointments_per_day" in payload:
        set_setting(db, "encargado_max_appointments_per_day", str(payload["encargado_max_appointments_per_day"]))
    if "encargado_max_clients_per_day" in payload:
        set_setting(db, "encargado_max_clients_per_day", str(payload["encargado_max_clients_per_day"]))
    if "encargado_max_services" in payload:
        set_setting(db, "encargado_max_services", str(payload["encargado_max_services"]))
    if "encargado_max_styles" in payload:
        set_setting(db, "encargado_max_styles", str(payload["encargado_max_styles"]))
    if "encargado_allow_full_admin" in payload:
        set_setting(db, "encargado_allow_full_admin", "true" if payload["encargado_allow_full_admin"] else "false")

    db.add(AuditLog(
        user_name=admin.username,
        module="Configuración",
        action="Actualizar Cuotas Encargado",
        record_id="encargado_limits",
        new_value=str(payload)
    ))
    db.commit()

    return {"status": "success", "message": "Configuración de límites de Encargado actualizada."}


@router.get("/api/admin/staff/fichajes")
def get_staff_fichajes_history(
    user_name: Optional[str] = Query(None),
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Retorna la auditoría detallada de horarios de ingreso y salida del personal/encargados."""
    query = db.query(AuditLog).filter(
        AuditLog.action.in_(["FICHAJE_INGRESO", "FICHAJE_SALIDA", "LOGIN_EXITOSO", "LOGOUT"])
    )
    if user_name:
        query = query.filter(AuditLog.user_name == user_name)
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    
    result = []
    for l in logs:
        action_type = "INGRESO" if ("INGRESO" in l.action or "LOGIN" in l.action) else "SALIDA"
        result.append({
            "id": l.id,
            "username": l.user_name or l.actor,
            "action": l.action,
            "action_type": action_type,
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "-",
            "time_art": l.timestamp.strftime("%H:%M:%S ART") if l.timestamp else "-",
            "date_art": l.timestamp.strftime("%d/%m/%Y") if l.timestamp else "-",
            "description": l.description,
            "ip_address": l.ip_address or "-"
        })
    return result


