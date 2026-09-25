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

        # 3. Test Display Billboard HTML
        res_tv = client.get("/display.html")
        self.assertEqual(res_tv.status_code, 200)
        self.assertIn("SIGUIENTE EN TURNO", res_tv.text)

        # 4. Test live agenda settings endpoint
        res_cfg = client.get("/api/live-agenda/settings")
        self.assertEqual(res_cfg.status_code, 200)
        self.assertIn("live_tv_title", res_cfg.json())

    def test_10_admin_password_change_invalidates_old(self):
        # 1. Login with default admin
        res_login = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["token"]

        # 2. Change password to newpass2026
        res_change = client.post(
            "/api/admin/change-password",
            json={"current_password": "admin123", "new_password": "newpass2026"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_change.status_code, 200)

        # 3. Old password admin123 MUST be rejected now!
        res_old_try = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res_old_try.status_code, 401)

        # 4. New password works
        res_new_try = client.post("/api/admin/login", json={"username": "admin", "password": "newpass2026"})
        self.assertEqual(res_new_try.status_code, 200)
        new_token = res_new_try.json()["token"]

        # 5. Restore original password admin123
        res_restore = client.post(
            "/api/admin/change-password",
            json={"current_password": "newpass2026", "new_password": "admin123"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        self.assertEqual(res_restore.status_code, 200)

    def test_11_token_logout_revocation(self):
        login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        token = login_res.json()["token"]

        # Before logout: me route works
        me_res = client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)

        # Perform logout
        logout_res = client.post("/api/admin/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logout_res.status_code, 200)

        # After logout: token is revoked and returns 401
        me_after = client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_after.status_code, 401)

    def test_12_delivery_minimum_and_inactive_zone(self):
        from app.database import SessionLocal
        from app.models import DeliveryZone, Product
        db = SessionLocal()
        
        zone = db.query(DeliveryZone).filter(DeliveryZone.name == "Zona Test Exclusiva").first()
        if not zone:
            zone = DeliveryZone(name="Zona Test Exclusiva", cost=500.0, min_order_amount=5000.0, is_active=False)
            db.add(zone)
            db.commit()
            db.refresh(zone)
        else:
            zone.is_active = False
            zone.min_order_amount = 5000.0
            db.commit()

        prod = db.query(Product).first()
        db.close()

        # Try ordering with inactive zone
        payload_inactive = {
            "client_name": "Test Minimum Client",
            "client_phone": "5493834000111",
            "delivery_type": "delivery",
            "delivery_zone_id": zone.id,
            "payment_method": "Efectivo",
            "items": [{"product_id": prod.id, "quantity": 1}]
        }
        res_inactive = client.post("/api/shop/orders", json=payload_inactive)
        self.assertEqual(res_inactive.status_code, 400)
        self.assertIn("activa", res_inactive.json()["detail"].lower())

        # Activate zone and test minimum order enforcement
        db = SessionLocal()
        zone_db = db.query(DeliveryZone).filter(DeliveryZone.id == zone.id).first()
        zone_db.is_active = True
        zone_db.min_order_amount = 999999.0  # High minimum
        db.commit()
        db.close()

        res_min = client.post("/api/shop/orders", json=payload_inactive)
        self.assertEqual(res_min.status_code, 400)
        self.assertIn("mínimo", res_min.json()["detail"].lower())

    def test_13_unique_order_number_format(self):
        res_p = client.get("/api/shop/products")
        prod = res_p.json()[0]

        order_payload = {
            "client_name": "Cliente Unique Order",
            "client_phone": "5493834999777",
            "delivery_type": "pickup",
            "payment_method": "Efectivo",
            "items": [{"product_id": prod["id"], "quantity": 1}]
        }
        res1 = client.post("/api/shop/orders", json=order_payload)
        res2 = client.post("/api/shop/orders", json=order_payload)

        num1 = res1.json()["order_number"]
        num2 = res2.json()["order_number"]

        self.assertNotEqual(num1, num2)
        self.assertRegex(num1, r"^PED-\d{8}-\d{6}-[A-F0-9]{4}$")

    def test_14_pwa_manifest_and_icons(self):
        res_m = client.get("/manifest.json")
        self.assertEqual(res_m.status_code, 200)
        manifest = res_m.json()
        self.assertIn("icons", manifest)
        self.assertGreaterEqual(len(manifest["icons"]), 2)

        res_i192 = client.get("/static/icon-192.png")
        self.assertEqual(res_i192.status_code, 200)
        self.assertEqual(res_i192.headers["content-type"], "image/png")

        res_i512 = client.get("/static/icon-512.png")
        self.assertEqual(res_i512.status_code, 200)
        self.assertEqual(res_i512.headers["content-type"], "image/png")

if __name__ == "__main__":
    unittest.main()

