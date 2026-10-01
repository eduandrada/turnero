"""
app/api/admin/dashboard.py - Endpoints de Estadísticas y Métricas del Panel de Administración
HiddenSYNC AI 2026
"""
from datetime import datetime, time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db, get_argentina_now
from app.models import AdminUser, Appointment, Client, Barber, Service, Product, Order
from app.schemas import DashboardStatsResponse
from app.core.dependencies import get_current_admin

router = APIRouter(tags=["Admin Dashboard"])

@router.get("/api/admin/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Retorna métricas consolidadas, turnos del día, alertas de stock y pedidos recientes."""
    now_arg = get_argentina_now().date()
    start_today = datetime.combine(now_arg, time.min)
    end_today = datetime.combine(now_arg, time.max)

    today_appts = db.query(Appointment).filter(Appointment.appointment_time >= start_today, Appointment.appointment_time <= end_today).count()
    pending_appts = db.query(Appointment).filter(Appointment.status == "PENDIENTE").count()
    confirmed_appts = db.query(Appointment).filter(Appointment.status == "CONFIRMADO").count()
    completed_appts = db.query(Appointment).filter(Appointment.status == "COMPLETADO").count()
    canceled_appts = db.query(Appointment).filter(Appointment.status == "CANCELADO").count()

    total_clients = db.query(Client).count()
    total_barbers = db.query(Barber).count()
    total_services = db.query(Service).count()
    total_products = db.query(Product).count()

    low_stock_prods = db.query(Product).filter(Product.stock <= Product.min_stock).count()
    pending_orders = db.query(Order).filter(Order.status.in_(["NUEVO", "CONFIRMADO", "PREPARANDO"])).count()

    orders_rev = db.query(func.sum(Order.total)).filter(Order.status != "CANCELADO").scalar() or 0.0

    # Recent appointments
    rec_appts = db.query(Appointment).order_by(Appointment.appointment_time.desc()).limit(8).all()
    rec_appts_list = [
        {
            "id": a.id,
            "client_name": a.client_name,
            "service": a.service,
            "barber_name": a.barber_name,
            "time": a.appointment_time.isoformat(),
            "status": a.status
        } for a in rec_appts
    ]

    # Recent orders
    rec_orders = db.query(Order).order_by(Order.created_at.desc()).limit(8).all()
    rec_orders_list = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "client_name": o.client_name,
            "total": o.total,
            "status": o.status,
            "created_at": o.created_at.isoformat()
        } for o in rec_orders
    ]

    # Low stock list
    low_stock = db.query(Product).filter(Product.stock <= Product.min_stock).all()
    low_stock_list = [
        {
            "id": p.id,
            "name": p.name,
            "stock": p.stock,
            "min_stock": p.min_stock,
            "price": p.price
        } for p in low_stock
    ]

    return DashboardStatsResponse(
        today_appointments=today_appts,
        pending_appointments=pending_appts,
        confirmed_appointments=confirmed_appts,
        completed_appointments=completed_appts,
        canceled_appointments=canceled_appts,
        total_clients=total_clients,
        total_barbers=total_barbers,
        total_services=total_services,
        total_products=total_products,
        low_stock_products=low_stock_prods,
        pending_orders=pending_orders,
        total_orders_revenue=round(orders_rev, 2),
        estimated_turnover_revenue=0.0,
        recent_appointments=rec_appts_list,
        recent_orders=rec_orders_list,
        low_stock_list=low_stock_list
    )
