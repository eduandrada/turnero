"""
app/core/security.py - Security primitives: password hashing, HMAC-SHA256 JWT tokens, and token revocation.
"""
import time
import json
import base64
import hmac
import secrets
import hashlib
import logging
from typing import Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_secret_key, verify_production_secrets
from app.core.logging import security_logger

logger = security_logger

SECRET_KEY = get_secret_key()
verify_production_secrets()

# In-memory revocation cache for instant logout check
REVOKED_TOKENS: Set[str] = set()

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${dk.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against PBKDF2 or legacy SHA256 format for backward compatibility."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            _, iter_str, salt_hex, hash_hex = parts
            iterations = int(iter_str)
            salt = bytes.fromhex(salt_hex)
            expected_dk = bytes.fromhex(hash_hex)
            actual_dk = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
            return hmac.compare_digest(expected_dk, actual_dk)
        except Exception:
            return False
    else:
        # Legacy fallback verification for existing DB entries using SHA256 + salt
        legacy_salt = "hiddensync_salt_2026"
        legacy_hash = hashlib.sha256((plain_password + legacy_salt).encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, hashed_password)

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode(data_str + padding)

def create_admin_token(username: str, expires_delta_minutes: Optional[int] = None, role: str = "admin") -> str:
    """Creates a signed HMAC-SHA256 token with expiration timestamp and user role."""
    expire_minutes = expires_delta_minutes if expires_delta_minutes is not None else 1440
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
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

def revoke_token(token: str, db: Optional[Session] = None) -> None:
    """Adds a token to the in-memory revocation list and optionally persists to DB."""
    if token:
        REVOKED_TOKENS.add(token)
        if db:
            try:
                from app.models import RevokedToken
                if not db.query(RevokedToken).filter(RevokedToken.token_str == token).first():
                    db.add(RevokedToken(token_str=token))
                    db.commit()
            except Exception as e:
                logger.error(f"Error persistiendo revocación de token: {e}")
