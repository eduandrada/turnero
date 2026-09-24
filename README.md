# 💈 BladeSync AI (Edición 2026) // Urban Barber Engine & Booking PWA

Sistema integral de gestión de reservas y fidelización de clientes para barberías de autor y estudios urbanos de alta gama. Combina una arquitectura backend asíncrona en **FastAPI (Python 3.11+)**, una interfaz de usuario **PWA Mobile-First** con diseño *Dark Obsidian / Cyber-Minimalist*, un motor de tareas cron con **APScheduler** para notificaciones interactivas por **WhatsApp Cloud API** (Meta Graph API v20.0), y un **Asesor Morfológico de Estilo con IA (Visagismo)**.

---

## 🏛️ Arquitectura del Sistema

```text
                    ┌─────────────────────────┐
                    │   Cliente / PWA Móvil   │
                    │ (HTML5 + Tailwind + JS) │
                    └────────────┬────────────┘
                                 │ REST API / JSON
                                 ▼
                    ┌─────────────────────────┐
                    │     FastAPI Backend     │
                    │   (Python 3 / Async)    │
                    ├────────────┬────────────┤
                    │   SQLite   │ APScheduler│ (Cron cada 5m / 2h antes)
                    │ SQLAlchemy │  Worker    │
                    └──────┬─────┴─────┬──────┘
                           │           │
           Meta Graph API  ▼           ▼  Algoritmo Visagista / AI
        ┌─────────────────────┐     ┌──────────────────────┐
        │ WhatsApp Cloud API  │     │ Asesor de Estilo IA  │
        │ [Confirm] [Cancel]  │     │ (Morfología & Fade)  │
        └─────────────────────┘     └──────────────────────┘
```

---

## 🚀 Características Principales

1. **Backend Asíncrono Modular:**
   - **FastAPI** de alto rendimiento con validaciones estrictas vía **Pydantic v2**.
   - Persistencia relacional mediante **SQLAlchemy ORM** con SQLite (fácilmente migrable a PostgreSQL).
   - Sembrado automático de barberos y catálogo de servicios de autor en el arranque.

2. **Notificaciones Interactivas por WhatsApp Cloud API:**
   - Worker en segundo plano (**APScheduler**) que evalúa cada 5 minutos las citas que se celebrarán en la ventana de **2 horas previas**.
   - Envío de mensajes interactivos con botones de acción rápida: **`[✅ Confirmar]`** y **`[❌ Cancelar]`**.
   - **Webhook bidireccional (`/api/whatsapp-webhook`)** con verificación de handshake de Meta (`hub.mode`, `hub.challenge`) y captura de clics en tiempo real para actualizar el estado del turno sin intervención humana.

3. **Asesor Morfológico con IA (Visagismo Facial):**
   - Análisis de forma de cráneo/rostro (Ovalado, Cuadrado, Redondo, Diamante, Triangular, Corazón), densidad capilar y textura.
   - Algoritmo que recomienda la técnica de corte (ej. *Low Skin Fade*, *French Crop*, *Pompadour*) con consejos de peinado y selección directa del servicio en la reserva.

4. **Frontend PWA Mobile-First "Obsidian Cyber-Barber 2026":**
   - Paleta de color curada: Fondo Obsidian (`#0a0a0c`), superficies de cristal translúcido con efecto *backdrop-blur* (`#131318`), acentos Neón Volt (`#d4ff00`) y Neón Cian (`#00f2fe`).
   - Tipografía moderna: **Space Grotesk** para cifras/horarios y **Plus Jakarta Sans** para interfaz.
   - Grilla dinámica de slots cada 45 minutos (09:00 a 20:00 hs) calculada en tiempo real descartando turnos reservados y horas pasadas.

---

## 📁 Estructura del Proyecto

```text
turnero/
├── app/
│   ├── __init__.py
│   ├── database.py         # Configuración del motor SQLAlchemy y sesiones
│   ├── models.py           # Modelos ORM: Barber, Service, Appointment
│   ├── schemas.py          # Esquemas Pydantic v2 (Create, Read, Requests)
│   ├── scheduler.py        # Worker APScheduler y cliente WhatsApp Cloud API
│   ├── main.py             # Aplicación FastAPI, endpoints REST y Webhook
│   └── static/
│       ├── index.html      # UI Mobile-First con Tailwind CSS CDN y Obsidian Theme
│       └── app.js          # Lógica reactiva de selección, slots dinámicos e IA
├── .env.example            # Plantilla de variables de entorno
├── .env                    # Configuración local de desarrollo
├── requirements.txt        # Dependencias de Python
├── Dockerfile              # Empaquetado para despliegue en producción
└── README.md               # Documentación técnica completa
```

---

## ⚙️ Requisitos Previos

- **Python 3.11+** o **Docker**
- Token de acceso y Phone Number ID de **Meta for Developers** (WhatsApp Cloud API) para envíos reales. *(En modo desarrollo, el sistema simula el envío y registra los payloads en los logs sin interrumpir la ejecución).*

---

## 🛠️ Instalación y Ejecución Local

### 1. Clonar y preparar entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows PowerShell:
.\venv\Scripts\Activate.ps1
# O en Linux/macOS:
# source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia el archivo `.env.example` a `.env` y edita los valores correspondientes:

```ini
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./barberia.db

# Credenciales de WhatsApp Cloud API
WHATSAPP_CLOUD_API_TOKEN=tu_token_permanente_de_meta
WHATSAPP_PHONE_NUMBER_ID=109876543210
WHATSAPP_VERIFY_TOKEN=bladesync_webhook_secret_token_2026
```

### 3. Iniciar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accede a la interfaz web en tu navegador:
👉 **[http://localhost:8000](http://localhost:8000)**

Documentación interactiva de la API (Swagger UI):
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🐳 Despliegue con Docker

Para construir y ejecutar el contenedor en cualquier servidor o plataforma cloud (Render, Railway, Fly.io, AWS ECS):

```bash
# Construir la imagen
docker build -t bladesync-barber .

# Ejecutar el contenedor
docker run -d -p 8000:8000 --name bladesync-app --env-file .env bladesync-barber
```

---

## 📲 Configuración del Webhook de WhatsApp Cloud API (Meta)

1. Ingresa al panel de [Meta for Developers](https://developers.facebook.com/).
2. En tu App de WhatsApp, dirígete a **WhatsApp > Configuración > Webhook**.
3. Haz clic en **Editar**:
   - **URL de devolución de llamada:** `https://tu-dominio.com/api/whatsapp-webhook`
   - **Identificador de verificación (Verify Token):** El mismo valor configurado en `WHATSAPP_VERIFY_TOKEN` (por defecto: `bladesync_webhook_secret_token_2026`).
4. Guarda y suscríbete al evento **`messages`**.
5. Cuando el cliente presione **✅ Confirmar** o **❌ Cancelar** en su teléfono, WhatsApp enviará el evento interactivo al webhook y el sistema marcará automáticamente la cita como confirmada o cancelada.

---

## 📡 Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Retorna la aplicación PWA frontend. |
| `GET` | `/api/barbers` | Lista de barberos y sus especialidades. |
| `GET` | `/api/services` | Catálogo de servicios de autor, duración y tarifas. |
| `GET` | `/api/available-slots` | Calcula la disponibilidad de turnos (intervalos de 45 min). Parámetros: `barber_name`, `date`. |
| `POST` | `/api/appointments` | Reserva un turno validando colisiones de horario. |
| `GET` | `/api/appointments` | Consulta de citas registradas (dashboard/monitor). |
| `POST` | `/api/ai-advisor` | Asesor morfológico facial con sugerencias de corte y styling. |
| `GET` | `/api/whatsapp-webhook` | Handshake y verificación exigida por Meta Graph API. |
| `POST` | `/api/whatsapp-webhook` | Ingesta de respuestas interactivas de botones WhatsApp. |

---

## 🛡️ Licencia y Autoría

Desarrollado bajo estándares modernos de software para barberías y estudios urbanos de vanguardia.
**BladeSync AI 2026 — All rights reserved.**
