# AUDITORÍA RESPONSIVE Y MULTIDISPOSITIVO - BLADESYNC AI

**Fecha:** 2026-09-26  
**Autor:** Arquitecto UX/UI Senior & Frontend Lead  
**Estado:** FASE 1 COMPLETADA — AUDITORÍA Y ESTRATEGIA DE ADAPTABILIDAD  

---

## 1. EVALUACIÓN POR TIPO DE PANTALLA

### 1.1. Móvil (360px - 430px)
- **Turnero (`index.html` + `app.js`):** La experiencia de reserva requiere botones de slots adaptables mediante grilla fluida (`minmax(90px, 1fr)`). Los formularios deben usar una sola columna con inputs de tamaño táctil mínimo (44x44px).
- **Admin (`admin.html` + `admin.css`):** Las tablas HTML extensas (Turnos, Pedidos, Productos) provocan scroll horizontal involuntario en móviles si no se transforman en tarjetas estructuradas (*card layout*). El menú lateral debe convertirse en menú desplegable/drawer o navegación inferior.
- **Shop (`shop.html` + `shop.css`):** Las tarjetas de catálogo deben ajustarse dinámicamente en 1 o 2 columnas según el ancho real (`min(100%, 280px)`). El carrito de compras requiere comportarse como *bottom sheet* desplegable.
- **PWA & Notch:** Requiere incorporar soporte explícito para `viewport-fit=cover` y variables de `env(safe-area-inset-*)`.

### 1.2. Tablet (768px - 1024px)
- Redistribución inteligente a 2 columnas para formularios y widgets de dashboard.
- Adaptación del sidebar administrativo en modo compacto con iconos y descripciones legibles.

### 1.3. Desktop & Notebook (1366px - 1920px)
- Evitar estiramientos excesivos de contenido fijando `max-width: 1440px` y centrado horizontal (`margin-inline: auto`).
- Layout multicolumna limpio para administración y catálogo del shop.

### 1.4. TV & Sala de Espera (`display.html` / `live.html`)
- Tipografía gigante y fluida utilizando `clamp()`.
- Cartelera con contraste elevado, tarjetas de llamado destacadas y locución por voz sincronizada.
- Visualización de cola de espera en tiempo real optimizada para lectura a distancia (3 a 5 metros).

---

## 2. ESTRATEGIA DE DISEÑO SISTÉMICO (DESIGN SYSTEM TOKENS)

Se definirán tokens CSS unificados en `:root`:

```css
:root {
  /* Breakpoints fluidos y Contenedores */
  --container-max-width: 1440px;

  /* Espaciado Fluido */
  --space-xs: clamp(0.35rem, 0.3rem + 0.2vw, 0.5rem);
  --space-sm: clamp(0.5rem, 0.4rem + 0.3vw, 0.75rem);
  --space-md: clamp(0.75rem, 0.6rem + 0.5vw, 1.25rem);
  --space-lg: clamp(1rem, 0.8rem + 0.8vw, 2rem);
  --space-xl: clamp(1.5rem, 1.2rem + 1.2vw, 3rem);

  /* Tipografía Fluida */
  --font-xs: clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);
  --font-sm: clamp(0.875rem, 0.8rem + 0.25vw, 1rem);
  --font-md: clamp(1rem, 0.9rem + 0.4vw, 1.25rem);
  --font-lg: clamp(1.25rem, 1.1rem + 0.6vw, 1.75rem);
  --font-xl: clamp(1.75rem, 1.4rem + 1vw, 2.5rem);
  --font-tv: clamp(2.5rem, 2rem + 2vw, 4.5rem);

  /* Capas Z-Index */
  --z-base: 1;
  --z-header: 100;
  --z-dropdown: 200;
  --z-modal: 500;
  --z-toast: 1000;
  --z-loader: 2000;
}
```

---

## 3. HOJA DE RUTA DE REFACTORIZACIÓN RESPONSIVE

1. **Tokens y Reset:** Consolidación de variables CSS de espaciado, tipografía fluida y z-index en la hoja de estilos global.
2. **Safe Areas PWA:** Inclusión de metatags y reglas CSS de padding inferior para dispositivos móviles.
3. **Tablas Adaptativas:** Conversión de tablas complejas en tarjetas (*card view*) en breakpoints inferiores a 768px.
4. **Modales y Bottom Sheets:** Adaptación de ventanas modales para comportarse como *bottom sheets* táctiles en dispositivos móviles.
5. **Reorganización del Dashboard:** Grillas adaptativas `repeat(auto-fit, minmax(min(100%, 280px), 1fr))` para widgets administrativos.
