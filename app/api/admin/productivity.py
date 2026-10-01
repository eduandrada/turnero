"""
app/api/admin/productivity.py - Reporte de Productividad e Incentivos por Barbero
HiddenSYNC AI 2026
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db, get_argentina_now
from app.models import Barber, Appointment, SalesRecord, AdminUser
from app.core.dependencies import require_encargado_or_admin

logger = logging.getLogger("hiddensync.admin.productivity")

router = APIRouter(prefix="/api/admin/staff/productivity", tags=["Admin Staff Productivity"])


@router.get("")
def get_barber_productivity_report(
    start_date: Optional[str] = None, # YYYY-MM-DD
    end_date: Optional[str] = None,   # YYYY-MM-DD
    barber_id: Optional[int] = None,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """
    Retorna métricas detalladas de productividad e incentivos por barbero:
    - Promedio de minutos por corte.
    - Turnos atendidios / completados / no-shows / tasa ausentismo.
    - Total facturado (Servicios + Productos recomendados).
    - Propinas recibidas.
    - Comisión por servicios (% configurable por barbero).
    - Comisión por venta de productos (% configurable por barbero).
    - Total incentivos / compensación acumulada.
    """
    now = get_argentina_now().replace(tzinfo=None)

    # Parse dates or default to current month
    if start_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            s_dt = now.replace(day=1, hour=0, minute=0, second=0)
    else:
        s_dt = now.replace(day=1, hour=0, minute=0, second=0)

    if end_date:
        try:
            e_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            e_dt = now.replace(hour=23, minute=59, second=59)
    else:
        e_dt = now.replace(hour=23, minute=59, second=59)

    # Fetch active barbers
    barbers_query = db.query(Barber).filter(Barber.is_active == True)
    if barber_id:
        barbers_query = barbers_query.filter(Barber.id == barber_id)
    barbers = barbers_query.order_by(Barber.display_order.asc(), Barber.name.asc()).all()

    report_items = []
    total_shop_revenue = 0.0
    total_shop_tips = 0.0
    total_shop_commissions = 0.0
    total_shop_appointments = 0

    for barber in barbers:
        # Fetch appointments in date range
        apps = (
            db.query(Appointment)
            .filter(
                Appointment.barber_id == barber.id,
                Appointment.appointment_time >= s_dt,
                Appointment.appointment_time <= e_dt
            )
            .all()
        )

        total_apps = len(apps)
        completed_apps = [a for a in apps if a.status == "COMPLETADO"]
        no_show_apps = [a for a in apps if a.status == "NO_SHOW"]
        canceled_apps = [a for a in apps if a.status == "CANCELADO"]
        pending_apps = [a for a in apps if a.status in ["PENDIENTE", "CONFIRMADO"]]

        completed_count = len(completed_apps)
        no_show_count = len(no_show_apps)

        no_show_rate = round((no_show_count / total_apps * 100.0), 1) if total_apps > 0 else 0.0

        # Minutes per haircut (average duration)
        durations = [
            a.actual_duration_min or a.duration_min or 45
            for a in completed_apps
        ]
        avg_min_per_cut = round(sum(durations) / len(durations), 1) if durations else 45.0

        # Services revenue
        services_revenue = sum(
            a.service_price_snapshot or 0.0 for a in completed_apps
        )

        # Tips from appointments
        tips_apps = sum(a.tip_amount or 0.0 for a in apps)

        # Sales records for products sold by this barber
        sales = (
            db.query(SalesRecord)
            .filter(
                SalesRecord.barber_id == barber.id,
                SalesRecord.created_at >= s_dt,
                SalesRecord.created_at <= e_dt
            )
            .all()
        )

        products_revenue = sum(
            s.total_amount for s in sales if s.sale_type in ["PRODUCTO", "MIXTO"]
        )
        tips_sales = sum(s.tip_amount for s in sales)

        total_tips = tips_apps + tips_sales

        # Commissions
        comm_services_pct = barber.commission_services_percent if barber.commission_services_percent is not None else 50.0
        comm_products_pct = barber.commission_products_percent if barber.commission_products_percent is not None else 10.0

        commission_services = round(services_revenue * (comm_services_pct / 100.0), 2)
        commission_products = round(products_revenue * (comm_products_pct / 100.0), 2)
        total_commissions = commission_services + commission_products
        total_earnings = total_commissions + total_tips

        total_revenue = services_revenue + products_revenue

        total_shop_revenue += total_revenue
        total_shop_tips += total_tips
        total_shop_commissions += total_commissions
        total_shop_appointments += completed_count

        report_items.append({
            "barber_id": barber.id,
            "barber_name": barber.name,
            "avatar_url": barber.avatar_url,
            "specialties": barber.specialties,
            "total_appointments": total_apps,
            "completed_count": completed_count,
            "no_show_count": no_show_count,
            "canceled_count": len(canceled_apps),
            "no_show_rate": no_show_rate,
            "avg_min_per_cut": avg_min_per_cut,
            "services_revenue": services_revenue,
            "products_revenue": products_revenue,
            "total_revenue": total_revenue,
            "tips": total_tips,
            "comm_services_pct": comm_services_pct,
            "comm_products_pct": comm_products_pct,
            "commission_services": commission_services,
            "commission_products": commission_products,
            "total_commissions": total_commissions,
            "total_compensation": total_earnings
        })

    return {
        "period": {
            "start_date": s_dt.strftime("%Y-%m-%d"),
            "end_date": e_dt.strftime("%Y-%m-%d")
        },
        "summary": {
            "total_barbers": len(barbers),
            "total_completed_appointments": total_shop_appointments,
            "total_revenue": total_shop_revenue,
            "total_tips": total_shop_tips,
            "total_commissions": total_shop_commissions
        },
        "barbers": report_items
    }
