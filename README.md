# BladeSync AI / Turnero & Shop Barber Digital Ecosystem 2026

![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)
![FastAPI Version](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)
![Tests Status](https://img.shields.io/badge/tests-32%20passed-brightgreen.svg)
![Security](https://img.shields.io/badge/RBAC-Admin%20%7C%20Encargado%20%7C%20Barbero-orange.svg)

Ecosistema digital integral para barberías de autor: **Reserva de Turnos Concurrente**, **Asesor de Estilo con Visagismo**, **Agenda en Vivo & Pantalla TV Kiosk**, **Shop Barber con Stock Atómico**, **Integración Oficial WhatsApp Cloud API** y **Panel de Administración PWA Multi-dispositivo**.

---

## 💈 MÓDULOS PRINCIPALES

1. **Turnero Público Concurrente (`/` / `index.html`):**
   - Selección dinámica de servicios, barberos y fechas con cálculo atómico de horarios disponibles en intervalos de 15 minutos según duración.
   - **Prevención de Doble Reserva Transaccional:** Bloqueo exclusivo a nivel base de datos (`BEGIN IMMEDIATE`) y validación de superposición. Ante dos reservas simultáneas para el mismo horario y barbero, el sistema acepta exactamente una y rechaza la otra de forma determinista.
   - Asesor heurístico de visagismo por morfología facial.
2. **Shop Barber con Stock Atómico (`/shop.html`):**
   - Catálogo de productos profesionales organizado por categorías.
   - Carrito de compras local y checkout con cálculo transparente de envío por zona y monto mínimo.
   - **Prevención de Sobreventa:** Descuento atómico mediante condición SQL (`stock >= qty`). En compras simultáneas sobre la última unidad disponible, solo una se confirma.
   - Código de pedido único generado en formato `PED-YYYYMMDD-HHMMSS-XXXX`.
3. **Agenda en Vivo & Pantalla TV Display (`/live.html` / `/display.html`):**
   - Monitoreo en tiempo real de turnos: en espera, llamados, en sillón y completados.
   - Consola para recepción con locución por voz y chime sintetizado sincronizado para pantalla gigante de sala de espera.
   - Soporte para ingreso de clientes espontáneos (Walk-in) y actualización de configuración en caliente (POST y PUT).
4. **Seguridad y Control de Acceso RBAC (`/admin.html`):**
   - Autenticación JWT Bearer con roles estrictos en backend:
     - `ADMIN`: Control total (branding, precios, usuarios, barberos, servicios, stock, copias de seguridad, auditoría).
     - `ENCARGADO`: Operaciones de agenda, llamados, walk-in, pedidos, ventas y stock.
     - `BARBERO`: Acceso restringido exclusivamente a su propia agenda de turnos asignados.
   - Auditoría estructurada de eventos (logins, modificaciones de stock, llamados TV, cambios de configuración).
   - Eliminación de credenciales por defecto (`admin123` / `barber`). Endpoint seguro de configuración del primer administrador (`/api/admin/setup-initial-admin`).
5. **WhatsApp Cloud API (Meta Graph API v20.0):**
   - Notificación interactiva al cliente con botones de confirmación y cancelación.
   - Notificación privada al barbero con los detalles del turno (el número privado del barbero nunca se expone en la API pública).
   - Verificación criptográfica obligatoria de Webhook mediante firma HMAC-SHA256 (`X-Hub-Signature-256`) y validación de número remitente.
   - Registro de ciclo de vida en `NotificationLog`: `PENDING`, `SENT`, `DELIVERED`, `READ`, `ERROR`, con ejecución asíncrona no bloqueante.
6. **PWA & Service Worker:**
   - Manifest dinámico e instalación como aplicación de escritorio o móvil.
   - Service Worker optimizado con exclusión estricta de rutas de API (`/api/*`) para evitar retención de datos sensibles en caché.

---

## 🚀 REQUISITOS E INSTALACIÓN

### Requisitos
- Python 3.11+
- Git

### Instalación Paso a Paso
```bash
# 1. Clonar el repositorio y acceder al directorio
cd turnero

# 2. Crear y activar el entorno virtual
python -m venv venv
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# En Linux / macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores de producción
```

### Sembrado de Datos de Demostración (Opcional)
Para iniciar con un catálogo y barberos de prueba limpios sin datos operativos reales:
```bash
python seed_demo.py
```

### Iniciar Servidor de Desarrollo
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Acceso desde el navegador: `http://localhost:8000/`

---

## 🔐 VARIABLES DE ENTORNO CRÍTICAS (.env)

```env
# Entorno
ENV=production
HOST=0.0.0.0
PORT=8000

# Clave Secreta para JWT (MANDATORIA EN PRODUCCIÓN - Mínimo 32 caracteres)
APP_SECRET_KEY=clave_secreta_altamente_segura_de_produccion_2026

# Contraseña Inicial del Administrador (solo usada en la siembra inicial)
ADMIN_INITIAL_PASSWORD=MiContrasenaSegura2026!#

# Base de Datos (SQLite por defecto o PostgreSQL)
DATABASE_URL=sqlite:///./barberia.db
TIMEZONE=America/Argentina/Buenos_Aires
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Meta WhatsApp Cloud API
WHATSAPP_CLOUD_API_TOKEN=your_meta_access_token_here
WHATSAPP_PHONE_NUMBER_ID=109876543210123
WHATSAPP_VERIFY_TOKEN=bladesync_webhook_secret_token_2026
WHATSAPP_APP_SECRET=your_meta_app_secret_here_for_hmac_sha256
```

---

## 🧪 SUITE DE PRUEBAS AUTOMATIZADAS

La suite incluye pruebas automatizadas exhaustivas que verifican seguridad, concurrencia, WhatsApp, Live Agenda, Stock y casos límite sin tocar la base de datos de producción (utilizan `barberia_test.db` aislada).

### Ejecutar con Pytest (32 tests completos)
```bash
pytest tests/ -v
```

### Ejecutar con Standalone Test Runner (17 tests)
```bash
python tests/run_tests.py
```

### Resumen de Pruebas:
- **Seguridad:** Protección 401 sin token, permisos RBAC (Admin, Encargado, Barbero), revocación de tokens y login.
- **Concurrencia:** Doble reserva simultánea (hilos en paralelo) y sobreventa de stock simultánea.
- **Live Agenda:** Rutas estáticas antes de dinámicas, guardado POST/PUT, walk-in y llamado de turno.
- **WhatsApp:** Verificación HMAC-SHA256, rechazo de firma inválida, webhook y privacidad de teléfono de barberos.
- **Configuraciones:** Whitelist en `/api/public/settings` garantizando que no se filtren credenciales o secretos.

---

## 🐳 DESPLIEGUE EN PRODUCCIÓN

### Con Docker
```bash
docker build -t turnero-barberia .
docker run -d -p 8000:8000 --env-file .env turnero-barberia
```

### En Render / PaaS Cloud
El repositorio incluye `render.yaml` y `Procfile`. Configura las variables de entorno en el panel del proveedor y el despliegue se completará de forma automática.
