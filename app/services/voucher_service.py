"""
app/services/voucher_service.py - Voucher, promo codes and yield management service.
Handles validation rules (role, date validity, happy hours, usage limits, scope)
and atomic redemption recording.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models import Voucher, VoucherRedemption, Appointment, Order
from app.core.database import get_argentina_now


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
                current_dt = datetime.fromisoformat(td) if isinstance(td, str) else td
            except Exception:
                pass

    orig_total = float(original_total or 0.0)
    now = current_dt or get_argentina_now()

    try:
        if not actual_code:
            raise VoucherValidationError("CODE_REQUIRED", "Debe ingresar un código de cupón.")

        v = db.query(Voucher).filter(Voucher.code == actual_code).first()
        if not v or not v.is_active:
            raise VoucherValidationError("INVALID_CODE", "El cupón ingresado no existe o no se encuentra activo.")

        # 1. Permiso mínimo
        roles_hierarchy = {"public": 0, "encargado": 1, "admin": 2}
        req_role = (v.min_role or "public").lower()
        user_level = roles_hierarchy.get(operator_role.lower(), 0)
        req_level = roles_hierarchy.get(req_role, 0)
        if user_level < req_level:
            raise VoucherValidationError("ROLE_NOT_AUTHORIZED", "No posee los permisos necesarios para aplicar este cupón.")

        # 2. Fechas de vigencia
        if v.valid_from and now < v.valid_from:
            raise VoucherValidationError("NOT_YET_VALID", "El cupón aún no ha entrado en vigencia.")
        if v.valid_to and now > v.valid_to:
            raise VoucherValidationError("EXPIRED", "El cupón se encuentra expirado.")

        # 3. Días de la semana permitidos (CSV e.g. '0,1')
        if v.allowed_days:
            allowed = [int(d.strip()) for d in v.allowed_days.split(",") if d.strip().isdigit()]
            if now.weekday() not in allowed:
                raise VoucherValidationError("DAY_NOT_ALLOWED", "El cupón no es válido para el día seleccionado.")

        # 4. Rango horario
        if v.allowed_start_time and v.allowed_end_time:
            now_time_str = now.strftime("%H:%M")
            if not (v.allowed_start_time <= now_time_str <= v.allowed_end_time):
                raise VoucherValidationError("TIME_NOT_ALLOWED", f"El cupón solo es válido de {v.allowed_start_time} a {v.allowed_end_time} hs.")

        # 5. Límite de usos totales
        if v.max_total_uses and (v.current_uses or 0) >= v.max_total_uses:
            raise VoucherValidationError("MAX_USES_REACHED", "El cupón ha alcanzado el límite máximo de canjes.")

        # 6. Límite de usos por cliente
        if client_phone and v.max_uses_per_client:
            clean_p = "".join(filter(str.isdigit, client_phone))
            user_redemptions = db.query(VoucherRedemption).filter(
                VoucherRedemption.voucher_id == v.id,
                VoucherRedemption.client_phone.ilike(f"%{clean_p[-8:]}%")
            ).count()
            if user_redemptions >= v.max_uses_per_client:
                raise VoucherValidationError("MAX_CLIENT_USES_REACHED", "Ya has utilizado este cupón el número máximo de veces permitidas.")

        # 7. Monto mínimo
        if v.min_ticket_amount and orig_total < v.min_ticket_amount:
            raise VoucherValidationError("MIN_AMOUNT_NOT_MET", f"El monto mínimo de compra para este cupón es de ${v.min_ticket_amount:,.2f}.")

        # 8. Compatibilidad de alcance (Scope)
        if v.scope == "SERVICES_ONLY" and not service_id:
            raise VoucherValidationError("SERVICES_ONLY", "Este cupón solo puede aplicarse a servicios de barbería.")
        if v.scope == "PRODUCTS_ONLY" and not product_ids:
            raise VoucherValidationError("PRODUCTS_ONLY", "Este cupón solo puede aplicarse a productos del Shop.")

        if v.applicable_service_ids and service_id:
            allowed_services = [int(s.strip()) for s in v.applicable_service_ids.split(",") if s.strip().isdigit()]
            if service_id not in allowed_services:
                raise VoucherValidationError("SERVICE_NOT_ELIGIBLE", "El servicio seleccionado no está incluido en esta promoción.")

        # 9. Cálculo del descuento
        discount_applied = 0.0
        if v.discount_type == "PERCENTAGE":
            discount_applied = (orig_total * (v.discount_value / 100.0))
            if v.max_discount_amount and discount_applied > v.max_discount_amount:
                discount_applied = v.max_discount_amount
        elif v.discount_type == "FIXED_AMOUNT":
            discount_applied = min(v.discount_value, orig_total)
        elif v.discount_type == "FIXED_PRICE":
            if orig_total > v.discount_value:
                discount_applied = orig_total - v.discount_value
        elif v.discount_type == "FREE_ITEM":
            discount_applied = orig_total

        final_total = max(0.0, orig_total - discount_applied)

        # 10. Impacto en comisión
        barber_commission_base = orig_total
        if v.discount_absorption == "PROPORTIONAL":
            barber_commission_base = final_total

        return {
            "valid": True,
            "voucher_id": v.id,
            "code": v.code,
            "discount_type": v.discount_type,
            "discount_value": v.discount_value,
            "discount_applied": round(discount_applied, 2),
            "final_total": round(final_total, 2),
            "commission_impact": v.discount_absorption,
            "barber_commission_base": round(barber_commission_base, 2),
            "original_total": orig_total
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
    """Registra de manera atómica e inmutable el canje del cupón en VoucherRedemption e incrementa current_uses."""
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


class VoucherService:
    @staticmethod
    def validate(db: Session, **kwargs) -> Dict[str, Any]:
        return validate_and_calculate_discount(db, **kwargs)

    @staticmethod
    def redeem(db: Session, **kwargs) -> VoucherRedemption:
        return record_voucher_redemption(db, **kwargs)


voucher_service = VoucherService()
