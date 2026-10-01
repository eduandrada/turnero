"""
app/core/dependencies.py - FastAPI dependency injectors for authentication and role-based access control.
"""
from typing import Optional
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token, REVOKED_TOKENS
from app.models import AdminUser, RevokedToken

security_bearer = HTTPBearer(auto_error=False)

def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Dependency that enforces user authentication (Admin, Encargado, or Barbero)."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación requeridas para acceder al tablero de control.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    if token in REVOKED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión fue cerrada. Token revocado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check persistence in database if not cached in memory
    if db.query(RevokedToken).filter(RevokedToken.token_str == token).first():
        REVOKED_TOKENS.add(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión fue cerrada. Token revocado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    username = payload.get("sub")
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene un usuario válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_admin_role(current_user: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Dependency that ensures the authenticated user is an Administrator."""
    user_role = (current_user.role or "").strip().lower()
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren permisos de Administrador para acceder a esta sección."
        )
    return current_user

def require_encargado_or_admin(current_user: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Dependency that allows either Encargado or Admin (operational access)."""
    user_role = (current_user.role or "").strip().lower()
    if user_role not in ["admin", "encargado"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren permisos operativos de Encargado o Administrador."
        )
    return current_user

def require_any_staff_role(current_user: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Dependency that allows Admin, Encargado or Barbero."""
    user_role = (current_user.role or "").strip().lower()
    if user_role not in ["admin", "encargado", "barbero"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Permisos de personal requeridos."
        )
    return current_user
