"""
app/api/admin/finance.py - Endpoints de Finanzas, Arqueo de Caja, Ventas y Cierres de Turno
HiddenSYNC AI 2026
"""
from datetime import datetime, time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, get_argentina_now
from app.models import AdminUser, ShiftClosure, SalesRecord, Appointment, Service, Order, AuditLog
from app.schemas import (
    ShiftClosureCreate,
    ShiftClosureRead,
    ShiftCalculationResponse,
    SalesRecordCreate,
    SalesRecordRead,
)
from app.core.dependencies import get_current_admin, require_encargado_or_admin

router = APIRouter(tags=["Admin Finance & Cashier"])

@router.get("/api/shift-closures/calculate", response_model=ShiftCalculationResponse)
def calculate_shift_totals(
    fondo_inicial: float = Query(0.0),
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Calcula los totales en caja y ventas registradas desde la última rendición."""
    last_closure = db.query(ShiftClosure).order_by(ShiftClosure.fecha_cierre.desc()).first()
    now_naive = get_argentina_now().replace(tzinfo=None)

    if last_closure and last_closure.fecha_cierre:
        fecha_inicio = last_closure.fecha_cierre
    else:
        fecha_inicio = datetime.combine(now_naive.date(), time.min)

    fecha_cierre = now_naive

    appts = db.query(Appointment).filter(
        Appointment.appointment_time >= fecha_inicio,
        Appointment.appointment_time <= fecha_cierre,
        Appointment.canceled == False,
        Appointment.status != "CANCELADO"
    ).all()

    total_cortes = 0.0
    services = db.query(Service).all()
    srv_price_map = {s.name.lower(): s.price for s in services}

    for a in appts:
        p = srv_price_map.get((a.service or "").lower(), 4500.0)
        total_cortes += p

    orders = db.query(Order).filter(
        Order.created_at >= fecha_inicio,
        Order.created_at <= fecha_cierre,
        Order.status != "CANCELADO"
    ).all()

    total_productos = 0.0
    total_efectivo = 0.0
    total_transferencia = 0.0

    total_efectivo += total_cortes

    for o in orders:
        total_productos += (o.total or 0.0)
        pm = (o.payment_method or "").lower()
        if "efectivo" in pm:
            total_efectivo += (o.total or 0.0)
        else:
            total_transferencia += (o.total or 0.0)

    total_calculado = fondo_inicial + total_efectivo + total_transferencia

    prod_efectivo = sum(o.total or 0.0 for o in orders if "efectivo" in (o.payment_method or "").lower())
    prod_transferencia = sum(o.total or 0.0 for o in orders if "efectivo" not in (o.payment_method or "").lower())

    return ShiftCalculationResponse(
        fecha_inicio=fecha_inicio,
        fecha_cierre=fecha_cierre,
        fondo_inicial=fondo_inicial,
        total_cortes_efectivo=total_cortes,
        total_cortes_transferencia=0.0,
        total_productos_efectivo=prod_efectivo,
        total_productos_transferencia=prod_transferencia,
        total_efectivo=total_efectivo,
        total_transferencia=total_transferencia,
        total_cortes=total_cortes,
        total_productos=total_productos,
        total_calculado=total_calculado,
        total_turnos_atendidos=len(appts)
    )

@router.post("/api/shift-closures", response_model=ShiftClosureRead)
def create_shift_closure(
    data: ShiftClosureCreate,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Registra el cierre de turno y rendición de caja."""
    diferencia = data.balance_declarado - data.total_calculado

    closure = ShiftClosure(
        encargado_id=current_user.id,
        encargado_name=current_user.username,
        fecha_inicio=data.fecha_inicio,
        fecha_cierre=data.fecha_cierre,
        fondo_inicial=data.fondo_inicial,
        total_efectivo=data.total_efectivo,
        total_transferencia=data.total_transferencia,
        total_cortes=data.total_cortes,
        total_productos=data.total_productos,
        total_calculado=data.total_calculado,
        balance_declarado=data.balance_declarado,
        diferencia=diferencia,
        total_turnos_atendidos=data.total_turnos_atendidos,
        notas=data.notas
    )
    db.add(closure)
    db.commit()
    db.refresh(closure)

    db.add(AuditLog(
        user_name=current_user.username,
        module="Arqueo de Caja",
        action="Cierre de Turno",
        record_id=str(closure.id),
        new_value=f"Declarado: ${data.balance_declarado:,.2f} | Dif: ${diferencia:,.2f}"
    ))
    db.commit()

    return closure

@router.get("/api/admin/shift-closures", response_model=List[ShiftClosureRead])
def get_shift_closures(
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna la lista histórica de cierres de caja y auditorías."""
    return db.query(ShiftClosure).order_by(ShiftClosure.fecha_cierre.desc()).all()

@router.post("/api/admin/sales", response_model=SalesRecordRead)
def create_sales_record(
    data: SalesRecordCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Registra una venta o cobro en caja con desglose de ítems y medios de pago."""
    record = SalesRecord(
        sale_type=data.sale_type,
        appointment_id=data.appointment_id,
        order_id=data.order_id,
        client_id=data.client_id,
        client_name=data.client_name,
        barber_id=data.barber_id,
        barber_name=data.barber_name,
        payment_method=data.payment_method,
        original_amount=data.original_amount,
        discount_amount=data.discount_amount,
        final_amount=data.final_amount,
        voucher_code=data.voucher_code,
        items_detail=data.items_detail,
        cashier_name=admin.username,
        notes=data.notes
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    db.add(AuditLog(
        user_name=admin.username,
        module="Caja",
        action="Venta Registrada",
        record_id=str(record.id),
        new_value=f"${record.final_amount} ({record.payment_method}) - {record.sale_type}"
    ))
    db.commit()
    return record

@router.get("/api/admin/sales/summary")
def get_daily_sales_summary(
    date_str: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_encargado_or_admin)
):
    """Calcula el balance y resumen del día filtrado por medios de pago."""
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else get_argentina_now().date()
    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    sales = db.query(SalesRecord).filter(
        SalesRecord.created_at >= start_dt,
        SalesRecord.created_at <= end_dt
    ).all()

    total_sales = sum(s.final_amount for s in sales)
    total_discounts = sum(s.discount_amount for s in sales)
    by_method = {}
    for s in sales:
        by_method[s.payment_method] = by_method.get(s.payment_method, 0.0) + s.final_amount

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "total_operations": len(sales),
        "total_income": total_sales,
        "total_discounts": total_discounts,
        "by_payment_method": by_method
    }
