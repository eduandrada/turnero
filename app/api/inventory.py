"""
app/api/inventory.py - Endpoints de Inventario, Gestión de Stock y Catálogo de Productos
HiddenSYNC AI 2026
"""
import os
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db, get_argentina_now
from app.models import AdminUser, Product, StockMovement, Order, OrderItem, AuditLog
from app.schemas import (
    ProductRead,
    ProductCreate,
    ProductUpdate,
    StockAdjustment,
    StockMovementCreate,
    StockMovementRead,
    InventoryAnalyticsResponse,
)
from app.core.dependencies import get_current_admin, require_encargado_or_admin
from app.image_service import delete_orphan_file, UPLOAD_BASE_DIR

router = APIRouter(tags=["Inventory & Products"])

STATIC_DIR = os.path.dirname(UPLOAD_BASE_DIR)
UPLOAD_PRODUCTS_DIR = os.path.join(UPLOAD_BASE_DIR, "products")
os.makedirs(UPLOAD_PRODUCTS_DIR, exist_ok=True)

@router.get("/api/inventory/products", response_model=List[ProductRead])
def get_inventory_products(
    category: Optional[str] = Query(None, description="reventa o insumo"),
    alert_only: bool = Query(False, description="Solo productos con stock <= min_stock"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre"),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista productos del inventario con filtros de categoría, alertas y búsqueda."""
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    if alert_only:
        query = query.filter(Product.stock <= Product.min_stock)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.order_by(Product.display_order.asc(), Product.name.asc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        res.append(p_read)
    return res

@router.post("/api/inventory/products", response_model=ProductRead)
def create_inventory_product(
    prod_in: ProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Crea un nuevo producto en el catálogo / inventario."""
    data = prod_in.model_dump()
    if data.get("sale_price") is not None:
        data["price"] = data["sale_price"]
    if data.get("current_stock") is not None:
        data["stock"] = data["current_stock"]
    data.pop("sale_price", None)
    data.pop("current_stock", None)

    p = Product(**data)
    db.add(p)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Inventario",
        action="Crear Producto",
        record_id=str(p.id),
        new_value=f"{p.name} ({p.category}, Costo: ${p.cost_price}, Venta: ${p.price}, Stock: {p.stock})"
    ))
    db.commit()

    p_read = ProductRead.model_validate(p)
    p_read.cost_price = p.cost_price or 0.0
    p_read.sale_price = p.price or 0.0
    p_read.current_stock = p.stock or 0
    p_read.category = p.category or "reventa"
    return p_read

@router.put("/api/inventory/products/{product_id}", response_model=ProductRead)
def update_inventory_product(
    product_id: int,
    prod_in: ProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Actualiza datos y precios de un producto en inventario."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    data = prod_in.model_dump(exclude_unset=True)
    if "sale_price" in data and data["sale_price"] is not None:
        data["price"] = data["sale_price"]
    if "current_stock" in data and data["current_stock"] is not None:
        data["stock"] = data["current_stock"]
    data.pop("sale_price", None)
    data.pop("current_stock", None)

    old_info = f"{p.name} (Stock: {p.stock}, Costo: ${p.cost_price}, Venta: ${p.price})"
    old_image = p.image_url

    if "image_url" in data and data["image_url"] != old_image and old_image:
        delete_orphan_file(old_image)

    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Inventario",
        action="Editar Producto",
        record_id=str(p.id),
        old_value=old_info,
        new_value=f"{p.name} (Stock: {p.stock}, Costo: ${p.cost_price}, Venta: ${p.price})"
    ))
    db.commit()

    p_read = ProductRead.model_validate(p)
    p_read.cost_price = p.cost_price or 0.0
    p_read.sale_price = p.price or 0.0
    p_read.current_stock = p.stock or 0
    p_read.category = p.category or "reventa"
    return p_read

@router.delete("/api/inventory/products/{product_id}")
def delete_inventory_product(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Borrado lógico de producto del inventario."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    p.is_active = False
    db.commit()

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Inventario",
        action="Borrado Lógico Producto",
        record_id=str(product_id),
        old_value=p.name
    ))
    db.commit()
    return {"message": f"Producto '{p.name}' deshabilitado del inventario (borrado lógico)."}

@router.post("/api/inventory/movements", response_model=StockMovementRead)
def create_stock_movement(
    mov_in: StockMovementCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Registra un movimiento manual de stock (ingreso, egreso, uso interno, ajuste)."""
    p = db.query(Product).filter(Product.id == mov_in.product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    qty = mov_in.quantity
    m_type = mov_in.movement_type.lower()

    if m_type in ["ingreso_compra"]:
        qty = abs(qty)
        p.stock += qty
    elif m_type in ["venta", "uso_interno"]:
        qty = -abs(qty)
        if p.stock + qty < 0:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para el producto '{p.name}'. Stock actual: {p.stock}.")
        p.stock += qty
    elif m_type == "ajuste":
        p.stock += qty
        if p.stock < 0:
            p.stock = 0

    mov = StockMovement(
        product_id=p.id,
        movement_type=m_type,
        quantity=qty,
        notes=mov_in.notes,
        registered_by=mov_in.registered_by or admin.username
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)

    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Inventario",
        action=f"Movimiento {m_type.upper()}",
        record_id=str(p.id),
        new_value=f"Variación: {qty} un. Nuevo stock: {p.stock}"
    ))
    db.commit()

    res = StockMovementRead.model_validate(mov)
    res.product_name = p.name
    return res

@router.get("/api/inventory/alerts", response_model=List[ProductRead])
def get_inventory_alerts(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna productos cuyo stock actual sea menor o igual al umbral mínimo."""
    products = db.query(Product).filter(Product.is_active == True, Product.stock <= Product.min_stock).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        res.append(p_read)
    return res

@router.get("/api/inventory/analytics", response_model=InventoryAnalyticsResponse)
def get_inventory_analytics(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Calcula analíticas globales de stock, valorización e impacto de ventas."""
    active_prods = db.query(Product).filter(Product.is_active == True).all()

    total_cost = sum((p.stock or 0) * (p.cost_price or 0.0) for p in active_prods)
    total_sale = sum((p.stock or 0) * (p.price or 0.0) for p in active_prods if (p.category or 'reventa') == 'reventa')

    completed_items = db.query(OrderItem).join(Order).filter(Order.status != "CANCELADO").all()
    net_profit = 0.0
    for item in completed_items:
        p_match = db.query(Product).filter(Product.id == item.product_id).first()
        c_price = p_match.cost_price if (p_match and p_match.cost_price) else 0.0
        net_profit += ((item.unit_price or 0.0) - c_price) * (item.quantity or 1)

    low_stock_items = [p for p in active_prods if (p.stock or 0) <= (p.min_stock or 2)]

    return InventoryAnalyticsResponse(
        total_products=len(active_prods),
        total_valuation_cost=total_cost,
        total_valuation_sale=total_sale,
        total_net_profit_recorded=net_profit,
        low_stock_count=len(low_stock_items)
    )

@router.get("/api/products", response_model=List[ProductRead])
def get_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Consulta de productos para el panel de administración / encargado."""
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    if search:
        s_term = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(s_term), Product.description.ilike(s_term)))

    products = query.order_by(Product.display_order.asc(), Product.id.desc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        p_read.cost_price = p.cost_price or 0.0
        p_read.sale_price = p.price or 0.0
        p_read.current_stock = p.stock or 0
        p_read.category = p.category or "reventa"
        res.append(p_read)
    return res

@router.post("/api/products", response_model=ProductRead)
async def create_product_with_photo(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    stock: int = Form(0),
    category: Optional[str] = Form("reventa"),
    cost_price: Optional[float] = Form(0.0),
    min_stock: Optional[int] = Form(2),
    file: Optional[UploadFile] = File(None),
    actor: Optional[str] = Form(None),
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Creación de producto con carga de fotografía multipart/form-data."""
    image_url = None
    if file and file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if not file_ext or file_ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            file_ext = ".jpg"

        timestamp_str = str(int(get_argentina_now().timestamp()))
        safe_filename = f"prod_{timestamp_str}_{secrets.token_hex(4)}{file_ext}"
        file_path = os.path.join(UPLOAD_PRODUCTS_DIR, safe_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        image_url = f"/static/uploads/products/{safe_filename}"

    new_prod = Product(
        name=name.strip(),
        description=description.strip() if description else None,
        price=price,
        stock=stock,
        cost_price=cost_price or 0.0,
        category=category or "reventa",
        min_stock=min_stock or 2,
        image_url=image_url,
        is_active=True,
        created_at=get_argentina_now().replace(tzinfo=None)
    )
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)

    client_ip = request.client.host if (request and request.client) else None
    actor_name = current_user.username

    db.add(AuditLog(
        user_name=actor_name,
        actor=actor_name,
        module="Productos",
        action="CREAR_PRODUCTO",
        description=f"Nuevo producto creado: '{name}' (${price:.2f}) - Stock Inicial: {stock}",
        record_id=str(new_prod.id),
        new_value=f"Precio: ${price:.2f}, Stock: {stock}",
        ip_address=client_ip
    ))

    if stock > 0:
        db.add(StockMovement(
            product_id=new_prod.id,
            movement_type="ingreso_compra",
            quantity=stock,
            notes="Carga inicial al crear producto",
            registered_by=actor_name
        ))

    db.commit()

    p_read = ProductRead.model_validate(new_prod)
    p_read.cost_price = new_prod.cost_price or 0.0
    p_read.sale_price = new_prod.price or 0.0
    p_read.current_stock = new_prod.stock or 0
    p_read.category = new_prod.category or "reventa"
    return p_read

@router.patch("/api/products/{product_id}/stock", response_model=ProductRead)
def adjust_product_stock(
    product_id: int,
    request: Request,
    adj: StockAdjustment,
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Ajuste rápido de stock de un producto con auditoría de movimientos."""
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    old_stock = product.stock or 0

    if adj.stock is not None:
        new_stock = max(0, adj.stock)
        delta = new_stock - old_stock
    elif adj.quantity is not None:
        delta = adj.quantity
        new_stock = max(0, old_stock + delta)
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'quantity' (variación) o 'stock' (valor absoluto).")

    product.stock = new_stock

    actor_name = current_user.username
    action_type = adj.action_type or ("VENTA_PRODUCTO" if delta < 0 else "MODIFICAR_STOCK")

    m_type = "venta" if delta < 0 else "ingreso_compra"
    if adj.action_type == "AJUSTE_STOCK":
        m_type = "ajuste"

    db.add(StockMovement(
        product_id=product.id,
        movement_type=m_type,
        quantity=delta,
        notes=adj.reason or f"Ajuste manual de stock por {actor_name}",
        registered_by=actor_name
    ))

    db.add(AuditLog(
        user_name=actor_name,
        actor=actor_name,
        module="Productos",
        action=action_type,
        description=f"Stock de '{product.name}' modificado: {old_stock} -> {new_stock} (Delta: {delta:+d})",
        record_id=str(product.id),
        old_value=f"Stock: {old_stock}",
        new_value=f"Stock: {new_stock}",
        ip_address=request.client.host if (request and request.client) else None
    ))

    db.commit()
    db.refresh(product)

    p_read = ProductRead.model_validate(product)
    p_read.cost_price = product.cost_price or 0.0
    p_read.sale_price = product.price or 0.0
    p_read.current_stock = product.stock or 0
    p_read.category = product.category or "reventa"
    return p_read
