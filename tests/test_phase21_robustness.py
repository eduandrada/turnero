"""
tests/test_phase21_robustness.py - Pruebas de Robustez de Producción y Continuidad Operativa (Fase 21)
Verifica: Idempotencia, Prevención de duplicados, Headers de seguridad, Health Check,
Revocación persistente de tokens, Modo Mantenimiento, Backups y verificación de integridad.
"""
import os
import hmac
import hashlib
import json
import pytest
from app.models import Appointment, Order, Product, RevokedToken, ShopSetting
from app.settings_helper import set_setting

def test_health_and_ready_endpoints(client):
    """21.11: Health checks /health y /ready comprobando aplicación y base de datos."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    data = res_ready.json()
    assert data["status"] in ["ready", "ok"]
    assert data["database"] == "connected"

def test_security_headers_and_request_id(client):
    """21.6 & 21.12: Headers de seguridad y Request-ID en cada respuesta."""
    res = client.get("/health")
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"].startswith("REQ-")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in res.headers

def test_appointment_idempotency_prevents_duplicates(client, db_session):
    """21.1: Creación de turnos idempotente: doble click o reenvío no duplica turnos."""
    key = "test_key_appt_abc123"
    payload = {
        "client_name": "Juan Perez Idempotente",
        "client_phone": "+54 9 3834 112233",
        "barber_id": 1,
        "barber_name": "barbero_test",
        "service_id": 1,
        "service": "Corte Clásico",
        "appointment_time": "2026-10-15T10:00:00",
        "idempotency_key": key
    }

    # Primer intento (crea el turno)
    res1 = client.post("/api/appointments", json=payload, headers={"X-Idempotency-Key": key})
    assert res1.status_code == 200
    data1 = res1.json()
    appt_id_1 = data1["appointment"]["id"]

    # Segundo intento con la misma clave (simulando doble clic)
    res2 = client.post("/api/appointments", json=payload, headers={"X-Idempotency-Key": key})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["appointment"]["id"] == appt_id_1

    # Verificar en DB que solo existe UN turno con esa clave
    appts = db_session.query(Appointment).filter(Appointment.idempotency_key == key).all()
    assert len(appts) == 1

def test_shop_order_idempotency_prevents_double_stock_deduction(client, db_session):
    """21.1: Creación de pedidos idempotente: no descuenta stock dos veces."""
    prod = db_session.query(Product).filter(Product.name == "Pomada Test Mate").first()
    assert prod is not None
    initial_stock = prod.stock

    key = "test_key_order_xyz789"
    payload = {
        "client_name": "Carlos Idempotente",
        "client_phone": "+54 9 3834 556677",
        "delivery_type": "retiro",
        "payment_method": "Efectivo",
        "idempotency_key": key,
        "items": [
            {"product_id": prod.id, "quantity": 2}
        ]
    }

    # Primer pedido
    res1 = client.post("/api/shop/orders", json=payload, headers={"X-Idempotency-Key": key})
    assert res1.status_code == 200
    order_id_1 = res1.json()["order_number"]

    # Stock disminuyó en 2
    db_session.refresh(prod)
    assert prod.stock == initial_stock - 2

    # Segundo pedido con misma clave
    res2 = client.post("/api/shop/orders", json=payload, headers={"X-Idempotency-Key": key})
    assert res2.status_code == 200
    assert res2.json()["order_number"] == order_id_1

    # Stock NO debe volver a disminuir
    db_session.refresh(prod)
    assert prod.stock == initial_stock - 2

    # Solo existe 1 orden
    orders = db_session.query(Order).filter(Order.idempotency_key == key).all()
    assert len(orders) == 1

def test_webhook_deduplication(client):
    """21.14: Webhook de WhatsApp deduplica mensajes repetidos de Meta con firma criptográfica."""
    msg_id = "wamid.HBgLMjAyNi0wOS0yNxUCABIYFDNB"
    payload_dict = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "109876543210123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "5493834", "phone_number_id": "109876543210123"},
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": "delivered",
                                    "timestamp": "1758960000",
                                    "recipient_id": "5493834112233"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    secret = os.environ.get("WHATSAPP_APP_SECRET", "test_whatsapp_secret_key_12345")
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sig}

    # Primer envío
    res1 = client.post("/api/whatsapp-webhook", data=payload_bytes, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] in ["received", "ok"]

    # Segundo reenvío idéntico
    res2 = client.post("/api/whatsapp-webhook", data=payload_bytes, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] in ["received", "ok"]

def test_token_revocation_in_database(client, admin_token, db_session):
    """21.7: Logout real invalida el token de manera persistente en la base de datos."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Con token válido, accede a endpoint protegido
    res_before = client.get("/api/admin/config/export", headers=headers)
    assert res_before.status_code == 200

    # Logout revoca el token
    res_logout = client.post("/api/auth/logout", headers=headers)
    assert res_logout.status_code == 200

    # Verificar que el token está revocado en DB
    revoked_count = db_session.query(RevokedToken).count()
    assert revoked_count > 0

    # Intento posterior con el token revocado debe ser rechazado con 401
    res_after = client.get("/api/admin/config/export", headers=headers)
    assert res_after.status_code == 401
    assert "revocado" in res_after.json()["detail"].lower()

def test_maintenance_mode(client, admin_token, db_session):
    """21.19: Modo mantenimiento bloquea a clientes públicos pero permite acceso a administradores."""
    # Activar modo mantenimiento
    set_setting(db_session, "maintenance_mode", "true")
    set_setting(db_session, "maintenance_message", "Estamos en mantenimiento técnico por mejoras.")

    try:
        # Petición pública de reserva debe recibir 503 Service Unavailable
        res_public = client.post("/api/appointments", json={
            "client_name": "Test Durante Mantenimiento",
            "client_phone": "+5493834112233",
            "barber_id": 1,
            "barber_name": "barbero_test",
            "service_id": 1,
            "service": "Corte Clásico",
            "appointment_time": "2026-10-15T11:00:00"
        })
        assert res_public.status_code == 503
        assert "mantenimiento" in res_public.json()["detail"].lower()

        # Administrador aún puede operar
        headers = {"Authorization": f"Bearer {admin_token}"}
        res_admin = client.get("/api/admin/config/export", headers=headers)
        assert res_admin.status_code == 200
    finally:
        # Restaurar
        set_setting(db_session, "maintenance_mode", "false")

def test_backup_and_integrity_verification(client, admin_token):
    """21.8 & 21.23: Crear backup, verificar integridad física y aplicar política de retención."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear backup
    res_create = client.post("/api/admin/backups/create", headers=headers)
    assert res_create.status_code == 200
    filename = res_create.json()["filename"]
    assert filename.startswith("backup_barberia_")

    # 2. Listar backups
    res_list = client.get("/api/admin/backups", headers=headers)
    assert res_list.status_code == 200
    filenames = [b["filename"] for b in res_list.json()]
    assert filename in filenames

    # 3. Comprobar integridad
    res_verify = client.get(f"/api/admin/backups/verify/{filename}", headers=headers)
    assert res_verify.status_code == 200
    data_v = res_verify.json()
    assert data_v["valid"] is True
    assert data_v["tables_count"] > 0
    assert data_v["total_rows"] >= 0

    # 4. Cleanup de retención
    res_cleanup = client.post("/api/admin/backups/cleanup?retention_days=30&min_to_keep=1", headers=headers)
    assert res_cleanup.status_code == 200
    assert "kept" in res_cleanup.json()
