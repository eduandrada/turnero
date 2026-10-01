"""
app/api/admin/clients.py - Endpoints de Gestión de Clientes, Ficha CRM y Notas Internas
HiddenSYNC AI 2026
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models import AdminUser, Client, Appointment, Order, AuditLog
from app.schemas import ClientRead, ClientCreate, ClientNotesUpdate
from app.core.dependencies import require_admin_role, require_encargado_or_admin, require_any_staff_role

router = APIRouter(tags=["Admin Clients"])

@router.get("/api/admin/clients", response_model=List[ClientRead])
def get_admin_clients(admin: AdminUser = Depends(require_any_staff_role), db: Session = Depends(get_db)):
    """Directorio general de clientes con métricas de visitas y turnos atendidos."""
    clients = db.query(Client).order_by(Client.id.desc()).all()
    if not clients:
        return []

    # Obtener todas las citas para computar métricas de fidelización y atención
    appts = db.query(Appointment).all()
    appt_map = {}
    for a in appts:
        c_id = a.client_id
        c_phone = (a.client_phone or "").strip()
        st = (a.status or "").upper()
        is_comp = st in ["COMPLETADO", "ATENDIDO", "FINALIZADO"]
        dt_str = a.appointment_time.strftime("%d/%m/%Y") if a.appointment_time else None

        # Indexar por id y por teléfono
        keys = []
        if c_id:
            keys.append(f"id:{c_id}")
        if c_phone:
            keys.append(f"phone:{c_phone}")

        for k in keys:
            if k not in appt_map:
                appt_map[k] = {"total": 0, "completed": 0, "last_visit": None}
            appt_map[k]["total"] += 1
            if is_comp:
                appt_map[k]["completed"] += 1
                if not appt_map[k]["last_visit"]:
                    appt_map[k]["last_visit"] = dt_str

    result = []
    for c in clients:
        k_id = f"id:{c.id}"
        k_phone = f"phone:{(c.phone or '').strip()}"
        metrics = appt_map.get(k_id) or appt_map.get(k_phone) or {"total": 0, "completed": 0, "last_visit": None}
        
        c_dict = {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "notes": getattr(c, "notes", None),
            "is_active": c.is_active,
            "created_at": c.created_at,
            "total_turnos": metrics["total"],
            "turnos_completados": metrics["completed"],
            "ultima_visita": metrics["last_visit"]
        }
        result.append(ClientRead(**c_dict))
    return result

@router.post("/api/admin/clients", response_model=ClientRead)
def create_admin_client(
    client_in: ClientCreate,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Crea manualmente un cliente en el directorio."""
    c = Client(**client_in.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.get("/api/admin/clients/{client_id}/profile")
def get_client_profile(
    client_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Ficha integral CRM del cliente: historial de turnos, barbero habitual, no-shows y pedidos del shop."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    appts = db.query(Appointment).filter(
        or_(Appointment.client_id == client.id, Appointment.client_phone == client.phone)
    ).order_by(Appointment.appointment_time.desc()).all()

    total_turns = len(appts)
    completed_turns = len([a for a in appts if a.status == "COMPLETADO"])
    cancelled_turns = len([a for a in appts if a.status == "CANCELADO" or a.canceled])
    noshow_turns = len([a for a in appts if a.status == "NO_SHOW"])

    barber_counts = {}
    for a in appts:
        if a.barber_name:
            barber_counts[a.barber_name] = barber_counts.get(a.barber_name, 0) + 1
    favorite_barber = max(barber_counts, key=barber_counts.get) if barber_counts else "Sin asignar"

    orders = db.query(Order).filter(
        or_(Order.client_id == client.id, Order.client_phone == client.phone)
    ).order_by(Order.created_at.desc()).all()

    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "email": client.email,
        "notes": getattr(client, "notes", None),
        "total_turnos": total_turns,
        "cumplidos": completed_turns,
        "cancelados": cancelled_turns,
        "no_show": noshow_turns,
        "barbero_habitual": favorite_barber,
        "turnos_recientes": [
            {
                "id": a.id,
                "service": a.service,
                "barber_name": a.barber_name,
                "date": a.appointment_time.strftime("%Y-%m-%d %H:%M"),
                "status": a.status
            }
            for a in appts[:10]
        ],
        "pedidos_shop": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "total": o.total,
                "status": o.status,
                "date": o.created_at.strftime("%Y-%m-%d") if o.created_at else ""
            }
            for o in orders[:5]
        ]
    }

@router.put("/api/admin/clients/{client_id}/notes")
def update_client_notes(
    client_id: int,
    data: ClientNotesUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Actualiza notas internas privadas del cliente (preferencias técnicas, alergias, advertencias)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    client.notes = data.notes
    db.commit()
    return {"status": "success", "message": "Notas internas del cliente actualizadas."}

@router.delete("/api/admin/clients/{client_id}")
@router.delete("/api/clients/{client_id}", deprecated=True)
def delete_admin_client(
    client_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina definitivamente un cliente del directorio resguardando sus turnos y pedidos históricos."""
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    name = c.name
    # Desvincular turnos y pedidos asociados para preservar integridad de BD
    db.query(Appointment).filter(Appointment.client_id == client_id).update({"client_id": None})
    db.query(Order).filter(Order.client_id == client_id).update({"client_id": None})

    db.delete(c)
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        module="Clientes",
        action="Eliminar Cliente",
        record_id=str(client_id),
        old_value=name
    ))
    db.commit()
    return {"message": f"Cliente '{name}' eliminado exitosamente."}
