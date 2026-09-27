"""
app/voucher_engine.py - Motor de Vouchers, Cupones y Descuentos Configurables
BladeSync AI 2026

Implementa validación estricta, yield management (happy hours/días ociosos),
cálculo de impacto en comisiones (BUSINESS_ABSORBED vs PROPORTIONAL)
y canje atómico antifraude con trazabilidad inmutable.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models import Voucher, VoucherRedemption, Appointment, Order
from app.database import get_argentina_now

class VoucherValidationError(Exception):
    """Excepción para errores de validación de cupones."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_and_calculate_discount(
    db: Session,
    code: Optional[str] = None,
    original_total: Optional[float] = None,
    client_phone: Optional[str] = None,
    operator_role: str = "public",
    service_id: Optional[int] = None,
    product_ids: Optional[List[int]] = None,
    current_dt: Optional[datetime] = None,
    voucher_code: Optional[str] = None,
    cart_context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Valida en orden exhaustivo un código de cupón:
    1. Existencia y estado activo
    2. Nivel de permiso mínimo del operador
    3. Vigencia temporal (fechas y días de la semana permitidos)
    4. Límite de usos globales
    5. Límite de usos por cliente
    6. Monto mínimo de compra
    7. Compatibilidad de alcance (scope)
    8. Cálculo del descuento y del impacto en la liquidación de la comisión
    """
    # Unpack aliases
    actual_code = str(code or voucher_code or "").strip().upper()
    if cart_context:
        if original_total is None:
            original_total = cart_context.get("subtotal", 0.0)
        if service_id is None:
            service_id = cart_context.get("service_id")
        if product_ids is None:
            product_ids = cart_context.get("product_ids")
        if current_dt is None and cart_context.get("target_datetime"):
            try:
                td = cart_context["target_datetime"]
                if isinstance(td, str):
                    current_dt = datetime.fromisoformat(td)
                elif isinstance(td, datetime):
                    current_dt = td
            except Exception:
                pass

    orig_total = float(original_total or 0.0)
    now = current_dt or get_argentina_now()

    try:
        voucher = db.query(Voucher).filter(Voucher.code == actual_code).first()
        if not voucher or not voucher.is_active:
            raise VoucherValidationError("VOUCHER_NOT_FOUND", "El código de cupón no existe o está inactivo.")

        # 1. Rol mínimo
        if operator_role and operator_role.upper() != "ANY":
            role_hierarchy = {"admin": 3, "encargado": 2, "public": 1}
            op_level = role_hierarchy.get(operator_role.lower(), 1)
            req_level = role_hierarchy.get((voucher.min_role or "public").lower(), 1)
            if op_level < req_level:
                raise VoucherValidationError(
                    "INSUFFICIENT_PERMISSIONS",
                    f"El cupón {actual_code} requiere autorización de nivel {(voucher.min_role or 'ADMIN').upper()}."
                )

        # 2. Vigencia de fechas
        if voucher.valid_from and now < voucher.valid_from:
            raise VoucherValidationError("NOT_STARTED_YET", f"El cupón {actual_code} aún no está vigente.")
        if voucher.valid_to and now > voucher.valid_to:
            raise VoucherValidationError("EXPIRED", f"El cupón {actual_code} ha expirado.")

        # 3. Días de la semana permitidos (Yield Management)
        if voucher.allowed_days:
            allowed = [int(d.strip()) for d in voucher.allowed_days.split(",") if d.strip().isdigit()]
            if now.weekday() not in allowed:
                raise VoucherValidationError(
                    "DAY_NOT_ALLOWED",
                    f"El cupón {actual_code} no es válido en el día de hoy (solo válido en días autorizados)."
                )

        # 4. Límite de usos global
        if voucher.max_total_uses is not None and (voucher.current_uses or 0) >= voucher.max_total_uses:
            raise VoucherValidationError("GLOBAL_LIMIT_REACHED", "El cupón ha alcanzado el límite total de canjes disponibles.")

        # 5. Límite por cliente
        if client_phone and voucher.max_uses_per_client:
            user_redemptions = db.query(VoucherRedemption).filter(
                VoucherRedemption.voucher_id == voucher.id,
                VoucherRedemption.client_phone == client_phone
            ).count()
            if user_redemptions >= voucher.max_uses_per_client:
                raise VoucherValidationError("CLIENT_LIMIT_REACHED", "Has alcanzado el límite de usos para este cupón.")

        # 6. Monto mínimo
        if voucher.min_ticket_amount and orig_total < voucher.min_ticket_amount:
            raise VoucherValidationError(
                "MIN_TICKET_NOT_MET",
                f"El ticket mínimo requerido para este cupón es de ${voucher.min_ticket_amount:,.2f}."
            )

        # 7. Alcance (scope)
        if voucher.scope == "SERVICES_ONLY" and not service_id:
            raise VoucherValidationError("SCOPE_MISMATCH", "Este cupón es aplicable únicamente a servicios de barbería.")
        if voucher.scope == "PRODUCTS_ONLY" and not product_ids:
            raise VoucherValidationError("SCOPE_MISMATCH", "Este cupón es aplicable únicamente a productos del Shop.")

        # 8. Cálculo de descuento
        dtype = voucher.discount_type
        discount_amount = 0.0

        if dtype == "PERCENTAGE":
            calc = orig_total * (voucher.discount_value / 100.0)
            if voucher.max_discount_amount:
                calc = min(calc, voucher.max_discount_amount)
            discount_amount = calc
        elif dtype == "FIXED_AMOUNT":
            discount_amount = min(voucher.discount_value, orig_total)
        elif dtype == "FIXED_PRICE":
            if orig_total > voucher.discount_value:
                discount_amount = orig_total - voucher.discount_value
            else:
                discount_amount = 0.0
        elif dtype == "FREE_ITEM":
            discount_amount = orig_total

        discount_amount = min(discount_amount, orig_total)
        discount_amount = round(max(0.0, discount_amount), 2)
        final_total = round(max(0.0, orig_total - discount_amount), 2)

        # 9. Regla de impacto en comisiones
        absorption = voucher.discount_absorption or "BUSINESS_ABSORBED"
        barber_commission_base = orig_total if absorption == "BUSINESS_ABSORBED" else final_total

        return {
            "valid": True,
            "voucher_id": voucher.id,
            "code": voucher.code,
            "discount_type": voucher.discount_type,
            "discount_value": voucher.discount_value,
            "original_total": orig_total,
            "discount_amount": discount_amount,
            "discount_applied": discount_amount,
            "final_total": final_total,
            "discount_absorption": absorption,
            "commission_impact": absorption,
            "barber_commission_base": barber_commission_base
        }
    except VoucherValidationError as e:
        return {
            "valid": False,
            "error": e.message,
            "code": e.code,
            "discount_applied": 0.0,
            "final_total": orig_total,
            "commission_impact": "PROPORTIONAL",
            "barber_commission_base": orig_total
        }


def record_voucher_redemption(
    db: Session,
    voucher: Optional[Voucher] = None,
    voucher_id: Optional[int] = None,
    original_amount: Optional[float] = None,
    discount_amount: Optional[float] = None,
    final_amount: Optional[float] = None,
    client_phone: Optional[str] = None,
    appointment_id: Optional[int] = None,
    order_id: Optional[int] = None,
    client_id: Optional[int] = None,
    staff_user_id: Optional[int] = None,
    staff_username: Optional[str] = None,
    commission_impact: Optional[str] = None,
    validation_result: Optional[Dict[str, Any]] = None,
    **kwargs
) -> VoucherRedemption:
    """
    Registra de manera atómica e inmutable el canje del cupón en VoucherRedemption e incrementa current_uses.
    """
    v_id = voucher.id if voucher else voucher_id
    if not v_id and validation_result:
        v_id = validation_result.get("voucher_id")

    v_target = db.query(Voucher).filter(Voucher.id == v_id).with_for_update().first()
    if not v_target:
        raise VoucherValidationError("VOUCHER_NOT_FOUND", "El cupón no fue encontrado.")

    v_target.current_uses = (v_target.current_uses or 0) + 1

    orig = original_amount if original_amount is not None else (validation_result.get("original_total", 0.0) if validation_result else 0.0)
    disc = discount_amount if discount_amount is not None else (validation_result.get("discount_applied", 0.0) if validation_result else 0.0)
    fin = final_amount if final_amount is not None else (validation_result.get("final_total", 0.0) if validation_result else 0.0)
    impact = commission_impact or (validation_result.get("commission_impact") if validation_result else None) or v_target.discount_absorption

    redemption = VoucherRedemption(
        voucher_id=v_target.id,
        voucher_code=v_target.code,
        appointment_id=appointment_id,
        order_id=order_id,
        client_phone=client_phone or "Desconocido",
        staff_user_id=staff_user_id,
        staff_username=staff_username or "Cliente / Online",
        original_amount=orig,
        discount_amount=disc,
        final_amount=fin,
        barber_commission_impact=impact,
        created_at=get_argentina_now().replace(tzinfo=None)
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return redemption
