"""
app/api/admin/appointments.py - Endpoints de Gestión Administrativa de Turnos y Lista de Espera
HiddenSYNC AI 2026
"""
import os
import json
import logging
import urllib.parse
from datetime import datetime, time, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models import AdminUser, Appointment, Barber, AppointmentHistory, AuditLog, WaitlistEntry, Product, StockMovement, Client, get_now
from app.schemas import AppointmentRead, AppointmentUpdate, WaitlistEntryRead, AppointmentCheckoutRequest
from app.core.dependencies import require_admin_role, require_encargado_or_admin, require_any_staff_role
from app.settings_helper import get_setting
from app.api.loyalty import credit_client_loyalty_points

logger = logging.getLogger("hiddensync.admin.appointments")

router = APIRouter(tags=["Admin Appointments"])

from datetime import datetime, time, timedelta

@router.get("/api/admin/appointments", response_model=List[AppointmentRead])
def get_admin_appointments(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_preset: Optional[str] = None,
    barber_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 500,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """Consulta de turnos con filtros avanzados por fecha, rango, profesional y estado."""
    # Resolver presets si no se proporcionó fecha explícita
    if not date and date_preset:
        dp = date_preset.strip().lower()
        now = datetime.now()
        if dp == "today":
            date = now.strftime("%Y-%m-%d")
        elif dp == "tomorrow":
            date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    query = db.query(Appointment)
    if date:
        try:
            t_date = datetime.strptime(date, "%Y-%m-%d").date()
            s_day = datetime.combine(t_date, time.min)
            e_day = datetime.combine(t_date, time.max)
            query = query.filter(Appointment.appointment_time >= s_day, Appointment.appointment_time <= e_day)
            query = query.order_by(Appointment.appointment_time.asc())
        except ValueError:
            query = query.order_by(Appointment.appointment_time.desc())
    elif start_date and end_date:
        try:
            s_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_d = datetime.strptime(end_date, "%Y-%m-%d").date()
            s_day = datetime.combine(s_d, time.min)
            e_day = datetime.combine(e_d, time.max)
            query = query.filter(Appointment.appointment_time >= s_day, Appointment.appointment_time <= e_day)
            query = query.order_by(Appointment.appointment_time.desc())
        except ValueError:
            query = query.order_by(Appointment.appointment_time.desc())
    else:
        query = query.order_by(Appointment.appointment_time.desc())

    user_role = (admin.role or "").strip().lower()
    if user_role == "barbero":
        matched_b = db.query(Barber).filter(Barber.name.ilike(f"%{admin.username}%")).first()
        target_b_id = matched_b.id if matched_b else -1
        query = query.filter(Appointment.barber_id == target_b_id)
    elif barber_id:
        query = query.filter(Appointment.barber_id == barber_id)

    if status:
        st = status.strip().lower()
        if st in ["activos", "active", "pendientes_atencion"]:
            query = query.filter(
                Appointment.status.in_(["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"]),
                Appointment.canceled == False
            )
        elif st in ["completados", "completed", "atendidos"]:
            query = query.filter(Appointment.status.in_(["COMPLETADO", "ATENDIDO", "FINALIZADO"]))
        elif st in ["cancelados", "canceled"]:
            query = query.filter(or_(Appointment.status.in_(["CANCELADO", "NO_SHOW"]), Appointment.canceled == True))
        elif st not in ["todos", "all", ""]:
            query = query.filter(Appointment.status == status.upper())

    return query.limit(limit).all()

@router.put("/api/admin/appointments/{appointment_id}", response_model=AppointmentRead)
@router.put("/api/admin/appointments/{appointment_id}/status", response_model=AppointmentRead)
@router.post("/api/admin/appointments/{appointment_id}/status", response_model=AppointmentRead)
def update_admin_appointment(
    appointment_id: int,
    appt_in: AppointmentUpdate,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """Actualización integral de datos, horario y estado del turno."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    user_role = (admin.role or "").strip().lower()
    if user_role == "barbero":
        matched_b = db.query(Barber).filter(Barber.name.ilike(f"%{admin.username}%")).first()
        if not matched_b or appt.barber_id != matched_b.id:
            raise HTTPException(status_code=403, detail="Un barbero solo puede gestionar sus propios turnos.")

    old_status = appt.status or "PENDIENTE"
    for k, v in appt_in.model_dump(exclude_unset=True).items():
        setattr(appt, k, v)

    # Sincronización robusta de estados y banderas booleanas
    if appt_in.status:
        st = appt_in.status.upper().strip()
        appt.status = st
        if st == "CANCELADO":
            appt.canceled = True
            appt.confirmed = False
        elif st == "COMPLETADO":
            appt.canceled = False
            appt.confirmed = True
            # Barber Club: Acreditar puntos automáticamente por el servicio
            from app.api.loyalty import credit_client_loyalty_points
            amount = appt.service_price_snapshot or (appt.service_rel.price if appt.service_rel else 0.0)
            if amount > 0 and appt.client_phone:
                credit_client_loyalty_points(
                    db,
                    client_phone=appt.client_phone,
                    amount=amount,
                    reason=f"Corte/Servicio: {appt.service or 'Barbería'}",
                    reference_id=str(appt.id)
                )

        elif st in ["CONFIRMADO", "EN_SILLA", "EN_ATENCION"]:
            appt.canceled = False
            appt.confirmed = True
        elif st == "PENDIENTE":
            appt.canceled = False
            appt.confirmed = False

    db.commit()
    db.refresh(appt)

    # Registro en historial de auditoría de turnos
    if appt.status != old_status:
        try:
            db.add(AppointmentHistory(
                appointment_id=appt.id,
                previous_status=old_status,
                new_status=appt.status,
                changed_by=admin.username,
                change_reason=appt_in.notes or f"Estado cambiado a {appt.status}"
            ))
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar historial de turno: {e}")

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Turnos",
        action="Actualizar Turno",
        record_id=str(appt.id),
        old_value=f"Estado: {old_status}",
        new_value=f"Estado: {appt.status}",
        description=f"Turno #{appt.id} ({appt.client_name}) actualizado a {appt.status}"
    ))
    db.commit()
    return appt

@router.get("/api/admin/appointments/{appointment_id}/checkout-prep")
def get_appointment_checkout_prep(
    appointment_id: int,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """Retorna datos del turno, configuración de cobro y catálogo de productos activos (ligero y sin fotos pesadas)."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    # Parse extras si están almacenados
    extras_list = []
    if appt.extras_snapshot:
        try:
            parsed = json.loads(appt.extras_snapshot)
            if isinstance(parsed, list):
                extras_list = parsed
        except Exception:
            extras_list = [{"name": str(appt.extras_snapshot), "price": 0.0}]

    # Productos activos del shop para el selector ágil
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name.asc()).all()
    products_data = [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price or 0.0),
            "stock": int(p.stock or 0),
            "category": p.category or "reventa"
        }
        for p in products
    ]

    base_service_price = float(appt.service_price_snapshot if appt.service_price_snapshot is not None else (appt.service_rel.price if appt.service_rel else 0.0))
    alias = get_setting(db, "checkout_alias_transferencia", "") or get_setting(db, "deposit_mp_alias", "BARBERIA.PEREYRA.MP")
    titular = get_setting(db, "checkout_alias_titular", "Carmen Pereyra")
    promo_code = get_setting(db, "checkout_next_cut_promo_code", "VUELVO15")
    promo_percent = get_setting(db, "checkout_next_cut_discount_percent", "15")
    custom_msg = get_setting(db, "checkout_custom_message", "¡Gracias por visitarnos en Pereyras Barbers! Esperamos verte pronto.")

    return {
        "appointment": {
            "id": appt.id,
            "client_name": appt.client_name,
            "client_phone": appt.client_phone,
            "barber_name": appt.barber_name or "Sin asignar",
            "service": appt.service or "Corte & Barba",
            "service_price": base_service_price,
            "extras": extras_list,
            "deposit_paid": bool(appt.deposit_paid),
            "deposit_amount": float(appt.deposit_amount or 0.0),
            "appointment_time": appt.appointment_time.isoformat() if appt.appointment_time else "",
            "status": appt.status,
            "payment_status": appt.payment_status,
            "checkout_data": json.loads(appt.checkout_data) if appt.checkout_data else None
        },
        "products": products_data,
        "settings": {
            "alias": alias,
            "titular": titular,
            "promo_code": promo_code,
            "promo_percent": promo_percent,
            "custom_message": custom_msg
        }
    }

@router.post("/api/admin/appointments/{appointment_id}/checkout")
def checkout_admin_appointment(
    appointment_id: int,
    payload: AppointmentCheckoutRequest,
    admin: AdminUser = Depends(require_any_staff_role),
    db: Session = Depends(get_db)
):
    """
    Cobro de turno, deducción atómica de inventario del shop,
    generación de ticket virtual y redacción de comprobante WhatsApp.
    """
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    user_role = (admin.role or "").strip().lower()
    if user_role == "barbero":
        matched_b = db.query(Barber).filter(Barber.name.ilike(f"%{admin.username}%")).first()
        if not matched_b or appt.barber_id != matched_b.id:
            raise HTTPException(status_code=403, detail="Un barbero solo puede cobrar sus propios turnos.")

    # 1. Base Service Price
    if payload.override_service_price is not None:
        service_price = float(payload.override_service_price)
    elif appt.service_price_snapshot is not None:
        service_price = float(appt.service_price_snapshot)
    elif appt.service_rel:
        service_price = float(appt.service_rel.price)
    else:
        service_price = 0.0

    # 2. Extras
    extras_list = []
    extras_total = 0.0
    if appt.extras_snapshot:
        try:
            parsed = json.loads(appt.extras_snapshot)
            if isinstance(parsed, list):
                for ex in parsed:
                    ex_name = ex.get("name") or "Extra"
                    ex_price = float(ex.get("price") or 0.0)
                    extras_list.append({"name": ex_name, "price": ex_price})
                    extras_total += ex_price
        except Exception:
            extras_list.append({"name": str(appt.extras_snapshot), "price": 0.0})

    # 3. Productos del Shop & Reducción de Stock Conectada
    products_list = []
    products_total = 0.0
    for p_item in payload.products:
        if p_item.quantity <= 0:
            continue
        product = db.query(Product).filter(Product.id == p_item.product_id).first()
        if not product:
            continue

        unit_p = float(p_item.unit_price if p_item.unit_price is not None else (product.price or 0.0))
        item_subtotal = round(unit_p * p_item.quantity, 2)
        products_total += item_subtotal

        # Descontar stock atómicamente
        old_stock = product.stock or 0
        product.stock = max(0, old_stock - p_item.quantity)

        # Registrar movimiento de stock auditado
        movement = StockMovement(
            product_id=product.id,
            movement_type="venta",
            quantity=-p_item.quantity,
            date=get_now(),
            notes=f"Venta en Turno #{appt.id} ({appt.client_name})",
            registered_by=admin.username
        )
        db.add(movement)

        products_list.append({
            "product_id": product.id,
            "name": product.name,
            "quantity": p_item.quantity,
            "unit_price": unit_p,
            "subtotal": item_subtotal
        })

    # 4. Cálculo de Totales
    subtotal = round(service_price + extras_total + products_total, 2)
    deposit_credited = float(appt.deposit_amount or 0.0) if appt.deposit_paid else 0.0
    discount_amount = max(0.0, float(payload.discount_amount or 0.0))
    tip_amount = max(0.0, float(payload.tip_amount or 0.0))

    final_total = max(0.0, round(subtotal + tip_amount - deposit_credited - discount_amount, 2))

    # 5. Actualización del Turno
    old_status = appt.status or "PENDIENTE"
    appt.status = "COMPLETADO"
    appt.canceled = False
    appt.confirmed = True
    appt.payment_status = "TOTAL_PAGADO"
    appt.tip_amount = tip_amount
    if payload.notes:
        appt.notes = f"{(appt.notes or '').strip()} | Checkout: {payload.notes.strip()}".strip(" |")

    # 6. Barber Club & Puntos
    points_earned = 0
    if appt.client_phone and final_total > 0:
        try:
            points_earned = credit_client_loyalty_points(
                db,
                client_phone=appt.client_phone,
                amount=final_total,
                reason=f"Cobro Turno #{appt.id} ({appt.service or 'Corte'} + Shop)",
                reference_id=str(appt.id)
            ) or 0
        except Exception as e:
            logger.warning(f"Error al acreditar puntos Barber Club: {e}")

    # Actualizar gasto acumulado del cliente
    client = db.query(Client).filter(Client.phone == appt.client_phone).first() if appt.client_phone else None
    if client:
        client.total_spent = (client.total_spent or 0.0) + final_total

    # 7. Configuraciones de cobranza y fidelización
    alias = get_setting(db, "checkout_alias_transferencia", "") or get_setting(db, "deposit_mp_alias", "BARBERIA.PEREYRA.MP")
    titular = get_setting(db, "checkout_alias_titular", "Carmen Pereyra")
    promo_code = get_setting(db, "checkout_next_cut_promo_code", "VUELVO15")
    promo_percent = get_setting(db, "checkout_next_cut_discount_percent", "15")
    custom_msg = get_setting(db, "checkout_custom_message", "¡Gracias por visitarnos en Pereyras Barbers! Esperamos verte pronto.")

    # 8. Snapshot para Ticket Virtual
    checkout_snapshot = {
        "appointment_id": appt.id,
        "client_name": appt.client_name,
        "client_phone": appt.client_phone,
        "barber_name": appt.barber_name or "Sin asignar",
        "service_name": appt.service or "Corte de Barbería",
        "service_price": service_price,
        "extras": extras_list,
        "extras_total": extras_total,
        "products": products_list,
        "products_total": products_total,
        "subtotal": subtotal,
        "deposit_credited": deposit_credited,
        "discount_amount": discount_amount,
        "discount_code": payload.discount_code or "",
        "tip_amount": tip_amount,
        "total": final_total,
        "payment_method": payload.payment_method.lower(),
        "points_earned": points_earned,
        "client_total_points": client.points if client else 0,
        "alias": alias,
        "titular": titular,
        "promo_code": promo_code,
        "promo_percent": promo_percent,
        "checkout_at": get_now().strftime("%d/%m/%Y %H:%M"),
        "cashier": admin.username
    }
    appt.checkout_data = json.dumps(checkout_snapshot, ensure_ascii=False)

    # 9. Redacción Estructurada del Mensaje de WhatsApp
    lines = []
    lines.append("✂️ *PEREYRAS BARBERS - TICKET VIRTUAL* 💈")
    lines.append("────────────────────────")
    lines.append(f"👤 *Cliente:* {appt.client_name}")
    lines.append(f"💈 *Profesional:* {appt.barber_name or 'Equipo Pereyras'}")
    lines.append(f"📅 *Fecha:* {checkout_snapshot['checkout_at']} hs")
    lines.append("────────────────────────")
    lines.append("📋 *DETALLE DE SERVICIOS:*")
    lines.append(f"• {appt.service or 'Corte'}: ${service_price:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
    for ex in extras_list:
        lines.append(f"  + {ex['name']}: ${ex['price']:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))

    if products_list:
        lines.append("")
        lines.append("🛍️ *PRODUCTOS SHOP:*")
        for pr in products_list:
            lines.append(f"• {pr['quantity']}x {pr['name']} (${pr['unit_price']:,.2f} c/u): ${pr['subtotal']:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))

    lines.append("────────────────────────")
    if deposit_credited > 0:
        lines.append(f"🟢 *Seña Previa Descontada:* -${deposit_credited:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
    if discount_amount > 0:
        lines.append(f"🏷️ *Descuento Aplicado:* -${discount_amount:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))
    if tip_amount > 0:
        lines.append(f"🤝 *Propina:* +${tip_amount:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."))

    lines.append(f"💰 *TOTAL ABONADO: ${final_total:,.2f}*".replace(",", "@").replace(".", ",").replace("@", "."))
    lines.append(f"💳 *Medio de Pago:* {payload.payment_method.upper()}")

    # Si fue transferencia o para registro
    if payload.payment_method.lower() in ["transferencia", "mercadopago", "alias"]:
        lines.append("")
        lines.append("🏦 *DATOS BANCARIOS / TRANSFERENCIA:*")
        lines.append(f"• *Alias:* `{alias}`")
        lines.append(f"• *Titular:* {titular}")
        lines.append("📲 *Por favor envíanos la captura del comprobante por este chat para conciliar tu pago.*")

    if promo_code and promo_percent:
        lines.append("")
        lines.append("🎁 *REGALO PARA TU PRÓXIMA VISITA:*")
        lines.append(f"¡Tenés un *{promo_percent}% OFF* en tu próximo corte!")
        lines.append(f"🎟️ Cupón: *{promo_code}* (presentalo al agendar)")

    if points_earned > 0:
        lines.append("")
        lines.append(f"⭐ *BARBER CLUB:* ¡Sumaste *+{points_earned} pts*! Saldo total: *{client.points if client else points_earned} pts*")

    lines.append("")
    lines.append(f"🙏 *{custom_msg}*")

    wa_text = "\n".join(lines)
    clean_phone = "".join(filter(str.isdigit, appt.client_phone or ""))
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(wa_text)}"

    # 10. Auditoría e Historial
    try:
        db.add(AppointmentHistory(
            appointment_id=appt.id,
            previous_status=old_status,
            new_status="COMPLETADO",
            changed_by=admin.username,
            change_reason=f"Checkout finalizado con cobro total ${final_total} ({payload.payment_method})"
        ))
    except Exception as e:
        logger.warning(f"Error registrando historial: {e}")

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Turnos",
        action="Cobro de Turno / Checkout",
        record_id=str(appt.id),
        old_value=f"Estado: {old_status}",
        new_value=f"Total: ${final_total} ({payload.payment_method})",
        description=f"Turno #{appt.id} ({appt.client_name}) cobrado exitosamente. Stock descontado: {len(products_list)} items."
    ))

    db.commit()
    db.refresh(appt)

    return {
        "status": "success",
        "message": f"Turno #{appt.id} cobrado y finalizado exitosamente.",
        "appointment_id": appt.id,
        "total": final_total,
        "ticket": checkout_snapshot,
        "whatsapp_text": wa_text,
        "whatsapp_url": wa_url
    }

@router.delete("/api/admin/appointments/{appointment_id}")
def delete_admin_appointment(
    appointment_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina definitivamente un turno del sistema."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")

    db.delete(appt)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Turnos", action="Eliminar Turno", record_id=str(appointment_id)))
    db.commit()
    return {"message": "Turno eliminado correctamente."}

@router.get("/api/admin/waitlist", response_model=List[WaitlistEntryRead])
def list_admin_waitlist(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Lista las entradas registradas en la lista de espera."""
    query = db.query(WaitlistEntry)
    if status:
        query = query.filter(WaitlistEntry.status == status)
    return query.order_by(WaitlistEntry.created_at.desc()).all()

@router.delete("/api/admin/waitlist/{entry_id}")
def delete_waitlist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Elimina una entrada de la lista de espera."""
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada en lista de espera.")
    db.delete(entry)
    db.commit()
    return {"status": "success", "message": "Entrada eliminada de la lista de espera."}
