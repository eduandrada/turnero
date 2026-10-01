"""
app/api/shop.py - Endpoints Públicos de Shop Barber, Catálogo y Checkout
HiddenSYNC AI 2026
"""
import json
import logging
import secrets
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core.database import get_db, get_argentina_now
from app.models import Category, Product, DeliveryZone, Order, OrderItem, StockMovement, Client, IdempotencyRecord
from app.schemas import CategoryRead, ProductRead, DeliveryZoneRead, OrderRead, OrderCreate
from app.utils import normalize_phone
from app.rate_limiter import check_rate_limit

logger = logging.getLogger("hiddensync.shop")

router = APIRouter(tags=["Shop Barber"])

@router.get("/api/shop/categories", response_model=List[CategoryRead])
def list_shop_categories(db: Session = Depends(get_db)):
    """Retorna las categorías activas del shop."""
    return db.query(Category).filter(Category.is_active == True).order_by(Category.display_order.asc()).all()

@router.get("/api/shop/products", response_model=List[ProductRead])
def list_shop_products(
    category_id: Optional[int] = None,
    featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Retorna productos activos del shop sin exponer el costo mayorista."""
    query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if featured:
        query = query.filter(Product.is_featured == True)

    products = query.order_by(Product.display_order.asc()).all()
    result = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = 0.0  # Protección: ocultar costo mayorista a clientes públicos
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        result.append(p_read)
    return result

@router.get("/api/shop/delivery-zones", response_model=List[DeliveryZoneRead])
def list_delivery_zones(db: Session = Depends(get_db)):
    """Retorna zonas de delivery activas."""
    return db.query(DeliveryZone).filter(DeliveryZone.is_active == True).all()

@router.post("/api/shop/orders", response_model=OrderRead)
def create_shop_order(request: Request, order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Crea un pedido en el shop recalculando los precios en backend y
    descontando el stock de los productos. Protegido contra pedidos duplicados con Idempotency Key.
    """
    # 1. Rate Limiting de compras
    check_rate_limit(request, "shop_orders", max_requests=25, window_seconds=60)

    # 2. Idempotencia: Verificar si este pedido ya fue procesado
    idem_key = request.headers.get("X-Idempotency-Key") or getattr(order_in, "idempotency_key", None)
    if idem_key:
        cached = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idem_key,
            IdempotencyRecord.expires_at > get_argentina_now()
        ).first()
        if cached:
            cached_data = json.loads(cached.response_json)
            logger.info(f"[IDEMPOTENCY] Pedido repetido con clave '{idem_key}'. Retornando pedido en caché.")
            return OrderRead(**cached_data)

    # 3. Normalizar teléfono
    order_in.client_phone = normalize_phone(order_in.client_phone)

    if not order_in.items:
        raise HTTPException(status_code=400, detail="El carrito de compras no contiene productos.")

    subtotal = 0.0
    items_to_create = []

    for item in order_in.items:
        prod = db.query(Product).filter(Product.id == item.product_id, Product.is_active == True).first()
        if not prod:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Producto ID #{item.product_id} no disponible.")

        # Descuento atómico de stock condicional en base de datos
        stmt = (
            update(Product)
            .where(
                Product.id == item.product_id,
                Product.is_active == True,
                Product.stock >= item.quantity
            )
            .values(stock=Product.stock - item.quantity)
        )
        res = db.execute(stmt)
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{prod.name}'. Stock disponible: {prod.stock} un."
            )

        item_subtotal = prod.price * item.quantity
        subtotal += item_subtotal

        items_to_create.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "unit_price": prod.price,
            "quantity": item.quantity,
            "subtotal": item_subtotal
        })

    delivery_cost = 0.0
    if order_in.delivery_type == "delivery":
        if not order_in.delivery_zone_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar una zona de envío para entregas a domicilio."
            )
        dz = db.query(DeliveryZone).filter(
            DeliveryZone.id == order_in.delivery_zone_id,
            DeliveryZone.is_active == True
        ).first()
        if not dz:
            raise HTTPException(
                status_code=400,
                detail="La zona de envío seleccionada no existe o no se encuentra activa."
            )
        if dz.min_order_amount and subtotal < dz.min_order_amount:
            raise HTTPException(
                status_code=400,
                detail=f"El monto mínimo de productos para la zona '{dz.name}' es de ${dz.min_order_amount:,.2f}. Tu subtotal es ${subtotal:,.2f}."
            )
        delivery_cost = dz.cost

    total = subtotal + delivery_cost

    # Generar código de pedido único #PED-YYYYMMDD-HHMMSS-XXXX
    unique_suffix = secrets.token_hex(2).upper()
    order_num = f"PED-{get_argentina_now().strftime('%Y%m%d-%H%M%S')}-{unique_suffix}"

    # Buscar o crear cliente
    client_obj = db.query(Client).filter(Client.phone == order_in.client_phone).first()
    if not client_obj:
        client_obj = Client(
            name=order_in.client_name,
            phone=order_in.client_phone,
            email=order_in.client_email,
            is_active=True
        )
        db.add(client_obj)
        db.commit()
        db.refresh(client_obj)

    new_order = Order(
        order_number=order_num,
        client_id=client_obj.id if client_obj else None,
        client_name=order_in.client_name,
        client_phone=order_in.client_phone,
        client_email=order_in.client_email,
        address=order_in.address,
        neighborhood=order_in.neighborhood,
        city=order_in.city,
        notes=order_in.notes,
        subtotal=subtotal,
        delivery_cost=delivery_cost,
        total=total,
        delivery_type=order_in.delivery_type,
        payment_method=order_in.payment_method,
        idempotency_key=idem_key,
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
        db.add(StockMovement(
            product_id=it["product_id"],
            movement_type="venta",
            quantity=-it["quantity"],
            notes=f"Venta Online Pedido #{new_order.order_number}",
            registered_by="Shop Online"
        ))

    db.commit()
    db.refresh(new_order)

    if idem_key:
        order_read_dict = OrderRead.model_validate(new_order).model_dump(mode="json")
        db.add(IdempotencyRecord(
            idempotency_key=idem_key,
            request_path="/api/shop/orders",
            response_json=json.dumps(order_read_dict),
            expires_at=get_argentina_now() + timedelta(hours=24)
        ))
        db.commit()

    logger.info(f"Nuevo pedido creado {new_order.order_number} por ${total}")
    return new_order
