from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship, synonym
from app.database import Base, get_argentina_now

def get_now() -> datetime:
    """Retorna la fecha y hora oficial del negocio (Catamarca UTC-3) para persistencia consistente."""
    try:
        return get_argentina_now().replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)

get_utc_now = get_now

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(30), default="admin") # "admin" o "encargado"
    can_edit_stock = Column(Boolean, default=True)
    can_view_finances = Column(Boolean, default=False)
    can_cancel_appointments = Column(Boolean, default=True)
    can_manage_shop = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)


class ShopSetting(Base):
    __tablename__ = "shop_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


class Barber(Base):
    __tablename__ = "barbers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(40), nullable=True) # Datos privados del barbero (WhatsApp interno)
    specialties = Column(String(250), default="Master Barber")
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    experience = Column(String(100), nullable=True) # e.g. "5 años de experiencia"
    instagram = Column(String(100), nullable=True)
    facebook = Column(String(100), nullable=True)
    featured_styles = Column(String(250), nullable=True) # e.g. "Skin Fade, Visagismo, Ritual de Barba"
    working_days = Column(String(100), default="Lunes,Martes,Miércoles,Jueves,Viernes,Sábado")
    commission_services_percent = Column(Float, default=50.0)
    commission_products_percent = Column(Float, default=10.0)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    appointments = relationship("Appointment", back_populates="barber")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    duration_min = Column(Integer, default=45)
    prep_buffer_min = Column(Integer, default=0)
    clean_buffer_min = Column(Integer, default=5)
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
    points = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    tier = Column(String(30), default="BRONCE")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    appointments = relationship("Appointment", back_populates="client_rel")
    orders = relationship("Order", back_populates="client_rel")
    loyalty_transactions = relationship("LoyaltyTransaction", back_populates="client_rel", cascade="all, delete-orphan")


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
    service_price_snapshot = Column(Float, nullable=True)

    barber_name_snapshot = synonym("barber_name")
    service_name_snapshot = synonym("service")

    appointment_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_min = Column(Integer, default=45)
    actual_duration_min = Column(Integer, nullable=True)
    
    status = Column(String(20), default="PENDIENTE") # PENDIENTE, CONFIRMADO, CANCELADO, COMPLETADO, NO_SHOW
    confirmed = Column(Boolean, default=False)
    canceled = Column(Boolean, default=False)
    reminder_sent = Column(Boolean, default=False)
    push_reminder_sent = Column(Boolean, default=False)

    # Señas & Pasarela de pago
    deposit_required = Column(Boolean, default=False)
    deposit_amount = Column(Float, default=0.0)
    deposit_paid = Column(Boolean, default=False)
    deposit_payment_id = Column(String(100), nullable=True, index=True)
    payment_status = Column(String(30), default="SIN_SEÑA") # SIN_SEÑA, PENDIENTE_PAGO, SEÑA_PAGADA, TOTAL_PAGADO

    tip_amount = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    is_checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checkin_token = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=get_utc_now)

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
    price = Column(Float, nullable=False) # Precio de venta al público (sale_price)
    previous_price = Column(Float, nullable=True)
    cost_price = Column(Float, default=0.0) # Precio de costo (cuánto pagó la barbería)
    category = Column(String(50), default="reventa") # "reventa" o "insumo"
    sku = Column(String(50), nullable=True)
    stock = Column(Integer, default=0) # Stock actual (current_stock)
    min_stock = Column(Integer, default=2)
    image_url = Column(String(500), nullable=True)
    gallery_json = Column(Text, nullable=True) # JSON list of URLs
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    category_rel = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String(50), nullable=False) # "venta", "ingreso_compra", "uso_interno", "ajuste"
    quantity = Column(Integer, nullable=False) # Cantidad (+ o -)
    date = Column(DateTime, default=get_utc_now)
    notes = Column(Text, nullable=True)
    registered_by = Column(String(80), default="Admin")

    product = relationship("Product", back_populates="movements")


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
    idempotency_key = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=get_utc_now)

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
    created_at = Column(DateTime, default=get_utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(80), default="Administrador")
    actor = Column(String(80), default="Encargado / Recepción")
    module = Column(String(80), default="Productos")
    action = Column(String(120), nullable=False) # "CREAR_PRODUCTO", "MODIFICAR_STOCK", "EDITAR_PRODUCTO", "VENTA_PRODUCTO"
    description = Column(Text, nullable=True)
    record_id = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=get_utc_now)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    recipient = Column(String(50), nullable=False)
    recipient_role = Column(String(20), default="CLIENTE") # CLIENTE, BARBERO
    message_type = Column(String(50), default="WHATSAPP_CONFIRMACION")
    message_body = Column(Text, nullable=False)
    status = Column(String(20), default="ENVIADO") # ENVIADO, PENDIENTE, DELIVERED, READ, ERROR
    whatsapp_message_id = Column(String(100), nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    response_payload = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class ShiftClosure(Base):
    __tablename__ = "shift_closures"

    id = Column(Integer, primary_key=True, index=True)
    encargado_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    encargado_name = Column(String(80), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_cierre = Column(DateTime, default=get_utc_now)
    fondo_inicial = Column(Float, default=0.0)
    total_efectivo = Column(Float, default=0.0)
    total_transferencia = Column(Float, default=0.0)
    total_cortes = Column(Float, default=0.0)
    total_productos = Column(Float, default=0.0)
    total_calculado = Column(Float, default=0.0)
    balance_declarado = Column(Float, default=0.0)
    diferencia = Column(Float, default=0.0)
    total_turnos_atendidos = Column(Integer, default=0)
    notas = Column(Text, nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    scope = Column(String(50), nullable=False) # "appointment", "order", "whatsapp_webhook"
    response_code = Column(Integer, default=200)
    response_body = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    idempotency_key = synonym("key")
    request_path = synonym("scope")
    response_json = synonym("response_body")

    def __init__(self, *args, **kwargs):
        if "idempotency_key" in kwargs and "key" not in kwargs:
            kwargs["key"] = kwargs.pop("idempotency_key")
        if "request_path" in kwargs and "scope" not in kwargs:
            kwargs["scope"] = kwargs.pop("request_path")
        elif "endpoint" in kwargs and "scope" not in kwargs:
            kwargs["scope"] = kwargs.pop("endpoint")
        if "response_json" in kwargs and "response_body" not in kwargs:
            kwargs["response_body"] = kwargs.pop("response_json")
        super().__init__(*args, **kwargs)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_str = Column(String(255), unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, default=get_utc_now)
    expires_at = Column(DateTime, nullable=True)


class AppointmentHistory(Base):
    __tablename__ = "appointment_history"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    changed_by = Column(String(80), default="Sistema")
    change_reason = Column(Text, nullable=True)
    previous_time = Column(DateTime, nullable=True)
    new_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    def __init__(self, *args, **kwargs):
        if "old_status" in kwargs and "previous_status" not in kwargs:
            kwargs["previous_status"] = kwargs.pop("old_status")
        super().__init__(*args, **kwargs)

    @property
    def old_status(self):
        return self.previous_status

    @old_status.setter
    def old_status(self, val):
        self.previous_status = val


class BarberSchedule(Base):
    __tablename__ = "barber_schedules"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False) # 0=Lunes, 1=Martes ... 6=Domingo
    start_time_1 = Column(String(10), default="09:00")
    end_time_1 = Column(String(10), default="13:00")
    start_time_2 = Column(String(10), nullable=True, default="16:00")
    end_time_2 = Column(String(10), nullable=True, default="21:00")
    is_working = Column(Boolean, default=True)


class ScheduleException(Base):
    __tablename__ = "schedule_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"), nullable=True, index=True) # NULL = toda la barbería
    date = Column(String(10), nullable=False, index=True) # YYYY-MM-DD
    start_time = Column(String(10), nullable=True) # NULL = todo el día
    end_time = Column(String(10), nullable=True)
    exception_type = Column(String(50), default="bloqueo_manual") # feriado, vacaciones, licencia, bloqueo_manual, horario_especial
    reason = Column(String(250), nullable=True)
    created_by = Column(String(80), default="Admin")
    created_at = Column(DateTime, default=get_utc_now)


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(120), nullable=False)
    client_phone = Column(String(40), nullable=False, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    date = Column(String(10), nullable=False, index=True) # YYYY-MM-DD
    time_range_start = Column(String(10), default="09:00")
    time_range_end = Column(String(10), default="21:00")
    status = Column(String(30), default="WAITING") # WAITING, NOTIFIED, BOOKED, EXPIRED, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    preferred_date = synonym("date")
    preferred_time_range = synonym("time_range_start")

    def __init__(self, *args, **kwargs):
        if "preferred_date" in kwargs and "date" not in kwargs:
            kwargs["date"] = kwargs.pop("preferred_date")
        if "preferred_time_range" in kwargs and "time_range_start" not in kwargs:
            kwargs["time_range_start"] = kwargs.pop("preferred_time_range")
        super().__init__(*args, **kwargs)


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_type = Column(String(30), default="PERCENTAGE") # PERCENTAGE, FIXED_AMOUNT, FIXED_PRICE, FREE_ITEM
    discount_value = Column(Float, nullable=False)
    max_discount_amount = Column(Float, nullable=True)
    min_ticket_amount = Column(Float, default=0.0)
    discount_absorption = Column(String(30), default="BUSINESS_ABSORBED") # BUSINESS_ABSORBED o PROPORTIONAL
    scope = Column(String(30), default="TOTAL_TICKET") # TOTAL_TICKET, SERVICES_ONLY, PRODUCTS_ONLY
    applicable_service_ids = Column(String(200), nullable=True) # CSV de IDs o NULL
    applicable_product_ids = Column(String(200), nullable=True)
    allowed_days = Column(String(50), nullable=True) # CSV de días "0,1" (Lunes y Martes) o NULL
    allowed_start_time = Column(String(10), nullable=True)
    allowed_end_time = Column(String(10), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    max_total_uses = Column(Integer, default=100)
    current_uses = Column(Integer, default=0)
    max_uses_per_client = Column(Integer, default=1)
    min_role = Column(String(20), default="admin") # "admin", "encargado", "public"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    commission_impact = synonym("discount_absorption")
    start_date = synonym("valid_from")
    end_date = synonym("valid_to")
    required_role = synonym("min_role")

    redemptions = relationship("VoucherRedemption", back_populates="voucher", cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        if "commission_impact" in kwargs and "discount_absorption" not in kwargs:
            kwargs["discount_absorption"] = kwargs.pop("commission_impact")
        if "start_date" in kwargs and "valid_from" not in kwargs:
            kwargs["valid_from"] = kwargs.pop("start_date")
        if "end_date" in kwargs and "valid_to" not in kwargs:
            kwargs["valid_to"] = kwargs.pop("end_date")
        if "required_role" in kwargs and "min_role" not in kwargs:
            kwargs["min_role"] = kwargs.pop("required_role")
        super().__init__(*args, **kwargs)


class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False, index=True)
    voucher_code = Column(String(50), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    client_phone = Column(String(40), nullable=False, index=True)
    staff_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    staff_username = Column(String(80), nullable=True)
    original_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, nullable=False)
    final_amount = Column(Float, nullable=False)
    barber_commission_impact = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    voucher = relationship("Voucher", back_populates="redemptions")


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shift_closures.id"), nullable=True)
    sale_type = Column(String(30), default="TURNO") # TURNO, PRODUCTO, MIXTO
    appointment_id = Column(Integer, nullable=True)
    order_id = Column(Integer, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    barber_id = Column(Integer, nullable=True)
    barber_name = Column(String(100), nullable=True)
    client_name = Column(String(120), nullable=True)
    original_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    payment_method = Column(String(50), default="Efectivo") # Efectivo, Transferencia, Tarjeta, Mercado Pago
    voucher_code = Column(String(50), nullable=True)
    items_detail = Column(Text, nullable=True)
    registered_by = Column(String(80), default="Encargado")
    tip_amount = Column(Float, default=0.0)
    commission_amount = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    final_amount = synonym("total_amount")
    cashier_name = synonym("registered_by")

    def __init__(self, *args, **kwargs):
        if "final_amount" in kwargs and "total_amount" not in kwargs:
            kwargs["total_amount"] = kwargs.pop("final_amount")
        if "cashier_name" in kwargs and "registered_by" not in kwargs:
            kwargs["registered_by"] = kwargs.pop("cashier_name")
        super().__init__(*args, **kwargs)


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False) # Positivos (acumulados) o Negativos (canjeados)
    reason = Column(String(120), nullable=False) # "Corte de pelo", "Compra en Shop", "Canje de premio"
    reference_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    client_rel = relationship("Client", back_populates="loyalty_transactions")


class LoyaltyReward(Base):
    __tablename__ = "loyalty_rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    points_required = Column(Integer, nullable=False)
    reward_type = Column(String(50), default="DISCOUNT_FIXED") # DISCOUNT_FIXED, DISCOUNT_PERCENT, FREE_SERVICE, FREE_PRODUCT
    reward_value = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_phone = Column(String(40), nullable=True, index=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    user_agent = Column(String(250), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)





