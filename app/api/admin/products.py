"""
app/api/admin/products.py - Endpoints de Gestión de Productos del Shop y Pedidos Online
HiddenSYNC AI 2026
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser, Product, Order, OrderItem, AuditLog
from app.schemas import ProductRead, ProductCreate, ProductUpdate, OrderRead, OrderStatusUpdate
from app.core.dependencies import get_current_admin
from app.image_service import delete_orphan_file

router = APIRouter(tags=["Admin Shop Products & Orders"])

@router.get("/api/admin/products", response_model=List[ProductRead])
def get_admin_products(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista todos los productos del catálogo comercial."""
    products = db.query(Product).order_by(Product.display_order.asc()).all()
    res = []
    for p in products:
        p_read = ProductRead.model_validate(p)
        if p.category_rel:
            p_read.category_name = p.category_rel.name
        res.append(p_read)
    return res

@router.post("/api/admin/products", response_model=ProductRead)
def create_admin_product(
    prod_in: ProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Crea un nuevo producto en el catálogo."""
    p = Product(**prod_in.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Crear Producto", record_id=str(p.id), new_value=f"{p.name} (${p.price}, stock: {p.stock})"))
    db.commit()
    return p

@router.put("/api/admin/products/{product_id}", response_model=ProductRead)
def update_admin_product(
    product_id: int,
    prod_in: ProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Actualiza datos, precios y fotos de un producto."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    old_info = f"{p.name} (${p.price}, stock: {p.stock})"
    old_image = p.image_url
    updates = prod_in.model_dump(exclude_unset=True)

    if "image_url" in updates and updates["image_url"] != old_image and old_image:
        delete_orphan_file(old_image)

    for k, v in updates.items():
        if k == "price" and v != p.price:
            p.previous_price = p.price
        setattr(p, k, v)
    db.commit()
    db.refresh(p)

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Editar Producto", record_id=str(p.id), old_value=old_info, new_value=f"{p.name} (${p.price}, stock: {p.stock})"))
    db.commit()
    return p

@router.delete("/api/admin/products/{product_id}")
def delete_admin_product(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Elimina definitivamente un producto y su archivo de imagen asociado."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    name = p.name
    old_image = p.image_url

    # Desvincular de pedidos históricos para no violar constraints de PostgreSQL
    db.query(OrderItem).filter(OrderItem.product_id == product_id).update({OrderItem.product_id: None}, synchronize_session=False)

    db.delete(p)
    db.commit()

    if old_image:
        delete_orphan_file(old_image)

    db.add(AuditLog(user_name=admin.username, module="Shop", action="Eliminar Producto", record_id=str(product_id), old_value=name))
    db.commit()
    return {"message": f"Producto '{name}' eliminado."}

@router.get("/api/admin/orders", response_model=List[OrderRead])
def get_admin_orders(
    status: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Consulta de pedidos realizados en el Shop."""
    query = db.query(Order).order_by(Order.created_at.desc())
    if status:
        query = query.filter(Order.status == status)
    return query.all()

@router.put("/api/admin/orders/{order_id}/status", response_model=OrderRead)
def update_admin_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Actualiza el estado de un pedido y restaura stock en caso de cancelación."""
    ord_obj = db.query(Order).filter(Order.id == order_id).first()
    if not ord_obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    old_status = ord_obj.status
    new_status = status_in.status

    # Si pasa a CANCELADO y no estaba cancelado previamente -> Restaurar stock
    if new_status == "CANCELADO" and old_status != "CANCELADO":
        for item in ord_obj.items:
            if item.product_id:
                prod = db.query(Product).filter(Product.id == item.product_id).first()
                if prod:
                    prod.stock += item.quantity

    ord_obj.status = new_status
    db.commit()
    db.refresh(ord_obj)

    db.add(AuditLog(
        user_name=admin.username,
        module="Pedidos",
        action="Cambio Estado Pedido",
        record_id=ord_obj.order_number,
        old_value=old_status,
        new_value=new_status
    ))
    db.commit()
    return ord_obj
