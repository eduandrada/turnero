"""
app/services/client_service.py - Client entity and CRM management.
Handles client deduplication by normalized phone number, full profile calculation
(attendance, cancellations, no-show rate, favorite barber), and notes management.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException

from app.models import Client, Appointment, Order
from app.utils import normalize_phone


class ClientService:
    """Manages customer profiles, loyalty history, and CRM notes."""

    @staticmethod
    def get_or_create(db: Session, name: str, phone: str, email: Optional[str] = None) -> Client:
        """Busca un cliente por su teléfono normalizado o crea uno nuevo."""
        norm_phone = normalize_phone(phone)
        client = db.query(Client).filter(Client.phone == norm_phone).first()
        if not client:
            client = Client(
                name=name.strip(),
                phone=norm_phone,
                email=email.strip() if email else None,
                is_active=True
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        return client

    @staticmethod
    def get_client_profile(db: Session, client_id: int) -> Dict[str, Any]:
        """Calcula el perfil CRM del cliente con estadísticas de asistencia y pedidos."""
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

    @staticmethod
    def update_client_notes(db: Session, client_id: int, notes: str) -> Client:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        client.notes = notes
        db.commit()
        db.refresh(client)
        return client


client_service = ClientService()
