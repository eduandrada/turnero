import os
import time
import json
import base64
import hmac
import secrets
import hashlib
from typing import Optional, Set
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser

SECRET_KEY = os.getenv("SECRET_KEY", "bladesync_secret_key_barberia_2026_x99")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Default 24 hours
security_bearer = HTTPBearer(auto_error=False)

# In-memory revocation list for logged-out tokens
REVOKED_TOKENS: Set[str] = set()

def hash_password(password: str) -> str:
    """Hash password using SHA256 with salt."""
    salt = "bladesync_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode(data_str + padding)

def create_admin_token(username: str, expires_delta_minutes: Optional[int] = None) -> str:
    """Creates a signed HMAC-SHA256 token with expiration timestamp."""
    expire_minutes = expires_delta_minutes if expires_delta_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + (expire_minutes * 60),
        "jti": secrets.token_hex(8)
    }
    
    header_bytes = json.dumps({"alg": "HS256", "typ": "JWT"}).encode('utf-8')
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    header_b64 = _base64url_encode(header_bytes)
    payload_b64 = _base64url_encode(payload_bytes)
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_token(token: str) -> dict:
    """Verifies HMAC signature, revocation status, and expiration of token."""
    if token in REVOKED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión fue cerrada. Token revocado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token de acceso inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    
    try:
        actual_sig = _base64url_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma de token inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma de token inválida o alterada.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        payload_json = _base64url_decode(payload_b64)
        payload = json.loads(payload_json.decode('utf-8'))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contenido de token ilegible.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    exp = payload.get("exp", 0)
    if int(time.time()) > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada. Por favor inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return payload

def revoke_token(token: str) -> None:
    """Adds a token to the in-memory revocation list."""
    if token:
        REVOKED_TOKENS.add(token)

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
    payload = decode_token(token)
    username = payload.get("sub")
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene un usuario válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario administrador no encontrado o inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin

