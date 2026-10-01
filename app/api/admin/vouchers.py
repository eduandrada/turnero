"""
app/api/admin/vouchers.py - Endpoints de Gestión y Auditoría de Cupones / Vouchers
HiddenSYNC AI 2026
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser, Voucher, VoucherRedemption, AuditLog
from app.schemas import VoucherRead, VoucherCreate
from app.core.dependencies import require_encargado_or_admin

router = APIRouter(tags=["Admin Vouchers"])

@router.get("/api/admin/vouchers", response_model=List[VoucherRead])
def list_admin_vouchers(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Lista todos los cupones configurados en el sistema."""
    return db.query(Voucher).order_by(Voucher.created_at.desc()).all()

@router.post("/api/admin/vouchers", response_model=VoucherRead)
def create_admin_voucher(
    data: VoucherCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Crea una nueva regla promocional o cupón de descuento."""
    code_clean = data.code.strip().upper()
    existing = db.query(Voucher).filter(Voucher.code == code_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un cupón con el código '{code_clean}'.")

    voucher = Voucher(
        code=code_clean,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        max_discount_amount=data.max_discount_amount,
        scope=data.scope,
        commission_impact=data.commission_impact,
        min_ticket_amount=data.min_ticket_amount,
        start_date=data.start_date,
        end_date=data.end_date,
        allowed_days=data.allowed_days,
        allowed_start_time=data.allowed_start_time,
        allowed_end_time=data.allowed_end_time,
        max_total_uses=data.max_total_uses,
        max_uses_per_client=data.max_uses_per_client,
        required_role=data.required_role,
        is_active=data.is_active,
        description=data.description
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)

    db.add(AuditLog(
        user_name=admin.username,
        module="Vouchers",
        action="Crear Cupón",
        record_id=str(voucher.id),
        new_value=f"Cupón {voucher.code}: {voucher.discount_type} {voucher.discount_value}"
    ))
    db.commit()
    return voucher

@router.delete("/api/admin/vouchers/{voucher_id}")
def delete_admin_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Desactiva un cupón (borrado lógico)."""
    v = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Cupón no encontrado.")
    v.is_active = False
    db.commit()
    return {"status": "success", "message": f"Cupón '{v.code}' desactivado."}

@router.get("/api/admin/vouchers/redemptions")
def list_voucher_redemptions(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Historial inmutable de canjes de cupones y auditoría de descuentos aplicados."""
    redemptions = db.query(VoucherRedemption).order_by(VoucherRedemption.created_at.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "voucher_code": r.voucher_code,
            "appointment_id": r.appointment_id,
            "order_id": r.order_id,
            "client_phone": r.client_phone,
            "staff_username": r.staff_username,
            "original_amount": r.original_amount,
            "discount_applied": r.discount_applied,
            "final_amount": r.final_amount,
            "commission_impact": r.commission_impact,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in redemptions
    ]
