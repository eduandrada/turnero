"""
tests/test_appointment_status_management.py
Pruebas integrales para la gestión de estados de turnos:
Confirmar, En Silla, Completar (atendido), Cancelar y Reactivar,
además de la verificación de la bandeja limpia (filtro activos).
"""
import pytest
from datetime import datetime, timedelta, timezone

def test_appointment_full_status_lifecycle_and_clean_board(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_dt = (datetime.now(timezone.utc) + timedelta(days=5)).replace(minute=0, second=0, microsecond=0)
    target_date_str = target_dt.strftime("%Y-%m-%d")

    # 1. Crear 2 turnos para la misma fecha
    appt1_payload = {
        "client_name": "Juan Perez Test",
        "client_phone": "+5491144445555",
        "client_email": "juan@test.com",
        "barber_id": 1,
        "service": "Corte Clásico",
        "appointment_time": (target_dt.replace(hour=14)).isoformat()
    }
    res1 = client.post("/api/appointments", json=appt1_payload)
    assert res1.status_code == 200
    appt1_id = res1.json()["appointment"]["id"]

    appt2_payload = {
        "client_name": "Carlos Gomez Test",
        "client_phone": "+5491166667777",
        "client_email": "carlos@test.com",
        "barber_id": 1,
        "service": "Barba y Afeitado",
        "appointment_time": (target_dt.replace(hour=15)).isoformat()
    }
    res2 = client.post("/api/appointments", json=appt2_payload)
    assert res2.status_code == 200
    appt2_id = res2.json()["appointment"]["id"]

    # 2. Inicialmente ambos deben ser PENDIENTE y aparecer en "activos"
    res_active_init = client.get(f"/api/admin/appointments?date={target_date_str}&status=activos", headers=headers)
    assert res_active_init.status_code == 200
    active_ids = [item["id"] for item in res_active_init.json()]
    assert appt1_id in active_ids
    assert appt2_id in active_ids

    # 3. Confirmar appt1
    res_conf = client.put(f"/api/admin/appointments/{appt1_id}/status", json={"status": "CONFIRMADO"}, headers=headers)
    assert res_conf.status_code == 200
    data_conf = res_conf.json()
    assert data_conf["status"] == "CONFIRMADO"
    assert data_conf["confirmed"] is True
    assert data_conf["canceled"] is False

    # 4. Pasar appt1 a EN_SILLA (en atención)
    res_silla = client.put(f"/api/admin/appointments/{appt1_id}/status", json={"status": "EN_SILLA"}, headers=headers)
    assert res_silla.status_code == 200
    data_silla = res_silla.json()
    assert data_silla["status"] == "EN_SILLA"

    # 5. Completar appt1 (Cliente atendido) -> Deja la bandeja limpia
    res_comp = client.put(f"/api/admin/appointments/{appt1_id}/status", json={"status": "COMPLETADO"}, headers=headers)
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert data_comp["status"] == "COMPLETADO"
    assert data_comp["confirmed"] is True
    assert data_comp["canceled"] is False

    # 6. Cancelar appt2
    res_canc = client.put(f"/api/admin/appointments/{appt2_id}/status", json={"status": "CANCELADO"}, headers=headers)
    assert res_canc.status_code == 200
    data_canc = res_canc.json()
    assert data_canc["status"] == "CANCELADO"
    assert data_canc["canceled"] is True

    # 7. Comprobar que en 'activos' la bandeja queda LIMPIA (ninguno de los dos aparece)
    res_active_clean = client.get(f"/api/admin/appointments?date={target_date_str}&status=activos", headers=headers)
    assert res_active_clean.status_code == 200
    active_clean_ids = [item["id"] for item in res_active_clean.json()]
    assert appt1_id not in active_clean_ids
    assert appt2_id not in active_clean_ids

    # 8. Comprobar que appt1 aparece en 'completados'
    res_completed = client.get(f"/api/admin/appointments?date={target_date_str}&status=completados", headers=headers)
    assert res_completed.status_code == 200
    completed_ids = [item["id"] for item in res_completed.json()]
    assert appt1_id in completed_ids
    assert appt2_id not in completed_ids

    # 9. Comprobar que appt2 aparece en 'cancelados'
    res_canceled = client.get(f"/api/admin/appointments?date={target_date_str}&status=cancelados", headers=headers)
    assert res_canceled.status_code == 200
    canceled_ids = [item["id"] for item in res_canceled.json()]
    assert appt2_id in canceled_ids
    assert appt1_id not in canceled_ids

    # 10. Reactivar appt2 de vuelta a PENDIENTE
    res_reactivate = client.put(f"/api/admin/appointments/{appt2_id}/status", json={"status": "PENDIENTE"}, headers=headers)
    assert res_reactivate.status_code == 200
    assert res_reactivate.json()["status"] == "PENDIENTE"
    assert res_reactivate.json()["canceled"] is False

    # Debe volver a aparecer en 'activos'
    res_active_after = client.get(f"/api/admin/appointments?date={target_date_str}&status=activos", headers=headers)
    assert res_active_after.status_code == 200
    after_ids = [item["id"] for item in res_active_after.json()]
    assert appt2_id in after_ids
    assert appt1_id not in after_ids
