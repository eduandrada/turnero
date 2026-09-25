/**
 * Admin Panel Controller - BladeSync Barber Ecosystem 2026
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

let adminToken = localStorage.getItem("bladesync_admin_token") || "";

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
});

function showLoginOverlay() {
  document.getElementById("loginOverlay").style.display = "flex";
  document.getElementById("adminApp").style.display = "none";
}

function hideLoginOverlay() {
  document.getElementById("loginOverlay").style.display = "none";
  document.getElementById("adminApp").style.display = "flex";
}

async function handleAdminLogin() {
  const u = document.getElementById("loginUsername").value.trim();
  const p = document.getElementById("loginPassword").value.trim();

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p })
    });

    const data = await res.json();
    if (res.ok && data.token) {
      adminToken = data.token;
      localStorage.setItem("bladesync_admin_token", adminToken);
      hideLoginOverlay();
      loadAdminDashboard();
    } else {
      alert(data.detail || "Error de inicio de sesión.");
    }
  } catch (e) {
    alert("Error de conexión al servidor.");
  }
}

async function verifyAdminSession() {
  try {
    const res = await fetch("/api/admin/me", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (res.ok) {
      hideLoginOverlay();
      loadAdminDashboard();
      loadSettingsToForm();
    } else {
      adminLogout();
    }
  } catch (e) {
    adminLogout();
  }
}

function adminLogout() {
  if (adminToken) {
    fetch('/api/admin/logout', { method: 'POST', headers: authHeaders() }).catch(() => {});
  }
  adminToken = "";
  localStorage.removeItem("bladesync_admin_token");
  showLoginOverlay();
}

function authHeaders() {
  return {
    "Authorization": `Bearer ${adminToken}`,
    "Content-Type": "application/json"
  };
}

// Navigation
function switchSection(secId) {
  document.querySelectorAll(".admin-section").forEach(s => s.style.display = "none");
  document.querySelectorAll(".admin-nav-item").forEach(i => i.classList.remove("active"));

  const target = document.getElementById(`section-${secId}`);
  if (target) target.style.display = "block";

  const titles = {
    dashboard: "Dashboard",
    appointments: "Turnos & Agenda",
    clients: "Directorio de Clientes",
    barbers: "Barberos de Autor",
    services: "Servicios & Precios",
    styles: "Estilos de Corte",
    schedules: "Horarios de Atención",
    stats: "Historial & Auditoría",
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
    backups: "Copias de Seguridad"
  };

  document.getElementById("currentSectionTitle").textContent = titles[secId] || "Panel";

  if (secId === "dashboard") loadAdminDashboard();
  else if (secId === "appointments") loadAdminAppointments();
  else if (secId === "clients") loadAdminClients();
  else if (secId === "barbers") loadAdminBarbers();
  else if (secId === "services") loadAdminServices();
  else if (secId === "styles") loadAdminStyles();
  else if (secId === "schedules") loadAdminSchedules();
  else if (secId === "stats") loadAdminAuditLogs();
  else if (secId === "products") loadAdminProducts();
  else if (secId === "orders") loadAdminOrders();
  else if (secId === "delivery") loadAdminDelivery();
  else if (secId === "identity" || secId === "appearance" || secId === "content" || secId === "pwa" || secId === "whatsapp") loadSettingsToForm();
  else if (secId === "backups") loadAdminBackups();
}

// 1. DASHBOARD
async function loadAdminDashboard() {
  try {
    const res = await fetch("/api/admin/dashboard/stats", { headers: authHeaders() });
    if (!res.ok) return;
    const stats = await res.json();

    const grid = document.getElementById("dashboardStatsGrid");
    grid.innerHTML = `
      <div class="stat-card">
        <span class="stat-card-label">Turnos de Hoy</span>
        <span class="stat-card-value">${stats.today_appointments}</span>
        <span class="stat-card-sub">${stats.pending_appointments} Pendientes</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-label">Turnos Confirmados</span>
        <span class="stat-card-value" style="color: #10b981;">${stats.confirmed_appointments}</span>
        <span class="stat-card-sub">${stats.completed_appointments} Completados</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-label">Clientes Totales</span>
        <span class="stat-card-value">${stats.total_clients}</span>
        <span class="stat-card-sub">${stats.total_barbers} Barberos</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-label">Ventas Shop</span>
        <span class="stat-card-value" style="color: #d4ff00;">$${stats.total_orders_revenue.toLocaleString("es-AR")}</span>
        <span class="stat-card-sub">${stats.pending_orders} Pedidos Pendientes</span>
      </div>
    `;

    // Recent appts
    const apptsBody = document.getElementById("dashRecentAppts");
    apptsBody.innerHTML = "";
    stats.recent_appointments.forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(a.client_name)}</strong></td>
        <td>${escapeHtml(a.service)}</td>
        <td>${escapeHtml(a.barber_name)}</td>
        <td>${a.time.replace("T", " ").substring(0, 16)} hs</td>
        <td><span class="badge badge-${a.status.toLowerCase()}">${a.status}</span></td>
      `;
      apptsBody.appendChild(tr);
    });

    // Recent orders
    const ordersBody = document.getElementById("dashRecentOrders");
    ordersBody.innerHTML = "";
    stats.recent_orders.forEach(o => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(o.order_number)}</strong></td>
        <td>${escapeHtml(o.client_name)}</td>
        <td style="color: #d4ff00;">$${o.total.toLocaleString("es-AR")}</td>
        <td><span class="badge badge-pending">${o.status}</span></td>
      `;
      ordersBody.appendChild(tr);
    });

  } catch (e) {
    console.error(e);
  }
}

// 2. TURNOS
async function loadAdminAppointments() {
  const date = document.getElementById("filterApptDate").value;
  const status = document.getElementById("filterApptStatus").value;

  let url = "/api/admin/appointments?";
  if (date) url += `date=${date}&`;
  if (status) url += `status=${status}&`;

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const appts = await res.json();

    const tbody = document.getElementById("appointmentsTableBody");
    tbody.innerHTML = "";

    appts.forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>#${a.id}</td>
        <td><strong>${escapeHtml(a.client_name)}</strong></td>
        <td><a href="https://wa.me/${a.client_phone.replace(/\D/g, '')}" target="_blank" style="color: #00f2fe;">${escapeHtml(a.client_phone)}</a></td>
        <td>${escapeHtml(a.barber_name || '-')}</td>
        <td>${escapeHtml(a.service || '-')}</td>
        <td>${a.appointment_time.replace("T", " ").substring(0, 16)} hs</td>
        <td><span class="badge badge-${a.status.toLowerCase()}">${a.status}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="changeApptStatus(${a.id}, 'CONFIRMADO')">Confirmar</button>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="changeApptStatus(${a.id}, 'COMPLETADO')">Completar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="changeApptStatus(${a.id}, 'CANCELADO')">Cancelar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error(e);
  }
}

async function changeApptStatus(id, newStatus) {
  try {
    const res = await fetch(`/api/admin/appointments/${id}`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      loadAdminAppointments();
    }
  } catch (e) {
    alert("Error al actualizar turno.");
  }
}

// 3. CLIENTES
async function loadAdminClients() {
  try {
    const res = await fetch("/api/admin/clients", { headers: authHeaders() });
    if (!res.ok) return;
    const clients = await res.json();
    const tbody = document.getElementById("clientsTableBody");
    tbody.innerHTML = "";
    clients.forEach(c => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>#${c.id}</td>
        <td><strong>${escapeHtml(c.name)}</strong></td>
        <td>${escapeHtml(c.phone)}</td>
        <td>${escapeHtml(c.email || '-')}</td>
        <td>${c.created_at ? c.created_at.substring(0, 10) : '-'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

// Global cache for editing
let adminBarbersList = [];
let adminServicesList = [];
let adminStylesList = [];
let adminProductsList = [];
let adminDeliveryList = [];
let adminOrdersList = [];

// 4. BARBEROS
async function loadAdminBarbers() {
  try {
    const res = await fetch("/api/admin/barbers", { headers: authHeaders() });
    if (!res.ok) return;
    adminBarbersList = await res.json();
    const tbody = document.getElementById("barbersTableBody");
    tbody.innerHTML = "";
    adminBarbersList.forEach(b => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><img src="${b.avatar_url || ''}" style="width: 36px; height: 36px; object-fit: cover; border-radius: 50%;"></td>
        <td><strong>${escapeHtml(b.name)}</strong></td>
        <td>${escapeHtml(b.specialties || '')}</td>
        <td>${escapeHtml(b.working_days || '')}</td>
        <td><span class="badge ${b.is_active ? 'badge-confirmed' : 'badge-canceled'}">${b.is_active ? 'ACTIVO' : 'INACTIVO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editBarberModal(${b.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteBarber(${b.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function deleteBarber(id) {
  if (!confirm("¿Eliminar este barbero?")) return;
  await fetch(`/api/admin/barbers/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminBarbers();
}

// 5. SERVICIOS & PRECIOS
async function loadAdminServices() {
  try {
    const res = await fetch("/api/admin/services", { headers: authHeaders() });
    if (!res.ok) return;
    adminServicesList = await res.json();
    const tbody = document.getElementById("servicesTableBody");
    tbody.innerHTML = "";
    adminServicesList.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.category || 'General')}</td>
        <td>${s.duration_min} min</td>
        <td style="color: #d4ff00; font-weight: bold;">$${s.price.toLocaleString("es-AR")}</td>
        <td style="color: #9ca3af; text-decoration: line-through;">${s.previous_price ? '$' + s.previous_price.toLocaleString("es-AR") : '-'}</td>
        <td><span class="badge ${s.is_active ? 'badge-confirmed' : 'badge-canceled'}">${s.is_active ? 'ACTIVO' : 'INACTIVO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editServiceModal(${s.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteService(${s.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function deleteService(id) {
  if (!confirm("¿Eliminar este servicio?")) return;
  await fetch(`/api/admin/services/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminServices();
}

// 6. ESTILOS DE CORTE
async function loadAdminStyles() {
  try {
    const res = await fetch("/api/admin/styles", { headers: authHeaders() });
    if (!res.ok) return;
    adminStylesList = await res.json();
    const tbody = document.getElementById("stylesTableBody");
    tbody.innerHTML = "";
    adminStylesList.forEach(st => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(st.name)}</strong></td>
        <td>${escapeHtml(st.category || 'Fade')}</td>
        <td>${st.approx_duration} min</td>
        <td>$${st.suggested_price.toLocaleString("es-AR")}</td>
        <td><span class="badge ${st.is_active ? 'badge-confirmed' : 'badge-canceled'}">${st.is_active ? 'ACTIVO' : 'INACTIVO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editStyleModal(${st.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteStyle(${st.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function deleteStyle(id) {
  if (!confirm("¿Eliminar este estilo?")) return;
  await fetch(`/api/admin/styles/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminStyles();
}

// 7. HORARIOS DE ATENCIÓN
async function loadAdminSchedules() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (!res.ok) return;
    const sets = await res.json();
    let bh = {};
    try { bh = JSON.parse(sets.business_hours || "{}"); } catch (e) {}

    const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
    const container = document.getElementById("businessHoursContainer");
    container.innerHTML = "";

    days.forEach(day => {
      const cfg = bh[day] || { active: True, open: "09:00", close: "20:00" };
      const card = document.createElement("div");
      card.className = "admin-card";
      card.style.margin = "0";
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <strong style="font-family: 'Space Grotesk', monospace;">${day}</strong>
          <label style="font-size: 0.75rem;"><input type="checkbox" id="bh_active_${day}" ${cfg.active ? 'checked' : ''}> Abierto</label>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <div>
            <label style="font-size: 0.7rem;">Apertura</label>
            <input type="time" id="bh_open_${day}" class="form-control" value="${cfg.open || '09:00'}">
          </div>
          <div>
            <label style="font-size: 0.7rem;">Cierre</label>
            <input type="time" id="bh_close_${day}" class="form-control" value="${cfg.close || '20:00'}">
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (e) { console.error(e); }
}

async function saveBusinessHours() {
  const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  const bh = {};
  days.forEach(day => {
    bh[day] = {
      active: document.getElementById(`bh_active_${day}`).checked,
      open: document.getElementById(`bh_open_${day}`).value,
      close: document.getElementById(`bh_close_${day}`).value
    };
  });

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ settings: { business_hours: JSON.stringify(bh) } })
    });
    if (res.ok) alert("Horarios guardados correctamente.");
  } catch (e) { alert("Error al guardar."); }
}

// 8. PRODUCTOS & STOCK
async function loadAdminProducts() {
  try {
    const res = await fetch("/api/admin/products", { headers: authHeaders() });
    if (!res.ok) return;
    adminProductsList = await res.json();
    const tbody = document.getElementById("productsTableBody");
    tbody.innerHTML = "";
    adminProductsList.forEach(p => {
      const tr = document.createElement("tr");
      const isLow = p.stock <= p.min_stock;
      tr.innerHTML = `
        <td><img src="${p.image_url || ''}" style="width: 36px; height: 36px; object-fit: cover; border-radius: 8px;"></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${escapeHtml(p.category_name || '-')}</td>
        <td style="color: #d4ff00; font-weight: bold;">$${p.price.toLocaleString("es-AR")}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 6px;">
            <button class="btn-admin btn-admin-sm btn-admin-secondary" style="padding: 2px 8px; font-weight: bold;" onclick="quickAdjustStock(${p.id}, -1)">-</button>
            <strong style="color: ${isLow ? '#ef4444' : '#10b981'}; font-size: 0.9rem;">${p.stock} un.</strong>
            <button class="btn-admin btn-admin-sm btn-admin-secondary" style="padding: 2px 8px; font-weight: bold;" onclick="quickAdjustStock(${p.id}, 1)">+</button>
          </div>
          ${isLow ? '<span style="color: #ef4444; font-size: 0.65rem; font-weight: bold; display: block; margin-top: 2px;">⚠️ Stock Crítico</span>' : ''}
        </td>
        <td>${p.min_stock} un.</td>
        <td><span class="badge ${p.is_active ? 'badge-confirmed' : 'badge-canceled'}">${p.is_active ? 'DISPONIBLE' : 'OCULTO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editProductModal(${p.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteProduct(${p.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function quickAdjustStock(productId, delta) {
  const prod = adminProductsList.find(p => p.id === productId);
  if (!prod) return;
  const newStock = Math.max(0, prod.stock + delta);
  try {
    const res = await fetch(`/api/admin/products/${productId}`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ stock: newStock })
    });
    if (res.ok) loadAdminProducts();
  } catch (e) { alert("Error al actualizar stock."); }
}

async function deleteProduct(id) {
  if (!confirm("¿Eliminar este producto?")) return;
  await fetch(`/api/admin/products/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminProducts();
}

// 9. PEDIDOS SHOP & COORDINACIÓN DE DELIVERY
async function loadAdminOrders() {
  try {
    const res = await fetch("/api/admin/orders", { headers: authHeaders() });
    if (!res.ok) return;
    adminOrdersList = await res.json();
    const tbody = document.getElementById("ordersTableBody");
    tbody.innerHTML = "";
    adminOrdersList.forEach(o => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(o.order_number)}</strong></td>
        <td>${escapeHtml(o.client_name)}</td>
        <td><a href="https://wa.me/${o.client_phone.replace(/\D/g, '')}" target="_blank" style="color: #00f2fe;">${escapeHtml(o.client_phone)}</a></td>
        <td>${o.delivery_type === 'delivery' ? '🚚 Delivery' : '💈 Retiro'}</td>
        <td style="color: #d4ff00; font-weight: bold;">$${o.total.toLocaleString("es-AR")}</td>
        <td><span class="badge badge-pending">${o.status}</span></td>
        <td style="display: flex; gap: 6px; align-items: center;">
          <select class="form-control" style="padding: 4px; font-size: 0.75rem;" onchange="updateOrderStatus(${o.id}, this.value)">
            <option value="NUEVO" ${o.status==='NUEVO'?'selected':''}>NUEVO</option>
            <option value="CONFIRMADO" ${o.status==='CONFIRMADO'?'selected':''}>CONFIRMADO</option>
            <option value="PREPARANDO" ${o.status==='PREPARANDO'?'selected':''}>PREPARANDO</option>
            <option value="LISTO" ${o.status==='LISTO'?'selected':''}>LISTO</option>
            <option value="EN_CAMINO" ${o.status==='EN_CAMINO'?'selected':''}>EN CAMINO</option>
            <option value="ENTREGADO" ${o.status==='ENTREGADO'?'selected':''}>ENTREGADO</option>
            <option value="CANCELADO" ${o.status==='CANCELADO'?'selected':''}>CANCELADO</option>
          </select>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openOrderDetailsModal(${o.id})">🔍 Coordinar / Detalle</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function updateOrderStatus(id, newStatus) {
  try {
    await fetch(`/api/admin/orders/${id}/status`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ status: newStatus })
    });
    loadAdminOrders();
    loadAdminProducts(); // Actualiza inventario si fue cancelado
  } catch (e) { alert("Error al actualizar pedido."); }
}

// 10. DELIVERY
async function loadAdminDelivery() {
  try {
    const res = await fetch("/api/admin/delivery-zones", { headers: authHeaders() });
    if (!res.ok) return;
    adminDeliveryList = await res.json();
    const tbody = document.getElementById("deliveryTableBody");
    tbody.innerHTML = "";
    adminDeliveryList.forEach(z => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(z.name)}</strong></td>
        <td>$${z.cost.toLocaleString("es-AR")}</td>
        <td>$${z.min_order_amount.toLocaleString("es-AR")}</td>
        <td><span class="badge ${z.is_active ? 'badge-confirmed' : 'badge-canceled'}">${z.is_active ? 'ACTIVA' : 'INACTIVA'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editDeliveryModal(${z.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteDeliveryZone(${z.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function deleteDeliveryZone(id) {
  if (!confirm("¿Eliminar esta zona de delivery?")) return;
  await fetch(`/api/admin/delivery-zones/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminDelivery();
}

// 11. AUDITORÍA
async function loadAdminAuditLogs() {
  try {
    const res = await fetch("/api/admin/audit-logs", { headers: authHeaders() });
    if (!res.ok) return;
    const logs = await res.json();
    const tbody = document.getElementById("auditLogsBody");
    tbody.innerHTML = "";
    logs.forEach(l => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${l.timestamp ? l.timestamp.replace("T", " ").substring(0, 19) : '-'}</td>
        <td><strong>${escapeHtml(l.user_name)}</strong></td>
        <td>${escapeHtml(l.module)}</td>
        <td><span class="badge badge-confirmed">${escapeHtml(l.action)}</span></td>
        <td style="font-size: 0.75rem; color: #9ca3af;">${escapeHtml(l.new_value || l.old_value || '-')}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

// 12. BACKUPS
async function loadAdminBackups() {
  try {
    const res = await fetch("/api/admin/backups", { headers: authHeaders() });
    if (!res.ok) return;
    const backups = await res.json();
    const tbody = document.getElementById("backupsTableBody");
    tbody.innerHTML = "";
    backups.forEach(b => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(b.filename)}</strong></td>
        <td>${(b.size_bytes / 1024).toFixed(1)} KB</td>
        <td>${b.created_at.replace("T", " ").substring(0, 19)}</td>
        <td>
          <a class="btn-admin btn-admin-sm btn-admin-secondary" href="/api/admin/backups/download/${b.filename}">Descargar</a>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="restoreBackup('${b.filename}')">Restaurar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error(e); }
}

async function triggerCreateBackup() {
  try {
    const res = await fetch("/api/admin/backups/create", { method: "POST", headers: authHeaders() });
    if (res.ok) {
      alert("Backup creado con éxito.");
      loadAdminBackups();
    }
  } catch (e) { alert("Error al crear backup."); }
}

async function restoreBackup(filename) {
  if (!confirm(`¿Restaurar la base de datos desde '${filename}'? Se realizará una copia de seguridad automática previa.`)) return;
  try {
    const res = await fetch(`/api/admin/backups/restore?filename=${encodeURIComponent(filename)}`, { method: "POST", headers: authHeaders() });
    if (res.ok) {
      alert("Base de datos restaurada exitosamente.");
      loadAdminDashboard();
    }
  } catch (e) { alert("Error al restaurar."); }
}

// 13. SETTINGS & IDENTITY
function updateAdminBrandUI(sets) {
  if (!sets) return;
  const bName = sets.barber_name || sets.app_name || "DON CARLOS";
  const brandEl = document.getElementById("sidebarBrandName");
  if (brandEl) {
    brandEl.innerHTML = `${escapeHtml(bName.toUpperCase())}<span>_</span>`;
  }
  document.title = `${bName} // Panel Administrativo`;
}

async function loadSettingsToForm() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (!res.ok) return;
    const sets = await res.json();
    for (const [k, v] of Object.entries(sets)) {
      const el = document.getElementById(`setting_${k}`);
      if (el) el.value = v;
    }
    updateAdminBrandUI(sets);
  } catch (e) { console.error(e); }
}

async function saveSettingsSection(secName) {
  const fields = document.querySelectorAll("[id^='setting_']");
  const updates = {};
  fields.forEach(el => {
    const key = el.id.replace("setting_", "");
    updates[key] = el.value;
  });

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ settings: updates })
    });
    if (res.ok) {
      const updatedSets = await res.json();
      updateAdminBrandUI(updatedSets);
      alert("Configuración guardada exitosamente.");
    }
  } catch (e) { alert("Error al guardar configuración."); }
}

async function updateAdminPassword() {
  const cur = document.getElementById("changeCurrPass").value;
  const nw = document.getElementById("changeNewPass").value;

  try {
    const res = await fetch("/api/admin/change-password", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ current_password: cur, new_password: nw })
    });
    const data = await res.json();
    if (res.ok) {
      alert("Contraseña actualizada con éxito.");
      document.getElementById("changeCurrPass").value = "";
      document.getElementById("changeNewPass").value = "";
    } else {
      alert(data.detail || "Error al cambiar contraseña.");
    }
  } catch (e) { alert("Error al actualizar contraseña."); }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// --- MODAL CONTROLLER FOR ADMIN ---
let currentModalType = "";
let editingRecordId = null;

function closeAdminModal() {
  document.getElementById("adminModal").style.display = "none";
  editingRecordId = null;
}

function openBarberModal() {
  currentModalType = "barber";
  editingRecordId = null;
  document.getElementById("modalAdminTitle").textContent = "+ AGREGAR BARBERO";
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE COMPLETO</label>
      <input type="text" id="modal_barber_name" class="form-control" placeholder="Ej: Mateo Rossi" required>
    </div>
    <div class="form-group">
      <label>ESPECIALIDADES</label>
      <input type="text" id="modal_barber_specialties" class="form-control" placeholder="Ej: Fade, Barba, Profilado">
    </div>
    <div class="form-group">
      <label>DÍAS DE TRABAJO</label>
      <input type="text" id="modal_barber_days" class="form-control" placeholder="Ej: Lunes a Sábado" value="Lunes a Sábado">
    </div>
    <div class="form-group">
      <label>URL FOTO / AVATAR</label>
      <input type="text" id="modal_barber_avatar" class="form-control" placeholder="/static/barbers/barber1.jpg">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function editBarberModal(id) {
  const b = adminBarbersList.find(item => item.id === id);
  if (!b) return;
  currentModalType = "barber";
  editingRecordId = id;
  document.getElementById("modalAdminTitle").textContent = `✏️ EDITAR BARBERO #${id}`;
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE COMPLETO</label>
      <input type="text" id="modal_barber_name" class="form-control" value="${escapeHtml(b.name)}" required>
    </div>
    <div class="form-group">
      <label>ESPECIALIDADES</label>
      <input type="text" id="modal_barber_specialties" class="form-control" value="${escapeHtml(b.specialties || '')}">
    </div>
    <div class="form-group">
      <label>DÍAS DE TRABAJO</label>
      <input type="text" id="modal_barber_days" class="form-control" value="${escapeHtml(b.working_days || '')}">
    </div>
    <div class="form-group">
      <label>URL FOTO / AVATAR</label>
      <input type="text" id="modal_barber_avatar" class="form-control" value="${escapeHtml(b.avatar_url || '')}">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function openServiceModal() {
  currentModalType = "service";
  editingRecordId = null;
  document.getElementById("modalAdminTitle").textContent = "+ AGREGAR SERVICIO";
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL SERVICIO</label>
      <input type="text" id="modal_service_name" class="form-control" placeholder="Ej: Corte Ejecutivo" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA</label>
      <input type="text" id="modal_service_category" class="form-control" placeholder="Ej: Corte, Barba, Combo" value="Corte">
    </div>
    <div class="form-group">
      <label>PRECIO ($)</label>
      <input type="number" step="0.01" id="modal_service_price" class="form-control" placeholder="8000" required>
    </div>
    <div class="form-group">
      <label>PRECIO ANTERIOR ($ - Opcional tachado)</label>
      <input type="number" step="0.01" id="modal_service_prev_price" class="form-control" placeholder="10000">
    </div>
    <div class="form-group">
      <label>DURACIÓN ESTIMADA (MINUTOS)</label>
      <input type="number" id="modal_service_duration" class="form-control" value="30" required>
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN</label>
      <input type="text" id="modal_service_desc" class="form-control" placeholder="Corte de cabello a tijera/máquina con acabado premium">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function editServiceModal(id) {
  const s = adminServicesList.find(item => item.id === id);
  if (!s) return;
  currentModalType = "service";
  editingRecordId = id;
  document.getElementById("modalAdminTitle").textContent = `✏️ EDITAR SERVICIO #${id}`;
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL SERVICIO</label>
      <input type="text" id="modal_service_name" class="form-control" value="${escapeHtml(s.name)}" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA</label>
      <input type="text" id="modal_service_category" class="form-control" value="${escapeHtml(s.category || 'Corte')}">
    </div>
    <div class="form-group">
      <label>PRECIO ($)</label>
      <input type="number" step="0.01" id="modal_service_price" class="form-control" value="${s.price}" required>
    </div>
    <div class="form-group">
      <label>PRECIO ANTERIOR ($ - Opcional tachado)</label>
      <input type="number" step="0.01" id="modal_service_prev_price" class="form-control" value="${s.previous_price || ''}">
    </div>
    <div class="form-group">
      <label>DURACIÓN ESTIMADA (MINUTOS)</label>
      <input type="number" id="modal_service_duration" class="form-control" value="${s.duration_min}" required>
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN</label>
      <input type="text" id="modal_service_desc" class="form-control" value="${escapeHtml(s.description || '')}">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function openStyleModal() {
  currentModalType = "style";
  editingRecordId = null;
  document.getElementById("modalAdminTitle").textContent = "+ AGREGAR ESTILO DE CORTE";
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL ESTILO</label>
      <input type="text" id="modal_style_name" class="form-control" placeholder="Ej: Mid Fade Textured" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA / TIPO DE ROSTRO</label>
      <input type="text" id="modal_style_category" class="form-control" placeholder="Ej: Fade, Ovalado, Cuadrado" value="Fade">
    </div>
    <div class="form-group">
      <label>PRECIO SUGERIDO ($)</label>
      <input type="number" step="0.01" id="modal_style_price" class="form-control" placeholder="8500" required>
    </div>
    <div class="form-group">
      <label>DURACIÓN APROX (MINUTOS)</label>
      <input type="number" id="modal_style_duration" class="form-control" value="40" required>
    </div>
    <div class="form-group">
      <label>URL IMAGEN ILUSTRATIVA</label>
      <input type="text" id="modal_style_image" class="form-control" placeholder="/static/styles/fade.jpg">
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN / RECOMENDACIÓN</label>
      <input type="text" id="modal_style_desc" class="form-control" placeholder="Ideal para rostros ovalados y angulares">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function editStyleModal(id) {
  const st = adminStylesList.find(item => item.id === id);
  if (!st) return;
  currentModalType = "style";
  editingRecordId = id;
  document.getElementById("modalAdminTitle").textContent = `✏️ EDITAR ESTILO #${id}`;
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL ESTILO</label>
      <input type="text" id="modal_style_name" class="form-control" value="${escapeHtml(st.name)}" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA / TIPO DE ROSTRO</label>
      <input type="text" id="modal_style_category" class="form-control" value="${escapeHtml(st.category || 'Fade')}">
    </div>
    <div class="form-group">
      <label>PRECIO SUGERIDO ($)</label>
      <input type="number" step="0.01" id="modal_style_price" class="form-control" value="${st.suggested_price}" required>
    </div>
    <div class="form-group">
      <label>DURACIÓN APROX (MINUTOS)</label>
      <input type="number" id="modal_style_duration" class="form-control" value="${st.approx_duration}" required>
    </div>
    <div class="form-group">
      <label>URL IMAGEN ILUSTRATIVA</label>
      <input type="text" id="modal_style_image" class="form-control" value="${escapeHtml(st.image_url || '')}">
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN / RECOMENDACIÓN</label>
      <input type="text" id="modal_style_desc" class="form-control" value="${escapeHtml(st.description || '')}">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function openProductModal() {
  currentModalType = "product";
  editingRecordId = null;
  document.getElementById("modalAdminTitle").textContent = "+ AGREGAR PRODUCTO AL INVENTARIO";
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL PRODUCTO</label>
      <input type="text" id="modal_product_name" class="form-control" placeholder="Ej: Cera Modeladora Matte" required>
    </div>
    <div class="form-group">
      <label>PRECIO DE VENTA ($)</label>
      <input type="number" step="0.01" id="modal_product_price" class="form-control" placeholder="12500" required>
    </div>
    <div class="form-group">
      <label>STOCK ACTUAL</label>
      <input type="number" id="modal_product_stock" class="form-control" value="15" required>
    </div>
    <div class="form-group">
      <label>STOCK MÍNIMO (ALERTA)</label>
      <input type="number" id="modal_product_min_stock" class="form-control" value="3" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA</label>
      <input type="text" id="modal_product_category" class="form-control" placeholder="Ej: Ceras & Pomadas, Cuidado Barba" value="Ceras & Pomadas">
    </div>
    <div class="form-group">
      <label>URL IMAGEN PRODUCTO</label>
      <input type="text" id="modal_product_image" class="form-control" placeholder="/static/products/cera.jpg">
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN</label>
      <input type="text" id="modal_product_desc" class="form-control" placeholder="Fijación fuerte efecto mate 100g">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function editProductModal(id) {
  const p = adminProductsList.find(item => item.id === id);
  if (!p) return;
  currentModalType = "product";
  editingRecordId = id;
  document.getElementById("modalAdminTitle").textContent = `✏️ EDITAR PRODUCTO #${id}`;
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DEL PRODUCTO</label>
      <input type="text" id="modal_product_name" class="form-control" value="${escapeHtml(p.name)}" required>
    </div>
    <div class="form-group">
      <label>PRECIO DE VENTA ($)</label>
      <input type="number" step="0.01" id="modal_product_price" class="form-control" value="${p.price}" required>
    </div>
    <div class="form-group">
      <label>STOCK ACTUAL</label>
      <input type="number" id="modal_product_stock" class="form-control" value="${p.stock}" required>
    </div>
    <div class="form-group">
      <label>STOCK MÍNIMO (ALERTA CRÍTICA)</label>
      <input type="number" id="modal_product_min_stock" class="form-control" value="${p.min_stock}" required>
    </div>
    <div class="form-group">
      <label>CATEGORÍA</label>
      <input type="text" id="modal_product_category" class="form-control" value="${escapeHtml(p.category_name || 'Ceras & Pomadas')}">
    </div>
    <div class="form-group">
      <label>URL IMAGEN PRODUCTO</label>
      <input type="text" id="modal_product_image" class="form-control" value="${escapeHtml(p.image_url || '')}">
    </div>
    <div class="form-group">
      <label>DESCRIPCIÓN</label>
      <input type="text" id="modal_product_desc" class="form-control" value="${escapeHtml(p.description || '')}">
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function openDeliveryModal() {
  currentModalType = "delivery";
  editingRecordId = null;
  document.getElementById("modalAdminTitle").textContent = "+ AGREGAR ZONA DE DELIVERY";
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DE LA ZONA</label>
      <input type="text" id="modal_delivery_name" class="form-control" placeholder="Ej: Zona Norte / San Fernando" required>
    </div>
    <div class="form-group">
      <label>COSTO DE ENVÍO ($)</label>
      <input type="number" step="0.01" id="modal_delivery_cost" class="form-control" placeholder="2000" required>
    </div>
    <div class="form-group">
      <label>MONTO MÍNIMO DE COMPRA ($)</label>
      <input type="number" step="0.01" id="modal_delivery_min_amount" class="form-control" value="0" required>
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

function editDeliveryModal(id) {
  const z = adminDeliveryList.find(item => item.id === id);
  if (!z) return;
  currentModalType = "delivery";
  editingRecordId = id;
  document.getElementById("modalAdminTitle").textContent = `✏️ EDITAR ZONA DE DELIVERY #${id}`;
  document.getElementById("modalAdminBody").innerHTML = `
    <div class="form-group">
      <label>NOMBRE DE LA ZONA</label>
      <input type="text" id="modal_delivery_name" class="form-control" value="${escapeHtml(z.name)}" required>
    </div>
    <div class="form-group">
      <label>COSTO DE ENVÍO ($)</label>
      <input type="number" step="0.01" id="modal_delivery_cost" class="form-control" value="${z.cost}" required>
    </div>
    <div class="form-group">
      <label>MONTO MÍNIMO DE COMPRA ($)</label>
      <input type="number" step="0.01" id="modal_delivery_min_amount" class="form-control" value="${z.min_order_amount}" required>
    </div>
  `;
  document.getElementById("adminModal").style.display = "flex";
}

async function submitAdminModal() {
  try {
    const isEdit = editingRecordId !== null;
    const method = isEdit ? "PUT" : "POST";

    if (currentModalType === "barber") {
      const name = document.getElementById("modal_barber_name").value.trim();
      const specialties = document.getElementById("modal_barber_specialties").value.trim();
      const working_days = document.getElementById("modal_barber_days").value.trim();
      const avatar_url = document.getElementById("modal_barber_avatar").value.trim();
      const url = isEdit ? `/api/admin/barbers/${editingRecordId}` : "/api/admin/barbers";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, specialties, working_days, avatar_url, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        loadAdminBarbers();
      } else {
        const err = await res.json();
        alert(err.detail || "Error al procesar barbero.");
      }
    } else if (currentModalType === "service") {
      const name = document.getElementById("modal_service_name").value.trim();
      const category = document.getElementById("modal_service_category").value.trim();
      const price = parseFloat(document.getElementById("modal_service_price").value || "0");
      const prevVal = document.getElementById("modal_service_prev_price").value;
      const previous_price = prevVal ? parseFloat(prevVal) : null;
      const duration_min = parseInt(document.getElementById("modal_service_duration").value || "30");
      const description = document.getElementById("modal_service_desc").value.trim();
      const url = isEdit ? `/api/admin/services/${editingRecordId}` : "/api/admin/services";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, category, price, previous_price, duration_min, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        loadAdminServices();
      } else {
        const err = await res.json();
        alert(err.detail || "Error al procesar servicio.");
      }
    } else if (currentModalType === "style") {
      const name = document.getElementById("modal_style_name").value.trim();
      const category = document.getElementById("modal_style_category").value.trim();
      const suggested_price = parseFloat(document.getElementById("modal_style_price").value || "0");
      const approx_duration = parseInt(document.getElementById("modal_style_duration").value || "30");
      const image_url = document.getElementById("modal_style_image").value.trim();
      const description = document.getElementById("modal_style_desc").value.trim();
      const url = isEdit ? `/api/admin/styles/${editingRecordId}` : "/api/admin/styles";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, category, suggested_price, approx_duration, image_url, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        loadAdminStyles();
      } else {
        const err = await res.json();
        alert(err.detail || "Error al procesar estilo.");
      }
    } else if (currentModalType === "product") {
      const name = document.getElementById("modal_product_name").value.trim();
      const price = parseFloat(document.getElementById("modal_product_price").value || "0");
      const stock = parseInt(document.getElementById("modal_product_stock").value || "0");
      const min_stock = parseInt(document.getElementById("modal_product_min_stock").value || "0");
      const category_name = document.getElementById("modal_product_category").value.trim();
      const image_url = document.getElementById("modal_product_image").value.trim();
      const description = document.getElementById("modal_product_desc").value.trim();
      const url = isEdit ? `/api/admin/products/${editingRecordId}` : "/api/admin/products";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, price, stock, min_stock, category_name, image_url, description, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        loadAdminProducts();
      } else {
        const err = await res.json();
        alert(err.detail || "Error al procesar producto.");
      }
    } else if (currentModalType === "delivery") {
      const name = document.getElementById("modal_delivery_name").value.trim();
      const cost = parseFloat(document.getElementById("modal_delivery_cost").value || "0");
      const min_order_amount = parseFloat(document.getElementById("modal_delivery_min_amount").value || "0");
      const url = isEdit ? `/api/admin/delivery-zones/${editingRecordId}` : "/api/admin/delivery-zones";

      const res = await fetch(url, {
        method: method,
        headers: authHeaders(),
        body: JSON.stringify({ name, cost, min_order_amount, is_active: true })
      });
      if (res.ok) {
        closeAdminModal();
        loadAdminDelivery();
      } else {
        const err = await res.json();
        alert(err.detail || "Error al procesar zona.");
      }
    }
  } catch (e) {
    alert("Error de conexión al procesar la solicitud.");
  }
}

// --- MODAL DE DETALLE Y COORDINACIÓN INTELIGENTE DE PEDIDOS ---
function closeOrderDetailModal() {
  document.getElementById("orderDetailModal").style.display = "none";
}

function openOrderDetailsModal(orderId) {
  const o = adminOrdersList.find(item => item.id === orderId);
  if (!o) return;

  document.getElementById("orderDetailTitle").textContent = `Pedido #${o.order_number}`;

  let itemsHtml = "";
  if (o.items && o.items.length > 0) {
    itemsHtml = `
      <table class="admin-table" style="margin-top: 10px; font-size: 0.8rem;">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cant.</th>
            <th>Precio U.</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          ${o.items.map(it => `
            <tr>
              <td><strong>${escapeHtml(it.product_name)}</strong></td>
              <td>${it.quantity} un.</td>
              <td>$${it.unit_price.toLocaleString("es-AR")}</td>
              <td style="color: #d4ff00; font-weight: bold;">$${it.subtotal.toLocaleString("es-AR")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } else {
    itemsHtml = `<p style="font-size: 0.8rem; color: #9ca3af;">Sin ítems detallados registrados.</p>`;
  }

  const cleanPhone = o.client_phone.replace(/\D/g, "");
  const bName = "Barbería";
  const waMsg = encodeURIComponent(
    `¡Hola ${o.client_name}! Te contactamos de la Barbería por tu pedido #${o.order_number}.\n\n` +
    `📋 Resumen: Total $${o.total.toLocaleString("es-AR")} (${o.delivery_type === 'delivery' ? 'Envío a domicilio: ' + (o.address || 'Dirección de envío') : 'Retiro en barbería'}).\n\n` +
    `¿Coordinamos el envío / entrega de tu compra?`
  );

  document.getElementById("orderDetailContent").innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 16px;">
      <div style="background: #1a1a22; padding: 12px; border-radius: 12px; border: 1px solid #23232c;">
        <span style="font-size: 0.7rem; color: #d4ff00; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">DATOS DEL CLIENTE</span>
        <p style="color: #fff; font-weight: bold; margin: 4px 0 2px 0;">${escapeHtml(o.client_name)}</p>
        <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">📱 <a href="https://wa.me/${cleanPhone}" target="_blank" style="color: #00f2fe;">${escapeHtml(o.client_phone)}</a></p>
        ${o.client_email ? `<p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">✉️ ${escapeHtml(o.client_email)}</p>` : ''}
      </div>

      <div style="background: #1a1a22; padding: 12px; border-radius: 12px; border: 1px solid #23232c;">
        <span style="font-size: 0.7rem; color: #00f2fe; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">LOGÍSTICA DE ENTREGA</span>
        <p style="color: #fff; font-weight: bold; margin: 4px 0 2px 0;">${o.delivery_type === 'delivery' ? '🚚 Delivery a Domicilio' : '💈 Retiro en Barbería'}</p>
        ${o.address ? `<p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">📍 ${escapeHtml(o.address)} ${o.neighborhood ? '('+escapeHtml(o.neighborhood)+')' : ''}</p>` : ''}
        <p style="font-size: 0.8rem; color: #d4ff00; font-weight: bold; margin-top: 4px;">Costo Delivery: $${o.delivery_cost.toLocaleString("es-AR")}</p>
      </div>
    </div>

    <div style="margin-bottom: 16px;">
      <span style="font-size: 0.75rem; color: #9ca3af; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">PRODUCTOS COMPRADOS</span>
      ${itemsHtml}
    </div>

    <div style="background: #1a1a22; padding: 16px; border-radius: 12px; border: 1px solid #23232c; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
      <div>
        <span style="font-size: 0.75rem; color: #9ca3af;">TOTAL DE LA COMPRA</span>
        <h3 style="font-family: 'Space Grotesk', monospace; color: #d4ff00; margin: 0; font-size: 1.5rem;">$${o.total.toLocaleString("es-AR")}</h3>
      </div>
      <div>
        <a href="https://wa.me/${cleanPhone}?text=${waMsg}" target="_blank" class="btn-admin" style="background: #25D366; color: #000; font-weight: bold; padding: 10px 16px; font-size: 0.85rem;">
          💬 Coordinar Despacho por WhatsApp →
        </a>
      </div>
    </div>
  `;

  document.getElementById("orderDetailModal").style.display = "flex";
}


