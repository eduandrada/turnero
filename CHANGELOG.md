# CHANGELOG - HiddenSYNC AI / TURNERO & SHOP BARBER

Todas las modificaciones notables aplicadas al proyecto durante este ciclo de refactorización y estabilización se documentan en este archivo.

---

## [2.1.0-AUDIT-STABLE] - 2026-10-01

### 🛡️ Auditoría Integral del Panel Admin y Estabilización Frontend
- **Manejo Defensivo DOM:** Inclusión de verificaciones opcionales (`?.` y validación `if (el)`) en `app/static/js/admin/roadmap_features.js` para evitar excepciones `TypeError: Cannot set properties of null` durante la navegación por secciones.
- **Dispatcher Resiliente:** Envoltorio con `try...catch` en `switchSection()` dentro de `app/static/js/admin/core.js` para asegurar que el fallo aislado de una vista no impida mostrar el panel completo.
- **Registro de Secciones en Panel Admin:** Integración de los conectores y dispatchers para `live_settings` (📺 Pantalla TV & Agenda) y `promotions` (🎟️ Promociones).
- **Vista Previa Live Banners:** Se incorporaron elementos dinámicos en HTML/JS para la grilla interactiva de Banners y Vouchers en la sección `shop_promos`.
- **Invalidación de Cache:** Actualización masiva de parámetros query `?v=20261001_6` en hojas de estilo y scripts de `admin.html`.

### 🧪 Suite de Tests y Resiliencia Temporal
- **Ampliación de Pool de Barberos en Fixture:** Se agregaron los barberos `b3` (Tercer Barbero) y `b4` (Cuarto Barbero) a `tests/conftest.py` para permitir la creación concurrente de turnos sin solapamiento de agenda.
- **Estabilización de Tests Ecosistema (`test_audit_4_pruebas_ecosistema.py`):** Asignación de barberos independientes por prueba para garantizar ejecución 100% determinista en cualquier hora del día.
- **Cobertura 100% Passing:** 82 de 82 pruebas pasaron limpiamente (`82 passed in 9.91s`).

---

## [2.0.0-STABLE] - 2026-09-26

### 🛡️ Seguridad & Autenticación
- **Fortalecimiento de Hashing de Contraseñas:** Se reemplazó el esquema legado de SHA-256 simple por **PBKDF2-HMAC-SHA256 con 100.000 iteraciones y salt aleatorio de 16 bytes**.
- **Retrocompatibilidad Transparente:** `verify_password` soporta tanto contraseñas en formato `pbkdf2_sha256$` como hashes legados SHA256, actualizándolos automáticamente en la base de datos tras un inicio de sesión exitoso.
- **Remediación de Credenciales por Defecto:** Se integró la variable de entorno `ADMIN_INITIAL_PASSWORD` para definir de manera segura la contraseña del usuario administrador inicial.
- **Verificación Estricta de Secret Key:** Se agregó validación de `APP_SECRET_KEY` para bloquear el inicio inseguro en entornos de producción (`ENV=production`).

### 🧪 Tests & Estabilidad
- **Test Determinista de Slots Disponibles (`test_03_available_slots`):** Se refactorizó la prueba para buscar dinámicamente un día laboral abierto (Lunes a Sábado) y verificar también que un día cerrado (Domingo) retorne 0 slots.
- **Aislamiento de Stock en Tests de Pedidos (`test_12` y `test_13`):** Se aseguró la reposición de stock en la fase de setup de pruebas para evitar fallos falsos por agotamiento de producto.
- **Nuevas Pruebas Borde (`test_15`):** Inclusión de tests para fechas con formato inválido (400 Bad Request) y reservas en horarios transcurridos (400 Bad Request).
- **Cobertura Suite:** 15 de 15 pruebas pasando al 100% de manera determinista (`Ran 15 tests in ~2.1s - OK`).

### 📱 Responsive UI, UX & PWA
- **Service Worker Optimizada (`service-worker.js`):** Actualizado a versión `v3` con política **Network-First para `/api/*`** y **Cache-First para activos estáticos**, evitando el bloqueo de peticiones dinámicas del backend.
- **Metatags Viewport Adaptativos:** Se reemplazó `user-scalable=no` por `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">` en todas las páginas HTML (`index.html`, `admin.html`, `shop.html`, `live.html`, `display.html`).
- **Navegación Táctil y por Teclado:** Integración global de escuchador de tecla `Escape` para cerrar ventanas modales, paneles y asistentes en `app.js`, `admin.js` y `shop.js`.

### 🗄️ Base de Datos & Configuración
- **Desacoplamiento PostgreSQL:** Conversión automática de cadenas `postgres://` a `postgresql://` para compatibilidad nativa con SQLAlchemy 2.0 en proveedores Cloud (Render, Neon, Supabase).
- **Archivos de Configuración:** Actualización de `.gitignore` profesional y `.env.example` completo.
