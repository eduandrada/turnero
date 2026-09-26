# AUDITORÍA TÉCNICA - BLADESYNC AI / TURNERO & SHOP BARBER

**Fecha:** 2026-09-26  
**Autor:** Arquitecto de Software Senior  
**Estado:** FASE 1 COMPLETADA — AUDITORÍA TÉCNICA Y DIAGNÓSTICO  

---

## 1. RESUMEN EXECUTIVO

Se ha realizado la inspección completa del sistema **BladeSync AI / Turnero & Shop Barber**. El proyecto es una aplicación web full-stack basada en **FastAPI (Python)**, **SQLAlchemy (SQLite)**, **HTML5/JS Vanilla/CSS3** y **PWA**.

El sistema actualmente cuenta con una base funcional amplia que incluye:
- **Turnero público:** Selección de servicio, barbero, fecha, horario disponible y confirmación de cita.
- **Asesor de Estilo:** Motor heurístico de visagismo por morfología facial.
- **Agenda en Vivo & Pantalla TV (Display):** Monitoreo en tiempo real con locución/sintetizador de voz, llamado de clientes, turnos en sillón y cartelera interactiva.
- **Shop Barber:** Catálogo de productos, categorías, carrito de compras, zonas de delivery, cálculo de envío, monto mínimo por zona y generación de número de pedido único (`PED-YYYYMMDD-HHMMSS-XXXX`).
- **Administración completa:** Dashboard con estadísticas de ventas/turnos/stock, gestión de barberos, servicios, estilos, clientes, turnos, productos, pedidos, zonas de delivery, configuraciones globales (branding, horarios, PWA, TV), logs de auditoría y copias de seguridad.
- **PWA & Offline support:** Manifest dinámico y Service Worker.
- **Integración WhatsApp Cloud API:** Recordatorios automáticos interactivos con botones de confirmación/cancelación y webhook para recibir respuesta.

---

## 2. INVENTARIO DE ARQUITECTURA Y MÓDULOS

### 2.1. Backend (FastAPI + SQLAlchemy)

| Archivo | Responsabilidad / Descripción | Estado Auditoría |
| :--- | :--- | :--- |
| [`app/main.py`](file:///c:/Users/Usuario/turnero/app/main.py) | Punto de entrada FastAPI, endpoints públicos, admin, shop, live agenda, TV, backup, static files mount. | **Funcional / Requiere refactorización de seguridad y modularización.** |
| [`app/models.py`](file:///c:/Users/Usuario/turnero/app/models.py) | Modelos ORM (14 entidades: `AdminUser`, `ShopSetting`, `Barber`, `Service`, `Style`, `Client`, `Appointment`, `Category`, `Product`, `DeliveryZone`, `Order`, `OrderItem`, `Promotion`, `AppNotification`, `AuditLog`). | **Completo / Relaciones correctas.** |
| [`app/schemas.py`](file:///c:/Users/Usuario/turnero/app/schemas.py) | Esquemas Pydantic v2 para validación de entrada/salida de datos. | **Correcto / Tipado robusto.** |
| [`app/database.py`](file:///c:/Users/Usuario/turnero/app/database.py) | Conexión Engine, `SessionLocal`, zona horaria Argentina (`America/Argentina/Buenos_Aires`) y migraciones automáticas al iniciar. | **Estable.** |
| [`app/auth.py`](file:///c:/Users/Usuario/turnero/app/auth.py) | Autenticación JWT Bearer con HMAC-SHA256, hash de contraseñas (SHA256 simple + salt) y lista en memoria de revocación. | **CRÍTICO: Hash inseguro (SHA-256 simple), Secret Key por defecto si falta env, y revocación en memoria no persistente.** |
| [`app/settings_helper.py`](file:///c:/Users/Usuario/turnero/app/settings_helper.py) | Centralización de configuraciones globales (branding, horarios en JSON, textos, colores, TV, PWA). | **Funcional / Excelente abstracción.** |
| [`app/scheduler.py`](file:///c:/Users/Usuario/turnero/app/scheduler.py) | APScheduler para recordatorio automatizado vía WhatsApp Cloud API cada 5 minutos. | **Funcional / Maneja fallback si no hay token real.** |
| [`app/backup_helper.py`](file:///c:/Users/Usuario/turnero/app/backup_helper.py) | Generación de backups JSON estructurados y restauración segura con backup automático previo. | **Funcional.** |

### 2.2. Frontend (Static Assets)

| Archivo | Tipo | Función |
| :--- | :--- | :--- |
| [`app/static/index.html`](file:///c:/Users/Usuario/turnero/app/static/index.html) | HTML | Landing pública del turnero, reserva de citas y asesor de visagismo. |
| [`app/static/app.js`](file:///c:/Users/Usuario/turnero/app/static/app.js) | JS | Lógica del turnero público, fetch de slots, selector de fecha/hora, modal de reserva. |
| [`app/static/admin.html`](file:///c:/Users/Usuario/turnero/app/static/admin.html) | HTML | Panel de administración SPA (Dashboard, Turnos, Barberos, Servicios, Shop, Pedidos, Ajustes, Backup, Audit). |
| [`app/static/admin.js`](file:///c:/Users/Usuario/turnero/app/static/admin.js) | JS | Lógica SPA del administrador, gestión de modales, consumo de API Bearer token, tablas y filtros. |
| [`app/static/admin.css`](file:///c:/Users/Usuario/turnero/app/static/admin.css) | CSS | Estilos del panel de administración. |
| [`app/static/shop.html`](file:///c:/Users/Usuario/turnero/app/static/shop.html) | HTML | Tienda online Barber Shop (Catálogo, Filtro por categoría, Carrito lateral, Checkout). |
| [`app/static/shop.js`](file:///c:/Users/Usuario/turnero/app/static/shop.js) | JS | Carrito en `localStorage`, cálculo de envío por zona, envío de pedido al backend. |
| [`app/static/shop.css`](file:///c:/Users/Usuario/turnero/app/static/shop.css) | CSS | Estilos del Shop. |
| [`app/static/live.html`](file:///c:/Users/Usuario/turnero/app/static/live.html) | HTML | Agenda en Vivo y Consola de Llamados para el equipo de recepción. |
| [`app/static/display.html`](file:///c:/Users/Usuario/turnero/app/static/display.html) | HTML | Pantalla TV gigante para sala de espera (Llamado visual/sonoro, siguiente en turno, cartelera). |
| [`app/static/service-worker.js`](file:///c:/Users/Usuario/turnero/app/static/service-worker.js) | JS | PWA Service Worker con estrategia de caché. **Atención:** actualmente puede interceptar o cachear peticiones `GET` sin distinguir `/api/`. |

---

## 3. HALLAZGOS Y PROBLEMAS DETECTADOS

### 3.1. Pruebas Automatizadas (`tests/run_tests.py`)
- **Fallo identificado en `test_03_available_slots`:**
  - **Causa raíz:** El test calcula `tomorrow = get_argentina_now() + timedelta(days=1)`. Cuando el test se ejecuta en sábado, `tomorrow` es domingo. Según `DEFAULT_SETTINGS["business_hours"]`, el domingo está configurado como `active: false`. Por lo tanto, `/api/available-slots` retorna `slots: []`, provocando la falla `AssertionError: 0 not greater than 0`.
  - **Solución planificada (Fase 5):** Reestructurar la prueba para buscar de manera determinista el próximo día laboral activo (o mockear/asegurar un día abierto), probando tanto días abiertos como días cerrados sin depender del día de la semana en que corra la suite.

### 3.2. Seguridad & Autenticación
- **Contraseña predeterminada débil:** Sembrado automático de `admin / admin123` en `seed_initial_data()`.
- **Algoritmo de Hashing de contraseñas:** Uso de `hashlib.sha256(password + salt)`. Debe actualizarse a un algoritmo moderno y seguro diseñado para contraseñas (como **Argon2** o **bcrypt** / **scrypt** con `passlib`/`hashlib.scrypt`).
- **Secret Key en Fallback:** `SECRET_KEY` fallback público en `auth.py`. En entorno de producción sin `APP_SECRET_KEY` configurada debe arrojar un error explícito o requerir clave segura.
- **Revocación de Tokens:** La lista `REVOKED_TOKENS` se almacena exclusivamente en memoria RAM. Al reiniciar el proceso Uvicorn, los tokens revocados vuelven a ser válidos hasta expiración.

### 3.3. PWA / Service Worker
- `service-worker.js` intercepta todo evento `fetch` `GET` y responde con `caches.match() || fetch()`. Esto puede hacer que respuestas de APIs dinámicas (como `/api/public/settings` o endpoints admin) queden atascadas en caché.
- Debe implementarse una política Network-First para `/api/*` y Cache-First para recursos estáticos reales (imágenes, CSS, JS estático), invalidando el caché cuando cambie `CACHE_NAME`.

### 3.4. Calidad de Código & Git
- `barberia - copia.db` y `turnero.zip` presentes en el workspace.
- `.gitignore` requiere revisión para asegurar que no se suban archivos generados ni datos sensibles.
- `.env.example` debe enriquecerse con todas las variables necesarias de producción (`APP_SECRET_KEY`, `ADMIN_INITIAL_PASSWORD`, `DATABASE_URL`, `WHATSAPP_*`).

---

## 4. PLAN DE ACCIÓN POR FASES

- **FASE 1 (Actual):** Entrega de `AUDITORIA_TECNICA.md` y `RESPONSIVE_AUDIT.md`.
- **FASE 2:** Limpieza del workspace, optimización de `.gitignore` y actualización de `.env.example`.
- **FASE 3:** Fortalecimiento de seguridad (Algoritmo de hash Argon2/scrypt, remediación de credenciales por defecto, validación estricta de `APP_SECRET_KEY`, persistencia/validación de sesiones).
- **FASE 4:** Verificación del esquema de Base de Datos y estrategia de backup/migración transparente.
- **FASE 5:** Corrección determinista de `test_03_available_slots` y ampliación de suite de pruebas de turnero.
- **FASE 6:** Estabilización y refactor del Panel Administrativo.
- **FASE 7:** Estabilización de Shop, carrito, stock transaccional y checkout.
- **FASE 8:** Ajustes PWA, actualización de Service Worker sin bloqueo de API y safe areas.
- **FASE 9:** Verificación y robustez de integración WhatsApp / APScheduler.
- **FASE 10:** Suite completa de Testing Integral.
- **FASE 11:** Preparación final para despliegue (Docker, Render) y reportes.

---

## 5. CONCLUSIÓN DE FASE 1
El sistema tiene una base sólida y funcional. La estrategia de refactorización preservará el 100% de la funcionalidad existente mientras eleva los estándares de seguridad, testing y experiencia multidispositivo.
