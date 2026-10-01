"""
tests/test_roadmap_features.py - Pruebas de integración de Pasarela de Pagos, Barber Club, Push PWA y Productividad
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import AdminUser, Barber, Appointment, Client, LoyaltyReward, ShopSetting

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_payments_config_endpoint():
    res = client.get("/api/payments/config")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "deposit_percentage" in data
    assert "provider" in data

def test_payment_preference_creation():
    payload = {
        "amount": 1500.0,
        "description": "Seña 30%: Corte de Autor",
        "client_name": "Juan Perez",
        "client_phone": "3834123456"
    }
    res = client.post("/api/payments/create-preference", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "init_point" in data

def test_loyalty_config_and_rewards():
    res = client.get("/api/loyalty/config")
    assert res.status_code == 200
    assert res.json()["enabled"] is True

    res_rewards = client.get("/api/loyalty/rewards")
    assert res_rewards.status_code == 200
    rewards = res_rewards.json()
    assert len(rewards) > 0

def test_push_config():
    res = client.get("/api/push/config")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "vapid_public_key" in data

def test_admin_login_and_productivity_report():
    from app.auth import create_admin_token
    token = create_admin_token(username="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    res_prod = client.get("/api/admin/staff/productivity", headers=headers)
    assert res_prod.status_code == 200
    prod_data = res_prod.json()
    assert "summary" in prod_data
    assert "barbers" in prod_data

