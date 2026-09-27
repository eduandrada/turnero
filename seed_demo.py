"""
seed_demo.py - Sembrador de datos de demostración limpios y seguros.
Permite inicializar una base de datos de desarrollo/demo sin datos personales ni operativos reales.
"""
import os
import sys
from datetime import datetime, timedelta

# Asegurar path de importación
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal, init_db_and_migrate
from app.models import (
    AdminUser, ShopSetting, Barber, Service, Style, Client, Appointment,
    Category, Product, DeliveryZone
)
from app.auth import hash_password
from app.settings_helper import DEFAULT_SETTINGS

def seed_demo_data(db_session=None):
    close_at_end = False
    if db_session is None:
        init_db_and_migrate()
        db = SessionLocal()
        close_at_end = True
    else:
        db = db_session

    try:
        print("[DEMO] Verificando y poblando datos de demostración...")

        # 1. Administrador Demo
        if db.query(AdminUser).count() == 0:
            demo_pass = os.getenv("DEMO_ADMIN_PASSWORD", "AdminDemo2026!#")
            admin = AdminUser(
                username="admin_demo",
                password_hash=hash_password(demo_pass),
                role="admin",
                is_active=True,
                can_edit_stock=True,
                can_view_finances=True,
                can_cancel_appointments=True,
                can_manage_shop=True
            )
            db.add(admin)
            print(f"  ✓ Usuario administrador demo creado: 'admin_demo' (pass: {demo_pass})")

        # 2. Settings iniciales
        for k, v in DEFAULT_SETTINGS.items():
            if not db.query(ShopSetting).filter(ShopSetting.key == k).first():
                db.add(ShopSetting(key=k, value=str(v)))
        db.commit()
        print("  ✓ Configuración inicial de la barbería establecida.")

        # 3. Barberos Demo
        if db.query(Barber).count() == 0:
            barbers = [
                Barber(
                    name="Misael Fade Demo",
                    phone="+5491100000001",
                    specialties="Master Barber // Skin Fade & Visagismo",
                    description="Especialista en degradados a navaja y morfología facial.",
                    avatar_url="/static/barber1.png",
                    working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
                    is_active=True,
                    display_order=1
                ),
                Barber(
                    name="Enzo Scissor Demo",
                    phone="+5491100000002",
                    specialties="Classic Barber // Diseños y Texturas",
                    description="Cortes clásicos a tijera y perfilado de barba tradicional.",
                    avatar_url="/static/barber2.png",
                    working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
                    is_active=True,
                    display_order=2
                )
            ]
            db.add_all(barbers)
            db.commit()
            print("  ✓ Barberos demo registrados.")

        # 4. Servicios Demo
        if db.query(Service).count() == 0:
            services = [
                Service(
                    name="Corte Clásico & Fade",
                    description="Degradado pulido con navaja o tijera + lavado y peinado con pomada mate.",
                    duration_min=45,
                    price=4500.0,
                    category="Cortes",
                    is_active=True,
                    display_order=1
                ),
                Service(
                    name="Ritual de Barba Completo",
                    description="Toalla caliente con aceites esenciales, perfilado con navaja y bálsamo hidratante.",
                    duration_min=30,
                    price=3000.0,
                    category="Barba",
                    is_active=True,
                    display_order=2
                ),
                Service(
                    name="Combo Deluxe (Corte + Barba)",
                    description="Servicio completo de corte personalizado y perfilado artesanal de barba.",
                    duration_min=60,
                    price=6500.0,
                    category="Combos",
                    is_active=True,
                    display_order=3
                )
            ]
            db.add_all(services)
            db.commit()
            print("  ✓ Servicios demo registrados.")

        # 5. Categorías y Productos del Shop
        if db.query(Category).count() == 0:
            cat_pomadas = Category(name="Pomadas y Ceras", slug="pomadas-y-ceras", display_order=1, is_active=True)
            cat_barba = Category(name="Cuidado de Barba", slug="cuidado-de-barba", display_order=2, is_active=True)
            db.add_all([cat_pomadas, cat_barba])
            db.commit()
            db.refresh(cat_pomadas)
            db.refresh(cat_barba)

            prods = [
                Product(
                    name="Pomada Mate Alta Fijación 100g",
                    description="Efecto natural sin brillo, base de agua de fácil lavado.",
                    price=3500.0,
                    cost_price=1800.0,
                    stock=15,
                    min_stock=3,
                    category="reventa",
                    category_id=cat_pomadas.id,
                    is_active=True,
                    is_featured=True,
                    display_order=1
                ),
                Product(
                    name="Óleo Nutritivo para Barba 30ml",
                    description="Enriquecido con argán y jojoba para hidratar y suavizar vello facial.",
                    price=2800.0,
                    cost_price=1300.0,
                    stock=8,
                    min_stock=2,
                    category="reventa",
                    category_id=cat_barba.id,
                    is_active=True,
                    is_featured=True,
                    display_order=2
                )
            ]
            db.add_all(prods)
            db.commit()
            print("  ✓ Catálogo de productos y categorías demo registrados.")

        # 6. Zonas de Entrega
        if db.query(DeliveryZone).count() == 0:
            zones = [
                DeliveryZone(name="Retiro en Barbería (Pick-up)", cost=0.0, is_active=True),
                DeliveryZone(name="Zona Centro / Barrio", cost=800.0, is_active=True)
            ]
            db.add_all(zones)
            db.commit()
            print("  ✓ Zonas de delivery demo creadas.")

        print("[DEMO] ¡Población de demostración completada exitosamente!")
    finally:
        if close_at_end:
            db.close()

if __name__ == "__main__":
    seed_demo_data()
