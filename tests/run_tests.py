import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_argentina_now, init_db_and_migrate

# Run migrations on database schema before tests execute
init_db_and_migrate()

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
        now_dt = get_argentina_now()
        open_date = None
        closed_date = None

        for days_ahead in range(1, 14):
            candidate = now_dt + timedelta(days=days_ahead)
            if candidate.weekday() != 6 and open_date is None:
                open_date = candidate.strftime("%Y-%m-%d")
            elif candidate.weekday() == 6 and closed_date is None:
                closed_date = candidate.strftime("%Y-%m-%d")
            if open_date and closed_date:
                break

        # 1. Test open day (Mon-Sat) returns available slots
        res_open = client.get(f"/api/available-slots?date={open_date}&barber_id=1")
        self.assertEqual(res_open.status_code, 200)
        data_open = res_open.json()
        self.assertIn("slots", data_open)
        self.assertGreater(len(data_open["slots"]), 0)

        # 2. Test closed day (Sunday) returns 0 slots
        if closed_date:
            res_closed = client.get(f"/api/available-slots?date={closed_date}&barber_id=1")
            self.assertEqual(res_closed.status_code, 200)
            data_closed = res_closed.json()
            self.assertEqual(len(data_closed["slots"]), 0)

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
        
        prod = db.query(Product).first()
        if prod:
            prod.stock = 50
            prod_id = prod.id
        else:
            prod_id = 1

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

        zone_id = zone.id
        db.close()

        # Try ordering with inactive zone
        payload_inactive = {
            "client_name": "Test Minimum Client",
            "client_phone": "5493834000111",
            "delivery_type": "delivery",
            "delivery_zone_id": zone_id,
            "payment_method": "Efectivo",
            "items": [{"product_id": prod_id, "quantity": 1}]
        }
        res_inactive = client.post("/api/shop/orders", json=payload_inactive)
        self.assertEqual(res_inactive.status_code, 400)
        self.assertIn("activa", res_inactive.json()["detail"].lower())

        # Activate zone and test minimum order enforcement
        db = SessionLocal()
        zone_db = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
        zone_db.is_active = True
        zone_db.min_order_amount = 999999.0  # High minimum
        db.commit()
        db.close()

        res_min = client.post("/api/shop/orders", json=payload_inactive)
        self.assertEqual(res_min.status_code, 400)
        self.assertIn("mínimo", res_min.json()["detail"].lower())

    def test_13_unique_order_number_format(self):
        from app.database import SessionLocal
        from app.models import Product
        db = SessionLocal()
        prod_db = db.query(Product).first()
        if prod_db:
            prod_db.stock = 50
            db.commit()
            prod_id = prod_db.id
        else:
            prod_id = 1
        db.close()

        order_payload = {
            "client_name": "Cliente Unique Order",
            "client_phone": "5493834999777",
            "delivery_type": "pickup",
            "payment_method": "Efectivo",
            "items": [{"product_id": prod_id, "quantity": 1}]
        }
        res1 = client.post("/api/shop/orders", json=order_payload)
        self.assertEqual(res1.status_code, 200)
        res2 = client.post("/api/shop/orders", json=order_payload)
        self.assertEqual(res2.status_code, 200)

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

    def test_15_available_slots_edge_cases(self):
        # 1. Invalid date format returns 400
        res_invalid_date = client.get("/api/available-slots?date=2026-13-45&barber_id=1")
        self.assertEqual(res_invalid_date.status_code, 400)
        self.assertIn("inválido", res_invalid_date.json()["detail"].lower())

        # 2. Appointment in past time returns 400
        past_time = (get_argentina_now() - timedelta(days=1)).isoformat()
        payload_past = {
            "client_name": "Cliente Pasado",
            "client_phone": "5493834000999",
            "barber_id": 1,
            "service_id": 1,
            "appointment_time": past_time
        }
        res_past = client.post("/api/appointments", json=payload_past)
        self.assertEqual(res_past.status_code, 400)
        self.assertIn("transcurridos", res_past.json()["detail"].lower())

    def test_16_inventory_module_and_stock_movements(self):
        login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create inventory product
        prod_payload = {
            "name": "Pomada Insumo Test",
            "category": "insumo",
            "cost_price": 3000.0,
            "sale_price": 0.0,
            "current_stock": 5,
            "min_stock": 2,
            "sku": "INS-TEST-01"
        }
        create_res = client.post("/api/inventory/products", json=prod_payload, headers=headers)
        self.assertEqual(create_res.status_code, 200)
        prod_data = create_res.json()
        prod_id = prod_data["id"]
        self.assertEqual(prod_data["category"], "insumo")
        self.assertEqual(prod_data["cost_price"], 3000.0)

        # 2. Get inventory products list
        list_res = client.get("/api/inventory/products?category=insumo", headers=headers)
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(p["id"] == prod_id for p in list_res.json()))

        # 3. Post stock movement (ingreso_compra +10)
        mov_payload = {
            "product_id": prod_id,
            "movement_type": "ingreso_compra",
            "quantity": 10,
            "notes": "Compra Distribuidor Test"
        }
        mov_res = client.post("/api/inventory/movements", json=mov_payload, headers=headers)
        self.assertEqual(mov_res.status_code, 200)
        self.assertEqual(mov_res.json()["quantity"], 10)

        # 4. Analytics endpoint
        analytics_res = client.get("/api/inventory/analytics", headers=headers)
        self.assertEqual(analytics_res.status_code, 200)
        data = analytics_res.json()
        self.assertIn("total_inventory_cost", data)
        self.assertIn("critical_products", data)

        # 5. Delete product (logical delete)
        del_res = client.delete(f"/api/inventory/products/{prod_id}", headers=headers)
        self.assertEqual(del_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()

