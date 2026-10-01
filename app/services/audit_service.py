"""
app/services/audit_service.py - Centralized Audit Logging & Idempotency Service.
Provides persistent audit trail recording for security-sensitive and transactional actions.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.database import get_argentina_now
from app.core.logging import audit_logger
from app.models import AuditLog, IdempotencyRecord

logger = audit_logger


class AuditService:
    """Service for registering and reading security and operational audit logs."""

    @staticmethod
    def log(
        db: Session,
        user_name: str,
        module: str,
        action: str,
        description: Optional[str] = None,
        record_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None,
        actor: Optional[str] = None
    ) -> AuditLog:
        """Registra un evento de auditoría en la base de datos de manera uniforme."""
        log_entry = AuditLog(
            user_name=user_name,
            actor=actor or user_name,
            module=module,
            action=action,
            description=description,
            record_id=str(record_id) if record_id is not None else None,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address
        )
        db.add(log_entry)
        try:
            db.commit()
            db.refresh(log_entry)
        except Exception as e:
            logger.error(f"Fallo al registrar entrada de auditoría: {e}")
            db.rollback()
        return log_entry

    @staticmethod
    def get_idempotency_response(db: Session, key: str) -> Optional[Dict[str, Any]]:
        """Verifica si existe una respuesta idempotente válida en caché para esta clave."""
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == key,
            IdempotencyRecord.expires_at > get_argentina_now()
        ).first()
        if record and record.response_json:
            try:
                return json.loads(record.response_json)
            except Exception:
                return None
        return None

    @staticmethod
    def store_idempotency_response(
        db: Session,
        key: str,
        scope: str,
        response_data: Dict[str, Any],
        expire_hours: int = 24
    ) -> None:
        """Guarda la respuesta de una operación para garantizar idempotencia en reintentos."""
        try:
            record = IdempotencyRecord(
                idempotency_key=key,
                scope=scope,
                response_json=json.dumps(response_data, default=str),
                expires_at=get_argentina_now() + timedelta(hours=expire_hours)
            )
            db.add(record)
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo guardar registro de idempotencia: {e}")
            db.rollback()


audit_service = AuditService()
