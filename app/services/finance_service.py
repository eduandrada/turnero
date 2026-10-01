"""
app/services/finance_service.py - Financial Operations, Cashier Shifts, and Sales Analytics.
Encapsulates cashier sales recording, daily cash drawer closures, and income analytics.
"""
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import SalesRecord, ShiftClosure, AuditLog
from app.core.database import get_argentina_now


class FinanceService:
    """Service handling cash register transactions, shift balance reconciliations, and financials."""

    @staticmethod
    def record_sale(
        db: Session,
        sale_type: str,
        total_amount: float,
        payment_method: str = "Efectivo",
        original_amount: float = 0.0,
        discount_amount: float = 0.0,
        client_name: Optional[str] = None,
        barber_name: Optional[str] = None,
        client_id: Optional[int] = None,
        barber_id: Optional[int] = None,
        appointment_id: Optional[int] = None,
        order_id: Optional[int] = None,
        voucher_code: Optional[str] = None,
        items_detail: Optional[str] = None,
        cashier_name: str = "Encargado",
        notes: Optional[str] = None
    ) -> SalesRecord:
        """Registra una venta en el libro de caja diario con auditoría."""
        record = SalesRecord(
            sale_type=sale_type,
            appointment_id=appointment_id,
            order_id=order_id,
            client_id=client_id,
            client_name=client_name,
            barber_id=barber_id,
            barber_name=barber_name,
            payment_method=payment_method,
            original_amount=original_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            voucher_code=voucher_code,
            items_detail=items_detail,
            cashier_name=cashier_name,
            notes=notes,
            created_at=get_argentina_now().replace(tzinfo=None)
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        db.add(AuditLog(
            user_name=cashier_name,
            actor=cashier_name,
            module="Caja",
            action="Venta Registrada",
            record_id=str(record.id),
            new_value=f"${record.total_amount} ({record.payment_method}) - {record.sale_type}"
        ))
        db.commit()
        return record

    @staticmethod
    def get_daily_sales_summary(db: Session, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Calcula el resumen de operaciones e ingresos del día por método de pago."""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else get_argentina_now().date()
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)

        sales = db.query(SalesRecord).filter(
            SalesRecord.created_at >= start_dt,
            SalesRecord.created_at <= end_dt
        ).all()

        total_sales = sum(s.final_amount for s in sales)
        total_discounts = sum(s.discount_amount for s in sales)
        by_method: Dict[str, float] = {}
        for s in sales:
            by_method[s.payment_method] = by_method.get(s.payment_method, 0.0) + s.final_amount

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_operations": len(sales),
            "total_income": total_sales,
            "total_discounts": total_discounts,
            "by_payment_method": by_method
        }


finance_service = FinanceService()
