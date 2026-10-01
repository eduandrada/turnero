"""
app/api/auth.py - Endpoints de Autenticación, Sesión y Seguridad Administrativa
HiddenSYNC AI 2026
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser, AuditLog
from app.schemas import LoginRequest, LoginResponse, PasswordChangeRequest, StaffUserCreate
from app.core.security import (
    create_admin_token,
    hash_password,
    verify_password,
    revoke_token,
)
from app.core.dependencies import get_current_admin, security_bearer

logger = logging.getLogger("hiddensync.auth")

router = APIRouter(tags=["Auth"])

@router.post("/api/admin/setup-initial-admin")
def setup_initial_admin(data: StaffUserCreate, db: Session = Depends(get_db)):
    """Permite configurar el primer usuario administrador únicamente si la base de datos no tiene administradores."""
    admin_count = db.query(AdminUser).count()
    if admin_count > 0:
        raise HTTPException(
            status_code=403,
            detail="La instalación inicial ya fue completada. Endpoint deshabilitado permanentemente."
        )
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")
    new_admin = AdminUser(
        username=data.username.strip(),
        password_hash=hash_password(data.password),
        role="admin",
        is_active=True,
        can_edit_stock=True,
        can_view_finances=True,
        can_cancel_appointments=True,
        can_manage_shop=True
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    logger.info(f"[ADMIN] Primer administrador inicial '{new_admin.username}' configurado exitosamente.")
    return {"message": "Administrador inicial creado exitosamente.", "username": new_admin.username}

@router.post("/api/auth/login", response_model=LoginResponse)
@router.post("/api/admin/login", response_model=LoginResponse)
def admin_login(creds: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Inicio de sesión administrativo con hashing seguro y registro de auditoría."""
    user = db.query(AdminUser).filter(AdminUser.username == creds.username, AdminUser.is_active == True).first()
    client_ip = request.client.host if (request and request.client) else None

    if not user or not verify_password(creds.password, user.password_hash):
        db.add(AuditLog(
            user_name=creds.username or "desconocido",
            actor=creds.username or "desconocido",
            module="Seguridad",
            action="LOGIN_FALLIDO",
            description=f"Intento fallido de autenticación para el usuario '{creds.username}'",
            ip_address=client_ip
        ))
        db.commit()
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    # Auto-actualizar hash si el usuario aún tenía la versión legada
    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(creds.password)
        db.commit()

    user_role = user.role or "admin"
    token = create_admin_token(user.username, role=user_role)

    db.add(AuditLog(
        user_name=user.username,
        actor=user.username,
        module="Seguridad",
        action="LOGIN_EXITOSO",
        description=f"Inicio de sesión exitoso en el sistema. Rol asignado: {user_role}",
        ip_address=client_ip
    ))
    db.commit()

    return LoginResponse(
        token=token,
        access_token=token,
        username=user.username,
        role=user_role,
        message="Autenticación exitosa."
    )

@router.post("/api/admin/logout")
@router.post("/api/auth/logout")
def admin_logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cierre de sesión administrativo con revocación de token e historial de auditoría."""
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials, db=db)

    client_ip = request.client.host if (request and request.client) else None
    db.add(AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Seguridad",
        action="LOGOUT",
        description=f"Cierre de sesión para el usuario '{admin.username}'",
        ip_address=client_ip
    ))
    db.commit()
    return {"message": "Sesión cerrada correctamente."}

@router.get("/api/admin/me")
def get_admin_me(admin: AdminUser = Depends(get_current_admin)):
    """Retorna información y permisos del usuario administrativo autenticado."""
    return {
        "id": admin.id,
        "username": admin.username,
        "role": admin.role or "admin",
        "is_active": admin.is_active,
        "can_edit_stock": admin.can_edit_stock if admin.can_edit_stock is not None else True,
        "can_view_finances": admin.can_view_finances if admin.can_view_finances is not None else True,
        "can_cancel_appointments": admin.can_cancel_appointments if admin.can_cancel_appointments is not None else True,
        "can_manage_shop": admin.can_manage_shop if admin.can_manage_shop is not None else True
    }

@router.post("/api/admin/change-password")
def change_admin_password(
    data: PasswordChangeRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cambio seguro de contraseña para el usuario autenticado."""
    if admin.password_hash and not verify_password(data.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    
    admin.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña de administrador actualizada con éxito."}

@router.post("/api/admin/fichaje")
def record_fichaje(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Registra un fichaje de ingreso en el reloj digital de gestión (Argentina ART) en los logs de auditoría."""
    from app.core.database import get_argentina_now
    client_ip = request.client.host if (request and request.client) else None
    now_art = get_argentina_now()
    timestamp_str = now_art.strftime("%H:%M:%S ART (%d/%m/%Y)")
    
    log_entry = AuditLog(
        user_name=admin.username,
        actor=admin.username,
        module="Auditoría",
        action="FICHAJE_INGRESO",
        description=f"Fichaje de ingreso registrado en Reloj Digital Fichero a las {timestamp_str}",
        ip_address=client_ip
    )
    db.add(log_entry)
    db.commit()
    
    return {
        "status": "success",
        "username": admin.username,
        "fichaje_time": timestamp_str,
        "raw_time": now_art.strftime("%H:%M:%S")
    }

