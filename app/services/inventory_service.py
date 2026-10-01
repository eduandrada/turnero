"""
app/services/inventory_service.py - Unified Inventory & Stock Management Service.
Centralizes product catalog lifecycle, atomic stock decrements (with anti-overselling guarantees),
stock movements, critical stock alerts, and inventory analytics.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import update, func
from fastapi import HTTPException

from app.core.exceptions import CapacityExceededError, NotFoundError
from app.core.logging import app_logger, audit_logger
from app.models import Product, StockMovement, Category, AuditLog, OrderItem
from app.core.database import get_argentina_now

logger = app_logger


class InventoryService:
    """Unified service for inventory catalog and atomic stock operations."""

    @staticmethod
    def decrement_stock_atomic(
        db: Session,
        product_id: int,
        quantity: int,
        registered_by: str = "Sistema",
        notes: str = "Venta"
    ) -> Product:
        """
        Decrementa el stock de forma atómica a nivel de base de datos garantizando que stock >= quantity.
        Previene colisiones concurrentes y sobreventa.
        """
        prod = db.query(Product).filter(Product.id == product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        stmt = (
            update(Product)
            .where(Product.id == product_id, Product.stock >= quantity)
            .values(stock=Product.stock - quantity)
        )
        res = db.execute(stmt)
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{prod.name}'. Stock disponible: {prod.stock} un."
            )

        # Registrar movimiento de stock
        db.add(StockMovement(
            product_id=product_id,
            movement_type="venta",
            quantity=-quantity,
            notes=notes,
            registered_by=registered_by
        ))
        db.commit()
        db.refresh(prod)
        return prod

    @staticmethod
    def adjust_stock(
        db: Session,
        product_id: int,
        movement_type: str,
        quantity: int,
        notes: Optional[str] = None,
        registered_by: str = "Admin"
    ) -> StockMovement:
        """
        Ajusta el stock de un producto sumando o restando según el tipo de movimiento:
        'ingreso_compra', 'venta', 'uso_interno', 'ajuste'.
        """
        prod = db.query(Product).filter(Product.id == product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        old_stock = prod.stock
        qty_change = quantity

        if movement_type in ["venta", "uso_interno"] or (movement_type == "ajuste" and quantity < 0):
            needed = abs(quantity)
            if prod.stock < needed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para registrar salida. Stock actual: {prod.stock}, requerido: {needed}"
                )
            qty_change = -needed
            prod.stock -= needed
        elif movement_type in ["ingreso_compra"] or (movement_type == "ajuste" and quantity > 0):
            prod.stock += abs(quantity)
            qty_change = abs(quantity)

        mov = StockMovement(
            product_id=product_id,
            movement_type=movement_type,
            quantity=qty_change,
            notes=notes,
            registered_by=registered_by
        )
        db.add(mov)

        db.add(AuditLog(
            user_name=registered_by,
            actor=registered_by,
            module="Inventario",
            action="Ajuste de Stock",
            record_id=str(prod.id),
            old_value=f"Stock: {old_stock}",
            new_value=f"Stock: {prod.stock} ({qty_change:+d} por {movement_type})",
            description=f"Movimiento '{movement_type}' de {qty_change} unidades en '{prod.name}'"
        ))
        db.commit()
        db.refresh(mov)
        return mov

    @staticmethod
    def get_critical_stock_products(db: Session) -> List[Product]:
        """Obtiene productos con stock menor o igual a su stock mínimo configurado."""
        return db.query(Product).filter(
            Product.is_active == True,
            Product.stock <= Product.min_stock
        ).order_by(Product.stock.asc()).all()

    @staticmethod
    def get_inventory_analytics(db: Session) -> Dict[str, Any]:
        """Calcula métricas clave de inventario, valorización de activos y rotación."""
        prods = db.query(Product).filter(Product.is_active == True).all()

        total_products = len(prods)
        total_units = sum(p.stock for p in prods)
        total_valuation = sum(p.stock * p.price for p in prods)
        total_cost_valuation = sum(p.stock * (p.cost_price or 0.0) for p in prods)
        low_stock_count = sum(1 for p in prods if p.stock <= p.min_stock)
        out_of_stock_count = sum(1 for p in prods if p.stock == 0)

        # Productos más vendidos en los últimos 30 días
        thirty_days_ago = get_argentina_now() - timedelta(days=30)
        top_selling = db.query(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.subtotal).label("revenue")
        ).join(Product, Product.id == OrderItem.product_id, isouter=True)\
         .group_by(OrderItem.product_id, OrderItem.product_name)\
         .order_by(func.sum(OrderItem.quantity).desc())\
         .limit(5).all()

        top_selling_data = [
            {
                "product_id": r.product_id,
                "name": r.product_name,
                "units_sold": int(r.units_sold or 0),
                "revenue": float(r.revenue or 0.0)
            }
            for r in top_selling
        ]

        # Productos con stock estancado (sin movimientos en 60 días)
        sixty_days_ago = get_argentina_now() - timedelta(days=60)
        recent_mov_prod_ids = [
            m.product_id for m in db.query(StockMovement.product_id)
            .filter(StockMovement.date >= sixty_days_ago)
            .distinct().all()
        ]

        stagnant = [
            {"id": p.id, "name": p.name, "stock": p.stock, "valuation": p.stock * p.price}
            for p in prods if p.id not in recent_mov_prod_ids and p.stock > 0
        ]

        return {
            "total_products": total_products,
            "total_units": total_units,
            "total_retail_valuation": total_valuation,
            "total_cost_valuation": total_cost_valuation,
            "potential_profit": total_valuation - total_cost_valuation,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "top_selling_products": top_selling_data,
            "stagnant_stock": stagnant[:5]
        }


inventory_service = InventoryService()
