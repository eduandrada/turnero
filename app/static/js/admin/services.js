/**
 * Admin Panel - Services, Styles & Delivery Zones Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles service catalog, styles, pricing, duration, and delivery zones.
 */

let adminServicesList = [];
let adminExtrasList = [];
let adminStylesList = [];
let adminDeliveryList = [];

// 1. SERVICIOS & PRECIOS
async function loadAdminServices() {
  try {
    loadAdminExtras();
    const res = await fetch("/api/admin/services", { headers: authHeaders() });
    if (!res.ok) return;
    adminServicesList = await res.json();
    const tbody = document.getElementById("servicesTableBody");
    if (!tbody) return;
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
  } catch (e) { console.error("Error al cargar servicios:", e); }
}

async function deleteService(id) {
  if (!confirm("¿Eliminar este servicio? Esta acción no se puede deshacer.")) return;
  try {
    const res = await fetch(`/api/admin/services/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) {
      showAdminToast("Servicio eliminado correctamente.", "success");
      loadAdminServices();
    } else {
      const err = await res.json().catch(() => ({}));
      showAdminToast(err.detail || "Error al eliminar servicio.", "error");
      loadAdminServices();
    }
  } catch (e) {
    showAdminToast("Error de conexión al eliminar servicio.", "error");
  }
}

function openServiceModal() {
  currentModalType = "service";
  editingRecordId = null;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = "+ AGREGAR SERVICIO";
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

async function editServiceModal(id) {
  let s = adminServicesList.find(item => item.id == id);
  if (!s) {
    try {
      const res = await fetch("/api/admin/services", { headers: authHeaders() });
      if (res.ok) {
        adminServicesList = await res.json();
        s = adminServicesList.find(item => item.id == id);
      }
    } catch (e) {}
  }
  if (!s) {
    showAdminToast("No se encontró el servicio en el servidor. Actualizando...", "warning");
    loadAdminServices();
    return;
  }
  currentModalType = "service";
  editingRecordId = id;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = `✏️ EDITAR SERVICIO #${id}`;
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

// 2. ESTILOS DE CORTE
async function loadAdminStyles() {
  try {
    const res = await fetch("/api/admin/styles", { headers: authHeaders() });
    if (!res.ok) return;
    adminStylesList = await res.json();
    const tbody = document.getElementById("stylesTableBody");
    if (!tbody) return;
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
  } catch (e) { console.error("Error al cargar estilos:", e); }
}

async function deleteStyle(id) {
  if (!confirm("¿Eliminar este estilo? Esta acción no se puede deshacer.")) return;
  try {
    const res = await fetch(`/api/admin/styles/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) {
      showAdminToast("Estilo eliminado correctamente.", "success");
      loadAdminStyles();
    } else {
      const err = await res.json().catch(() => ({}));
      showAdminToast(err.detail || "Error al eliminar estilo.", "error");
      loadAdminStyles();
    }
  } catch (e) {
    showAdminToast("Error de conexión al eliminar estilo.", "error");
  }
}

function openStyleModal() {
  currentModalType = "style";
  editingRecordId = null;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = "+ AGREGAR ESTILO DE CORTE";
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

async function editStyleModal(id) {
  let st = adminStylesList.find(item => item.id == id);
  if (!st) {
    try {
      const res = await fetch("/api/admin/styles", { headers: authHeaders() });
      if (res.ok) {
        adminStylesList = await res.json();
        st = adminStylesList.find(item => item.id == id);
      }
    } catch (e) {}
  }
  if (!st) {
    showAdminToast("No se encontró el estilo en el servidor. Actualizando...", "warning");
    loadAdminStyles();
    return;
  }
  currentModalType = "style";
  editingRecordId = id;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = `✏️ EDITAR ESTILO #${id}`;
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

// 3. ZONAS DE DELIVERY
async function loadAdminDelivery() {
  try {
    const res = await fetch("/api/admin/delivery-zones", { headers: authHeaders() });
    if (!res.ok) return;
    adminDeliveryList = await res.json();
    const tbody = document.getElementById("deliveryTableBody");
    if (!tbody) return;
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
  } catch (e) { console.error("Error al cargar zonas de delivery:", e); }
}

async function deleteDeliveryZone(id) {
  if (!confirm("¿Eliminar esta zona de delivery? Esta acción no se puede deshacer.")) return;
  try {
    const res = await fetch(`/api/admin/delivery-zones/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) {
      showAdminToast("Zona de delivery eliminada correctamente.", "success");
      loadAdminDelivery();
    } else {
      const err = await res.json().catch(() => ({}));
      showAdminToast(err.detail || "Error al eliminar zona de delivery.", "error");
      loadAdminDelivery();
    }
  } catch (e) {
    showAdminToast("Error de conexión al eliminar zona.", "error");
  }
}

function openDeliveryModal() {
  currentModalType = "delivery";
  editingRecordId = null;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = "+ AGREGAR ZONA DE DELIVERY";
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

async function editDeliveryModal(id) {
  let z = adminDeliveryList.find(item => item.id == id);
  if (!z) {
    try {
      const res = await fetch("/api/admin/delivery-zones", { headers: authHeaders() });
      if (res.ok) {
        adminDeliveryList = await res.json();
        z = adminDeliveryList.find(item => item.id == id);
      }
    } catch (e) {}
  }
  if (!z) {
    showAdminToast("No se encontró la zona en el servidor. Actualizando...", "warning");
    loadAdminDelivery();
    return;
  }
  currentModalType = "delivery";
  editingRecordId = id;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = `✏️ EDITAR ZONA DE DELIVERY #${id}`;
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
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
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

// ==========================================
// 5. AGREGADOS & SERVICIOS EXTRA (TILDABLES)
// ==========================================
async function loadAdminExtras() {
  try {
    const res = await fetch("/api/admin/service-extras", { headers: authHeaders() });
    if (!res.ok) return;
    adminExtrasList = await res.json();
    const tbody = document.getElementById("extrasTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (adminExtrasList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #9ca3af; padding: 20px;">No hay opciones adicionales configuradas. Haz clic en "+ Agregar Opción Extra".</td></tr>`;
      return;
    }
    adminExtrasList.forEach(e => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span style="font-size: 1.1rem; margin-right: 6px;">${escapeHtml(e.icon || '✂️')}</span> <strong>${escapeHtml(e.name)}</strong></td>
        <td style="color: #9ca3af; font-size: 0.8rem;">${escapeHtml(e.description || '-')}</td>
        <td>+${e.duration_min} min</td>
        <td style="color: #d4ff00; font-weight: bold;">+$${e.price.toLocaleString("es-AR")}</td>
        <td><span class="badge ${e.is_active ? 'badge-confirmed' : 'badge-canceled'}">${e.is_active ? 'ACTIVO' : 'INACTIVO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editExtraModal(${e.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteExtra(${e.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error al cargar extras:", err);
  }
}

async function deleteExtra(id) {
  if (!confirm("¿Eliminar esta opción extra?")) return;
  try {
    const res = await fetch(`/api/admin/service-extras/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) {
      showAdminToast("Opción extra eliminada.", "success");
      loadAdminExtras();
    } else {
      const err = await res.json().catch(() => ({}));
      showAdminToast(err.detail || "Error al eliminar extra.", "error");
    }
  } catch (e) {
    showAdminToast("Error de conexión al eliminar extra.", "error");
  }
}

function openExtraModal() {
  currentModalType = "extra";
  editingRecordId = null;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = "+ AGREGAR OPCIÓN EXTRA";
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
      <div class="form-group">
        <label>NOMBRE DEL AGREGADO / EXTRA</label>
        <input type="text" id="modal_extra_name" class="form-control" placeholder="Ej: Perfilado con Navaja" required>
      </div>
      <div class="form-group">
        <label>PRECIO ADICIONAL ($)</label>
        <input type="number" step="0.01" id="modal_extra_price" class="form-control" placeholder="1500" required>
      </div>
      <div class="form-group">
        <label>DURACIÓN ADICIONAL (MINUTOS)</label>
        <input type="number" id="modal_extra_duration" class="form-control" value="15" required>
      </div>
      <div class="form-group">
        <label>ICONO / EMOJI</label>
        <input type="text" id="modal_extra_icon" class="form-control" value="✂️" placeholder="✂️, 🧔, ✨, 🎨, 💈">
      </div>
      <div class="form-group">
        <label>DESCRIPCIÓN BREVE</label>
        <input type="text" id="modal_extra_desc" class="form-control" placeholder="Ej: Definición nítida de líneas con navaja tradicional">
      </div>
    `;
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

async function editExtraModal(id) {
  let e = adminExtrasList.find(item => item.id == id);
  if (!e) {
    try {
      const res = await fetch("/api/admin/service-extras", { headers: authHeaders() });
      if (res.ok) {
        adminExtrasList = await res.json();
        e = adminExtrasList.find(item => item.id == id);
      }
    } catch (err) {}
  }
  if (!e) {
    showAdminToast("No se encontró el extra. Actualizando...", "warning");
    loadAdminExtras();
    return;
  }
  currentModalType = "extra";
  editingRecordId = id;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = `✏️ EDITAR OPCIÓN EXTRA #${id}`;
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
      <div class="form-group">
        <label>NOMBRE DEL AGREGADO / EXTRA</label>
        <input type="text" id="modal_extra_name" class="form-control" value="${escapeHtml(e.name)}" required>
      </div>
      <div class="form-group">
        <label>PRECIO ADICIONAL ($)</label>
        <input type="number" step="0.01" id="modal_extra_price" class="form-control" value="${e.price}" required>
      </div>
      <div class="form-group">
        <label>DURACIÓN ADICIONAL (MINUTOS)</label>
        <input type="number" id="modal_extra_duration" class="form-control" value="${e.duration_min}" required>
      </div>
      <div class="form-group">
        <label>ICONO / EMOJI</label>
        <input type="text" id="modal_extra_icon" class="form-control" value="${escapeHtml(e.icon || '✂️')}">
      </div>
      <div class="form-group">
        <label>DESCRIPCIÓN BREVE</label>
        <input type="text" id="modal_extra_desc" class="form-control" value="${escapeHtml(e.description || '')}">
      </div>
      <div class="form-group">
        <label>ESTADO</label>
        <select id="modal_extra_active" class="form-control">
          <option value="true" ${e.is_active ? 'selected' : ''}>ACTIVO (Disponible para clientes)</option>
          <option value="false" ${!e.is_active ? 'selected' : ''}>INACTIVO (Pausado)</option>
        </select>
      </div>
    `;
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

