"""
app/services/order_service.py - Shop Order Processing and Checkout Service.
Coordinates atomic stock decrement via InventoryService, delivery zone minimums,
customer association, voucher redemptions, and unique order numbers.
"""
import secrets
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Order, OrderItem, DeliveryZone, Client, Product
from app.core.database import get_argentina_now
from app.services.inventory_service import inventory_service
from app.services.client_service import client_service


class OrderService:
    """Service handling e-commerce orders, cart verification, and delivery calculations."""

    @staticmethod
    def process_order(
        db: Session,
        client_name: str,
        client_phone: str,
        client_email: Optional[str],
        address: Optional[str],
        neighborhood: Optional[str],
        city: Optional[str],
        notes: Optional[str],
        delivery_type: str,
        payment_method: str,
        items: List[Dict[str, Any]],
        delivery_zone_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Order:
        """Procesa una orden de compra decrementando stock de forma atómica y registrando items."""
        if not items:
            raise HTTPException(status_code=400, detail="El carrito no puede estar vacío.")

        subtotal = 0.0
        items_to_create = []

        # 1. Validar y decrementar stock atómicamente por cada item
        for item in items:
            prod_id = item.get("product_id")
            qty = int(item.get("quantity", 1))
            if qty <= 0:
                continue

            prod = db.query(Product).filter(Product.id == prod_id).first()
            if not prod or not prod.is_active:
                raise HTTPException(status_code=400, detail=f"El producto con ID {prod_id} no está disponible.")

            # Decremento atómico
            inventory_service.decrement_stock_atomic(
                db=db,
                product_id=prod_id,
                quantity=qty,
                registered_by="Shop Online",
                notes=f"Venta Online Shop - {prod.name}"
            )

            item_subtotal = prod.price * qty
            subtotal += item_subtotal
            items_to_create.append({
                "product_id": prod.id,
                "product_name": prod.name,
                "unit_price": prod.price,
                "quantity": qty,
                "subtotal": item_subtotal
            })

        # 2. Calcular costo de entrega
        delivery_cost = 0.0
        if delivery_type == "delivery":
            if not delivery_zone_id:
                raise HTTPException(status_code=400, detail="Debe seleccionar una zona de envío para entregas a domicilio.")
            dz = db.query(DeliveryZone).filter(DeliveryZone.id == delivery_zone_id, DeliveryZone.is_active == True).first()
            if not dz:
                raise HTTPException(status_code=400, detail="La zona de envío seleccionada no existe o no se encuentra activa.")
            if dz.min_order_amount and subtotal < dz.min_order_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"El monto mínimo de productos para la zona '{dz.name}' es de ${dz.min_order_amount:,.2f}. Tu subtotal es ${subtotal:,.2f}."
                )
            delivery_cost = dz.cost

        total = subtotal + delivery_cost

        # 3. Código único de orden
        unique_suffix = secrets.token_hex(2).upper()
        order_num = f"PED-{get_argentina_now().strftime('%Y%m%d-%H%M%S')}-{unique_suffix}"

        # 4. Resolver o crear cliente
        client_obj = client_service.get_or_create(db, name=client_name, phone=client_phone, email=client_email)

        new_order = Order(
            order_number=order_num,
            client_id=client_obj.id if client_obj else None,
            client_name=client_name,
            client_phone=client_phone,
            client_email=client_email,
            address=address,
            neighborhood=neighborhood,
            city=city,
            notes=notes,
            subtotal=subtotal,
            delivery_cost=delivery_cost,
            total=total,
            delivery_type=delivery_type,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            status="NUEVO"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        for it in items_to_create:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=it["product_id"],
                product_name=it["product_name"],
                unit_price=it["unit_price"],
                quantity=it["quantity"],
                subtotal=it["subtotal"]
            )
            db.add(order_item)

        db.commit()
        db.refresh(new_order)
        return new_order


order_service = OrderService()
