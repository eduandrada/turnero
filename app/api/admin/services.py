"""
app/api/admin/services.py - Endpoints de Servicios, Estilos, Categorías y Zonas de Entrega
HiddenSYNC AI 2026
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser, Service, Style, Category, DeliveryZone, AuditLog
from app.schemas import (
    ServiceRead,
    ServiceCreate,
    ServiceUpdate,
    StyleRead,
    StyleCreate,
    StyleUpdate,
    CategoryRead,
    CategoryCreate,
    DeliveryZoneRead,
    DeliveryZoneCreate,
)
from app.core.dependencies import get_current_admin, require_admin_role, require_any_staff_role

router = APIRouter(tags=["Admin Services & Catalog"])

# 1. SERVICIOS
@router.get("/api/admin/services", response_model=List[ServiceRead])
def get_admin_services(admin: AdminUser = Depends(require_any_staff_role), db: Session = Depends(get_db)):
    """Retorna todos los servicios configurados en la barbería."""
    return db.query(Service).order_by(Service.display_order.asc()).all()

@router.post("/api/admin/services", response_model=ServiceRead)
def create_admin_service(
    service_in: ServiceCreate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Crea un nuevo servicio en el catálogo."""
    s = Service(**service_in.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Crear Servicio", record_id=str(s.id), new_value=f"{s.name} - ${s.price}"))
    db.commit()
    return s

@router.put("/api/admin/services/{service_id}", response_model=ServiceRead)
def update_admin_service(
    service_id: int,
    service_in: ServiceUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza precio, duración o datos de un servicio."""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")

    old_info = f"{s.name} - ${s.price} ({s.duration_min}m)"
    for k, v in service_in.model_dump(exclude_unset=True).items():
        if k == "price" and v != s.price:
            s.previous_price = s.price
        setattr(s, k, v)
    db.commit()
    db.refresh(s)

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Editar Servicio", record_id=str(s.id), old_value=old_info, new_value=f"{s.name} - ${s.price} ({s.duration_min}m)"))
    db.commit()
    return s

@router.delete("/api/admin/services/{service_id}")
def delete_admin_service(
    service_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina un servicio del catálogo."""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")

    name = s.name
    db.delete(s)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Servicios", action="Eliminar Servicio", record_id=str(service_id), old_value=name))
    db.commit()
    return {"message": f"Servicio '{name}' eliminado."}

# 2. ESTILOS DE CORTE
@router.get("/api/admin/styles", response_model=List[StyleRead])
def get_admin_styles(admin: AdminUser = Depends(require_any_staff_role), db: Session = Depends(get_db)):
    """Retorna todos los estilos de corte."""
    return db.query(Style).order_by(Style.display_order.asc()).all()

@router.post("/api/admin/styles", response_model=StyleRead)
def create_admin_style(
    style_in: StyleCreate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Crea un nuevo estilo en el catálogo visual."""
    st = Style(**style_in.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Crear Estilo", record_id=str(st.id), new_value=st.name))
    db.commit()
    return st

@router.put("/api/admin/styles/{style_id}", response_model=StyleRead)
def update_admin_style(
    style_id: int,
    style_in: StyleUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza datos de un estilo."""
    st = db.query(Style).filter(Style.id == style_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Estilo no encontrado.")

    old_name = st.name
    for k, v in style_in.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    db.commit()
    db.refresh(st)

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Editar Estilo", record_id=str(st.id), old_value=old_name, new_value=st.name))
    db.commit()
    return st

@router.delete("/api/admin/styles/{style_id}")
def delete_admin_style(
    style_id: int,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina un estilo del catálogo visual."""
    st = db.query(Style).filter(Style.id == style_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Estilo no encontrado.")

    name = st.name
    db.delete(st)
    db.commit()

    db.add(AuditLog(user_name=admin.username, module="Estilos", action="Eliminar Estilo", record_id=str(style_id), old_value=name))
    db.commit()
    return {"message": f"Estilo '{name}' eliminado."}

# 3. CATEGORÍAS
@router.get("/api/admin/categories", response_model=List[CategoryRead])
def get_admin_categories(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista las categorías del shop."""
    return db.query(Category).order_by(Category.display_order.asc()).all()

@router.post("/api/admin/categories", response_model=CategoryRead)
def create_admin_category(
    cat_in: CategoryCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Crea una nueva categoría de productos."""
    cat = Category(**cat_in.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

# 4. ZONAS DE DELIVERY
@router.get("/api/admin/delivery-zones", response_model=List[DeliveryZoneRead])
def get_admin_delivery_zones(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista las zonas de reparto activas."""
    return db.query(DeliveryZone).all()

@router.post("/api/admin/delivery-zones", response_model=DeliveryZoneRead)
def create_admin_delivery_zone(
    dz_in: DeliveryZoneCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Crea una nueva zona de delivery y sus costos."""
    dz = DeliveryZone(**dz_in.model_dump())
    db.add(dz)
    db.commit()
    db.refresh(dz)
    return dz

@router.delete("/api/admin/delivery-zones/{zone_id}")
def delete_admin_delivery_zone(
    zone_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Elimina una zona de reparto."""
    dz = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not dz:
        raise HTTPException(status_code=404, detail="Zona de delivery no encontrada")
    db.delete(dz)
    db.commit()
    return {"message": "Zona eliminada correctamente"}
