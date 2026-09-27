"""
tests/test_concurrency_reservations.py - Pruebas de concurrencia y prevención de doble reserva simultánea.
FASE 9: Garantizar transaccionalmente que dos solicitudes concurrentes para el mismo barbero y horario
resulten en exactamente 1 reserva confirmada y 1 reserva rechazada.
"""
import pytest
import concurrent.futures
from datetime import datetime, timedelta
from app.database import get_argentina_now

def test_single_appointment_creation(client):
    """Crea una reserva válida normal."""
    target_dt = (get_argentina_now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
    payload = {
        "client_name": "Cliente Normal Test",
        "client_phone": "+5491133334444",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": target_dt.isoformat()
    }
    res = client.post("/api/appointments", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "appointment" in data

def test_sequential_double_booking_prevention(client):
    """Verifica que una reserva idéntica posterior sea rechazada con error de conflicto."""
    target_dt = (get_argentina_now() + timedelta(days=4)).replace(hour=11, minute=0, second=0, microsecond=0)
    payload1 = {
        "client_name": "Primer Cliente",
        "client_phone": "+5491122223333",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": target_dt.isoformat()
    }
    payload2 = {
        "client_name": "Segundo Cliente",
        "client_phone": "+5491144445555",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": target_dt.isoformat()
    }

    res1 = client.post("/api/appointments", json=payload1)
    assert res1.status_code == 200

    res2 = client.post("/api/appointments", json=payload2)
    assert res2.status_code in [400, 409]
    err_msg = res2.json()["detail"].lower()
    assert "ocupado" in err_msg or "disponible" in err_msg or "solap" in err_msg

def test_simultaneous_concurrent_double_booking(client):
    """
    PRUEBA OBLIGATORIA DE CONCURRENCIA:
    Lanzar 2 peticiones HTTP exactamente al mismo tiempo mediante threads paralelos
    para el mismo barbero, misma fecha y misma hora.
    Resultado esperado:
    - 1 reserva aceptada (HTTP 200)
    - 1 reserva rechazada (HTTP 400 / 409)
    - NUNCA 2 reservas confirmadas
    """
    target_dt = (get_argentina_now() + timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0)
    iso_time = target_dt.isoformat()

    payload_a = {
        "client_name": "Solicitud Simultánea A",
        "client_phone": "+5491199991111",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": iso_time
    }
    payload_b = {
        "client_name": "Solicitud Simultánea B",
        "client_phone": "+5491199992222",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": iso_time
    }

    def make_booking_request(payload):
        from fastapi.testclient import TestClient
        from app.main import app
        # Usar nuevo cliente para thread safety
        c = TestClient(app)
        return c.post("/api/appointments", json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_a = executor.submit(make_booking_request, payload_a)
        f_b = executor.submit(make_booking_request, payload_b)
        
        res_a = f_a.result()
        res_b = f_b.result()

    statuses = [res_a.status_code, res_b.status_code]
    print(f"\n[CONCURRENCY_TEST] Códigos de respuesta para reservas simultáneas: {statuses}")

    # Exactamente una exitosa y una rechazada
    success_count = statuses.count(200)
    rejected_count = statuses.count(400) + statuses.count(409)

    assert success_count == 1, f"Se esperaba exactamente 1 reserva confirmada, pero hubo {success_count}. Estados: {statuses}"
    assert rejected_count == 1, f"Se esperaba exactamente 1 reserva rechazada, pero hubo {rejected_count}. Estados: {statuses}"
