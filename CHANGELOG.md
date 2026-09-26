# CHANGELOG - BLADESYNC AI / TURNERO & SHOP BARBER

Todas las modificaciones notables aplicadas al proyecto durante este ciclo de refactorización y estabilización se documentan en este archivo.

---

## [2.0.0-STABLE] - 2026-09-26

### 🛡️ Seguridad & Autenticación
- **Fortalecimiento de Hashing de Contraseñas:** Se reemplazó el esquema legado de SHA-256 simple por **PBKDF2-HMAC-SHA256 con 100.000 iteraciones y salt aleatorio de 16 bytes**.
- **Retrocompatibilidad Transparente:** `verify_password` soporta tanto contraseñas en formato `pbkdf2_sha256$` como hashes legados SHA256, actualizándolos automáticamente en la base de datos tras un inicio de sesión exitoso.
- **Remediación de Credenciales por Defecto:** Se integró la variable de entorno `ADMIN_INITIAL_PASSWORD` para definir de manera segura la contraseña del usuario administrador inicial.
- **Verificación Estricta de Secret Key:** Se agregó validación de `APP_SECRET_KEY` para bloquear el inicio inseguro en entornos de producción (`ENV=production`).

### 🧪 Tests & Estabilidad
- **Test Determinista deSlots Disponibles (`test_03_available_slots`):** Se refactorizó la prueba para buscar dinámicamente un día laboral abierto (Lunes a Sábado) y verificar también que un día cerrado (Domingo) retorne 0 slots.
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
