"""
tests/test_whatsapp.py - Pruebas para integración de WhatsApp:
Verificación de firma HMAC-SHA256, rechazo de firmas falsificadas,
mensajes a clientes y barberos, y manejo no bloqueante de fallos.
"""
import os
import hmac
import hashlib
import json
import pytest
from unittest.mock import patch, MagicMock

from app.whatsapp_service import verify_whatsapp_signature, send_whatsapp_message, send_appointment_whatsapp_notifications
from app.models import Appointment, Barber, NotificationLog

def test_whatsapp_signature_verification():
    """Prueba la validación criptográfica HMAC-SHA256 del webhook de WhatsApp."""
    secret = "test_whatsapp_secret_key_12345"
    payload = b'{"entry":[{"changes":[{"value":{"messages":[{"text":{"body":"CONFIRM_10"}}]}}]}]}'

    # 1. Firma correcta
    sig_hash = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    valid_header = f"sha256={sig_hash}"
    assert verify_whatsapp_signature(payload, valid_header, secret) is True

    # 2. Firma inválida o alterada
    invalid_header = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
    assert verify_whatsapp_signature(payload, invalid_header, secret) is False

    # 3. Encabezado ausente
    assert verify_whatsapp_signature(payload, None, secret) is False

def test_webhook_endpoint_rejects_invalid_signature(client):
    """Verifica que el endpoint /api/whatsapp-webhook rechace solicitudes con firma inválida (403)."""
    payload = json.dumps({"entry": []})
    
    # Sin header de firma
    res_no_sig = client.post("/api/whatsapp-webhook", data=payload, headers={"Content-Type": "application/json"})
    assert res_no_sig.status_code == 403

    # Con firma errónea
    res_bad_sig = client.post(
        "/api/whatsapp-webhook",
        data=payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=invalid"}
    )
    assert res_bad_sig.status_code == 403

def test_webhook_endpoint_accepts_valid_signature_and_confirms_appointment(client, db_session):
    """Verifica que un webhook con firma válida y remitente coincidente procese la confirmación del turno."""
    from datetime import datetime, timedelta
    
    secret = "test_whatsapp_secret_key_12345"
    
    # 1. Crear turno de prueba
    appt = Appointment(
        client_name="Cliente WhatsApp Test",
        client_phone="+5491177778888",
        barber_id=1,
        service_id=1,
        appointment_time=datetime.utcnow() + timedelta(days=2),
        status="PENDIENTE"
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    # 2. Construir payload de webhook simulando respuesta del cliente
    payload_dict = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "5491177778888",
                        "text": {"body": f"CONFIRM_{appt.id}"}
                    }]
                }
            }]
        }]
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig_hash = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={sig_hash}"
    }

    res = client.post("/api/whatsapp-webhook", data=payload_bytes, headers=headers)
    assert res.status_code == 200

    # 3. Verificar que el estado del turno se actualizó a CONFIRMADO
    db_session.refresh(appt)
    assert appt.status == "CONFIRMADO"
    assert appt.confirmed is True

def test_barber_private_phone_is_hidden_from_public_api(client):
    """Garantiza que el número de teléfono del barbero jamás aparezca en el perfil público."""
    res = client.get("/api/barbers")
    assert res.status_code == 200
    barbers = res.json()
    assert len(barbers) > 0
    for b in barbers:
        assert "phone" not in b or b.get("phone") is None, "¡Fuga de seguridad! El teléfono privado del barbero está expuesto públicamente."

def test_whatsapp_notification_non_blocking_on_api_error(db_session):
    """Verifica que un fallo de la API externa de WhatsApp no rompa el flujo y registre estado ERROR."""
    from datetime import datetime, timedelta
    
    appt = Appointment(
        client_name="Test Error WhatsApp",
        client_phone="+5491155554444",
        barber_id=1,
        service_id=1,
        appointment_time=datetime.utcnow() + timedelta(days=1),
        status="CONFIRMADO"
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    # Simular fallo de red o error 500 de Meta Cloud API
    with patch("app.whatsapp_service.send_whatsapp_message", return_value=(False, None, "Meta API Service Unavailable")):
        send_appointment_whatsapp_notifications(
            db=db_session,
            appointment=appt
        )

    # Verificar que se crearon los registros de notificación con estado ERROR en NotificationLog sin hacer crash
    logs = db_session.query(NotificationLog).filter(NotificationLog.appointment_id == appt.id).all()
    assert len(logs) >= 1
    for log in logs:
        assert log.status == "ERROR"
        assert log.error_details is not None
