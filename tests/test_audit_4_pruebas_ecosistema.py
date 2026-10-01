"""
tests/test_audit_4_pruebas_ecosistema.py
Auditoría y Pruebas de Fuego de Consistencia de Clientes a través de:
- /turnolive.html
- /display.html
- /checkin.html
- /admin.html (Turnos & Agenda)
"""
import pytest
from datetime import datetime, timedelta
from app.core.database import get_argentina_now

def test_prueba_1_creacion_turno_y_consistencia_cross_pantalla(client, admin_token):
    """
    PRUEBA 1:
    - Crear turno para hoy con PIN de 4 dígitos.
    - Verificar que se refleja consistentemente en admin.html (/api/admin/appointments),
      turnolive.html y display.html (/api/live-agenda).
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    now_dt = get_argentina_now()
    appt_time = (now_dt + timedelta(minutes=5)).replace(microsecond=0)

    # 1. Crear Turno
    create_res = client.post("/api/appointments", json={
        "client_name": "Maximiliano Rossi",
        "client_phone": "5493834888801",
        "barber_id": 1,
        "service": "Corte Clásico",
        "appointment_time": appt_time.isoformat()
    })
    assert create_res.status_code == 200, f"Error al crear turno: {create_res.text}"
    created = create_res.json()["appointment"]
    appt_id = created["id"]
    pin = created.get("checkin_token")

    # Verificar PIN de 4 dígitos
    assert pin is not None, "El turno debe tener un PIN asignado"
    assert len(str(pin)) == 4, f"El PIN debe ser de 4 dígitos, se obtuvo: {pin}"
    assert str(pin).isdigit(), f"El PIN debe ser numérico: {pin}"

    # 2. Verificar en /api/admin/appointments (usado por admin.html y turnolive.html)
    admin_res = client.get(f"/api/admin/appointments?date={now_dt.strftime('%Y-%m-%d')}", headers=headers)
    assert admin_res.status_code == 200
    admin_list = admin_res.json()
    matching_admin = [a for a in admin_list if a["id"] == appt_id]
    assert len(matching_admin) == 1, "El turno debe estar visible en la agenda de admin.html y turnolive.html"
    assert matching_admin[0]["client_name"] == "Maximiliano Rossi"
    assert matching_admin[0]["checkin_token"] == str(pin)
    assert matching_admin[0]["is_checked_in"] is False

    # 3. Verificar en /api/live-agenda (usado por display.html TV)
    live_res = client.get("/api/live-agenda")
    assert live_res.status_code == 200
    live_data = live_res.json()
    all_live_ids = [u["id"] for u in (live_data.get("upcoming", []) + live_data.get("next_up", []) + live_data.get("in_service", []))]
    assert appt_id in all_live_ids, "El turno debe aparecer en la cartelera / cola de display.html"


def test_prueba_2_checkin_con_pin_y_activacion_sala_espera(client, admin_token):
    """
    PRUEBA 2:
    - Cliente llega a la barbería e ingresa su PIN en checkin.html.
    - Se verifica que pasa a is_checked_in = True con su hora.
    - En admin.html / turnolive.html se refleja con insignia y en la píldora "📍 En Sala".
    - En display.html (TV) pasa a tener la insignia "📍 EN SALA DE ESPERA".
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    now_dt = get_argentina_now()
    appt_time = (now_dt + timedelta(minutes=5)).replace(microsecond=0)

    # 1. Crear Turno con Barbero 2
    create_res = client.post("/api/appointments", json={
        "client_name": "Valentin Gómez",
        "client_phone": "5493834888802",
        "barber_id": 2,
        "service": "Corte Clásico",
        "appointment_time": appt_time.isoformat()
    })
    assert create_res.status_code == 200, f"Error al crear turno: {create_res.text}"
    created = create_res.json()["appointment"]
    appt_id = created["id"]
    pin = created["checkin_token"]

    # 2. Check-in con PIN en /checkin.html (/api/public/checkin)
    checkin_res = client.post("/api/public/checkin", json={"identifier": str(pin)})
    assert checkin_res.status_code == 200, f"Error en checkin con PIN: {checkin_res.text}"
    checkin_data = checkin_res.json()
    assert checkin_data["status"] == "success"
    assert checkin_data["is_checked_in"] is True
    assert checkin_data["client_name"] == "Valentin Gómez"
    assert checkin_data["checked_in_at"] is not None

    # 3. Verificar que admin.html / turnolive.html detectan is_checked_in
    admin_res = client.get(f"/api/admin/appointments?date={now_dt.strftime('%Y-%m-%d')}", headers=headers)
    matching = [a for a in admin_res.json() if a["id"] == appt_id][0]
    assert matching["is_checked_in"] is True
    assert matching["checked_in_at"] is not None

    # 4. Verificar en display.html (/api/live-agenda)
    live_res = client.get("/api/live-agenda")
    live_data = live_res.json()
    all_live = (live_data.get("in_service", []) + 
                live_data.get("next_up", []) + 
                live_data.get("upcoming", []))
    matching_live = [x for x in all_live if x["id"] == appt_id]
    assert len(matching_live) > 0, "Debe estar en la agenda en vivo de display.html"
    assert matching_live[0]["is_checked_in"] is True
    assert matching_live[0]["checked_in_at"] is not None


def test_prueba_3_checkin_con_telefono_inteligente(client, admin_token):
    """
    PRUEBA 3:
    - Cliente llega al local y en checkin.html ingresa su número de celular (o sufijo).
    - El backend localiza el turno de hoy asociado a ese teléfono.
    - El cliente queda anunciado en sala de espera.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    now_dt = get_argentina_now()
    appt_time = (now_dt + timedelta(minutes=55)).replace(microsecond=0)
    phone = "5493834888803"

    # 1. Crear Turno con Barbero 1 (después del turno 1)
    create_res = client.post("/api/appointments", json={
        "client_name": "Lucas Benítez",
        "client_phone": phone,
        "barber_id": 1,
        "service": "Corte Clásico",
        "appointment_time": appt_time.isoformat()
    })
    assert create_res.status_code == 200, f"Error al crear turno: {create_res.text}"
    created = create_res.json()["appointment"]
    appt_id = created["id"]

    # 2. Check-in ingresando sólo el celular
    checkin_res = client.post("/api/public/checkin", json={"identifier": phone})
    assert checkin_res.status_code == 200, f"Error en checkin con teléfono: {checkin_res.text}"
    data = checkin_res.json()
    assert data["status"] == "success"
    assert data["appointment_id"] == appt_id
    assert data["client_name"] == "Lucas Benítez"
    assert data["is_checked_in"] is True

    # 3. Verificar estado en Admin y Turno Live
    admin_res = client.get(f"/api/admin/appointments?date={now_dt.strftime('%Y-%m-%d')}", headers=headers)
    matching = [a for a in admin_res.json() if a["id"] == appt_id][0]
    assert matching["is_checked_in"] is True


def test_prueba_4_flujo_sillon_y_finalizacion_sincronizada(client, admin_token):
    """
    PRUEBA 4:
    - Pasar turno a 'EN_SILLA' (Atención en sillón).
    - Verificar que display.html lo coloca en in_service ("EN SILLÓN AHORA").
    - Finalizar corte ('COMPLETADO').
    - Verificar que pasa a COMPLETADO en admin.html, turnolive.html y sale de atención activa en display.html.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    now_dt = get_argentina_now()
    appt_time = (now_dt + timedelta(minutes=55)).replace(microsecond=0)

    # 1. Crear Turno con Barbero 2 (después del turno 2)
    create_res = client.post("/api/appointments", json={
        "client_name": "Federico Silva",
        "client_phone": "5493834888804",
        "barber_id": 2,
        "service": "Corte Clásico",
        "appointment_time": appt_time.isoformat()
    })
    assert create_res.status_code == 200, f"Error al crear turno: {create_res.text}"
    appt_id = create_res.json()["appointment"]["id"]

    # 2. Pasar a EN_SILLA desde admin o turnolive
    status_res = client.put(f"/api/admin/appointments/{appt_id}/status", json={"status": "EN_SILLA"}, headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "EN_SILLA"

    # 3. Verificar en display.html (/api/live-agenda)
    live_res = client.get("/api/live-agenda")
    assert live_res.status_code == 200
    in_service = live_res.json().get("in_service", [])
    in_service_ids = [s["id"] for s in in_service]
    assert appt_id in in_service_ids, "El cliente debe figurar en 'in_service' (EN SILLÓN AHORA) en display.html"

    # 4. Finalizar turno
    finish_res = client.put(f"/api/admin/appointments/{appt_id}/status", json={"status": "COMPLETADO"}, headers=headers)
    assert finish_res.status_code == 200
    assert finish_res.json()["status"] == "COMPLETADO"

    # 5. Verificar que ya no está en in_service y figura como completado
    live_after = client.get("/api/live-agenda").json()
    in_service_after = [s["id"] for s in live_after.get("in_service", [])]
    assert appt_id not in in_service_after, "El turno completado no debe seguir en el sillón activo de la TV"

    completed_ids = [c["id"] for c in live_after.get("completed", [])]
    assert appt_id in completed_ids, "El turno completado debe figurar en la lista de completados"
