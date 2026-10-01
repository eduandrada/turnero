"""
tests/test_live_agenda.py - Pruebas para Live Agenda: resolución de conflicto de rutas,
actualización de configuración (POST/PUT), llamados de turnos y clientes espontáneos.
"""
import pytest
from datetime import datetime, timedelta

def test_live_agenda_route_no_collision_with_settings(client):
    """Garantiza que /api/live-agenda/settings NO sea interpretado como {appointment_id}."""
    res = client.get("/api/live-agenda/settings")
    assert res.status_code == 200
    data = res.json()
    assert "live_tv_title" in data
    assert "live_voice_enabled" in data

def test_live_agenda_settings_save_both_post_and_put(client, encargado_token):
    """Verifica compatibilidad de guardado de configuración Live TV tanto por POST como por PUT."""
    headers = {"Authorization": f"Bearer {encargado_token}"}
    
    payload_post = {
        "live_tv_title": "BARBERÍA CENTRAL LIVE",
        "live_tv_marquee": "Aviso: Turnos por orden de llamado en pantalla",
        "live_voice_enabled": "true"
    }
    res_post = client.post("/api/live-agenda/settings", json=payload_post, headers=headers)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "success"

    # Verificar que los cambios se aplicaron
    res_get = client.get("/api/live-agenda/settings")
    assert res_get.json()["live_tv_title"] == "BARBERÍA CENTRAL LIVE"

    payload_put = {
        "live_tv_title": "BARBERÍA PREMIUM PUT",
        "live_tv_marquee": "Texto actualizado por PUT",
        "live_voice_enabled": "false"
    }
    res_put = client.put("/api/live-agenda/settings", json=payload_put, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["status"] == "success"

    res_get2 = client.get("/api/live-agenda/settings")
    assert res_get2.json()["live_tv_title"] == "BARBERÍA PREMIUM PUT"

def test_live_agenda_walk_in_and_call_lifecycle(client, encargado_token):
    """Prueba el ciclo de vida: agregar walk-in, llamar turno al televisor y cambiar estado."""
    headers = {"Authorization": f"Bearer {encargado_token}"}

    # 1. Crear cliente espontáneo (walk-in)
    walkin_payload = {
        "client_name": "Cliente Espontáneo Test",
        "client_phone": "+5491188887777",
        "barber_id": 1,
        "service_name": "Corte Rápido",
        "duration_min": 30
    }
    res_walkin = client.post("/api/live-agenda/walk-in", json=walkin_payload, headers=headers)
    assert res_walkin.status_code == 200
    appt_id = res_walkin.json()["appointment_id"]
    assert appt_id > 0

    # 2. Llamar turno a pantalla TV
    res_call = client.post(f"/api/live-agenda/{appt_id}/call", headers=headers)
    assert res_call.status_code == 200
    data_call = res_call.json()
    assert data_call["status"] == "success"
    assert data_call["current_call"]["client_name"] == "Cliente Espontáneo Test"

    # 3. Cambiar estado a ATENDIENDO y luego COMPLETADO
    res_status1 = client.post(
        f"/api/live-agenda/{appt_id}/status",
        json={"status": "ATENDIENDO"},
        headers=headers
    )
    assert res_status1.status_code == 200

    res_status2 = client.post(
        f"/api/live-agenda/{appt_id}/status",
        json={"status": "COMPLETADO"},
        headers=headers
    )
    assert res_status2.status_code == 200

    # 4. Verificar que figure en la agenda en vivo
    res_board = client.get("/api/live-agenda")
    assert res_board.status_code == 200
    data_board = res_board.json()
    assert "completed" in data_board
    completed_ids = [c["id"] for c in data_board["completed"]]
    assert appt_id in completed_ids

def test_live_agenda_operational_endpoints_require_auth(client):
    """Verifica que usuarios anónimos no puedan ejecutar acciones operativas en Live Agenda."""
    res_call = client.post("/api/live-agenda/1/call")
    assert res_call.status_code == 401

    res_status = client.post("/api/live-agenda/1/status", json={"status": "CANCELADO"})
    assert res_status.status_code == 401

    res_walkin = client.post("/api/live-agenda/walk-in", json={"client_name": "Hack"})
    assert res_walkin.status_code == 401

def test_live_agenda_finish_and_next_flow(client, encargado_token):
    """Prueba el cierre ágil de corte 'Sigue el próximo' en un solo click."""
    headers = {"Authorization": f"Bearer {encargado_token}"}

    # 1. Crear Turno 1 (en silla) y Turno 2 (pendiente)
    w1 = client.post("/api/live-agenda/walk-in", json={"client_name": "Cliente Uno", "barber_id": 1}, headers=headers).json()
    w2 = client.post("/api/live-agenda/walk-in", json={"client_name": "Cliente Dos", "barber_id": 1}, headers=headers).json()

    id1, id2 = w1["appointment_id"], w2["appointment_id"]

    # Poner Turno 1 en silla
    client.post(f"/api/live-agenda/{id1}/status", json={"status": "EN_SILLA"}, headers=headers)

    # 2. Ejecutar 1-click finish and next
    res_fn = client.post("/api/live-agenda/finish-and-next", json={"appointment_id": id1, "barber_id": 1}, headers=headers)
    assert res_fn.status_code == 200
    data = res_fn.json()
    assert data["status"] == "success"
    assert data["completed_appointment"]["id"] == id1
    assert data["next_appointment"]["id"] == id2
    assert data["speech_text"] is not None


