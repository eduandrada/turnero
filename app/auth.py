"""
app/auth.py - Backward compatibility facade. Re-exports authentication and authorization functions from app.core.
"""
from app.core.security import (
    SECRET_KEY,
    REVOKED_TOKENS,
    hash_password,
    verify_password,
    create_admin_token,
    decode_token,
    revoke_token,
)
from app.core.dependencies import (
    security_bearer,
    get_current_admin,
    require_admin_role,
    require_encargado_or_admin,
    require_any_staff_role,
)

__all__ = [
    "SECRET_KEY",
    "REVOKED_TOKENS",
    "hash_password",
    "verify_password",
    "create_admin_token",
    "decode_token",
    "revoke_token",
    "security_bearer",
    "get_current_admin",
    "require_admin_role",
    "require_encargado_or_admin",
    "require_any_staff_role",
]
