"""
app/api/vouchers.py - Endpoints de Previsualización y Aplicación de Cupones / Vouchers
HiddenSYNC AI 2026
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser, Voucher
from app.schemas import VoucherPreviewRequest, VoucherApplyRequest
from app.core.dependencies import require_encargado_or_admin
from app.voucher_engine import validate_and_calculate_discount, record_voucher_redemption

router = APIRouter(tags=["Vouchers"])

@router.post("/api/vouchers/preview")
def preview_voucher(
    req: VoucherPreviewRequest,
    db: Session = Depends(get_db)
):
    """Simula la aplicación de un cupón calculando el descuento y validando restricciones."""
    cart_context = {
        "subtotal": req.subtotal,
        "service_id": req.service_id,
        "service_price": req.service_price or req.subtotal,
        "product_ids": req.product_ids or [],
        "target_datetime": req.target_datetime
    }
    result = validate_and_calculate_discount(
        db=db,
        voucher_code=req.voucher_code,
        cart_context=cart_context,
        client_phone=req.client_phone,
        operator_role="ANY"
    )
    return result

@router.post("/api/vouchers/apply")
def apply_voucher_at_checkout(
    req: VoucherApplyRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Aplica y consume atómicamente un cupón en el checkout con registro inmutable."""
    cart_context = {
        "subtotal": req.subtotal,
        "service_id": req.service_id,
        "service_price": req.service_price or req.subtotal,
        "product_ids": req.product_ids or []
    }
    result = validate_and_calculate_discount(
        db=db,
        voucher_code=req.voucher_code,
        cart_context=cart_context,
        client_phone=req.client_phone,
        operator_role=admin.role
    )
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Cupón inválido o no aplicable."))

    voucher = db.query(Voucher).filter(Voucher.code == req.voucher_code.strip().upper()).first()
    redemption = record_voucher_redemption(
        db=db,
        voucher=voucher,
        appointment_id=req.appointment_id,
        order_id=req.order_id,
        client_id=req.client_id,
        client_phone=req.client_phone,
        staff_username=admin.username,
        validation_result=result
    )
    return {
        "status": "success",
        "message": f"Cupón '{voucher.code}' aplicado exitosamente.",
        "discount_applied": result["discount_applied"],
        "final_total": result["final_total"],
        "commission_impact": result["commission_impact"],
        "barber_commission_base": result["barber_commission_base"],
        "redemption_id": redemption.id
    }


@router.get("/api/vouchers/verify/{code}")
def verify_voucher_code(code: str, db: Session = Depends(get_db)):
    """Retorna información pública de un cupón/voucher para la vista voucher.html."""
    from app.core.database import get_argentina_now
    code_clean = code.strip().upper()
    v = db.query(Voucher).filter(Voucher.code == code_clean).first()
    if not v:
        return {
            "valid": False,
            "code": code_clean,
            "error": "El código de voucher ingresado no existe en nuestro sistema."
        }
    
    now = get_argentina_now().replace(tzinfo=None)
    is_expired = bool(v.valid_to and now > v.valid_to)
    is_maxed = bool(v.max_total_uses and (v.current_uses or 0) >= v.max_total_uses)
    is_usable = bool(v.is_active and not is_expired and not is_maxed)

    title = ""
    if v.discount_type == "PERCENTAGE":
        if v.discount_value >= 100:
            title = "🎁 PASE LIBRE - 100% CORTE GRATIS"
        else:
            title = f"🔥 {int(v.discount_value)}% DE DESCUENTO"
    elif v.discount_type == "FIXED_AMOUNT":
        title = f"💰 ${v.discount_value:,.0f} OFF EN TU SERVICIO/COMPRA".replace(",", ".")
    elif v.discount_type == "FREE_ITEM":
        title = "🎁 PASE LIBRE - SERVICIO GRATUITO"
    elif v.discount_type == "FIXED_PRICE":
        title = f"🏷️ PRECIO FIJO ESPECIAL DE ${v.discount_value:,.0f}".replace(",", ".")
    else:
        title = f"🎟️ DESCUENTO ESPECIAL: {v.discount_value}"

    return {
        "valid": is_usable,
        "is_active": v.is_active,
        "is_expired": is_expired,
        "is_maxed": is_maxed,
        "code": v.code,
        "discount_type": v.discount_type,
        "discount_value": v.discount_value,
        "title": title,
        "description": v.description or "Voucher promocional oficial de Pereyras Barbers",
        "scope": v.scope,
        "min_ticket_amount": v.min_ticket_amount or 0.0,
        "valid_to": v.valid_to.strftime("%d/%m/%Y") if v.valid_to else None,
        "current_uses": v.current_uses or 0,
        "max_total_uses": v.max_total_uses
    }

