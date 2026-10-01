"""
tests/test_inventory_movements.py - Comprehensive tests for InventoryService movements and alerts.
Covers:
- Compra / Ingreso de stock mediante ajuste
- Venta / Salida de stock mediante decrement_stock_atomic
- Alertas de stock crítico
- Historial de movimientos de inventario
"""
import pytest
from fastapi import HTTPException
from app.services.inventory_service import InventoryService
from app.models import Product, StockMovement


def test_inventory_service_movements_and_alerts(db_session):
    # 1. Create a test product
    product = Product(
        name="Cera de Prueba Movements",
        price=1000.0,
        stock=5,
        min_stock=3,
        is_active=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    
    # 2. Add stock (ingreso mercadería: +10 units)
    mov = InventoryService.adjust_stock(
        db=db_session,
        product_id=product.id,
        movement_type="ingreso_compra",
        quantity=10,
        notes="Ingreso de mercadería proveedor",
        registered_by="Administrador"
    )
    assert mov is not None
    db_session.refresh(product)
    assert product.stock == 15
    
    # 3. Deduct stock atomically (salida/venta: -13 units)
    decremented_prod = InventoryService.decrement_stock_atomic(
        db=db_session,
        product_id=product.id,
        quantity=13,
        registered_by="Venta Mostrador",
        notes="Venta directa cliente"
    )
    assert decremented_prod.stock == 2
    db_session.refresh(product)
    assert product.stock == 2
    
    # 4. Check critical stock alerts (since stock=2 and min_stock=3)
    critical_prods = InventoryService.get_critical_stock_products(db_session)
    critical_ids = [p.id for p in critical_prods]
    assert product.id in critical_ids
    
    # 5. Overselling rejection
    with pytest.raises(HTTPException) as exc_info:
        InventoryService.decrement_stock_atomic(
            db=db_session,
            product_id=product.id,
            quantity=5 # Only 2 available
        )
    assert exc_info.value.status_code == 400
    assert "stock insuficiente" in exc_info.value.detail.lower()
    
    # Stock remains 2
    db_session.refresh(product)
    assert product.stock == 2
    
    # 6. Check movement logs in DB
    movements = db_session.query(StockMovement).filter(StockMovement.product_id == product.id).all()
    assert len(movements) >= 2
