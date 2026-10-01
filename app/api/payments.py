"""
app/api/payments.py - Pasarela de Pagos (Mercado Pago & Stripe) para Señas de Turnos
HiddenSYNC AI 2026
"""
import logging
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import Appointment, AdminUser, AuditLog, Order
from app.settings_helper import get_setting
from app.core.dependencies import require_encargado_or_admin

logger = logging.getLogger("hiddensync.api.payments")

router = APIRouter(prefix="/api/payments", tags=["Payments & Deposits"])


class PaymentPreferenceRequest(BaseModel):
    appointment_id: Optional[int] = None
    order_id: Optional[int] = None
    amount: float
    description: str
    client_name: str
    client_phone: str
    client_email: Optional[str] = None


class DepositStatusUpdate(BaseModel):
    deposit_required: Optional[bool] = None
    deposit_amount: Optional[float] = None
    deposit_paid: Optional[bool] = None
    payment_status: Optional[str] = None # "SIN_SEÑA", "PENDIENTE_PAGO", "SEÑA_PAGADA", "TOTAL_PAGADO"
    notes: Optional[str] = None


@router.get("/config")
def get_payment_config(db: Session = Depends(get_db)):
    """Retorna la configuración pública de pasarela de pago y señas."""
    enabled_global = get_setting(db, "payment_gateway_enabled", "0") in ["1", "true", "True"]
    enable_deposit = get_setting(db, "enable_deposit", "0") in ["1", "true", "True"]
    deposit_pct = float(get_setting(db, "deposit_percentage", "30") or 30.0)
    provider = get_setting(db, "payment_provider", "mercadopago")
    mp_public_key = get_setting(db, "mp_public_key", "")
    mp_alias = get_setting(db, "deposit_mp_alias", "")
    stripe_pub_key = get_setting(db, "stripe_publishable_key", "")

    return {
        "enabled": enabled_global or enable_deposit,
        "enable_deposit": enable_deposit or enabled_global,
        "deposit_percentage": deposit_pct,
        "provider": provider,
        "mp_public_key": mp_public_key,
        "deposit_mp_alias": mp_alias,
        "stripe_publishable_key": stripe_pub_key
    }


@router.post("/create-preference")
async def create_payment_preference(
    req: PaymentPreferenceRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Genera una preferencia de pago para Mercado Pago o Stripe (o simulación en desarrollo)."""
    provider = get_setting(db, "payment_provider", "mercadopago").lower()
    mp_access_token = get_setting(db, "mp_access_token", "").strip()
    stripe_secret = get_setting(db, "stripe_secret_key", "").strip()
    host_url = str(request.base_url).rstrip("/")

    appointment = None
    if req.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == req.appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Turno no encontrado.")

    # 1. MERCADO PAGO INTEGRATION
    if provider == "mercadopago" and mp_access_token:
        try:
            headers = {
                "Authorization": f"Bearer {mp_access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "items": [
                    {
                        "title": req.description[:250],
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(req.amount)
                    }
                ],
                "payer": {
                    "name": req.client_name,
                    "email": req.client_email or f"cliente_{req.client_phone}@barberia.app",
                    "phone": {"number": req.client_phone}
                },
                "back_urls": {
                    "success": f"{host_url}/api/payments/callback?status=approved&app_id={req.appointment_id or 0}",
                    "pending": f"{host_url}/api/payments/callback?status=pending&app_id={req.appointment_id or 0}",
                    "failure": f"{host_url}/api/payments/callback?status=rejected&app_id={req.appointment_id or 0}"
                },
                "auto_return": "approved",
                "notification_url": f"{host_url}/api/payments/webhook",
                "external_reference": f"APPOINTMENT_{req.appointment_id}" if req.appointment_id else f"ORDER_{req.order_id}"
            }

            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.mercadopago.com/checkout/preferences", json=payload, headers=headers, timeout=10.0)
                if res.status_code in [200, 201]:
                    data = res.json()
                    init_point = data.get("init_point") or data.get("sandbox_init_point")
                    if appointment:
                        appointment.payment_status = "PENDIENTE_PAGO"
                        appointment.deposit_amount = req.amount
                        db.commit()
                    return {
                        "status": "success",
                        "provider": "mercadopago",
                        "init_point": init_point,
                        "preference_id": data.get("id"),
                        "is_simulated": False
                    }
                else:
                    logger.warning(f"Mercado Pago API error response: {res.text}")
        except Exception as e:
            logger.error(f"Error invoking Mercado Pago API: {e}")

    # 2. STRIPE INTEGRATION
    if provider == "stripe" and stripe_secret:
        try:
            headers = {
                "Authorization": f"Bearer {stripe_secret}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "payment_method_types[]": "card",
                "line_items[0][price_data][currency]": "ars",
                "line_items[0][price_data][product_data][name]": req.description,
                "line_items[0][price_data][unit_amount]": str(int(req.amount * 100)),
                "line_items[0][quantity]": "1",
                "mode": "payment",
                "success_url": f"{host_url}/api/payments/callback?status=approved&app_id={req.appointment_id or 0}",
                "cancel_url": f"{host_url}/api/payments/callback?status=rejected&app_id={req.appointment_id or 0}",
                "client_reference_id": f"APP_{req.appointment_id}" if req.appointment_id else f"ORD_{req.order_id}"
            }

            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.stripe.com/v1/checkout/sessions", data=data, headers=headers, timeout=10.0)
                if res.status_code in [200, 201]:
                    session_data = res.json()
                    if appointment:
                        appointment.payment_status = "PENDIENTE_PAGO"
                        appointment.deposit_amount = req.amount
                        db.commit()
                    return {
                        "status": "success",
                        "provider": "stripe",
                        "init_point": session_data.get("url"),
                        "session_id": session_data.get("id"),
                        "is_simulated": False
                    }
        except Exception as e:
            logger.error(f"Error invoking Stripe API: {e}")

    # 3. FALLBACK / DEMO CHECKOUT SIMULATION LINK
    # Allows testing flow without production keys
    simulated_url = f"{host_url}/api/payments/callback?status=approved&app_id={req.appointment_id or 0}&simulated=true"
    if appointment:
        appointment.payment_status = "PENDIENTE_PAGO"
        appointment.deposit_amount = req.amount
        db.commit()

    return {
        "status": "success",
        "provider": provider,
        "init_point": simulated_url,
        "is_simulated": True,
        "message": "Se generó enlace de pago en modo prueba/simulado."
    }


@router.get("/callback")
def payment_callback(
    status: str,
    app_id: int,
    simulated: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """Callback de retorno tras completar el pago."""
    appointment = db.query(Appointment).filter(Appointment.id == app_id).first()
    if appointment:
        if status in ["approved", "success"]:
            appointment.deposit_paid = True
            appointment.payment_status = "SEÑA_PAGADA"
            appointment.confirmed = True
            appointment.status = "CONFIRMADO"
            db.commit()
            return {
                "message": "¡Seña recibida y turno confirmado con éxito!",
                "appointment_id": appointment.id,
                "status": "CONFIRMADO",
                "deposit_paid": True
            }
        else:
            appointment.payment_status = "PENDIENTE_PAGO"
            db.commit()
            return {
                "message": "El pago de la seña no se pudo completar.",
                "appointment_id": appointment.id,
                "status": appointment.status
            }
    return {"message": "Respuesta procesada."}


@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook IPN para Mercado Pago o Stripe."""
    try:
        payload = await request.json()
        logger.info(f"Payment Webhook received: {payload}")
        # Parse external reference or payment ID
        ref = payload.get("data", {}).get("id") or payload.get("external_reference")
        if ref and str(ref).startswith("APPOINTMENT_"):
            app_id = int(str(ref).replace("APPOINTMENT_", ""))
            appointment = db.query(Appointment).filter(Appointment.id == app_id).first()
            if appointment:
                appointment.deposit_paid = True
                appointment.payment_status = "SEÑA_PAGADA"
                appointment.confirmed = True
                appointment.status = "CONFIRMADO"
                db.commit()
    except Exception as e:
        logger.warning(f"Error processing payment webhook: {e}")
    return {"status": "received"}


@router.put("/appointment/{appointment_id}/deposit")
def update_appointment_deposit_status(
    appointment_id: int,
    data: DepositStatusUpdate,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Permite al encargado en gestion.html gestionar la seña opcional por turno."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    if data.deposit_required is not None:
        appointment.deposit_required = data.deposit_required
    if data.deposit_amount is not None:
        appointment.deposit_amount = data.deposit_amount
    if data.deposit_paid is not None:
        appointment.deposit_paid = data.deposit_paid
        if data.deposit_paid:
            appointment.payment_status = "SEÑA_PAGADA"
            appointment.confirmed = True
            appointment.status = "CONFIRMADO"
        else:
            appointment.payment_status = "SIN_SEÑA" if not appointment.deposit_required else "PENDIENTE_PAGO"
    if data.payment_status is not None:
        appointment.payment_status = data.payment_status

    if data.notes:
        appointment.notes = f"{appointment.notes or ''}\n[Seña]: {data.notes}".strip()

    db.add(AuditLog(
        user_name=admin.username,
        module="Turnos & Señas",
        action="Actualizar Seña Turno",
        description=f"Turno #{appointment.id} - Seña Requerida: {appointment.deposit_required}, Pagada: {appointment.deposit_paid}"
    ))
    db.commit()

    return {
        "message": "Estado de seña actualizado correctamente.",
        "appointment_id": appointment.id,
        "deposit_required": appointment.deposit_required,
        "deposit_amount": appointment.deposit_amount,
        "deposit_paid": appointment.deposit_paid,
        "payment_status": appointment.payment_status
    }
