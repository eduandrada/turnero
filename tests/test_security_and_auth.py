"""
tests/test_security_and_auth.py - Pruebas exhaustivas de Autenticación, Autorización (RBAC) y Seguridad.
"""
import pytest
import time
from app.auth import create_admin_token

def test_public_endpoints_accessible_without_token(client):
    """Verifica que los endpoints públicos respondan 200 sin autenticación."""
    public_routes = [
        "/api/public/settings",
        "/api/barbers",
        "/api/services",
        "/api/shop/products",
        "/api/shop/categories",
        "/api/live-agenda",
        "/api/live-agenda/settings"
    ]
    for route in public_routes:
        res = client.get(route)
        assert res.status_code == 200, f"Ruta pública falló con código {res.status_code}: {route}"

def test_protected_endpoints_require_authentication(client):
    """Verifica que endpoints sensibles rechacen peticiones sin token (401)."""
    protected_gets = [
        "/api/admin/appointments",
        "/api/admin/settings",
        "/api/admin/audit-logs",
        "/api/audit-logs",
        "/api/admin/backups",
        "/api/products",
        "/api/admin/staff"
    ]
    for route in protected_gets:
        res = client.get(route)
        assert res.status_code == 401, f"Ruta protegida no rechazó sin token ({res.status_code}): {route}"

def test_role_authorization_barbero_forbidden_admin_sections(client, barbero_token):
    """Verifica que un Barbero NO pueda acceder a auditoría, configuración ni backups (403)."""
    headers = {"Authorization": f"Bearer {barbero_token}"}

    res_audit = client.get("/api/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 403

    res_audit_alt = client.get("/api/audit-logs", headers=headers)
    assert res_audit_alt.status_code == 403

    res_settings = client.get("/api/admin/settings", headers=headers)
    assert res_settings.status_code == 403

    res_backups = client.get("/api/admin/backups", headers=headers)
    assert res_backups.status_code == 403

    res_staff = client.get("/api/admin/staff", headers=headers)
    assert res_staff.status_code == 403

def test_role_authorization_encargado_permissions(client, encargado_token):
    """Verifica permisos de Encargado: puede operar stock y live agenda, pero no auditoría global ni backups."""
    headers = {"Authorization": f"Bearer {encargado_token}"}

    # Encargado NO puede acceder a auditoría global ni backups
    res_audit = client.get("/api/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 403

    res_backups = client.get("/api/admin/backups", headers=headers)
    assert res_backups.status_code == 403

    # Encargado SÍ puede consultar inventario operativo
    res_prod = client.get("/api/products", headers=headers)
    assert res_prod.status_code == 200

def test_role_authorization_admin_full_access(client, admin_token):
    """Verifica que el Administrador tenga acceso a todas las áreas sensibles."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    res_audit = client.get("/api/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 200

    res_settings = client.get("/api/admin/settings", headers=headers)
    assert res_settings.status_code == 200

    res_backups = client.get("/api/admin/backups", headers=headers)
    assert res_backups.status_code == 200

def test_login_success_and_failure(client):
    """Prueba flujo de login con credenciales correctas e incorrectas."""
    # 1. Password incorrecta -> 401
    res_fail = client.post("/api/admin/login", json={"username": "admin_test", "password": "WrongPassword!"})
    assert res_fail.status_code == 401
    data_fail = res_fail.json()
    assert data_fail["success"] is False
    assert "detail" in data_fail

    # 2. Password correcta -> 200 con token y rol
    res_ok = client.post("/api/admin/login", json={"username": "admin_test", "password": "AdminTest2026!#"})
    assert res_ok.status_code == 200
    data_ok = res_ok.json()
    assert "token" in data_ok
    assert data_ok["role"] == "admin"

def test_token_tampering_and_revocation(client, admin_token):
    """Verifica que tokens alterados sean rechazados y tokens deslogueados sean revocados."""
    # 1. Token alterado -> 401
    tampered = admin_token[:-4] + "xxxx"
    res_tampered = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {tampered}"})
    assert res_tampered.status_code == 401

    # 2. Logout exitoso y revocación
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_logout = client.post("/api/admin/logout", headers=headers)
    assert res_logout.status_code == 200

    # 3. Intentar reusar token revocado -> 401
    res_reuse = client.get("/api/admin/audit-logs", headers=headers)
    assert res_reuse.status_code == 401
    assert "revocado" in res_reuse.json()["detail"].lower()


def test_token_expiration(client):
    """Verifica que un token expirado en el tiempo sea rechazado con 401."""
    from app.core.security import create_admin_token

    expired_token = create_admin_token(
        username="admin_test",
        expires_delta_minutes=-10,
        role="admin"
    )
    res = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expirada" in res.json()["detail"].lower()

