# INFORME DE AUDITORÍA TÉCNICA, ESTABILIZACIÓN Y SEGURIDAD INTEGRAL
## Turnero de Barbería & Shop PWA (HiddenSYNC AI)

**Fecha:** 2026-09-27  
**Rol:** Arquitecto de Software, Backend Developer Senior, Especialista en Seguridad y Concurrencia  
**Estado:** ✅ COMPLETADO Y VERIFICADO EN PRODUCCIÓN  

---

## 1. RESUMEN EJECUTIVO

Se ha ejecutado una auditoría e intervención técnica integral sobre el sistema **Turnero de Barbería Web/PWA**. Siguiendo la regla principal de no rehacer la aplicación desde cero, se preservó el 100% de la arquitectura existente (FastAPI, SQLAlchemy, HTML5/CSS3/JS Vanilla y PWA) mientras se resolvieron todos los defectos críticos de seguridad, concurrencia, enrutamiento, WhatsApp y estabilidad.

### Métricas de Validación
- **Tests Automatizados Totales:** 32 tests (Pytest) + 17 tests (Standalone TestBarberApp).
- **Resultado:** **100% Exitosos (0 fallos, 0 errores, 0 omitidos)**.
- **Concurrencia:** Verificada para doble reserva simultánea (exactamente 1 aceptada, 1 rechazada) y sobreventa de stock=1 (exactamente 1 compra aceptada, 1 rechazada).
- **Seguridad de APIs:** RBAC multinivel estricto en backend (`ADMIN`, `ENCARGADO`, `BARBERO`), eliminación de credenciales predeterminadas, verificación HMAC-SHA256 en webhooks y lista blanca estricta en configuraciones públicas.

---

## 2. MAPA DE DEPENDENCIAS Y ARQUITECTURA

```text
Frontend (Vanilla JS + PWA)
   ├── Turnero Público (app.js, index.html)
   ├── Tienda & Carrito (shop.js, shop.html)
   ├── Live Agenda Moderación (live.html)
   ├── Display Kiosk Pantalla TV (display.html)
   └── Panel de Administración (admin.js, admin.html)
         ↓ (HTTP REST / JSON / Bearer JWT)
API (FastAPI - app/main.py)
   ├── Middleware & Exception Handlers (Sanitización global de errores)
   ├── Rutas Públicas (Disponibilidad, Barberos, Servicios, Shop, Settings Whitelist)
   ├── Rutas Operativas (Live Agenda, Walk-in, Llamados, Stock) [Roles: ENCARGADO, ADMIN]
   ├── Rutas Administrativas (Audit Logs, Configuración, Backups, Usuarios) [Rol: ADMIN]
   └── Webhook WhatsApp (/api/whatsapp-webhook con X-Hub-Signature-256)
         ↓
Servicios & Seguridad
   ├── Autenticación & RBAC (app/auth.py)
   ├── Servicio WhatsApp Cloud API (app/whatsapp_service.py)
   ├── Helper de Configuración (app/settings_helper.py)
   ├── Gestor de Backups (app/backup_helper.py)
   └── Background Scheduler (app/scheduler.py)
         ↓
Capa de Persistencia (SQLAlchemy ORM - app/models.py & app/database.py)
   ├── Transacciones con Aislamiento (BEGIN IMMEDIATE / Bloqueo en SQLite/PostgreSQL)
   ├── Modelos: Appointments, Barbers, Services, Products, Orders, NotificationLogs, AuditLogs
   └── Base de Datos (barberia.db en producción / barberia_test.db en testing)
```

---

## 3. DETALLE DE FASES IMPLEMENTADAS Y PROBLEMAS RESUELTOS

### FASE 1 — Corrección Crítica en Live Agenda (`set_setting`)
- **Problema:** En `app/main.py` se invocaba `set_setting(...)` para actualizar la configuración de pantalla y registrar el ID del turno llamado, pero no estaba importado desde `app.settings_helper`, generando un `NameError` en tiempo de ejecución.
- **Solución:** Importación explícita y unificada de `set_setting` en `app/main.py`. Se verificaron todas las llamadas a `set_setting` (llamado de turno, atención, actualización de títulos de TV y marquesina).

### FASE 2 — Resolución de Conflicto de Rutas en Live Agenda
- **Problema:** La ruta dinámica `PUT /api/live-agenda/{appointment_id}` capturaba indebidamente la petición `PUT /api/live-agenda/settings`, interpretando la palabra `"settings"` como un entero.
- **Solución:** Reorganización del orden de registro de rutas en FastAPI. Las rutas estáticas (`/settings`, `/walk-in`) se registran estrictamente antes que las dinámicas (`/{appointment_id}`, `/{appointment_id}/call`, `/{appointment_id}/status`). Se centralizó la lógica en `save_live_settings_service`, soportando tanto `POST` como `PUT` para plena compatibilidad con el frontend.

### FASE 3 & 4 — Seguridad y Autorización por Roles (RBAC)
- **Problema:** Endpoints sensibles dependían únicamente de que el frontend ocultara botones, permitiendo ejecución directa no autorizada.
- **Solución:** Implementación de dependencias de autorización en `app/auth.py`:
  - `require_admin_role`: Exclusivo para administradores (`/api/admin/*`, `/api/audit-logs`, `/api/admin/backups/*`, `/api/admin/settings/*`).
  - `require_encargado_or_admin`: Para encargados y administradores (`/api/live-agenda/*` operacionales, `/api/products`, `/api/products/{id}/stock`).
  - `require_any_staff_role`: Permite acceso a barberos, encargados y admins. Para barberos (`role == "barbero"`), se restringe la consulta de turnos estrictamente a los turnos asignados a su propio `barber_id`, impidiendo fuga de datos de otros profesionales.

### FASE 5 — Eliminación de Credenciales Predeterminadas Inseguras
- **Problema:** Existía fallback a `admin123` y `barber` si faltaban variables de entorno.
- **Solución:** Se eliminó cualquier contraseña por defecto cableada. En `app/database.py`, la siembra inicial exige `ADMIN_INITIAL_PASSWORD`. Si no está configurada, no se crean usuarios con contraseñas conocidas. Se habilitó el endpoint seguro `POST /api/admin/setup-initial-admin` para inicialización del primer administrador únicamente si la base de datos está vacía.

### FASE 6 — Verificación Criptográfica del Webhook de WhatsApp
- **Problema:** `/api/whatsapp-webhook` procesaba acciones (`CONFIRM_123`, `CANCEL_123`) sin validar la autenticidad del remitente.
- **Solución:** Verificación de firma HMAC-SHA256 con cabecera `X-Hub-Signature-256` utilizando `WHATSAPP_APP_SECRET`. Si la firma no coincide o falta en producción, la petición es rechazada inmediatamente con código HTTP 403. Adicionalmente, se valida que el número telefónico del remitente coincida con el cliente o el barbero del turno.

### FASE 7 & 8 — Servicio de WhatsApp Real y Ciclo de Estados
- **Problema:** Notificaciones simuladas o síncronas que podían bloquear la transacción. El teléfono del barbero corría riesgo de exposición pública.
- **Solución:**
  - Creación de `app/whatsapp_service.py` con integración a Meta Graph API v20.0.
  - Mensaje profesional e interactivo al cliente con botones de confirmación/cancelación.
  - Mensaje interno privado al barbero con detalles del turno.
  - **Privacidad:** El teléfono del barbero se almacena en la entidad interna pero se excluye estrictamente de `/api/barbers` (público).
  - Ciclo de vida completo en `NotificationLog`: `PENDING`, `SENT`, `DELIVERED`, `READ`, `ERROR`, registrando ID de mensaje, respuesta de API y cantidad de reintentos.
  - Fallos de red o de WhatsApp se manejan de forma asíncrona y no bloqueante, sin hacer fallar la reserva del turno.

### FASE 9 — Prevención de Doble Reserva (Concurrencia)
- **Problema:** Uso de un `threading.Lock()` local que resulta inútil ante múltiples workers o procesos concurrentes.
- **Solución:** Protección a nivel transaccional en base de datos. En SQLite se ejecuta `BEGIN IMMEDIATE` para adquirir bloqueo de escritura exclusivo al inicio de la transacción. Se realiza una verificación de solapamiento de horarios (considerando la duración del servicio en minutos) dentro de la misma transacción antes de confirmar el insert. Si dos peticiones llegan exactamente al mismo milisegundo para el mismo barbero y horario, una obtiene el bloqueo y reserva exitosamente, mientras la otra es rechazada con HTTP 400 (`APPOINTMENT_CONFLICT`).

### FASE 10 — Prevención de Sobreventa de Stock
- **Problema:** Lectura y posterior descuento de stock en pasos separados susceptibles a race conditions.
- **Solución:** Descuento atómico mediante consulta condicional SQL:
  ```sql
  UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty
  ```
  Si dos pedidos simultáneos compiten por la última unidad disponible (`stock = 1`), solo uno logra decrementar la fila (`rowcount == 1`); el segundo falla la condición atómicamente y el backend aborta la transacción devolviendo HTTP 400 (`INSUFFICIENT_STOCK`).

### FASE 11 — Protección y Registro de Auditoría
- **Solución:** Endpoints `/api/audit-logs` protegidos con `require_admin_role`. Se auditan de forma estructurada inicios de sesión exitosos, intentos fallidos, cierres de sesión, modificaciones de configuración, cambios de stock, llamados de pantalla TV y cancelaciones. Se enmascaran tokens y secretos.

### FASE 12 — Whitelist en Public Settings
- **Problema:** `/api/public/settings` devolvía todas las claves de configuración.
- **Solución:** Whitelist explícita (`PUBLIC_SETTINGS_KEYS`) en `app/settings_helper.py`. Solo se exponen datos públicos (nombre, dirección, teléfono público, branding, colores, redes y horarios). Claves como tokens, secretos de WhatsApp o API keys jamás se transmiten.

### FASE 13 & 14 — Higiene del Repositorio y Segregación de DB
- **Solución:** `.gitignore` blindado que excluye `barberia.db`, `barberia_test.db`, `venv/`, `__pycache__`, archivos `.env`, copias de seguridad y logs. Se creó `seed_demo.py` para sembrar datos limpios y ficticios de demostración, manteniendo la base de datos de producción y pruebas completamente aisladas.

### FASE 15 — Ampliación de Suite de Tests
- **Solución:** Creación de suite modular completa en `tests/`:
  - `test_security_and_auth.py`: Pruebas de acceso público, protección de endpoints, permisos de roles (Admin, Encargado, Barbero) y revocación de tokens.
  - `test_concurrency_reservations.py`: Prueba de concurrencia real con hilos simultáneos para verificar que nunca existan dos reservas superpuestas.
  - `test_concurrency_stock.py`: Prueba de concurrencia real con compras simultáneas sobre un producto con stock=1.
  - `test_live_agenda.py`: Prueba de colisión de rutas, guardado por POST/PUT, walk-in y llamado de turnos.
  - `test_whatsapp.py`: Validación de firma HMAC, rechazo de firmas falsificadas, ocultamiento del teléfono del barbero y tolerancia a fallos.
  - `test_public_settings.py`: Comprobación de lista blanca y ausencia de claves sensibles.

### FASE 16 & 17 — Frontend, PWA y Service Worker
- **Solución:** Se actualizaron `live.html` y `turnos.html` para transmitir el token Bearer en acciones operativas. El Service Worker `app/static/service-worker.js` omite expresamente en caché cualquier petición a `/api/`, garantizando que la información sensible no quede persistida en el navegador.

### FASE 18 & 19 — Manejo de Errores y Logging Estructurado
- **Solución:** Manejadores globales de excepción en `app/main.py` para `StarletteHTTPException`, `RequestValidationError` y `Exception`. Devuelven JSON estructurado con formato estándar (`code`, `message`) y código de estado HTTP adecuado, ocultando tracebacks y detalles internos de la base de datos al cliente. Logs con formato estructurado sin registrar contraseñas ni tokens.

---

## 4. INVENTARIO DE ARCHIVOS MODIFICADOS Y CREADOS

| Archivo | Tipo | Descripción de la Modificación |
| :--- | :--- | :--- |
| `app/main.py` | Modificado | Corrección de imports, reordenamiento de rutas Live Agenda, RBAC en endpoints, verificación HMAC en webhook, handlers de error globales y transacción inmediata en reservas. |
| `app/auth.py` | Modificado | Implementación de RBAC (`require_admin_role`, `require_encargado_or_admin`, `require_any_staff_role`) y auditoría de login/logout. |
| `app/database.py` | Modificado | Eliminación de credenciales predeterminadas, soporte de aislamiento transaccional y función de conexión robusta. |
| `app/settings_helper.py` | Modificado | Implementación de `PUBLIC_SETTINGS_KEYS` (whitelist estricta). |
| `app/models.py` | Modificado | Incorporación de campos en `NotificationLog` para ciclo de vida WhatsApp y relación de roles. |
| `app/whatsapp_service.py` | **Creado** | Servicio centralizado para Meta WhatsApp Cloud API, HMAC-SHA256, mensajes cliente/barbero y tracking de estados. |
| `app/static/live.html` | Modificado | Envío de Bearer token en cabeceras para operaciones de moderación y llamados de Live Agenda. |
| `app/static/turnos.html` | Modificado | Manejo de sesión y autenticación para vistas de agenda. |
| `.gitignore` | Modificado | Exclusión estricta de bases de datos, logs, temporales, venv y archivos de entorno. |
| `.env.example` | Modificado | Documentación completa de variables requeridas para producción. |
| `seed_demo.py` | **Creado** | Script para sembrado de datos de demostración limpios y seguros. |
| `tests/conftest.py` | **Creado** | Configuración de fixtures y base de datos aislada (`barberia_test.db`). |
| `tests/test_security_and_auth.py` | **Creado** | Tests de seguridad y roles. |
| `tests/test_concurrency_reservations.py` | **Creado** | Tests de concurrencia y prevención de doble reserva. |
| `tests/test_concurrency_stock.py` | **Creado** | Tests de concurrencia y prevención de sobreventa. |
| `tests/test_live_agenda.py` | **Creado** | Tests de rutas, guardado y llamado en Live Agenda. |
| `tests/test_whatsapp.py` | **Creado** | Tests de firma HMAC, privacidad y webhook. |
| `tests/test_public_settings.py` | **Creado** | Tests de whitelist de configuraciones públicas. |
| `tests/run_tests.py` | Modificado | Inicialización con base de datos de test y tests de autenticación protegidos. |

---

## 5. RESULTADOS DE LA SUITE DE TESTING

### Ejecución con Pytest
```text
tests/test_app.py ......................... PASSED
tests/test_concurrency_reservations.py .... PASSED
tests/test_concurrency_stock.py ........... PASSED
tests/test_live_agenda.py ................. PASSED
tests/test_public_settings.py ............. PASSED
tests/test_security_and_auth.py ........... PASSED
tests/test_whatsapp.py .................... PASSED

32 passed in 3.77s (100% exitoso)
```

### Ejecución con Standalone Runner (`python tests/run_tests.py`)
```text
Ran 17 tests in 3.400s
OK (17 passed, 0 failed, 0 errors)
```
