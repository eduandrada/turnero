"""
tests/test_phase22_management.py - Pruebas de Gestión Integral y Experiencia Real de Barbería (Fase 22)
Verifica: Normalización de teléfonos, Motor fonético y presets de locución, Disponibilidad con buffers,
Excepciones de calendario, Vouchers con impacto en comisiones (Business Absorbed vs Proportional),
Lista de espera (Waitlist), Ficha del cliente con notas privadas y Caja diaria.
"""
import pytest
from datetime import date, datetime
from app.utils import normalize_phone, format_turn_for_speech, build_speech_announcement
from app.models import Service, Barber, ScheduleException, Voucher, Client, BarberSchedule
from app.voucher_engine import validate_and_calculate_discount

def test_phone_normalization_comprehensive():
    """21.4: Normalización centralizada de teléfonos para Argentina e internacional."""
    # Formato con 0 y 15 (Catamarca)
    assert normalize_phone("03834 15123456") == "+5493834123456"
    # Formato con +54 9 y espacios
    assert normalize_phone("+54 9 3834 12-3456") == "+5493834123456"
    # Formato directo sin 9 pero con +54
    assert normalize_phone("+543834123456") == "+5493834123456"
    # Formato local de 10 dígitos (Catamarca)
    assert normalize_phone("3834123456") == "+5493834123456"
    # Formato internacional extranjero (ej. España +34)
    assert normalize_phone("+34 612 34 56 78") == "+34612345678"

def test_speech_normalization_and_communication_presets():
    """Signage & Audio Engine: Fonética de turnos y presets de locución con fallback gramatical."""
    # Normalización fonética
    assert format_turn_for_speech("A-125") == "A ciento veinticinco"
    assert format_turn_for_speech("B-08") == "B ocho"
    assert format_turn_for_speech("BAR-025") == "B A R veinticinco"
    assert format_turn_for_speech("045") == "cuarenta y cinco"
    assert format_turn_for_speech("T-102") == "T ciento dos"

    # Presets dinámicos con barbero
    minimal = build_speech_announcement(style="minimal", turn_code="A-125", barber_name="Martín")
    assert "A ciento veinticinco" in minimal

    urbano = build_speech_announcement(style="urbano", turn_code="A-125", barber_name="Martín")
    assert "Martín" in urbano
    assert "ya podés pasar" in urbano

    moderno = build_speech_announcement(style="moderno", turn_code="A-125", barber_name="Martín")
    assert "te esperamos con Martín" in moderno

    # Fallback sin barbero (omisión sintáctica limpia sin fallos)
    urbano_sin_barbero = build_speech_announcement(style="urbano", turn_code="B-08", barber_name="")
    assert "ya podés pasar" in urbano_sin_barbero

    moderno_sin_barbero = build_speech_announcement(style="moderno", turn_code="B-08", barber_name=None)
    assert "te esperamos para tu atención" in moderno_sin_barbero

def test_availability_engine_with_buffers_and_exceptions(client, db_session, admin_token):
    """22.1, 22.2 & 22.3: Cálculo de disponibilidad considerando duración real, buffers y excepciones."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Configurar servicio con buffers de preparación y limpieza
    service = db_session.query(Service).filter(Service.name == "Corte Clásico").first()
    service.duration_min = 30
    service.prep_buffer_min = 5
    service.clean_buffer_min = 10
    db_session.commit()

    # 2. Consultar slots para una fecha futura
    target_date = "2026-10-20"
    res = client.get(f"/api/available-slots?date={target_date}&barber_id=1&service_id={service.id}")
    assert res.status_code == 200
    slots_data = res.json()
    slots_before = [s for s in slots_data.get("slots", []) if s.get("available")]
    assert len(slots_before) > 0

    # 3. Crear una excepción (bloqueo total del día por feriado o capacitación)
    exc_payload = {
        "barber_id": 1,
        "date": target_date,
        "reason": "Capacitación Master Barber",
        "exception_type": "FERIADO"
    }
    res_exc = client.post("/api/admin/schedules/exceptions", json=exc_payload, headers=headers)
    assert res_exc.status_code == 200
    exc_id = res_exc.json()["id"]

    # 4. Ahora para esa fecha debe dar 0 slots disponibles
    res_blocked = client.get(f"/api/available-slots?date={target_date}&barber_id=1&service_id={service.id}")
    assert res_blocked.status_code == 200
    slots_after = [s for s in res_blocked.json().get("slots", []) if s.get("available")]
    assert len(slots_after) == 0

    # 5. Limpiar excepción
    del_res = client.delete(f"/api/admin/schedules/exceptions/{exc_id}", headers=headers)
    assert del_res.status_code == 200

def test_voucher_engine_rules_and_commissions(client, db_session, admin_token):
    """Vouchers & Comisiones: Descuentos porcentuales, topes, y absorción Business vs Proportional."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear voucher porcentual absorbido por el negocio (BUSINESS_ABSORBED)
    v1_code = "PROMO50BUSINESS"
    res_v1 = client.post("/api/admin/vouchers", json={
        "code": v1_code,
        "discount_type": "PERCENTAGE",
        "discount_value": 50.0,
        "max_discount_amount": 3000.0,
        "scope": "TOTAL_TICKET",
        "commission_impact": "BUSINESS_ABSORBED",
        "min_ticket_amount": 2000.0,
        "is_active": True,
        "description": "50% off con tope de $3000, la casa absorbe el descuento"
    }, headers=headers)
    assert res_v1.status_code == 200

    # Simular cálculo con ticket de $10.000
    res_preview = client.post("/api/vouchers/preview", json={
        "voucher_code": v1_code,
        "subtotal": 10000.0,
        "service_price": 10000.0
    })
    assert res_preview.status_code == 200
    data = res_preview.json()
    assert data["valid"] is True
    # 50% de 10000 es 5000, pero tiene tope de 3000
    assert data["discount_applied"] == 3000.0
    assert data["final_total"] == 7000.0
    # En BUSINESS_ABSORBED, la base de comisión del barbero se mantiene sobre el total de lista ($10.000)
    assert data["barber_commission_base"] == 10000.0
    assert data["commission_impact"] == "BUSINESS_ABSORBED"

    # 2. Crear voucher con impacto PROPORTIONAL
    v2_code = "PROMO20PROP"
    res_v2 = client.post("/api/admin/vouchers", json={
        "code": v2_code,
        "discount_type": "PERCENTAGE",
        "discount_value": 20.0,
        "scope": "TOTAL_TICKET",
        "commission_impact": "PROPORTIONAL",
        "is_active": True
    }, headers=headers)
    assert res_v2.status_code == 200

    res_prop = client.post("/api/vouchers/preview", json={
        "voucher_code": v2_code,
        "subtotal": 10000.0,
        "service_price": 10000.0
    })
    assert res_prop.status_code == 200
    data_prop = res_prop.json()
    assert data_prop["discount_applied"] == 2000.0
    assert data_prop["final_total"] == 8000.0
    # En PROPORTIONAL, la base de comisión del barbero disminuye al neto cobrado ($8.000)
    assert data_prop["barber_commission_base"] == 8000.0

    # 3. Aplicar voucher atómicamente en checkout
    res_apply = client.post("/api/vouchers/apply", json={
        "voucher_code": v1_code,
        "subtotal": 5000.0,
        "client_phone": "+5493834112233"
    }, headers=headers)
    assert res_apply.status_code == 200
    assert res_apply.json()["status"] == "success"

def test_waitlist_flow(client, admin_token):
    """22.5: Lista de espera cuando un horario no está disponible."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Registro de cliente en lista de espera
    req = {
        "client_name": "Lautaro Espera",
        "client_phone": "3834998877",
        "service_id": 1,
        "barber_id": 1,
        "preferred_date": "2026-10-25",
        "preferred_time_range": "18:00 a 20:00",
        "notes": "Si se libera el sábado después de las 18 avisarme urgente"
    }
    res = client.post("/api/waitlist", json=req)
    assert res.status_code == 200
    entry_id = res.json()["id"]

    # Administrador consulta lista de espera
    res_list = client.get("/api/admin/waitlist", headers=headers)
    assert res_list.status_code == 200
    entries = res_list.json()
    assert any(e["id"] == entry_id for e in entries)

    # Administrador atiende o elimina entrada
    res_del = client.delete(f"/api/admin/waitlist/{entry_id}", headers=headers)
    assert res_del.status_code == 200

def test_client_profile_and_private_notes(client, db_session, admin_token):
    """22.8: Historial y ficha del cliente con notas internas protegidas."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Crear o consultar un cliente
    c = db_session.query(Client).first()
    if not c:
        c = Client(name="Cliente VIP", phone="+5493834123456", email="vip@barber.com")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

    # Obtener perfil administrativo del cliente
    res_prof = client.get(f"/api/admin/clients/{c.id}/profile", headers=headers)
    assert res_prof.status_code == 200
    prof = res_prof.json()
    assert prof["id"] == c.id
    assert "total_turnos" in prof
    assert "pedidos_shop" in prof

    # Actualizar notas internas confidenciales
    res_notes = client.put(f"/api/admin/clients/{c.id}/notes", json={
        "notes": "Cliente exigente. Prefiere degradado alto con navaja y café cortado."
    }, headers=headers)
    assert res_notes.status_code == 200

    # Verificar que las notas se guardaron
    res_prof2 = client.get(f"/api/admin/clients/{c.id}/profile", headers=headers)
    assert "degradado alto con navaja" in res_prof2.json()["notes"]

def test_sales_record_and_daily_summary(client, admin_token):
    """22.16 & 22.17: Registro de ventas en caja y arqueo diario."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Registrar venta de turno en efectivo
    sale_appt = {
        "sale_type": "TURNO",
        "client_name": "Matias Venta",
        "barber_name": "barbero_test",
        "payment_method": "Efectivo",
        "original_amount": 4000.0,
        "discount_amount": 500.0,
        "final_amount": 3500.0,
        "notes": "Turno cobrado en mostrador"
    }
    res1 = client.post("/api/admin/sales", json=sale_appt, headers=headers)
    assert res1.status_code == 200

    # 2. Registrar venta de producto por Transferencia
    sale_prod = {
        "sale_type": "PRODUCTO",
        "client_name": "Matias Venta",
        "payment_method": "Transferencia",
        "original_amount": 3000.0,
        "discount_amount": 0.0,
        "final_amount": 3000.0,
        "notes": "Pomada vendida"
    }
    res2 = client.post("/api/admin/sales", json=sale_prod, headers=headers)
    assert res2.status_code == 200

    # 3. Consultar resumen de caja del día
    today_str = date.today().strftime("%Y-%m-%d")
    res_sum = client.get(f"/api/admin/sales/summary?date_str={today_str}", headers=headers)
    assert res_sum.status_code == 200
    summary = res_sum.json()
    assert summary["total_operations"] >= 2
    assert summary["total_income"] >= 6500.0
    assert "Efectivo" in summary["by_payment_method"]
    assert "Transferencia" in summary["by_payment_method"]
