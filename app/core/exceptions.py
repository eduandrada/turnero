"""
app/core/exceptions.py - Standard application exceptions for HiddenSYNC / Turnero.
Ensures clean error propagation across routers, services, and middlewares.
"""

class HiddenSYNCException(Exception):
    """Base exception for all domain and application errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(HiddenSYNCException):
    """Resource was not found."""
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message, code="NOT_FOUND")


class ConflictError(HiddenSYNCException):
    """Action conflicts with current state (e.g. double booking, already exists)."""
    def __init__(self, message: str = "Conflicto con el estado actual del recurso"):
        super().__init__(message, code="CONFLICT")


class ValidationError(HiddenSYNCException):
    """Business validation failure."""
    def __init__(self, message: str = "Datos de entrada inválidos"):
        super().__init__(message, code="VALIDATION_ERROR")


class AuthError(HiddenSYNCException):
    """Authentication failure (invalid credentials, expired token)."""
    def __init__(self, message: str = "No autenticado"):
        super().__init__(message, code="AUTH_ERROR")


class PermissionDeniedError(HiddenSYNCException):
    """Authorization failure (insufficient privileges)."""
    def __init__(self, message: str = "Permiso denegado"):
        super().__init__(message, code="PERMISSION_DENIED")


class CapacityExceededError(HiddenSYNCException):
    """Capacity or stock limits exceeded."""
    def __init__(self, message: str = "Capacidad o stock insuficiente"):
        super().__init__(message, code="CAPACITY_EXCEEDED")


class SecurityError(HiddenSYNCException):
    """Security violation detected (e.g. path traversal, signature mismatch)."""
    def __init__(self, message: str = "Violación de seguridad detectada"):
        super().__init__(message, code="SECURITY_ERROR")
