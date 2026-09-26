# DESIGN SYSTEM & ARQUITECTURA VISUAL (DESIGN_SYSTEM.md)

**Proyecto:** BladeSync AI / Turnero & Shop Barber  
**Versión:** 2.0.0  

---

## 1. SISTEMA DE TOKENS Y VARIABLES CSS

Centralizado en las hojas de estilo del proyecto (`admin.css`, `shop.css` y bloques de estilo de `index.html`, `live.html`, `display.html`):

```css
:root {
  /* Paleta de Colores Curada */
  --bg-obsidian: #0a0a0c;
  --bg-surface: #121216;
  --bg-surface-elevated: #1a1a22;
  --border-subtle: rgba(255, 255, 255, 0.08);

  --neon-volt: #d4ff00;
  --neon-volt-glow: rgba(212, 255, 0, 0.25);
  --cyan-accent: #00f2fe;

  --text-primary: #ffffff;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  /* Espaciado Fluido */
  --space-xs: clamp(0.35rem, 0.3rem + 0.2vw, 0.5rem);
  --space-sm: clamp(0.5rem, 0.4rem + 0.3vw, 0.75rem);
  --space-md: clamp(0.75rem, 0.6rem + 0.5vw, 1.25rem);
  --space-lg: clamp(1rem, 0.8rem + 0.8vw, 2rem);

  /* Tipografía Fluida */
  --font-xs: clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);
  --font-sm: clamp(0.875rem, 0.8rem + 0.25vw, 1rem);
  --font-md: clamp(1rem, 0.9rem + 0.4vw, 1.25rem);
  --font-lg: clamp(1.25rem, 1.1rem + 0.6vw, 1.75rem);
  --font-xl: clamp(1.75rem, 1.4rem + 1vw, 2.5rem);
  --font-tv: clamp(2.5rem, 2rem + 2vw, 4.5rem);

  /* Capas de Z-Index */
  --z-base: 1;
  --z-header: 100;
  --z-dropdown: 200;
  --z-modal: 500;
  --z-toast: 1000;
  --z-loader: 2000;
}
```

---

## 2. COMPONENTES Y ESTRUCTURA RESPONSIVE

### 2.1. Contenedor Principal
```css
.container {
  width: min(100% - 2rem, 1440px);
  margin-inline: auto;
}
```

### 2.2. Grillas Adaptativas de Productos y Slots
```css
.grid-slots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: var(--space-xs);
}

.grid-products {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: var(--space-md);
}
```
