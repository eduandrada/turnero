"""
app/services/service_catalog.py - Service Catalog and Haircut Styles Management.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Service, Style


class ServiceCatalogService:
    """Service managing barber service catalog and hairstyle gallery."""

    @staticmethod
    def list_public_services(db: Session) -> List[Service]:
        """Retorna servicios activos ordenados por display_order."""
        return db.query(Service).filter(Service.is_active == True).order_by(Service.display_order.asc()).all()

    @staticmethod
    def get_service_by_id(db: Session, service_id: int) -> Service:
        s = db.query(Service).filter(Service.id == service_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Servicio no encontrado.")
        return s

    @staticmethod
    def list_styles(db: Session) -> List[Style]:
        return db.query(Style).filter(Style.is_active == True).order_by(Style.display_order.asc()).all()


service_catalog_service = ServiceCatalogService()
