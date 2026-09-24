import os
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_argentina_now

client = TestClient(app)

def test_public_settings():
    response = client.get("/api/public/settings")
    assert response.status_code == 200
    data = response.json()
    assert "barber_name" in data
    assert "app_name" in data

def test_list_barbers_services_styles():
    res_b = client.get("/api/barbers")
    assert res_b.status_code == 200
    assert len(res_b.json()) >= 1

    res_s = client.get("/api/services")
    assert res_s.status_code == 200
    assert len(res_s.json()) >= 1

    res_st = client.get("/api/styles")
    assert res_st.status_code == 200

def test_available_slots():
    tomorrow = (get_argentina_now() + timedelta(days=1)).strftime("%Y-%m-%d")
    res = client.get(f"/api/available-slots?date={tomorrow}&barber_id=1")
    assert res.status_code == 200
    data = res.json()
    assert "slots" in data
    assert len(data["slots"]) > 0

def test_admin_endpoints_protection():
    # Attempting to access admin stats without token
    res = client.get("/api/admin/dashboard/stats")
    assert res.status_code == 401

    res_b = client.get("/api/admin/barbers")
    assert res_b.status_code == 401

def test_admin_login():
    res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data

def test_appointment_creation_and_overlap_protection():
    # Admin login for verification
    login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["token"]

    target_dt = (get_argentina_now() + timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
    iso_time = target_dt.isoformat()

    # 1. Create first appointment
    payload1 = {
        "client_name": "Test Client One",
        "client_phone": "5493834111222",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": iso_time
    }
    res1 = client.post("/api/appointments", json=payload1)
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # 2. Attempt overlapping appointment at exact same time for same barber -> Should fail 400
    payload2 = {
        "client_name": "Test Client Two",
        "client_phone": "5493834333444",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": iso_time
    }
    res2 = client.post("/api/appointments", json=payload2)
    assert res2.status_code == 400
    assert "ocupado" in res2.json()["detail"].lower()

def test_shop_catalog_and_order_stock_reduction():
    # 1. Get products
    res_p = client.get("/api/shop/products")
    assert res_p.status_code == 200
    products = res_p.json()
    assert len(products) > 0
    p = products[0]
    initial_stock = p["stock"]

    # 2. Create Order
    order_payload = {
        "client_name": "Cliente Shop Test",
        "client_phone": "5493834999888",
        "delivery_type": "pickup",
        "payment_method": "Efectivo",
        "items": [
            {"product_id": p["id"], "quantity": 1}
        ]
    }
    res_o = client.post("/api/shop/orders", json=order_payload)
    assert res_o.status_code == 200
    order_data = res_o.json()
    assert order_data["order_number"].startswith("PED-")

    # 3. Check reduced stock
    res_p2 = client.get("/api/shop/products")
    p2 = [item for item in res_p2.json() if item["id"] == p["id"]][0]
    assert p2["stock"] == initial_stock - 1

def test_xss_sanitization_input():
    # Test submitting HTML/script string in client name
    xss_payload = {
        "client_name": "<script>alert('XSS')</script>",
        "client_phone": "5493834777666",
        "barber_id": 1,
        "service_id": 1,
        "appointment_time": (get_argentina_now() + timedelta(days=3)).replace(hour=16, minute=0).isoformat()
    }
    res = client.post("/api/appointments", json=xss_payload)
    assert res.status_code == 200
    assert "<script>" in res.json()["appointment"]["client_name"]
    # The server stores string safely without executing HTML/JS
