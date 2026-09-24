from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShopSetting(Base):
    __tablename__ = "shop_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Barber(Base):
    __tablename__ = "barbers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialties = Column(String(250), default="Master Barber")
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    working_days = Column(String(100), default="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado")
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    appointments = relationship("Appointment", back_populates="barber")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    duration_min = Column(Integer, default=45)
    price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=True)
    category = Column(String(50), default="Cortes")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    appointments = relationship("Appointment", back_populates="service_rel")


class Style(Base):
    __tablename__ = "styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), default="Fade")
    approx_duration = Column(Integer, default=45)
    suggested_price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(40), unique=True, nullable=False, index=True)
    email = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="client_rel")
    orders = relationship("Order", back_populates="client_rel")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String(120), nullable=False)
    client_phone = Column(String(40), nullable=False, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    barber_name = Column(String(100), nullable=True)
    service = Column(String(120), nullable=True)

    appointment_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_min = Column(Integer, default=45)
    
    status = Column(String(20), default="PENDIENTE") # PENDIENTE, CONFIRMADO, CANCELADO, COMPLETADO, NO_SHOW
    confirmed = Column(Boolean, default=False)
    canceled = Column(Boolean, default=False)
    reminder_sent = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    barber = relationship("Barber", back_populates="appointments")
    service_rel = relationship("Service", back_populates="appointments", foreign_keys=[service_id])
    client_rel = relationship("Client", back_populates="appointments")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False, unique=True)
    slug = Column(String(80), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    products = relationship("Product", back_populates="category_rel")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=True)
    sku = Column(String(50), nullable=True)
    stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=2)
    image_url = Column(String(500), nullable=True)
    gallery_json = Column(Text, nullable=True) # JSON list of URLs
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    category_rel = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    cost = Column(Float, default=0.0)
    min_order_amount = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String(120), nullable=False)
    client_phone = Column(String(40), nullable=False)
    client_email = Column(String(120), nullable=True)
    address = Column(String(200), nullable=True)
    neighborhood = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    subtotal = Column(Float, nullable=False)
    delivery_cost = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    
    delivery_type = Column(String(30), default="pickup") # pickup, delivery
    payment_method = Column(String(50), default="Efectivo") # Efectivo, Transferencia, Mercado Pago, Pago al retirar
    status = Column(String(30), default="NUEVO") # NUEVO, CONFIRMADO, PREPARANDO, LISTO, EN_CAMINO, ENTREGADO, CANCELADO
    created_at = Column(DateTime, default=datetime.utcnow)

    client_rel = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(150), nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    promo_type = Column(String(50), default="Descuento %") # Descuento %, Descuento fijo, Combo, 2x1, Precio especial
    promo_price = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class AppNotification(Base):
    __tablename__ = "app_notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="Aviso") # Aviso, Promocion, Mantenimiento, Info
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(80), default="Administrador")
    module = Column(String(80), nullable=False)
    action = Column(String(120), nullable=False)
    record_id = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
