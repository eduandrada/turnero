/**
 * Admin Panel - Users & Staff Permissions Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles staff accounts, granular role permissions (stock, finances, cancel, shop), and staff passwords.
 */

async function loadStaffData() {
  try {
    const res = await fetch("/api/admin/staff", { headers: authHeaders() });
    if (!res.ok) return;
    const staffList = await res.json();
    const tbody = document.getElementById("staffTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    staffList.forEach(u => {
      const tr = document.createElement("tr");
      const isEncargado = u.role === "encargado";
      tr.innerHTML = `
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td><span class="badge ${isEncargado ? 'badge-pending' : 'badge-confirmed'}">${u.role ? u.role.toUpperCase() : 'ADMIN'}</span></td>
        <td><span class="badge ${u.is_active ? 'badge-confirmed' : 'badge-canceled'}">${u.is_active ? 'ACTIVO' : 'INACTIVO'}</span></td>
        <td>
          <input type="checkbox" ${u.can_edit_stock ? 'checked' : ''} onchange="toggleStaffPermission(${u.id}, 'can_edit_stock', this.checked)" style="accent-color: #d4ff00; width: 18px; height: 18px; cursor: pointer;">
        </td>
        <td>
          <input type="checkbox" ${u.can_view_finances ? 'checked' : ''} onchange="toggleStaffPermission(${u.id}, 'can_view_finances', this.checked)" style="accent-color: #d4ff00; width: 18px; height: 18px; cursor: pointer;">
        </td>
        <td>
          <input type="checkbox" ${u.can_cancel_appointments ? 'checked' : ''} onchange="toggleStaffPermission(${u.id}, 'can_cancel_appointments', this.checked)" style="accent-color: #d4ff00; width: 18px; height: 18px; cursor: pointer;">
        </td>
        <td>
          <input type="checkbox" ${u.can_manage_shop ? 'checked' : ''} onchange="toggleStaffPermission(${u.id}, 'can_manage_shop', this.checked)" style="accent-color: #d4ff00; width: 18px; height: 18px; cursor: pointer;">
        </td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openChangeStaffPasswordModal(${u.id}, '${escapeHtml(u.username)}')">🔑 Pass</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    loadEncargadoSettingsInAdmin();
    loadStaffFichajesData();
  } catch (e) {
    console.error("Error al cargar personal:", e);
  }
}

async function loadEncargadoSettingsInAdmin() {
  try {
    const res = await fetch("/api/admin/encargado-settings", { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    if (document.getElementById("as_encargado_max_appts")) {
      document.getElementById("as_encargado_max_appts").value = data.encargado_max_appointments_per_day || 6;
      document.getElementById("as_encargado_max_clients").value = data.encargado_max_clients_per_day || 6;
      document.getElementById("as_encargado_max_services").value = data.encargado_max_services || 3;
      document.getElementById("as_encargado_max_styles").value = data.encargado_max_styles || 3;
      document.getElementById("as_encargado_allow_full").value = data.encargado_allow_full_admin ? "true" : "false";
    }
  } catch (e) {
    console.error("Error al cargar configuración de Encargados:", e);
  }
}

async function saveEncargadoSettingsFromAdmin() {
  const maxAppts = parseInt(document.getElementById("as_encargado_max_appts").value || "6");
  const maxClients = parseInt(document.getElementById("as_encargado_max_clients").value || "6");
  const maxServices = parseInt(document.getElementById("as_encargado_max_services").value || "3");
  const maxStyles = parseInt(document.getElementById("as_encargado_max_styles").value || "3");
  const allowFull = document.getElementById("as_encargado_allow_full").value === "true";

  try {
    const res = await fetch("/api/admin/encargado-settings", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        encargado_max_appointments_per_day: maxAppts,
        encargado_max_clients_per_day: maxClients,
        encargado_max_services: maxServices,
        encargado_max_styles: maxStyles,
        encargado_allow_full_admin: allowFull
      })
    });
    if (res.ok) {
      if (typeof showAdminToast === "function") {
        showAdminToast("Configuración de límites de Encargado guardada exitosamente.", "success");
      } else {
        alert("Configuración de límites de Encargado guardada exitosamente.");
      }
    } else {
      alert("Error al guardar la configuración.");
    }
  } catch (e) {
    alert("Error de conexión.");
  }
}


async function toggleStaffPermission(userId, permName, value) {
  try {
    const payload = {};
    payload[permName] = value;
    const res = await fetch(`/api/admin/staff/${userId}/permissions`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) alert("Error al actualizar permisos.");
  } catch (e) {
    alert("Error de conexión al actualizar permisos.");
  }
}

function openCreateStaffModal() {
  const u = document.getElementById("newStaffUsername");
  const p = document.getElementById("newStaffPassword");
  if (u) u.value = "";
  if (p) p.value = "";
  const m = document.getElementById("createStaffModal");
  if (m) m.style.display = "flex";
}

function closeCreateStaffModal() {
  const m = document.getElementById("createStaffModal");
  if (m) m.style.display = "none";
}

async function submitCreateStaff() {
  const u = document.getElementById("newStaffUsername")?.value.trim();
  const p = document.getElementById("newStaffPassword")?.value.trim();
  const r = document.getElementById("newStaffRole")?.value || "encargado";
  const cStock = document.getElementById("newStaffCanStock")?.checked || false;
  const cFin = document.getElementById("newStaffCanFinances")?.checked || false;
  const cCancel = document.getElementById("newStaffCanCancel")?.checked || false;
  const cShop = document.getElementById("newStaffCanShop")?.checked || false;

  try {
    const res = await fetch("/api/admin/staff", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        username: u,
        password: p,
        role: r,
        is_active: true,
        can_edit_stock: cStock,
        can_view_finances: cFin,
        can_cancel_appointments: cCancel,
        can_manage_shop: cShop
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`Usuario staff '${u}' creado correctamente.`);
      closeCreateStaffModal();
      loadStaffData();
    } else {
      alert(data.detail || "Error al crear usuario.");
    }
  } catch (e) {
    alert("Error de conexión.");
  }
}

function openChangeStaffPasswordModal(userId, username) {
  const idEl = document.getElementById("changePasswordStaffId");
  const userEl = document.getElementById("changePasswordStaffUsername");
  const passEl = document.getElementById("changePasswordNewPass");
  if (idEl) idEl.value = userId;
  if (userEl) userEl.value = username;
  if (passEl) passEl.value = "";
  const m = document.getElementById("changeStaffPasswordModal");
  if (m) m.style.display = "flex";
}

function closeChangeStaffPasswordModal() {
  const m = document.getElementById("changeStaffPasswordModal");
  if (m) m.style.display = "none";
}

async function submitChangeStaffPassword() {
  const userId = document.getElementById("changePasswordStaffId")?.value;
  const newPass = document.getElementById("changePasswordNewPass")?.value.trim();
  if (!newPass) return;

  try {
    const res = await fetch(`/api/admin/staff/${userId}/password`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ new_password: newPass })
    });
    const data = await res.json();
    if (res.ok) {
      alert("Contraseña actualizada con éxito.");
      closeChangeStaffPasswordModal();
    } else {
      alert(data.detail || "Error al cambiar contraseña.");
    }
  } catch (e) {
    alert("Error de conexión.");
  }
}

async function loadStaffFichajesData() {
  const tbody = document.getElementById("staffFichajesTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/admin/staff/fichajes", { headers: authHeaders() });
    if (!res.ok) return;
    const list = await res.json();
    tbody.innerHTML = "";

    if (list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #9ca3af; padding: 24px;">No hay registros de fichajes aún.</td></tr>`;
      return;
    }

    list.forEach(item => {
      const isIngreso = item.action_type === "INGRESO";
      const badgeClass = isIngreso ? "badge-confirmed" : "badge-canceled";
      const icon = isIngreso ? "🟢 INGRESO / INICIO" : "🔴 SALIDA / CIERRE";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family: monospace;">${item.date_art}</td>
        <td style="font-family: monospace; font-weight: bold; color: ${isIngreso ? '#d4ff00' : '#ff3355'};">${item.time_art}</td>
        <td><strong>@${escapeHtml(item.username)}</strong></td>
        <td><span class="badge ${badgeClass}">${icon}</span></td>
        <td style="font-size: 0.85rem; color: #9ca3af;">${escapeHtml(item.description || '-')}</td>
        <td style="font-family: monospace; font-size: 0.8rem;">${escapeHtml(item.ip_address)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #ef4444; padding: 24px;">Error al cargar fichajes.</td></tr>`;
  }
}

