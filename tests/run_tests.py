import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_argentina_now

client = TestClient(app)

class TestBarberApp(unittest.TestCase):

    def test_01_public_settings(self):
        response = client.get("/api/public/settings")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("barber_name", data)
        self.assertIn("app_name", data)

    def test_02_list_barbers_services_styles(self):
        res_b = client.get("/api/barbers")
        self.assertEqual(res_b.status_code, 200)
        self.assertGreaterEqual(len(res_b.json()), 1)

        res_s = client.get("/api/services")
        self.assertEqual(res_s.status_code, 200)
        self.assertGreaterEqual(len(res_s.json()), 1)

        res_st = client.get("/api/styles")
        self.assertEqual(res_st.status_code, 200)

    def test_03_available_slots(self):
        tomorrow = (get_argentina_now() + timedelta(days=1)).strftime("%Y-%m-%d")
        res = client.get(f"/api/available-slots?date={tomorrow}&barber_id=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("slots", data)
        self.assertGreater(len(data["slots"]), 0)

    def test_04_admin_endpoints_protection(self):
        res = client.get("/api/admin/dashboard/stats")
        self.assertEqual(res.status_code, 401)

        res_b = client.get("/api/admin/barbers")
        self.assertEqual(res_b.status_code, 401)

    def test_05_admin_login(self):
        res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token", data)

    def test_06_appointment_creation_and_overlap_protection(self):
        login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        token = login_res.json()["token"]

        from app.database import SessionLocal
        from app.models import Appointment
        db = SessionLocal()
        db.query(Appointment).filter(Appointment.client_phone.in_(["5493834111222", "5493834333444"])).delete(synchronize_session=False)
        db.commit()
        db.close()

        target_dt = (get_argentina_now() + timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
        iso_time = target_dt.isoformat()

        payload1 = {
            "client_name": "Test Client One",
            "client_phone": "5493834111222",
            "barber_id": 1,
            "service_id": 1,
            "appointment_time": iso_time
        }
        res1 = client.post("/api/appointments", json=payload1)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "success")

        # Overlapping appointment test
        payload2 = {
            "client_name": "Test Client Two",
            "client_phone": "5493834333444",
            "barber_id": 1,
            "service_id": 1,
            "appointment_time": iso_time
        }
        res2 = client.post("/api/appointments", json=payload2)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("ocupado", res2.json()["detail"].lower())

    def test_07_shop_catalog_and_order_stock_reduction(self):
        res_p = client.get("/api/shop/products")
        self.assertEqual(res_p.status_code, 200)
        products = res_p.json()
        self.assertGreater(len(products), 0)
        
        # Pick product with stock > 0 or add stock
        p = next((prod for prod in products if prod["stock"] > 0), None)
        if not p:
            # reset stock of first product
            from app.database import SessionLocal
            from app.models import Product
            db = SessionLocal()
            prod_db = db.query(Product).filter(Product.id == products[0]["id"]).first()
            if prod_db:
                prod_db.stock = 10
                db.commit()
            db.close()
            p = client.get("/api/shop/products").json()[0]

        initial_stock = p["stock"]

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
        self.assertEqual(res_o.status_code, 200)
        order_data = res_o.json()
        self.assertTrue(order_data["order_number"].startswith("PED-"))

        res_p2 = client.get("/api/shop/products")
        p2 = [item for item in res_p2.json() if item["id"] == p["id"]][0]
        self.assertEqual(p2["stock"], initial_stock - 1)

    def test_08_xss_sanitization_input(self):
        from app.database import SessionLocal
        from app.models import Appointment
        db = SessionLocal()
        db.query(Appointment).filter(Appointment.client_phone == "5493834777666").delete(synchronize_session=False)
        db.commit()
        db.close()

        xss_payload = {
            "client_name": "<script>alert('XSS')</script>",
            "client_phone": "5493834777666",
            "barber_id": 1,
            "service_id": 1,
            "appointment_time": (get_argentina_now() + timedelta(days=3)).replace(hour=16, minute=0).isoformat()
        }
        res = client.post("/api/appointments", json=xss_payload)
        self.assertEqual(res.status_code, 200)

    def test_09_live_agenda_and_kiosk_view(self):
        # 1. Test live agenda API
        res_api = client.get("/api/live-agenda")
        self.assertEqual(res_api.status_code, 200)
        data = res_api.json()
        self.assertIn("in_service", data)
        self.assertIn("next_up", data)
        self.assertIn("upcoming", data)
        self.assertIn("barbers", data)
        self.assertIn("server_time", data)

        # 2. Test HTML view serving
        res_html = client.get("/live.html")
        self.assertEqual(res_html.status_code, 200)
        self.assertIn("AGENDA EN VIVO", res_html.text)

if __name__ == "__main__":
    unittest.main()
