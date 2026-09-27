"""
tests/conftest.py - Fixtures y configuración aislada para la suite de pruebas automatizadas.
Utiliza 'barberia_test.db' para garantizar que jamás se modifique 'barberia.db' de producción.
"""
import os
import sys

# Configurar entorno de pruebas ANTES de importar la aplicación
TEST_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "barberia_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["ADMIN_INITIAL_PASSWORD"] = "TestAdminPass2026!#"
os.environ["WHATSAPP_APP_SECRET"] = "test_whatsapp_secret_key_12345"

# Agregar raíz al sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import AdminUser, Barber, Service, Style, Category, Product, DeliveryZone, ShopSetting
from app.auth import hash_password, create_admin_token
from app.settings_helper import DEFAULT_SETTINGS

test_engine = create_engine(
    f"sqlite:///{TEST_DB_FILE}",
    connect_args={"check_same_thread": False, "timeout": 30.0}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Inicializa la base de datos de pruebas aislada con esquema y datos semilla."""
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    try:
        # 1. Configuración de prueba
        for k, v in DEFAULT_SETTINGS.items():
            db.add(ShopSetting(key=k, value=str(v)))
        db.add(ShopSetting(key="whatsapp_access_token", value="EAAB_TEST_SECRET_TOKEN_DO_NOT_LEAK"))
        db.add(ShopSetting(key="whatsapp_phone_number_id", value="123456789012345"))
        db.commit()

        # 2. Usuarios con roles (ADMIN, ENCARGADO, BARBERO)
        admin_default = AdminUser(
            username="admin",
            password_hash=hash_password("AdminTest2026!#"),
            role="admin",
            is_active=True,
            can_edit_stock=True,
            can_view_finances=True,
            can_cancel_appointments=True,
            can_manage_shop=True
        )
        admin = AdminUser(
            username="admin_test",
            password_hash=hash_password("AdminTest2026!#"),
            role="admin",
            is_active=True,
            can_edit_stock=True,
            can_view_finances=True,
            can_cancel_appointments=True,
            can_manage_shop=True
        )
        encargado = AdminUser(
            username="encargado_test",
            password_hash=hash_password("EncargadoTest2026!#"),
            role="encargado",
            is_active=True,
            can_edit_stock=True,
            can_view_finances=False,
            can_cancel_appointments=True,
            can_manage_shop=True
        )
        barbero_user = AdminUser(
            username="barbero_test",
            password_hash=hash_password("BarberoTest2026!#"),
            role="barbero",
            is_active=True,
            can_edit_stock=False,
            can_view_finances=False,
            can_cancel_appointments=False,
            can_manage_shop=False
        )
        db.add_all([admin_default, admin, encargado, barbero_user])
        db.commit()

        # 3. Barberos de prueba
        b1 = Barber(
            name="barbero_test",
            phone="+5491199990001",
            specialties="Master Barber",
            description="Barbero para pruebas automatizadas",
            working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
            is_active=True,
            display_order=1
        )
        b2 = Barber(
            name="Segundo Barbero",
            phone="+5491199990002",
            specialties="Classic",
            working_days="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado",
            is_active=True,
            display_order=2
        )
        db.add_all([b1, b2])
        db.commit()

        # 4. Servicios
        s1 = Service(name="Corte Clásico", price=4000.0, duration_min=45, category="Cortes", is_active=True)
        s2 = Service(name="Barba", price=2500.0, duration_min=30, category="Barba", is_active=True)
        db.add_all([s1, s2])
        db.commit()

        # 5. Categorías y Productos
        cat = Category(name="Ceras y Pomadas", slug="ceras-y-pomadas", display_order=1, is_active=True)
        db.add(cat)
        db.commit()
        db.refresh(cat)

        p1 = Product(
            name="Pomada Test Mate",
            description="Pomada para pruebas",
            price=3000.0,
            cost_price=1500.0,
            stock=10,
            min_stock=2,
            category="reventa",
            category_id=cat.id,
            is_active=True
        )
        p_single = Product(
            name="Producto Stock Unico",
            description="Para pruebas de sobreventa concurrente",
            price=5000.0,
            cost_price=2500.0,
            stock=1,
            min_stock=1,
            category="reventa",
            category_id=cat.id,
            is_active=True
        )
        db.add_all([p1, p_single])
        db.commit()

        # 6. Delivery Zones
        zone = DeliveryZone(name="Retiro Local", cost=0.0, is_active=True)
        db.add(zone)
        db.commit()

    finally:
        db.close()

    yield

    # Teardown de pruebas
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
def client():
    """Cliente HTTP de prueba para interactuar con la app."""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Sesión directa de base de datos de prueba."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def admin_token():
    """Genera token JWT para rol admin."""
    return create_admin_token(username="admin_test", role="admin")

@pytest.fixture
def encargado_token():
    """Genera token JWT para rol encargado."""
    return create_admin_token(username="encargado_test", role="encargado")

@pytest.fixture
def barbero_token():
    """Genera token JWT para rol barbero."""
    return create_admin_token(username="barbero_test", role="barbero")
