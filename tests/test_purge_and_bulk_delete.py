import pytest
from app.models import AdminUser, Appointment, Client, Barber, NotificationLog, get_now

def test_bulk_delete_appointments(client, admin_token, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create mock appointments
    a1 = Appointment(client_name="Test Client 1", client_phone="123", service="Corte", status="COMPLETADO", appointment_time=get_now())
    a2 = Appointment(client_name="Test Client 2", client_phone="456", service="Barba", status="COMPLETADO", appointment_time=get_now())
    db_session.add(a1)
    db_session.add(a2)
    db_session.commit()
    db_session.refresh(a1)
    db_session.refresh(a2)

    res = client.post("/api/admin/appointments/bulk-delete", json={"appointment_ids": [a1.id, a2.id]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["deleted_count"] == 2

    # Verify deleted from DB
    remaining = db_session.query(Appointment).filter(Appointment.id.in_([a1.id, a2.id])).count()
    assert remaining == 0

def test_system_purge_endpoint(client, admin_token, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Test invalid confirmation
    res_bad = client.post("/api/admin/system/purge", json={"purge_appointments": True, "confirmation": "INVALID"}, headers=headers)
    assert res_bad.status_code == 400

    # Test valid purge
    res_ok = client.post("/api/admin/system/purge", json={"purge_appointments": True, "purge_messages": True, "confirmation": "CONFIRMAR"}, headers=headers)
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "success"
    assert isinstance(data["details"], list)
