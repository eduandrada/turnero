from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# ==========================================
# AUTH SCHEMAS
# ==========================================
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str
    role: Optional[str] = "admin"
    message: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

# ==========================================
# SETTINGS SCHEMAS
# ==========================================
class SettingsDictResponse(BaseModel):
    settings: Dict[str, Any]

class SettingUpdateItem(BaseModel):
    key: str
    value: str

class BulkSettingsUpdate(BaseModel):
    settings: Dict[str, Any]

# ==========================================
# BARBER SCHEMAS
# ==========================================
class BarberBase(BaseModel):
    name: str
    specialties: Optional[str] = "Master Barber"
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    experience: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    featured_styles: Optional[str] = None
    working_days: Optional[str] = "Lunes,Martes,Miércoles,Jueves,Viernes,Sábado"
    is_active: bool = True
    display_order: int = 0

class BarberCreate(BarberBase):
    phone: Optional[str] = None # Datos privados del barbero

class BarberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialties: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    experience: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    featured_styles: Optional[str] = None
    working_days: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class BarberRead(BarberBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class BarberAdminRead(BarberRead):
    phone: Optional[str] = None # Expuesto SOLO al Administrador
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# SERVICE SCHEMAS
# ==========================================
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_min: int = 45
    price: float
    previous_price: Optional[float] = None
    category: Optional[str] = "Cortes"
    image_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_min: Optional[int] = None
    price: Optional[float] = None
    previous_price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class ServiceRead(ServiceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# STYLE SCHEMAS
# ==========================================
class StyleBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = "Fade"
    approx_duration: int = 45
    suggested_price: float = 0.0
    is_active: bool = True
    display_order: int = 0

class StyleCreate(StyleBase):
    pass

class StyleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    approx_duration: Optional[int] = None
    suggested_price: Optional[float] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class StyleRead(StyleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# CLIENT SCHEMAS
# ==========================================
class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=7, max_length=40)
    email: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ClientRead(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# APPOINTMENT SCHEMAS
# ==========================================
class AppointmentCreate(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=100)
    client_phone: str = Field(..., min_length=7, max_length=25)
    barber_id: Optional[int] = None
    barber_name: Optional[str] = None
    service_id: Optional[int] = None
    service: Optional[str] = None
    appointment_time: datetime
    notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    barber_id: Optional[int] = None
    barber_name: Optional[str] = None
    service_id: Optional[int] = None
    service: Optional[str] = None
    appointment_time: Optional[datetime] = None
    status: Optional[str] = None # PENDIENTE, CONFIRMADO, CANCELADO, COMPLETADO, NO_SHOW
    confirmed: Optional[bool] = None
    canceled: Optional[bool] = None
    notes: Optional[str] = None

class AppointmentRead(BaseModel):
    id: int
    client_id: Optional[int] = None
    client_name: str
    client_phone: str
    barber_id: Optional[int] = None
    barber_name: Optional[str] = None
    service_id: Optional[int] = None
    service: Optional[str] = None
    appointment_time: datetime
    end_time: Optional[datetime] = None
    duration_min: int = 45
    status: str = "PENDIENTE"
    confirmed: bool = False
    canceled: bool = False
    reminder_sent: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AvailableSlotItem(BaseModel):
    time: str
    available: bool

class AvailableSlotsResponse(BaseModel):
    barber_id: Optional[int] = None
    barber_name: str
    date: str
    slots: List[AvailableSlotItem]

# ==========================================
# SHOP CATEGORY & PRODUCT SCHEMAS
# ==========================================
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0 # Precio de venta al público (sale_price)
    previous_price: Optional[float] = None
    cost_price: float = 0.0 # Precio de costo
    category: str = "reventa" # "reventa" o "insumo"
    sku: Optional[str] = None
    stock: int = 0 # Stock actual (current_stock)
    min_stock: int = 2
    image_url: Optional[str] = None
    gallery_json: Optional[str] = None
    category_id: Optional[int] = None
    is_featured: bool = False
    is_active: bool = True
    display_order: int = 0

class ProductCreate(ProductBase):
    cost_price: Optional[float] = 0.0
    sale_price: Optional[float] = None # alias para price
    current_stock: Optional[int] = None # alias para stock

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    previous_price: Optional[float] = None
    cost_price: Optional[float] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    stock: Optional[int] = None
    current_stock: Optional[int] = None
    min_stock: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class ProductRead(ProductBase):
    id: int
    cost_price: float = 0.0
    category: str = "reventa"
    current_stock: int = 0
    sale_price: float = 0.0
    category_name: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

ProductResponse = ProductRead

class StockAdjustment(BaseModel):
    quantity: Optional[int] = None
    stock: Optional[int] = None
    action_type: Optional[str] = "MODIFICAR_STOCK"
    notes: Optional[str] = None
    actor: Optional[str] = "Encargado / Recepción"

class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: str # "venta", "ingreso_compra", "uso_interno", "ajuste"
    quantity: int
    notes: Optional[str] = None
    registered_by: Optional[str] = "Admin"

class StockMovementRead(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity: int
    date: datetime
    notes: Optional[str] = None
    registered_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class InventoryAnalyticsResponse(BaseModel):
    total_inventory_cost: float
    total_inventory_sale_value: float
    net_profit_total: float
    critical_count: int
    top_rotating_products: List[Dict[str, Any]]
    critical_products: List[Dict[str, Any]]
    dead_stock_products: List[Dict[str, Any]]

# ==========================================
# ORDER SCHEMAS
# ==========================================
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class OrderItemRead(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    client_name: str = Field(..., min_length=2)
    client_phone: str = Field(..., min_length=7)
    client_email: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
    delivery_type: str = "pickup" # pickup, delivery
    delivery_zone_id: Optional[int] = None
    payment_method: str = "Efectivo"
    items: List[OrderItemCreate]

class OrderRead(BaseModel):
    id: int
    order_number: str
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
    subtotal: float
    delivery_cost: float
    total: float
    delivery_type: str
    payment_method: str
    status: str
    created_at: Optional[datetime] = None
    items: List[OrderItemRead] = []
    model_config = ConfigDict(from_attributes=True)

class OrderStatusUpdate(BaseModel):
    status: str

# ==========================================
# DELIVERY ZONE SCHEMAS
# ==========================================
class DeliveryZoneBase(BaseModel):
    name: str
    cost: float = 0.0
    min_order_amount: float = 0.0
    is_active: bool = True

class DeliveryZoneCreate(DeliveryZoneBase):
    pass

class DeliveryZoneRead(DeliveryZoneBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# PROMOTION & NOTIFICATION SCHEMAS
# ==========================================
class PromotionBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    promo_type: str = "Descuento %"
    promo_price: Optional[float] = None
    discount_percent: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True

class PromotionCreate(PromotionBase):
    pass

class PromotionRead(PromotionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AppNotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "Aviso"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = True

class AppNotificationCreate(AppNotificationBase):
    pass

class AppNotificationRead(AppNotificationBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# AUDIT & STATS SCHEMAS
# ==========================================
class AuditLogRead(BaseModel):
    id: int
    timestamp: datetime
    actor: str = "Encargado / Recepción"
    action: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_name: Optional[str] = "Administrador"
    module: Optional[str] = "Productos"
    record_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

AuditLogResponse = AuditLogRead

class NotificationLogRead(BaseModel):
    id: int
    appointment_id: Optional[int] = None
    recipient: str
    recipient_role: str
    message_type: str
    message_body: str
    status: str
    error_details: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DashboardStatsResponse(BaseModel):
    today_appointments: int
    pending_appointments: int
    confirmed_appointments: int
    completed_appointments: int
    canceled_appointments: int
    total_clients: int
    total_barbers: int
    total_services: int
    total_products: int
    low_stock_products: int
    pending_orders: int
    total_orders_revenue: float
    estimated_turnover_revenue: float
    recent_appointments: List[Dict[str, Any]]
    recent_orders: List[Dict[str, Any]]
    low_stock_list: List[Dict[str, Any]]

# ==========================================
# AI STYLE ADVISOR SCHEMAS
# ==========================================
class StyleAdviceRequest(BaseModel):
    face_shape: str
    hair_type: Optional[str] = "normal"
    hair_density: Optional[str] = "media"
    style_preference: Optional[str] = "moderno"

class StyleAdviceResponse(BaseModel):
    face_shape: str
    recommendation: str
    styling_tips: str
    recommended_service: str
    fade_type: str
    confidence_score: float

# ==========================================
# STAFF & PERMISSIONS SCHEMAS
# ==========================================
class StaffUserBase(BaseModel):
    username: str
    role: str = "encargado"
    can_edit_stock: bool = True
    can_view_finances: bool = False
    can_cancel_appointments: bool = True
    can_manage_shop: bool = True
    is_active: bool = True

class StaffUserCreate(StaffUserBase):
    password: str = Field(..., min_length=4)

class StaffUserUpdate(BaseModel):
    role: Optional[str] = None
    can_edit_stock: Optional[bool] = None
    can_view_finances: Optional[bool] = None
    can_cancel_appointments: Optional[bool] = None
    can_manage_shop: Optional[bool] = None
    is_active: Optional[bool] = None

class StaffPasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=4)

class StaffUserRead(StaffUserBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# SHIFT CLOSURE & CASH CONTROL SCHEMAS
# ==========================================
class ShiftClosureCreate(BaseModel):
    fecha_inicio: datetime
    fecha_cierre: datetime
    fondo_inicial: float = 0.0
    total_efectivo: float = 0.0
    total_transferencia: float = 0.0
    total_cortes: float = 0.0
    total_productos: float = 0.0
    total_calculado: float = 0.0
    balance_declarado: float = 0.0
    total_turnos_atendidos: int = 0
    notas: Optional[str] = None

class ShiftClosureRead(BaseModel):
    id: int
    encargado_id: Optional[int] = None
    encargado_name: str
    fecha_inicio: datetime
    fecha_cierre: datetime
    fondo_inicial: float
    total_efectivo: float
    total_transferencia: float
    total_cortes: float
    total_productos: float
    total_calculado: float
    balance_declarado: float
    diferencia: float
    total_turnos_atendidos: int
    notas: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ShiftCalculationResponse(BaseModel):
    fecha_inicio: datetime
    fecha_cierre: Optional[datetime] = None
    fondo_inicial: float = 0.0
    total_cortes_efectivo: float = 0.0
    total_cortes_transferencia: float = 0.0
    total_productos_efectivo: float = 0.0
    total_productos_transferencia: float = 0.0
    total_cortes: float = 0.0
    total_productos: float = 0.0
    total_efectivo: float = 0.0
    total_transferencia: float = 0.0
    total_calculado: float = 0.0
    total_turnos_atendidos: int = 0
