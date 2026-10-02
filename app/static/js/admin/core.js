/**
 * Admin Panel - Core Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles session, auth, navigation, sound, toast, modal base & shared utilities.
 */

// Web Audio API Micro-Sound Synthesizer
const UISound = {
  ctx: null,
  enabled: true,
  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  },
  play(type = "click") {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.ctx.destination);

      if (type === "click") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(600, now);
        osc.frequency.exponentialRampToValueAtTime(160, now + 0.04);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      } else if (type === "success") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554.37, now + 0.08);
        osc.frequency.setValueAtTime(659.25, now + 0.16);
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === "tab") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(400, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.03);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);
        osc.start(now);
        osc.stop(now + 0.03);
      }
    } catch (e) {}
  }
};

let adminToken = localStorage.getItem("hiddensync_admin_token") || localStorage.getItem("bladesync_admin_token") || "";
let currentUserRole = "";
let currentUserId = null;
let currentUsername = "";
let currentActiveSection = "dashboard";

// Shared Modal Controller State
let currentModalType = "";
let editingRecordId = null;

function showAdminToast(msg, type = "info") {
  let container = document.getElementById("adminToastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "adminToastContainer";
    container.className = "admin-toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `admin-toast ${type}`;
  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error" || type === "danger") icon = "❌";
  if (type === "warning") icon = "⚠️";

  toast.innerHTML = `<span style="font-size:1.1rem; line-height:1;">${icon}</span> <span>${escapeHtml(msg)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
window.showAdminToast = showAdminToast;
window.showToast = showAdminToast;

function showLoginOverlay() {
  const overlay = document.getElementById("loginOverlay");
  const app = document.getElementById("adminApp");
  if (overlay) overlay.style.display = "flex";
  if (app) app.style.display = "none";
}

function hideLoginOverlay() {
  const overlay = document.getElementById("loginOverlay");
  const app = document.getElementById("adminApp");
  if (overlay) overlay.style.display = "none";
  if (app) app.style.display = "flex";
}

function updateBottomNavActiveState() {
  document.querySelectorAll(".admin-bottom-nav-item").forEach(item => {
    const sec = item.getAttribute("data-section");
    if (sec === currentActiveSection) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });
}

function toggleSidebar(forceState) {
  const sidebar = document.getElementById("adminSidebar");
  const backdrop = document.getElementById("adminSidebarBackdrop");
  if (!sidebar) return;

  const isOpen = sidebar.classList.contains("open");
  const shouldOpen = forceState !== undefined ? forceState : !isOpen;

  if (shouldOpen) {
    sidebar.classList.add("open");
    if (backdrop) backdrop.classList.add("active");
    document.body.style.overflow = "hidden";
  } else {
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("active");
    document.body.style.overflow = "";
  }
}

function filterAdminMenu(query) {
  const q = (query || "").toLowerCase().trim();
  const navItems = document.querySelectorAll(".admin-nav-item");
  const categories = document.querySelectorAll(".admin-menu-category");

  navItems.forEach(item => {
    const text = item.textContent.toLowerCase();
    if (!q || text.includes(q)) {
      item.style.display = "flex";
    } else {
      item.style.display = "none";
    }
  });

  categories.forEach(cat => {
    if (!q) {
      cat.style.display = "block";
      return;
    }
    let nextEl = cat.nextElementSibling;
    let hasVisibleItem = false;
    while (nextEl && !nextEl.classList.contains("admin-menu-category")) {
      if (nextEl.classList.contains("admin-nav-item") && nextEl.style.display !== "none") {
        hasVisibleItem = true;
        break;
      }
      nextEl = nextEl.nextElementSibling;
    }
    cat.style.display = hasVisibleItem ? "block" : "none";
  });
}

async function handleAdminLogin() {
  const u = document.getElementById("loginUsername")?.value.trim();
  const p = document.getElementById("loginPassword")?.value.trim();
  if (!u || !p) return;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p })
    });

    const data = await res.json();
    const token = data.access_token || data.token;
    if (res.ok && token) {
      adminToken = token;
      localStorage.setItem("hiddensync_admin_token", adminToken);
      localStorage.setItem("hiddensync_admin_token", adminToken);
      currentUserRole = data.role || "admin";
      currentUserId = data.user_id;
      currentUsername = data.username || u;
      hideLoginOverlay();
      switchSection("dashboard");
      UISound.play("success");
    } else {
      alert(data.detail || "Credenciales incorrectas.");
    }
  } catch (e) {
    alert("Error de conexión al servidor.");
  }
}

async function verifyAdminSession() {
  if (!adminToken) {
    showLoginOverlay();
    return;
  }
  try {
    const res = await fetch("/api/admin/me", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      currentUserRole = data.role || "admin";
      currentUserId = data.id;
      currentUsername = data.username;
      hideLoginOverlay();
      switchSection("dashboard");
    } else {
      localStorage.removeItem("hiddensync_admin_token");
      localStorage.removeItem("hiddensync_admin_token");
      adminToken = "";
      showLoginOverlay();
    }
  } catch (e) {
    showLoginOverlay();
  }
}

function adminLogout() {
  localStorage.removeItem("hiddensync_admin_token");
  localStorage.removeItem("hiddensync_admin_token");
  adminToken = "";
  currentUserRole = "";
  currentUserId = null;
  currentUsername = "";
  showLoginOverlay();
}

function authHeaders() {
  return {
    "Authorization": `Bearer ${adminToken}`,
    "Content-Type": "application/json"
  };
}

// Navigation dispatcher
function switchSection(secId) {
  currentActiveSection = secId;
  document.querySelectorAll(".admin-section").forEach(s => s.style.display = "none");
  document.querySelectorAll(".admin-nav-item").forEach(i => i.classList.remove("active"));

  const activeNavItem = document.querySelector(`.admin-nav-item[data-section="${secId}"]`);
  if (activeNavItem) activeNavItem.classList.add("active");

  updateBottomNavActiveState();

  const target = document.getElementById(`section-${secId}`);
  if (target) {
    target.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const searchInput = document.getElementById("adminMenuSearch");
  if (searchInput && searchInput.value) {
    searchInput.value = "";
    filterAdminMenu("");
  }

  toggleSidebar(false);

  const titles = {
    dashboard: "Dashboard",
    appointments: "Turnos & Agenda",
    clients: "Directorio de Clientes",
    barbers: "Barberos de Autor",
    services: "Servicios & Precios",
    styles: "Estilos de Corte",
    schedules: "Horarios de Atención",
    stats: "📊 Historial de Clientes Atendidos & Métricas",
    products: "Productos & Stock",
    orders: "Pedidos Shop Barber",
    delivery: "Zonas de Delivery",
    promotions: "Promociones",
    whatsapp: "Configuración WhatsApp",
    notifications: "Notificaciones",
    identity: "Identidad & Barbería",
    appearance: "Apariencia & Tema",
    content: "Contenido & Textos",
    pwa: "Configuración PWA",
    security: "Seguridad",
    backups: "Copias de Seguridad",
    audit: "🛡️ Auditoría de Cambios",
    staff: "👥 Gestión de Personal & Permisos",
    shift_closures: "💵 Auditoría de Cajas & Rendiciones",
    payments_config: "💳 Pasarela de Pagos & Señas Previa",
    barber_club: "⭐ Barber Club // Fidelización & Puntos",
    push_pwa: "🔔 Notificaciones Push PWA Automatizadas",
    shop_promos: "🎨 Banners & Vouchers Shop Barber",
    barber_productivity: "📊 Reporte de Productividad e Incentivos por Barbero"
  };

  const titleEl = document.getElementById("currentSectionTitle");
  if (titleEl) titleEl.textContent = titles[secId] || "Panel";

  try {
    if (secId === "dashboard" && typeof loadAdminDashboard === "function") loadAdminDashboard();
    else if (secId === "appointments" && typeof loadAdminAppointments === "function") loadAdminAppointments();
    else if (secId === "clients" && typeof loadAdminClients === "function") loadAdminClients();
    else if (secId === "barbers" && typeof loadAdminBarbers === "function") loadAdminBarbers();
    else if (secId === "services" && typeof loadAdminServices === "function") loadAdminServices();
    else if (secId === "styles" && typeof loadAdminStyles === "function") loadAdminStyles();
    else if (secId === "schedules" && typeof loadAdminSchedules === "function") loadAdminSchedules();
    else if (secId === "stats" && typeof loadAttendedClientsStats === "function") loadAttendedClientsStats();
    else if (secId === "products" && typeof loadAdminProducts === "function") loadAdminProducts();
    else if (secId === "orders" && typeof loadAdminOrders === "function") loadAdminOrders();
    else if (secId === "delivery" && typeof loadAdminDelivery === "function") loadAdminDelivery();
    else if (secId === "notifications" && typeof loadAdminNotificationLogs === "function") loadAdminNotificationLogs();
    else if ((secId === "identity" || secId === "appearance" || secId === "content" || secId === "pwa" || secId === "whatsapp" || secId === "shop_promos") && typeof loadSettingsToForm === "function") loadSettingsToForm();
    else if (secId === "backups" && typeof loadAdminBackups === "function") loadAdminBackups();
    else if (secId === "audit" && typeof loadAuditLogsData === "function") loadAuditLogsData();
    else if (secId === "staff" && typeof loadStaffData === "function") loadStaffData();
    else if (secId === "shift_closures" && typeof loadShiftClosuresData === "function") loadShiftClosuresData();
    else if (secId === "payments_config" && typeof loadPaymentSettings === "function") loadPaymentSettings();
    else if (secId === "barber_club" && typeof loadLoyaltySettings === "function") loadLoyaltySettings();
    else if (secId === "push_pwa" && typeof loadPushSettings === "function") loadPushSettings();
    else if (secId === "barber_productivity" && typeof loadBarberProductivity === "function") loadBarberProductivity();
  } catch (err) {
    console.error(`Error cargando sección ${secId}:`, err);
  }
}

function getLocalDateStr(offsetDays = 0) {
  const d = new Date();
  if (offsetDays !== 0) d.setDate(d.getDate() + offsetDays);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function showToast(message, type = "success") {
  let container = document.getElementById("adminToastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "adminToastContainer";
    container.className = "admin-toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "admin-toast";
  if (type === "error") {
    toast.style.borderLeftColor = "#ef4444";
  } else if (type === "warning") {
    toast.style.borderLeftColor = "#f59e0b";
  }

  const icon = type === "error" ? "⚠️" : (type === "warning" ? "⏳" : "✅");
  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function closeAdminModal() {
  const m = document.getElementById("adminModal");
  if (m) m.style.display = "none";
  editingRecordId = null;
}

async function submitAdminModal() {
  try {
    const isEdit = editingRecordId !== null;
    const method = isEdit ? "PUT" : "POST";

    if (currentModalType === "barber") {
      const name = document.getElementById("modal_barber_name")?.value?.trim() || "";
      const phone = document.getElementById("modal_barber_phone")?.value?.trim() || "";
      const experience = document.getElementById("modal_barber_experience")?.value?.trim() || "";
      const featured_styles = document.getElementById("modal_barber_featured_styles")?.value?.trim() || "";
      const instagram = document.getElementById("modal_barber_instagram")?.value?.trim() || "";
      const facebook = document.getElementById("modal_barber_facebook")?.value?.trim() || "";
      const specialties = document.getElementById("modal_barber_specialties")?.value?.trim() || "";
      const working_days = document.getElementById("modal_barber_days")?.value?.trim() || "";
      const avatar_url = document.getElementById("modal_barber_avatar")?.value?.trim() || "";
      const url = isEdit ? `/api/admin/barbers/${editingRecordId}` : "/api/admin/barbers";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, phone, experience, featured_styles, instagram, facebook, specialties, working_days, avatar_url, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Barbero actualizado correctamente." : "Barbero creado exitosamente.", "success");
        if (typeof loadAdminBarbers === "function") loadAdminBarbers();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar barbero.", "error");
      }
    } else if (currentModalType === "service") {
      const name = document.getElementById("modal_service_name")?.value?.trim() || "";
      const category = document.getElementById("modal_service_category")?.value?.trim() || "Corte";
      const price = parseFloat(document.getElementById("modal_service_price")?.value || "0");
      const prevVal = document.getElementById("modal_service_prev_price")?.value;
      const previous_price = prevVal ? parseFloat(prevVal) : null;
      const duration_min = parseInt(document.getElementById("modal_service_duration")?.value || "30");
      const description = document.getElementById("modal_service_desc")?.value?.trim() || "";
      const url = isEdit ? `/api/admin/services/${editingRecordId}` : "/api/admin/services";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, category, price, previous_price, duration_min, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Servicio actualizado correctamente." : "Servicio creado exitosamente.", "success");
        if (typeof loadAdminServices === "function") loadAdminServices();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar servicio.", "error");
      }
    } else if (currentModalType === "extra") {
      const name = document.getElementById("modal_extra_name")?.value?.trim() || "";
      const price = parseFloat(document.getElementById("modal_extra_price")?.value || "0");
      const duration_min = parseInt(document.getElementById("modal_extra_duration")?.value || "15");
      const icon = document.getElementById("modal_extra_icon")?.value?.trim() || "✂️";
      const description = document.getElementById("modal_extra_desc")?.value?.trim() || "";
      const is_active = document.getElementById("modal_extra_active") ? (document.getElementById("modal_extra_active").value === "true") : true;
      const url = isEdit ? `/api/admin/service-extras/${editingRecordId}` : "/api/admin/service-extras";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, price, duration_min, icon, description, is_active })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Opción extra actualizada correctamente." : "Opción extra creada exitosamente.", "success");
        if (typeof loadAdminExtras === "function") loadAdminExtras();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar opción extra.", "error");
      }
    } else if (currentModalType === "style") {
      const name = document.getElementById("modal_style_name")?.value?.trim() || "";
      const category = document.getElementById("modal_style_category")?.value?.trim() || "Fade";
      const suggested_price = parseFloat(document.getElementById("modal_style_price")?.value || "0");
      const approx_duration = parseInt(document.getElementById("modal_style_duration")?.value || "30");
      const imgEl = document.getElementById("modal_style_img") || document.getElementById("modal_style_image");
      const image_url = imgEl ? imgEl.value.trim() : "";
      const description = document.getElementById("modal_style_desc")?.value?.trim() || "";
      const url = isEdit ? `/api/admin/styles/${editingRecordId}` : "/api/admin/styles";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, category, suggested_price, approx_duration, image_url, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Estilo actualizado correctamente." : "Estilo creado exitosamente.", "success");
        if (typeof loadAdminStyles === "function") loadAdminStyles();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar estilo.", "error");
      }
    } else if (currentModalType === "product") {
      const name = document.getElementById("modal_product_name")?.value?.trim() || "";
      const price = parseFloat(document.getElementById("modal_product_price")?.value || "0");
      const stock = parseInt(document.getElementById("modal_product_stock")?.value || "0");
      const min_stock = parseInt(document.getElementById("modal_product_min_stock")?.value || "0");
      const category_name = document.getElementById("modal_product_category")?.value?.trim() || "";
      const image_url = document.getElementById("modal_product_image")?.value?.trim() || "";
      const description = document.getElementById("modal_product_desc")?.value?.trim() || "";
      const url = isEdit ? `/api/admin/products/${editingRecordId}` : "/api/admin/products";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, price, stock, min_stock, category_name, image_url, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Producto actualizado correctamente." : "Producto creado exitosamente.", "success");
        if (typeof loadAdminProducts === "function") loadAdminProducts();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar producto.", "error");
      }
    } else if (currentModalType === "delivery") {
      const name = document.getElementById("modal_delivery_name")?.value?.trim() || "";
      const cost = parseFloat(document.getElementById("modal_delivery_cost")?.value || "0");
      const min_order_amount = parseFloat(document.getElementById("modal_delivery_min_amount")?.value || "0");
      const url = isEdit ? `/api/admin/delivery-zones/${editingRecordId}` : "/api/admin/delivery-zones";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, cost, min_order_amount, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        showAdminToast(isEdit ? "Zona actualizada correctamente." : "Zona creada exitosamente.", "success");
        if (typeof loadAdminDelivery === "function") loadAdminDelivery();
      } else {
        const err = await res.json().catch(() => ({}));
        showAdminToast(err.detail || "Error al procesar zona.", "error");
      }
    }
  } catch (e) {
    showAdminToast("Error inesperado al guardar.", "error");
    console.error("submitAdminModal error:", e);
  }
}

// Global bootstrap listeners
document.addEventListener("DOMContentLoaded", () => {
  if (adminToken) {
    verifyAdminSession();
  } else {
    showLoginOverlay();
  }

  document.body.addEventListener("click", (e) => {
    const btn = e.target.closest("button, a, select, input[type='submit']");
    if (btn && !btn.hasAttribute("data-no-sound")) {
      UISound.play("click");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      toggleSidebar(false);
      document.querySelectorAll(".modal-overlay, .modal, [id$='Modal'], [id$='Overlay']").forEach(el => {
        if (el.id !== "loginOverlay" && el.style.display && el.style.display !== "none") {
          el.style.display = "none";
        }
      });
    }
  });
});
