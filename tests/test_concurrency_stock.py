"""
tests/test_concurrency_stock.py - Pruebas de concurrencia y prevención de sobreventa de stock.
FASE 10: Descuento atómico condicional en base de datos.
Si stock = 1 y llegan dos compras simultáneamente: exactamente 1 completa la compra, la otra falla por falta de stock.
"""
import pytest
import concurrent.futures
from app.models import Product

def test_order_stock_reduction_sufficient(client, db_session):
    """Verifica que un pedido descuente el stock correctamente y recalcule precios en el backend."""
    # Buscar producto con stock
    prod = db_session.query(Product).filter(Product.stock > 2).first()
    assert prod is not None
    initial_stock = prod.stock

    payload = {
        "client_name": "Comprador Normal",
        "client_phone": "+5491111223344",
        "delivery_type": "pickup",
        "payment_method": "Efectivo",
        "items": [{"product_id": prod.id, "quantity": 1}]
    }

    res = client.post("/api/shop/orders", json=payload)
    assert res.status_code == 200
    order_data = res.json()
    assert order_data["order_number"].startswith("PED-")

    db_session.refresh(prod)
    assert prod.stock == initial_stock - 1

def test_order_stock_insufficient_rejected(client, db_session):
    """Verifica que un pedido por encima del stock disponible sea rechazado inmediatamente (400)."""
    prod = db_session.query(Product).filter(Product.is_active == True).first()
    assert prod is not None

    payload = {
        "client_name": "Comprador Excesivo",
        "client_phone": "+5491111223344",
        "delivery_type": "pickup",
        "payment_method": "Efectivo",
        "items": [{"product_id": prod.id, "quantity": prod.stock + 999}]
    }

    res = client.post("/api/shop/orders", json=payload)
    assert res.status_code == 400
    assert "stock" in res.json()["detail"].lower()

def test_simultaneous_concurrent_orders_single_stock(client, db_session):
    """
    PRUEBA OBLIGATORIA DE CONCURRENCIA DE STOCK:
    Producto con stock = 1.
    Dos compras concurrentes 'Compra A' y 'Compra B' se envían simultáneamente en hilos paralelos.
    Resultado esperado:
    - Exactamente 1 compra aceptada (200)
    - Exactamente 1 compra rechazada (400)
    - Stock final del producto = 0 (nunca -1 ni sobreventa)
    """
    # Crear producto exclusivo con stock = 1 para esta prueba
    single_prod = Product(
        name="Producto Exclusivo 1 Unidad",
        price=10000.0,
        cost_price=5000.0,
        stock=1,
        min_stock=1,
        category="reventa",
        is_active=True
    )
    db_session.add(single_prod)
    db_session.commit()
    db_session.refresh(single_prod)
    target_id = single_prod.id

    order_a = {
        "client_name": "Compra A",
        "client_phone": "+5491199990001",
        "delivery_type": "pickup",
        "payment_method": "Efectivo",
        "items": [{"product_id": target_id, "quantity": 1}]
    }

    order_b = {
        "client_name": "Compra B",
        "client_phone": "+5491199990002",
        "delivery_type": "pickup",
        "payment_method": "Efectivo",
        "items": [{"product_id": target_id, "quantity": 1}]
    }

    def place_order(order_payload):
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        return c.post("/api/shop/orders", json=order_payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(place_order, order_a)
        future_b = executor.submit(place_order, order_b)

        res_a = future_a.result()
        res_b = future_b.result()

    statuses = [res_a.status_code, res_b.status_code]
    print(f"\n[STOCK_CONCURRENCY] Respuestas para 2 compras simultáneas con stock=1: {statuses}")

    success_count = statuses.count(200)
    rejected_count = statuses.count(400)

    assert success_count == 1, f"Se esperaba exactamente 1 compra completada, pero hubo {success_count}. Estados: {statuses}"
    assert rejected_count == 1, f"Se esperaba exactamente 1 compra rechazada por stock insuficiente, pero hubo {rejected_count}. Estados: {statuses}"

    db_session.refresh(single_prod)
    assert single_prod.stock == 0, f"El stock final debe ser exactamente 0, pero es {single_prod.stock}"
