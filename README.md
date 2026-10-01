# HiddenSYNC AI / Turnero & Shop Barber Digital Ecosystem 2026

![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)
![FastAPI Version](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)
![Architecture](https://img.shields.io/badge/Architecture-Modular%20Layered-purple.svg)
![Tests Status](https://img.shields.io/badge/tests-67%20passed%20%7C%200%20failed-brightgreen.svg)
![Security](https://img.shields.io/badge/Security-Hardened%20RBAC-orange.svg)

Ecosistema digital integral de alto rendimiento para barberías de autor y salones modernos. Diseñado con una **arquitectura modular limpia por capas (Core, Models, Schemas, Services, API Routers, Workers)**, compatible de forma nativa con **SQLite y PostgreSQL**, seguridad criptográfica de grado producción, concurrencia transaccional sin doble reserva y frontend administrativo modularizado.

---

## 🏛️ ARQUITECTURA MODULAR DEL PROYECTO

El proyecto aplica una estricta separación de responsabilidades en capas desacopladas:

```text
app/
│
├── core/                       # Primitivas transversales y configuración
│   ├── config.py               # Settings, variables de entorno y validación de secretos
│   ├── database.py             # Engine SQLAlchemy multi-motor (SQLite / PostgreSQL)
│   ├── security.py             # Hash PBKDF2-SHA256, tokens HMAC-SHA256, revocación
│   ├── dependencies.py         # Inyección de dependencias y control de acceso (RBAC)
│   ├── logging.py              # Loggers estructurados con filtro de datos sensibles
│   ├── exceptions.py           # Jerarquía de excepciones de dominio
│   ├── path_security.py        # Prevención estricta de Path Traversal (safe_path)
│   └── seed.py                 # Siembra inicial de datos por defecto
│
├── models.py                   # Entidades SQLAlchemy (Users, Appointments, Clients, etc.)
│
├── schemas/                    # Contratos de validación Pydantic
│   ├── auth.py                 # Login, tokens, cambio de contraseñas
│   ├── appointments.py         # Creación y transición de turnos
│   ├── clients.py              # Directorio y CRM de clientes
│   ├── staff.py                # Barberos, personal y horarios
│   ├── services.py             # Servicios, precios y estilos
│   ├── shop.py                 # Pedidos, delivery y checkout
│   ├── inventory.py            # Productos, alertas y ajustes
│   ├── finance.py              # Rendición de caja y arqueos
│   └── notifications.py        # Webhooks y logs de WhatsApp
│
├── services/                   # Lógica de negocio pura (desacoplada de HTTP)
│   ├── appointment_service.py  # Concurrencia atómica, reservas y snapshots
│   ├── availability_service.py # Cálculo de slots, buffers y excepciones
│   ├── client_service.py       # CRM, historial y fidelización
│   ├── staff_service.py        # Gestión de barberos y horarios
│   ├── service_catalog.py      # Catálogo de servicios y estilos
│   ├── inventory_service.py    # Stock atómico, anti-sobreventa y movimientos
│   ├── order_service.py        # Checkout de tienda y zonas de entrega
│   ├── finance_service.py      # Arqueos de caja y auditoría de turnos
│   ├── voucher_service.py      # Yield management y cupones de descuento
│   ├── live_queue_service.py   # Cola de atención en vivo y locución TV
│   ├── style_advisor.py        # Asesor inteligente de visagismo
│   ├── backup_service.py       # Backups multi-motor (SQLite/PostgreSQL)
│   ├── scheduler_service.py    # Recordatorios automáticos en background
│   ├── whatsapp_service.py     # Integración Meta Cloud API y webhooks
│   └── audit_service.py        # Trazabilidad y auditoría de eventos
│
├── api/                        # Controladores HTTP / FastAPI Routers
│   ├── auth.py                 # Login, logout, perfil y credenciales
│   ├── public.py               # Disponibilidad, catálogo público y waitlist
│   ├── appointments.py         # Reserva pública atómica e idempotente
│   ├── live.py                 # Agenda en vivo, pantalla TV y llamados
│   ├── style_advisor.py        # Asesor de estilo
│   ├── shop.py                 # Tienda pública y checkout
│   ├── vouchers.py             # Consulta y canje de vouchers
│   ├── inventory.py            # Consultas de inventario y movimientos
│   ├── whatsapp.py             # Webhook oficial Meta WhatsApp (HMAC)
│   └── admin/                  # Sub-routers administrativos protegidos
│       ├── dashboard.py        # Métricas y KPIs en tiempo real
│       ├── appointments.py     # Gestión de turnos y agenda
│       ├── staff.py            # Barberos y horarios
│       ├── services.py         # Servicios, estilos y delivery
│       ├── clients.py          # CRM de clientes
│       ├── products.py         # Inventario y pedidos shop
│       ├── finance.py          # Rendición de cajas y ventas
│       ├── vouchers.py         # Cupones y promociones
│       ├── settings.py         # Configuración, logo y multimedia
│       └── backups.py          # Backups, restauración y descargas
│
├── workers/                    # Procesos en segundo plano independientes
│   └── scheduler.py            # Worker desacoplado de tareas periódicas
│
├── static/                     # Frontend estático y PWA
│   ├── js/admin/               # Módulos JavaScript del Panel Administrativo
│   │   ├── core.js             # Sesión, API helper, navegación, modales
│   │   ├── dashboard.js        # KPIs y gráficos
│   │   ├── appointments.js     # Gestión de agenda y estados
│   │   ├── staff.js            # Barberos y horarios
│   │   ├── services.js         # Servicios y estilos
│   │   ├── clients.js          # Directorio CRM
│   │   ├── shop.js             # Despacho y pedidos
│   │   ├── inventory.js        # Stock y alertas
│   │   ├── finance.js          # Auditoría de cajas
│   │   ├── users.js            # Permisos del personal
│   │   ├── settings.js         # Identidad visual y tema
│   │   └── backups.js          # Respaldos y restauración
│   ├── admin.js                # Coordinador modular y loader
│   ├── admin.html              # Panel de control administrativo
│   ├── index.html              # App pública para reserva de turnos
│   ├── shop.html               # Tienda online Barber Shop
│   ├── live.html               # Monitor de recepción en vivo
│   └── display.html            # Pantalla TV para sala de espera
│
└── main.py                     # Raíz de composición limpia (< 290 líneas)
```

---

## 💈 FUNCIONALIDADES PRINCIPALES

1. **Turnero Público Concurrente (`/`):**
   - Intervalos dinámicos según duración del servicio y descansos (buffers).
   - **Garantía Anti-Colisión Transaccional:** Bloqueo atómico a nivel base de datos (`APPOINTMENT_LOCK` / `BEGIN IMMEDIATE`) que impide la doble reserva en milisegundos concurrentes.
   - **Snapshots Históricos:** Registro inmutable del nombre del barbero, nombre del servicio y precio al momento del turno, protegiendo reportes históricos ante futuros cambios de precios.
2. **Shop Barber con Stock Atómico (`/shop.html`):**
   - Catálogo clasificado por categorías con carrito local y checkout.
   - **Prevención de Sobreventa:** Decremento condicional directo en SQL (`UPDATE products SET stock = stock - qty WHERE id = :id AND stock >= qty`).
   - Envío coordinado vía WhatsApp con cálculo de zonas de delivery.
3. **Agenda en Vivo & Pantalla TV Kiosk (`/live.html` / `/display.html`):**
   - Transiciones de estado: `PENDIENTE` → `CONFIRMADO` → `EN_SILLA` → `COMPLETADO`.
   - Locución de voz sintetizada con Web Audio API y chime para sala de espera.
   - Admisión de clientes espontáneos (*Walk-in*) sin reserva previa.
4. **Seguridad y Control de Acceso RBAC:**
   - Hashing seguro con PBKDF2-HMAC-SHA256 (100.000 iteraciones).
   - Roles jerárquicos: `ADMIN`, `ENCARGADO` y `BARBERO`.
   - Revocación instantánea de JWT en logout y protección de fuerza bruta.
   - **Cero contraseñas inseguras por defecto:** Requiere `ADMIN_INITIAL_PASSWORD` explícita en el primer inicio.
5. **WhatsApp Cloud API (Meta Graph API v20.0):**
   - Mensajes interactivos con botones de confirmación y cancelación.
   - Verificación estricta de firma HMAC-SHA256 (`X-Hub-Signature-256`).
   - Deduplicación idempotente de webhooks entrantes.
6. **Copias de Seguridad Inteligentes (BackupService):**
   - Soporte nativo para SQLite y PostgreSQL mediante adaptadores desacoplados.
   - Validación contra Path Traversal mediante `safe_path()`.
   - **Copia de seguridad preventiva automática** antes de aplicar cualquier restauración.
7. **Scheduler Desacoplado:**
   - Puede ejecutarse en el proceso web (`ENABLE_SCHEDULER=true`) o como worker independiente (`python -m app.workers.scheduler`) en infraestructuras distribuidas.

---

## 🚀 INSTALACIÓN Y PUESTA EN MARCHA

### Requisitos Previos
- Python 3.11 o superior.
- Git.

### 1. Clonar y Configurar Entorno
```bash
# Acceder al proyecto
cd turnero

# Crear entorno virtual limpio
python -m venv .venv

# Activar en Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Activar en Linux / macOS:
source .venv/bin/activate

# Instalar dependencias oficiales
pip install -r requirements.txt
```

### 2. Variables de Entorno
Copia la plantilla de configuración y personaliza los secretos:
```bash
cp .env.example .env
```

Para generar una clave secreta segura (`APP_SECRET_KEY`, `SECRET_KEY`) o token de WhatsApp (`WHATSAPP_VERIFY_TOKEN`) de 32 caracteres hexadecimales, ejecuta:
```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

Configura tus variables en `.env`:
```env
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./barberia.db
APP_SECRET_KEY=9a48d8c2e0f49c58b456d97c7bb1139e
SECRET_KEY=9a48d8c2e0f49c58b456d97c7bb1139e
ADMIN_INITIAL_PASSWORD=admin123
ENABLE_SCHEDULER=true
WHATSAPP_VERIFY_TOKEN=hiddensync_webhook_secret_token_2026
```

#### 🔑 Acceso al Panel de Control (Admin)
- **URL:** [http://localhost:8000/admin.html](http://localhost:8000/admin.html)
- **Usuario:** `admin`
- **Contraseña inicial:** `admin123` (o la definida en `ADMIN_INITIAL_PASSWORD`)

Para restablecer o verificar la contraseña del administrador en cualquier momento, utiliza la herramienta CLI:
```bash
# Restablecer a 'admin123' por defecto:
python reset_admin_password.py

# O definir una contraseña personalizada:
python reset_admin_password.py MiNuevaClaveSegura2026!
```

### 3. Iniciar la Aplicación en Desarrollo
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
La aplicación estará disponible en:
- **App Pública:** [http://localhost:8000/](http://localhost:8000/)
- **Panel Administrativo:** [http://localhost:8000/admin.html](http://localhost:8000/admin.html)
- **Tienda Shop:** [http://localhost:8000/shop.html](http://localhost:8000/shop.html)
- **Agenda en Vivo:** [http://localhost:8000/live.html](http://localhost:8000/live.html)
- **Pantalla TV:** [http://localhost:8000/display.html](http://localhost:8000/display.html)
- **Documentación Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🗄️ BASES DE DATOS (SQLite & PostgreSQL)

El sistema soporta indistintamente ambos motores mediante SQLAlchemy:

### Modo SQLite (Desarrollo o servidor único)
```env
DATABASE_URL=sqlite:///./barberia.db
```
- Transacciones inmediatas con modo WAL (`journal_mode=WAL`).
- Bloqueo transaccional de escritura exclusivo para reservas concurrentes.

### Modo PostgreSQL (Producción empresarial)
```env
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/turnero_prod
```
- Pool de conexiones transaccional optimizado.
- Restricciones de integridad y truncado en cascada para restauraciones.

---

## ⏰ BACKGROUND WORKER & SCHEDULER

Para entornos multi-worker (ej. Gunicorn con 4 uvicorn workers):
1. Configura en `.env`:
   ```env
   ENABLE_SCHEDULER=false
   ```
2. Ejecuta el worker en un proceso independiente:
   ```bash
   python -m app.workers.scheduler
   ```
Esto evita la ejecución duplicada de recordatorios de WhatsApp entre workers paralelos.

---

## 🧪 SUITE DE PRUEBAS AUTOMATIZADAS

La suite completa de tests garantiza la estabilidad y regresión cero:

```bash
# Ejecutar todas las pruebas con pytest
pytest -q
```

### Cobertura de Tests (67 tests, 0 fallos):
- **Auth & RBAC:** Login correcto, rechazo de credenciales incorrectas, expiración de tokens, cierre de sesión, revocación inmediata y permisos granulares de staff.
- **Turnos:** Creación de turnos, confirmación, cancelación, reprogramación, excepciones de horario y prueba de concurrencia contra doble reserva.
- **Clientes CRM:** Creación de perfil, enriquecimiento por teléfono, historial de turnos y métricas de fidelización.
- **Agenda & Pantalla TV:** Walk-in espontáneo, llamado a sillón, cambio de estado y síntesis de voz.
- **Inventario:** Ingreso de mercadería, ajuste manual, alertas de stock crítico y descuento atómico con prevención de sobreventa concurrente.
- **Shop Barber:** Validación de carrito, cálculo de delivery por zona y emisión de pedido único.
- **WhatsApp:** Recepción de webhook, verificación criptográfica HMAC-SHA256 y deduplicación de payloads idénticos.
- **Backups:** Generación de copias, verificación de integridad, bloqueo de path traversal y respaldo automático previo a la restauración.
- **Scheduler:** Ciclo de vida de APScheduler (inicio, apagado, reinicio tras shutdown y registro de tareas).

---

## 🐳 DESPLIEGUE EN PRODUCCIÓN

### Docker
```bash
# Construir la imagen
docker build -t turnero-barberia .

# Ejecutar el contenedor
docker run -d -p 8000:8000 --env-file .env --name barberia turnero-barberia
```

### PaaS (Render, Railway, Fly.io)
El proyecto incluye `render.yaml` y `Procfile` listos para despliegue continuo. Asegúrate de configurar las variables de entorno en el panel del proveedor.

---

## 📄 LICENCIA
Proyecto distribuido bajo la licencia MIT. Diseñado para ofrecer máxima robustez y escalabilidad.
