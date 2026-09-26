# BladeSync AI / Turnero & Shop Barber Digital Ecosystem 2026

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI Version](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)
![Build Status](https://img.shields.io/badge/tests-15%20passed-brightgreen.svg)

Ecosistema digital integral para barberías de autor: **Reserva de Turnos**, **Asesor de Estilo con Visagismo**, **Agenda en Vivo & Pantalla TV Kiosk**, **Shop Barber E-Commerce** y **Panel de Administración PWA Multi-dispositivo**.

---

## 💈 MÓDULOS PRINCIPALES

1. **Turnero Público (`/` / `index.html`):**
   - Selección dinámica de servicios, barberos y fechas.
   - Cálculo atómico y libre de colisiones de horarios disponibles en pasos de 15 minutos según la duración del servicio.
   - Asesor heurístico de visagismo por morfología facial (ovalada, cuadrada, redonda, diamante, etc.).
2. **Shop Barber (`/shop.html`):**
   - Catálogo de productos profesionales organizado por categorías.
   - Carrito de compras local y checkout con cálculo transparente de envío por zona y validación de monto mínimo.
   - Descuento de stock en base de datos al realizar el pedido y generación de código de pedido único (`PED-YYYYMMDD-HHMMSS-XXXX`).
3. **Agenda en Vivo & Pantalla TV (`/live.html` / `/display.html`):**
   - Monitoreo en tiempo real de turnos en atención, siguientes y completados.
   - Consola para recepción con locución por voz/chime sintetizado para pantalla gigante de sala de espera.
4. **Panel de Administración (`/admin.html`):**
   - Dashboard analítico con métricas de turnos, ingresos, clientes, barberos y alertas de bajo stock.
   - ABM completo de barberos, servicios, estilos, clientes, productos, categorías, turnos y zonas de delivery.
   - Gestión centralizada de branding (logos, colores, textos, PWA, TV), logs de auditoría y copias de seguridad (backup/restore).
5. **Integración WhatsApp Cloud API:**
   - Recordatorios automáticos interactivos con botones de confirmación/cancelación enviados vía Meta Graph API cada 5 minutos.
   - Webhook receptor para actualizar automáticamente el estado del turno.

---

## 🚀 REQUISITOS E INSTALACIÓN LOCAL

### Requisitos Previos
- Python 3.11+
- Virtualenv (`python -m venv venv`)

### Instalación Rápida
```bash
# 1. Clonar el repositorio y acceder
cd turnero

# 2. Crear y activar entorno virtual
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar archivo de configuración de variables de entorno
cp .env.example .env

# 5. Ejecutar la suite de pruebas automatizadas
python tests/run_tests.py

# 6. Iniciar el servidor local de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accede desde tu navegador a: `http://localhost:8000/`

---

## 🔐 CONFIGURACIÓN DE SEGURIDAD (.env)

Crea o edita tu archivo `.env` utilizando `.env.example` como plantilla:

```env
ENV=development
HOST=0.0.0.0
PORT=8000

# Clave Secreta de Aplicación (MANDATORIO EN PRODUCCIÓN)
APP_SECRET_KEY=su_clave_secreta_segura_aqui_32_caracteres

# Contraseña inicial del administrador (se usa al sembrar la DB por primera vez)
ADMIN_INITIAL_PASSWORD=MiContrasenaSegura2026!

DATABASE_URL=sqlite:///./barberia.db
TIMEZONE=America/Argentina/Buenos_Aires
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Meta WhatsApp Cloud API (Opcional en dev, simulación automática si falta token)
WHATSAPP_CLOUD_API_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=109876543210123
WHATSAPP_VERIFY_TOKEN=bladesync_webhook_secret_token_2026
```

---

## 🧪 SUITE DE PRUEBAS AUTOMATIZADAS

El proyecto incluye 15 pruebas unitarias y de integración que abarcan la API pública, turnos, autenticación, shop, PWA y casos borde:

```bash
python tests/run_tests.py
```

---

## 🐳 DESPLIEGUE EN PRODUCCIÓN (DOCKER / RENDER)

### Con Docker
```bash
docker build -t turnero-barberia .
docker run -d -p 8000:8000 --env-file .env turnero-barberia
```

### En Render / PaaS Cloud
El proyecto cuenta con `render.yaml` y `Procfile` configurados para despliegue inmediato. Simplemente conecta el repositorio a Render y configura las variables de entorno (`APP_SECRET_KEY`, `DATABASE_URL`, etc.).
