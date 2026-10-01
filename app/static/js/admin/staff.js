/**
 * Admin Panel - Staff & Barber Management Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles barbers list, CRUD modals, working schedules & business hours.
 */

let adminBarbersList = [];

async function loadAdminBarbers() {
  try {
    const res = await fetch("/api/admin/barbers", { headers: authHeaders() });
    if (!res.ok) return;
    adminBarbersList = await res.json();
    const tbody = document.getElementById("barbersTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    adminBarbersList.forEach(b => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><img src="${b.avatar_url || ''}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 50%;"></td>
        <td>
          <strong>${escapeHtml(b.name)}</strong>
          ${b.phone ? `<br><small style="color: #00f2fe;">🔒 WA: ${escapeHtml(b.phone)}</small>` : ''}
        </td>
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
  } catch (e) {
    console.error("Error al cargar barberos:", e);
  }
}

async function deleteBarber(id) {
  if (!confirm("¿Eliminar este barbero?")) return;
  await fetch(`/api/admin/barbers/${id}`, { method: "DELETE", headers: authHeaders() });
  loadAdminBarbers();
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
      <label>📱 TELÉFONO / WHATSAPP (PRIVADO - NOTIFICACIONES)</label>
      <input type="text" id="modal_barber_phone" class="form-control" placeholder="5493834123456" required>
      <small style="color: #94a3b8; font-size: 0.7rem;">⚠️ Uso interno del negocio. NUNCA se mostrará en el perfil público.</small>
    </div>
    <div class="form-group">
      <label>EXPERIENCIA / DESCRIPCIÓN</label>
      <input type="text" id="modal_barber_experience" class="form-control" placeholder="Ej: 5 años - Master Barber especialista en Fade & Barba">
    </div>
    <div class="form-group">
      <label>ESTILOS DESTACADOS (Separados por coma)</label>
      <input type="text" id="modal_barber_featured_styles" class="form-control" placeholder="Skin Fade, Mullet, Barba Exfoliante">
    </div>
    <div class="form-group">
      <label>INSTAGRAM (Opcional)</label>
      <input type="text" id="modal_barber_instagram" class="form-control" placeholder="@mateobarber">
    </div>
    <div class="form-group">
      <label>FACEBOOK (Opcional)</label>
      <input type="text" id="modal_barber_facebook" class="form-control" placeholder="mateo.barber">
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
      <label>📱 TELÉFONO / WHATSAPP (PRIVADO - NOTIFICACIONES)</label>
      <input type="text" id="modal_barber_phone" class="form-control" value="${escapeHtml(b.phone || '')}" required>
      <small style="color: #94a3b8; font-size: 0.7rem;">⚠️ Uso interno del negocio. NUNCA se mostrará en el perfil público.</small>
    </div>
    <div class="form-group">
      <label>EXPERIENCIA / DESCRIPCIÓN</label>
      <input type="text" id="modal_barber_experience" class="form-control" value="${escapeHtml(b.experience || '')}">
    </div>
    <div class="form-group">
      <label>ESTILOS DESTACADOS (Separados por coma)</label>
      <input type="text" id="modal_barber_featured_styles" class="form-control" value="${escapeHtml(b.featured_styles || '')}">
    </div>
    <div class="form-group">
      <label>INSTAGRAM (Opcional)</label>
      <input type="text" id="modal_barber_instagram" class="form-control" value="${escapeHtml(b.instagram || '')}">
    </div>
    <div class="form-group">
      <label>FACEBOOK (Opcional)</label>
      <input type="text" id="modal_barber_facebook" class="form-control" value="${escapeHtml(b.facebook || '')}">
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

async function loadAdminSchedules() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (!res.ok) return;
    const sets = await res.json();
    let bh = {};
    try { bh = JSON.parse(sets.business_hours || "{}"); } catch (e) {}

    const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
    const container = document.getElementById("businessHoursContainer");
    if (!container) return;
    container.innerHTML = "";

    days.forEach(day => {
      const cfg = bh[day] || { active: true, open: "09:00", close: "20:00" };
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
  } catch (e) { console.error("Error al cargar horarios:", e); }
}

async function saveBusinessHours() {
  const days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  const bh = {};
  days.forEach(day => {
    bh[day] = {
      active: document.getElementById(`bh_active_${day}`)?.checked || false,
      open: document.getElementById(`bh_open_${day}`)?.value || "09:00",
      close: document.getElementById(`bh_close_${day}`)?.value || "20:00"
    };
  });

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ settings: { business_hours: JSON.stringify(bh) } })
    });
    if (res.ok) alert("Horarios guardados correctamente.");
  } catch (e) { alert("Error al guardar horarios."); }
}
