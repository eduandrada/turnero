"""
tests/test_checkin.py - Integration & Unit Tests for Express QR Check-in System
"""
import pytest
from datetime import datetime, timedelta
from app.models import Appointment, Barber, Service
from app.core.database import get_argentina_now

def test_checkin_success_by_appointment_id(client, db_session):
    now_dt = get_argentina_now().replace(tzinfo=None)
    
    # Create test appointment for today
    appt = Appointment(
        client_name="Carlos Tevez",
        client_phone="5493834112233",
        service="Corte Barba",
        appointment_time=now_dt + timedelta(minutes=10),
        status="PENDIENTE",
        is_checked_in=False
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    # Perform check-in by appointment ID
    response = client.post("/api/public/checkin", json={
        "appointment_id": appt.id
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Carlos Tevez" in data["message"]
    assert data["appointment"]["id"] == appt.id

    # Verify DB model update
    db_session.refresh(appt)
    assert appt.is_checked_in is True
    assert appt.checked_in_at is not None

def test_checkin_success_by_phone(client, db_session):
    now_dt = get_argentina_now().replace(tzinfo=None)
    
    appt = Appointment(
        client_name="Lionel Messi",
        client_phone="5493834998877",
        service="Corte Completo",
        appointment_time=now_dt + timedelta(minutes=15),
        status="CONFIRMADO",
        is_checked_in=False
    )
    db_session.add(appt)
    db_session.commit()

    # Perform check-in by last 4 digits of phone
    response = client.post("/api/public/checkin", json={
        "phone": "8877"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Lionel Messi" in data["message"]

def test_checkin_not_found(client, db_session):
    response = client.post("/api/public/checkin", json={
        "phone": "0000"
    })

    assert response.status_code == 404
    assert "No encontramos ningún turno activo" in response.json()["detail"]
