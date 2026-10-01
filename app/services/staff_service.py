"""
app/services/staff_service.py - Staff, Barbers and Working Schedule Management.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Barber, BarberSchedule, ScheduleException, AuditLog


class StaffService:
    """Service handling barbers, shifts, and special exceptions."""

    @staticmethod
    def list_public_barbers(db: Session) -> List[Barber]:
        """Retorna barberos activos ordenados por display_order (excluyendo teléfonos privados)."""
        return db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).all()

    @staticmethod
    def get_barber_by_id(db: Session, barber_id: int) -> Barber:
        b = db.query(Barber).filter(Barber.id == barber_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Barbero no encontrado.")
        return b


staff_service = StaffService()
