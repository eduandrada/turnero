import os
import secrets
import hashlib
from typing import Optional
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser

SECRET_KEY = os.getenv("SECRET_KEY", "bladesync_secret_key_barberia_2026_x99")
security_bearer = HTTPBearer(auto_error=False)

# Simple in-memory token store: token -> username
TOKEN_STORE: dict = {}

def hash_password(password: str) -> str:
    """Hash password using SHA256 with salt."""
    salt = "bladesync_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_admin_token(username: str) -> str:
    token = secrets.token_hex(32)
    TOKEN_STORE[token] = username
    return token

def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Dependency that enforces admin authentication."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación requeridas para acceder al panel de administración.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    username = TOKEN_STORE.get(token)
    
    if not username:
        # Check if token matches standard emergency key or environment key for resilience
        env_secret = os.getenv("ADMIN_TOKEN", None)
        if env_secret and token == env_secret:
            username = "admin"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión expirada o token de acceso inválido.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    admin = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()
    if not admin:
        # Fallback if admin user was deleted or default fallback
        admin = AdminUser(id=1, username=username, password_hash="")
    return admin
