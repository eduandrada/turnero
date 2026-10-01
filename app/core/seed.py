"""
app/core/seed.py - Inicialización y datos por defecto del sistema
HiddenSYNC AI 2026
"""
import os
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    AdminUser, Barber, Service, Style, Category, Product, DeliveryZone
)
from app.core.security import hash_password

logger = logging.getLogger("hiddensync.seed")

def seed_initial_data():
    """Siembra usuario administrador, barberos, servicios, productos y configuraciones iniciales."""
    db: Session = SessionLocal()
    try:
        # 1. Admin User
        admin_user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin_user:
            initial_password = (os.getenv("ADMIN_INITIAL_PASSWORD") or "").strip()
            if not initial_password:
                logger.warning(
                    "[ADMIN BOOTSTRAP SEGURO] Variable 'ADMIN_INITIAL_PASSWORD' no configurada. "
                    "Por seguridad, no se creará automáticamente un usuario administrador inseguro. "
                    "Defina ADMIN_INITIAL_PASSWORD o inicialice el primer admin mediante POST /api/admin/setup-initial-admin."
                )
            else:
                default_admin = AdminUser(
                    username="admin",
                    password_hash=hash_password(initial_password),
                    role="admin",
                    is_active=True,
                    can_edit_stock=True,
                    can_view_finances=True,
                    can_cancel_appointments=True,
                    can_manage_shop=True
                )
                db.add(default_admin)
                db.commit()
                logger.info("[BOOTSTRAP] Usuario administrador inicial 'admin' creado exitosamente.")

        # 2. Staff Barbers iniciales
        if db.query(Barber).count() == 0:
            barbers = [
                Barber(
                    name="Misael",
                    phone="5493834000001",
                    specialties="Fade Master, Barboterapia, Diseño y Visagismo",
                    description="Especialista en cortes modernos, degradados a navaja y asesoría de imagen capilar.",
                    avatar_url="https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80",
                    experience="8 años de trayectoria",
                    featured_styles="Skin Fade, French Crop, Barba Esculpida",
                    is_active=True,
                    display_order=1
                ),
                Barber(
                    name="Ale",
                    phone="5493834000002",
                    specialties="Tijera Clásica, Pompadour, Ritual Tradicional",
                    description="Maestro de la vieja escuela, precisión milimétrica en tijera y afeitados tradicionales.",
                    avatar_url="https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=400&q=80",
                    experience="6 años de trayectoria",
                    featured_styles="Pompadour, Taper Fade, Afeitado Tradicional",
                    is_active=True,
                    display_order=2
                ),
                Barber(
                    name="Gabo",
                    phone="5493834000003",
                    specialties="Freestyle Hair Art, Texturizados, Colorimetría",
                    description="Innovador urbano, líneas nítidas, degradados limpios y styling de vanguardia.",
                    avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
                    experience="5 años de trayectoria",
                    featured_styles="Low Fade, Freestyle, Diseños Navaja",
                    is_active=True,
                    display_order=3
                )
            ]
            db.add_all(barbers)
            db.commit()

        # 3. Servicios iniciales
        if db.query(Service).count() == 0:
            services = [
                Service(
                    name="Corte Signature Fade",
                    description="Degradado milimétrico a elección (Low, Mid, High), lavado premium con masaje capilar y peinado con cera mate.",
                    duration_min=45,
                    price=4500.0,
                    previous_price=5000.0,
                    category="Cortes",
                    is_active=True,
                    display_order=1
                ),
                Service(
                    name="Barba Ritual + Toalla Caliente",
                    description="Vapor ozonizado, perfilado a navaja japonesa con aceites esenciales orgánicos.",
                    duration_min=30,
                    price=3000.0,
                    previous_price=3500.0,
                    category="Barba",
                    is_active=True,
                    display_order=2
                ),
                Service(
                    name="Combo HiddenSYNC Total (Corte + Barba)",
                    description="Servicio completo de autor: Asesoría morfológica, Fade, Barboterapia y styling.",
                    duration_min=60,
                    price=6800.0,
                    previous_price=7500.0,
                    category="Combos",
                    is_active=True,
                    display_order=3
                ),
                Service(
                    name="Perfilado de Barba & Líneas Clean",
                    description="Definición nítida de contornos con navaja tradicional y bálsamo hidratante.",
                    duration_min=20,
                    price=2200.0,
                    previous_price=2500.0,
                    category="Barba",
                    is_active=True,
                    display_order=4
                )
            ]
            db.add_all(services)
            db.commit()

        # 4. Estilos de Corte iniciales
        if db.query(Style).count() == 0:
            styles = [
                Style(name="Low Skin Fade", description="Degradado sutil desde la base de la nuca con acabado a cero nítido.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=1),
                Style(name="Mid Fade Clásico", description="Degradado equilibrado a media altura con textura superior.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=2),
                Style(name="High Drop Fade", description="Caída pronunciada en la parte posterior para un contraste agresivo.", approx_duration=45, suggested_price=4500, category="Fade", is_active=True, display_order=3),
                Style(name="Taper Fade", description="Degradado sutil centrado en patillas y nuca manteniendo longitud.", approx_duration=40, suggested_price=4200, category="Taper", is_active=True, display_order=4),
                Style(name="French Crop", description="Flequillo recto con textura caótica en coronilla y laterales rasurados.", approx_duration=45, suggested_price=4500, category="Crop", is_active=True, display_order=5),
                Style(name="Pompadour Moderno", description="Tupé voluminoso peinado hacia atrás con fijación mate duradera.", approx_duration=50, suggested_price=4800, category="Clásico", is_active=True, display_order=6)
            ]
            db.add_all(styles)
            db.commit()

        # 5. Categorías del Shop iniciales
        if db.query(Category).count() == 0:
            categories = [
                Category(name="Pomadas & Ceras", slug="pomadas-ceras", description="Fijadores, arcillas mate y cereales modeladores.", is_active=True, display_order=1),
                Category(name="Cuidado de Barba", slug="cuidado-barba", description="Aceites, bálsamos hidratantes y jabones de barboterapia.", is_active=True, display_order=2),
                Category(name="Shampoo & Acondicionador", slug="shampoo-acondicionador", description="Limpieza profunda y fortalecimiento capilar.", is_active=True, display_order=3),
                Category(name="Herramientas & Accesorios", slug="herramientas-accesorios", description="Peines de carbono, cepillos pulidores y navajas.", is_active=True, display_order=4)
            ]
            db.add_all(categories)
            db.commit()

        # 6. Productos iniciales del Shop
        if db.query(Product).count() == 0:
            cat_pomada = db.query(Category).filter(Category.slug == "pomadas-ceras").first()
            cat_barba = db.query(Category).filter(Category.slug == "cuidado-barba").first()

            products = [
                Product(
                    name="Pomada Arcilla Mate Matte Clay",
                    description="Fijación fuerte de acabado 100% mate sin residuos grasos. 100g.",
                    price=12500.0,
                    previous_price=14000.0,
                    sku="POM-CLAY-01",
                    stock=15,
                    min_stock=3,
                    image_url="https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_pomada.id if cat_pomada else 1,
                    is_featured=True,
                    is_active=True,
                    display_order=1
                ),
                Product(
                    name="Aceite Esencial para Barba Ritual Navaja",
                    description="Mezcla orgánica de argán, jojoba y cedro para hidratar piel y vello facial. 50ml.",
                    price=9800.0,
                    previous_price=11000.0,
                    sku="ACE-BARB-02",
                    stock=10,
                    min_stock=2,
                    image_url="https://images.unsplash.com/photo-1608248597379-397505553599?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_barba.id if cat_barba else 2,
                    is_featured=True,
                    is_active=True,
                    display_order=2
                ),
                Product(
                    name="Bálsamo Perfilador & Hidratante de Barba",
                    description="Suaviza el vello duro y protege la piel contra irritación tras el afeitado. 80g.",
                    price=8500.0,
                    previous_price=9500.0,
                    sku="BAL-BARB-03",
                    stock=8,
                    min_stock=2,
                    image_url="https://images.unsplash.com/photo-1626285861696-9f0bf5a49c6d?auto=format&fit=crop&w=400&q=80",
                    category_id=cat_barba.id if cat_barba else 2,
                    is_featured=False,
                    is_active=True,
                    display_order=3
                )
            ]
            db.add_all(products)
            db.commit()

        # 7. Zonas de Delivery iniciales
        if db.query(DeliveryZone).count() == 0:
            dz = [
                DeliveryZone(name="Retiro en Barbería (Gratis)", cost=0.0, min_order_amount=0.0, is_active=True),
                DeliveryZone(name="Zona Centro / Macrocentro", cost=1500.0, min_order_amount=5000.0, is_active=True),
                DeliveryZone(name="Zonas Periféricas / Barrios", cost=2500.0, min_order_amount=8000.0, is_active=True)
            ]
            db.add_all(dz)
            db.commit()

    finally:
        db.close()
