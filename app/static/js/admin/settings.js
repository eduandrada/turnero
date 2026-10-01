/**
 * Admin Panel - Settings, Branding, Audit & Notifications Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles branding, logo upload, live theme preview, settings saving, password change, audit logs, and notification logs.
 */

let allAuditLogsList = [];

function updateAdminBrandUI(sets) {
  if (!sets) return;
  const bName = sets.barber_name || sets.app_name || "Turnero";
  const brandEl = document.getElementById("sidebarBrandName");
  if (brandEl) {
    if (sets.logo_url) {
      brandEl.innerHTML = `<img src="${sets.logo_url}" alt="${escapeHtml(bName)}" style="max-height: 52px; max-width: 220px; object-fit: contain; filter: drop-shadow(0 0 10px rgba(212, 255, 0, 0.4)); mix-blend-mode: screen;">`;
    } else {
      brandEl.innerHTML = `${escapeHtml(bName.toUpperCase())}<span>_</span>`;
    }
  }
  document.title = `${bName} // Panel Administrativo`;
  applyThemeVariablesToRoot(sets);
}

function applyThemeVariablesToRoot(sets) {
  if (!sets) return;
  const root = document.documentElement;
  if (sets.color_primary) {
    root.style.setProperty('--color-primary', sets.color_primary);
    root.style.setProperty('--neon-volt', sets.color_primary);
  }
  if (sets.color_secondary) root.style.setProperty('--color-secondary', sets.color_secondary);
  if (sets.color_accent) root.style.setProperty('--color-accent', sets.color_accent);
  if (sets.color_background) {
    root.style.setProperty('--color-background', sets.color_background);
    root.style.setProperty('--obsidian', sets.color_background);
  }
  if (sets.color_surface) {
    root.style.setProperty('--color-surface', sets.color_surface);
    root.style.setProperty('--surface', sets.color_surface);
  }
  if (sets.color_text) root.style.setProperty('--color-text', sets.color_text);
  if (sets.color_muted) root.style.setProperty('--color-muted', sets.color_muted);
  if (sets.color_button) root.style.setProperty('--color-button', sets.color_button);
  if (sets.color_border) {
    root.style.setProperty('--color-border', sets.color_border);
    root.style.setProperty('--surface-border', sets.color_border);
  }
  if (sets.border_radius) {
    root.style.setProperty('--border-radius', sets.border_radius + 'px');
  }
}

async function loadSettingsToForm() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (!res.ok) return;
    const sets = await res.json();
    for (const [k, v] of Object.entries(sets)) {
      const el = document.getElementById(`setting_${k}`);
      if (el) el.value = v;

      // Sync color pickers
      const picker = document.getElementById(`setting_${k}_picker`);
      if (picker && v && v.startsWith('#')) {
        picker.value = v;
      }
    }

    if (sets.shop_banner_slides) {
      try {
        const slides = typeof sets.shop_banner_slides === "string" ? JSON.parse(sets.shop_banner_slides) : sets.shop_banner_slides;
        if (Array.isArray(slides)) {
          if (slides[0]) {
            if (document.getElementById("promo_s1_title")) document.getElementById("promo_s1_title").value = slides[0].title || "";
            if (document.getElementById("promo_s1_subtitle")) document.getElementById("promo_s1_subtitle").value = slides[0].subtitle || "";
            if (document.getElementById("promo_s1_badge")) document.getElementById("promo_s1_badge").value = slides[0].badge || "";
            if (document.getElementById("promo_s1_coupon")) document.getElementById("promo_s1_coupon").value = slides[0].coupon || "";
            if (document.getElementById("promo_s1_image")) document.getElementById("promo_s1_image").value = slides[0].image_url || "";
          }
          if (slides[1]) {
            if (document.getElementById("promo_s2_title")) document.getElementById("promo_s2_title").value = slides[1].title || "";
            if (document.getElementById("promo_s2_subtitle")) document.getElementById("promo_s2_subtitle").value = slides[1].subtitle || "";
            if (document.getElementById("promo_s2_badge")) document.getElementById("promo_s2_badge").value = slides[1].badge || "";
            if (document.getElementById("promo_s2_coupon")) document.getElementById("promo_s2_coupon").value = slides[1].coupon || "";
            if (document.getElementById("promo_s2_image")) document.getElementById("promo_s2_image").value = slides[1].image_url || "";
          }
        }
      } catch (e) {
        console.error("Error al parsear shop_banner_slides:", e);
      }
    }

    // Logo preview setup
    const logoPreviewContainer = document.getElementById("logoPreviewContainer");
    const logoPlaceholder = document.getElementById("logoPreviewPlaceholder") || document.getElementById("logoPlaceholder");
    const logoPreviewImage = document.getElementById("logoPreviewImg") || document.getElementById("logoPreviewImage");

    if (sets.logo_url && logoPreviewImage) {
      logoPreviewImage.src = sets.logo_url;
      logoPreviewImage.style.display = "block";
      if (logoPlaceholder) logoPlaceholder.style.display = "none";
    } else {
      if (logoPreviewImage) logoPreviewImage.style.display = "none";
      if (logoPlaceholder) logoPlaceholder.style.display = "block";
    }

    updateAdminBrandUI(sets);
    updateLiveThemePreview();
  } catch (e) { console.error("Error al cargar configuración:", e); }
}

async function handleLogoUpload(input) {
  if (!input || !input.files || input.files.length === 0) return;
  const file = input.files[0];

  const allowedExts = ["png", "jpg", "jpeg", "webp", "svg"];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowedExts.includes(ext)) {
    alert(`Formato de archivo no válido (.${ext}). Por favor selecciona una imagen PNG (preferente transparente), JPG, WebP o SVG.`);
    input.value = "";
    return;
  }

  const maxSize = 5 * 1024 * 1024; // 5 MB
  if (file.size > maxSize) {
    alert(`El archivo seleccionado dura ${(file.size / (1024 * 1024)).toFixed(2)} MB. El tamaño máximo permitido es 5 MB.`);
    input.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/admin/logo/upload", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${adminToken}`
      },
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.logo_url) {
      const settingInput = document.getElementById("setting_logo_url");
      if (settingInput) settingInput.value = data.logo_url;

      const logoPlaceholder = document.getElementById("logoPreviewPlaceholder") || document.getElementById("logoPlaceholder");
      const logoPreviewImage = document.getElementById("logoPreviewImg") || document.getElementById("logoPreviewImage");

      if (logoPreviewImage) {
        logoPreviewImage.src = data.logo_url;
        logoPreviewImage.style.display = "block";
        if (logoPlaceholder) logoPlaceholder.style.display = "none";
      }

      await loadSettingsToForm();
      alert("¡Logo subido y aplicado exitosamente a toda la aplicación!");
    } else {
      alert(data.detail || "Error al subir el logo.");
    }
  } catch (e) {
    alert("Error de conexión al subir el logo.");
  }
}

async function handleCoverUpload(input) {
  if (!input || !input.files || input.files.length === 0) return;
  const file = input.files[0];

  const allowedExts = ["png", "jpg", "jpeg", "webp"];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowedExts.includes(ext)) {
    alert(`Formato de archivo no válido (.${ext}). Selecciona una imagen PNG, JPG o WebP.`);
    input.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/admin/logo/upload", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${adminToken}`
      },
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.logo_url) {
      const settingInput = document.getElementById("setting_cover_image_url");
      if (settingInput) settingInput.value = data.logo_url;
      alert("¡Imagen de fondo subida y aplicada exitosamente!");
    } else {
      alert(data.detail || "Error al subir la imagen de fondo.");
    }
  } catch (e) {
    alert("Error de conexión al subir la imagen de fondo.");
  }
}


async function removeLogo() {
  if (!confirm("¿Estás seguro de eliminar el logo de la barbería? Se restaurará la visualización de texto por defecto.")) return;

  try {
    const res = await fetch("/api/admin/logo/delete", {
      method: "DELETE",
      headers: authHeaders()
    });

    if (res.ok) {
      const settingInput = document.getElementById("setting_logo_url");
      if (settingInput) settingInput.value = "";

      const fileInput = document.getElementById("setting_logo_file");
      if (fileInput) fileInput.value = "";

      const logoPreviewContainer = document.getElementById("logoPreviewContainer");
      const logoPlaceholder = document.getElementById("logoPlaceholder");
      if (logoPreviewContainer && logoPlaceholder) {
        logoPreviewContainer.style.display = "none";
        logoPlaceholder.style.display = "block";
      }

      await loadSettingsToForm();
      alert("Logo eliminado correctamente.");
    } else {
      alert("Error al eliminar el logo.");
    }
  } catch (e) {
    alert("Error de conexión al eliminar logo.");
  }
}

function syncColorPicker(key) {
  const textInput = document.getElementById(`setting_${key}`);
  const pickerInput = document.getElementById(`setting_${key}_picker`);
  if (textInput && pickerInput) {
    textInput.value = pickerInput.value;
  }
  updateLiveThemePreview();
}

function updateLiveThemePreview() {
  const getColor = (key, fallback) => {
    const el = document.getElementById(`setting_${key}`);
    return el && el.value ? el.value : fallback;
  };

  const primary = getColor("color_primary", "#d4ff00");
  const secondary = getColor("color_secondary", "#00f2fe");
  const accent = getColor("color_accent", "#ff0055");
  const bg = getColor("color_background", "#0a0a0c");
  const surface = getColor("color_surface", "#131318");
  const text = getColor("color_text", "#f3f4f6");
  const muted = getColor("color_muted", "#9ca3af");
  const button = getColor("color_button", "#d4ff00");
  const border = getColor("color_border", "#23232c");
  const radius = getColor("border_radius", "16");

  const root = document.documentElement;
  root.style.setProperty('--color-primary', primary);
  root.style.setProperty('--color-secondary', secondary);
  root.style.setProperty('--color-accent', accent);
  root.style.setProperty('--color-background', bg);
  root.style.setProperty('--color-surface', surface);
  root.style.setProperty('--color-text', text);
  root.style.setProperty('--color-muted', muted);
  root.style.setProperty('--color-button', button);
  root.style.setProperty('--color-border', border);
  root.style.setProperty('--border-radius', radius + 'px');
  root.style.setProperty('--neon-volt', primary);
  root.style.setProperty('--obsidian', bg);
  root.style.setProperty('--surface', surface);

  const previewBox = document.getElementById("themePreviewCard");
  if (previewBox) {
    previewBox.style.backgroundColor = bg;
    previewBox.style.borderColor = border;
    previewBox.style.borderRadius = radius + 'px';
  }

  const previewHeading = document.getElementById("themePreviewHeading");
  if (previewHeading) previewHeading.style.color = text;

  const previewText = document.getElementById("themePreviewText");
  if (previewText) previewText.style.color = muted;

  const previewBadge = document.getElementById("themePreviewBadge");
  if (previewBadge) {
    previewBadge.style.backgroundColor = primary;
    previewBadge.style.color = bg;
  }

  const previewSecondaryBadge = document.getElementById("themePreviewSecondaryBadge");
  if (previewSecondaryBadge) {
    previewSecondaryBadge.style.backgroundColor = secondary;
    previewSecondaryBadge.style.color = bg;
  }

  const previewAccentBadge = document.getElementById("themePreviewAccentBadge");
  if (previewAccentBadge) {
    previewAccentBadge.style.backgroundColor = accent;
    previewAccentBadge.style.color = '#ffffff';
  }

  const previewBtn = document.getElementById("themePreviewBtnPrimary");
  if (previewBtn) {
    previewBtn.style.backgroundColor = button;
    previewBtn.style.color = bg;
    previewBtn.style.borderRadius = radius + 'px';
  }
}

async function saveSettingsSection(secName) {
  const fields = document.querySelectorAll("[id^='setting_']");
  const updates = {};
  fields.forEach(el => {
    if (el.type !== "file" && !el.id.endsWith("_picker")) {
      const key = el.id.replace("setting_", "");
      updates[key] = el.value;
    }
  });

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ settings: updates })
    });
    if (res.ok) {
      const updatedSets = await res.json();
      updateAdminBrandUI(updatedSets.settings || updatedSets);
      alert("Configuración e identidad visual guardadas exitosamente.");
    } else {
      alert("Error al guardar la configuración.");
    }
  } catch (e) { alert("Error de conexión al guardar configuración."); }
}

async function updateAdminPassword() {
  const cur = document.getElementById("changeCurrPass")?.value;
  const nw = document.getElementById("changeNewPass")?.value;

  try {
    const res = await fetch("/api/admin/change-password", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ current_password: cur, new_password: nw })
    });
    const data = await res.json();
    if (res.ok) {
      alert("Contraseña actualizada con éxito.");
      const c1 = document.getElementById("changeCurrPass");
      const c2 = document.getElementById("changeNewPass");
      if (c1) c1.value = "";
      if (c2) c2.value = "";
    } else {
      alert(data.detail || "Error al cambiar contraseña.");
    }
  } catch (e) { alert("Error al actualizar contraseña."); }
}

let cachedNotificationLogs = [];
let selectedNotificationLogIds = new Set();

async function loadAdminNotificationLogs() {
  const statusFilter = document.getElementById("waLogStatusFilter")?.value || "";
  const typeFilter = document.getElementById("waLogTypeFilter")?.value || "";
  const search = document.getElementById("waLogSearchInput")?.value.trim() || "";

  let url = `/api/admin/notifications/logs?limit=300`;
  if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;
  if (typeFilter) url += `&message_type=${encodeURIComponent(typeFilter)}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    cachedNotificationLogs = await res.json();
    selectedNotificationLogIds.clear();
    updateWaSelectedCount();
    renderNotificationLogsTable(cachedNotificationLogs);
    updateNotificationKPIs(cachedNotificationLogs);
  } catch (e) {
    console.error("Error loading notification logs:", e);
  }
}

function updateNotificationKPIs(logs) {
  const total = logs.length;
  const success = logs.filter(l => (l.status || '').toUpperCase() === "ENVIADO" || (l.status || '').toUpperCase() === "DELIVERED" || (l.status || '').toUpperCase() === "READ").length;
  const failed = logs.filter(l => (l.status || '').toUpperCase() === "ERROR" || (l.status || '').toUpperCase() === "FALLIDO").length;

  const elTotal = document.getElementById("kpiWaTotalCount");
  const elSucc = document.getElementById("kpiWaSuccessCount");
  const elFail = document.getElementById("kpiWaFailedCount");

  if (elTotal) elTotal.textContent = total;
  if (elSucc) elSucc.textContent = success;
  if (elFail) elFail.textContent = failed;
}

function renderNotificationLogsTable(logs) {
  const tbody = document.getElementById("notificationLogsBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const selectAllCheck = document.getElementById("waSelectAllCheck");
  if (selectAllCheck) selectAllCheck.checked = false;

  if (logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #9ca3af; padding: 30px;">No se encontraron registros de auditoría de WhatsApp.</td></tr>`;
    return;
  }

  logs.forEach(l => {
    const tr = document.createElement("tr");
    
    const st = (l.status || '').toUpperCase();
    let statusBadge = "badge-pending";
    if (st === "ENVIADO" || st === "DELIVERED" || st === "READ") statusBadge = "badge-confirmed";
    else if (st === "ERROR" || st === "FALLIDO") statusBadge = "badge-canceled";

    const isChecked = selectedNotificationLogIds.has(l.id);
    const dtStr = l.created_at || l.sent_at ? (l.created_at || l.sent_at).replace("T", " ").substring(0, 19) : '-';

    const recipientName = l.recipient || l.recipient_name || '-';
    const recipientRole = l.recipient_role || l.recipient_type || 'CLIENTE';
    const cleanPhone = (recipientName.match(/\d+/g) || []).join("") || (l.recipient_phone || '').replace(/\D/g, "");

    const msgBody = l.message_body || l.message || '';
    const bodySnippet = msgBody.length > 45 ? msgBody.substring(0, 45) + "..." : msgBody;

    tr.innerHTML = `
      <td>
        <input type="checkbox" class="wa-log-check" value="${l.id}" ${isChecked ? 'checked' : ''} onchange="toggleWaLogSelection(${l.id}, this.checked)" style="accent-color: #d4ff00; width: 18px; height: 18px; cursor: pointer;">
      </td>
      <td style="font-size: 0.8rem; color: #cbd5e1;">${dtStr}</td>
      <td>
        <strong>${escapeHtml(recipientName)}</strong> 
        <span class="badge ${recipientRole === 'BARBERO' ? 'badge-pending' : 'badge-confirmed'}" style="font-size: 0.65rem;">${escapeHtml(recipientRole)}</span>
      </td>
      <td>
        <span class="badge" style="background: rgba(0, 242, 254, 0.15); color: #00f2fe; font-size: 0.75rem;">${escapeHtml(l.message_type || 'WHATSAPP')}</span>
      </td>
      <td>
        <span style="font-size: 0.82rem; color: #cbd5e1;">${escapeHtml(bodySnippet)}</span>
        ${msgBody.length > 45 ? `<button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openWaLogDetailModal(${l.id})" style="padding: 2px 6px; font-size: 0.7rem; margin-left: 4px;">Ver</button>` : ''}
      </td>
      <td style="font-family: monospace;">${l.appointment_id ? '#' + l.appointment_id : '-'}</td>
      <td><span class="badge ${statusBadge}">${escapeHtml(st)}</span></td>
      <td>
        <div style="display: flex; gap: 6px;">
          ${cleanPhone ? `<a href="https://wa.me/${cleanPhone}" target="_blank" class="btn-admin btn-admin-sm" style="background: #25D366; color: #000; font-weight: bold; text-decoration: none;" title="Abrir WhatsApp">💬</a>` : ''}
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteNotificationLog(${l.id})" title="Eliminar registro">🗑️</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function toggleWaLogSelection(id, checked) {
  if (checked) {
    selectedNotificationLogIds.add(id);
  } else {
    selectedNotificationLogIds.delete(id);
  }
  updateWaSelectedCount();
}

function toggleSelectAllWaLogs(checked) {
  const checkboxes = document.querySelectorAll(".wa-log-check");
  checkboxes.forEach(cb => {
    cb.checked = checked;
    const val = parseInt(cb.value);
    if (checked) selectedNotificationLogIds.add(val);
    else selectedNotificationLogIds.delete(val);
  });
  updateWaSelectedCount();
}

function updateWaSelectedCount() {
  const count = selectedNotificationLogIds.size;
  const lbl = document.getElementById("waSelectedCount");
  if (lbl) lbl.textContent = count;
  const btn = document.getElementById("btnBulkDeleteWaLogs");
  if (btn) btn.disabled = (count === 0);
}

async function deleteNotificationLog(id) {
  if (!confirm(`¿Eliminar este registro de auditoría de WhatsApp (#${id})?`)) return;
  try {
    const res = await fetch(`/api/admin/notifications/logs/${id}`, {
      method: "DELETE",
      headers: authHeaders()
    });
    if (res.ok) {
      if (typeof showAdminToast === "function") showAdminToast("Registro eliminado.", "success");
      loadAdminNotificationLogs();
    } else {
      alert("Error al eliminar registro.");
    }
  } catch (e) { alert("Error de conexión."); }
}

async function deleteSelectedWaLogs() {
  const ids = Array.from(selectedNotificationLogIds);
  if (ids.length === 0) {
    alert("No seleccionaste ningún registro para eliminar.");
    return;
  }
  if (!confirm(`¿Eliminar los ${ids.length} registros de auditoría de WhatsApp seleccionados?`)) return;

  try {
    const res = await fetch("/api/admin/notifications/logs/bulk-delete", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ ids: ids })
    });
    const data = await res.json();
    if (res.ok) {
      if (typeof showAdminToast === "function") showAdminToast(`Se eliminaron ${ids.length} registros.`, "success");
      selectedNotificationLogIds.clear();
      loadAdminNotificationLogs();
    } else {
      alert(data.detail || "Error al eliminar registros.");
    }
  } catch (e) { alert("Error de conexión."); }
}

function openWaLogDetailModal(id) {
  const log = cachedNotificationLogs.find(l => l.id === id);
  if (!log) return;
  
  let modal = document.getElementById("waLogDetailModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "waLogDetailModal";
    modal.style.cssText = "position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 999; display: flex; align-items: center; justify-content: center; padding: 16px;";
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div style="background: #131318; border: 1px solid #23232c; border-radius: 16px; width: 100%; max-width: 520px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.9);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #23232c;">
        <h3 style="font-family: 'Space Grotesk', monospace; color: #fff; margin: 0;">💬 Mensaje Completo WhatsApp #${log.id}</h3>
        <button onclick="document.getElementById('waLogDetailModal').style.display='none'" style="background: transparent; border: none; color: #9ca3af; font-size: 1.2rem; cursor: pointer;">✕</button>
      </div>

      <div style="margin-bottom: 12px;">
        <span style="font-size: 0.75rem; color: #9ca3af;">DESTINATARIO:</span>
        <strong style="color: #fff; font-size: 0.95rem; margin-left: 6px;">${escapeHtml(log.recipient || log.recipient_name || '-')}</strong>
      </div>

      <div style="margin-bottom: 16px;">
        <span style="font-size: 0.75rem; color: #9ca3af; display: block; margin-bottom: 4px;">CONTENIDO COMPLETO ENVIADO:</span>
        <textarea class="form-control" rows="8" readonly style="font-family: monospace; font-size: 0.85rem;">${escapeHtml(log.message_body || '')}</textarea>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn-admin btn-admin-secondary" onclick="document.getElementById('waLogDetailModal').style.display='none'">Cerrar</button>
      </div>
    </div>
  `;
  modal.style.display = "flex";
}


async function loadAdminAuditLogs() {
  return loadAuditLogsData();
}

async function loadAuditLogsData() {
  try {
    const res = await fetch("/api/admin/audit-logs?limit=300", { headers: authHeaders() });
    if (!res.ok) {
      const fallbackRes = await fetch("/api/audit-logs?limit=300");
      if (fallbackRes.ok) {
        allAuditLogsList = await fallbackRes.json();
      }
    } else {
      allAuditLogsList = await res.json();
    }
    renderAuditLogsTable();
  } catch (e) {
    console.error("Error loading audit logs:", e);
    const tbody = document.getElementById("auditLogsTableBody");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #ef4444; padding: 30px;">Error al cargar registros de auditoría.</td></tr>`;
    }
  }
}

function renderAuditLogsTable() {
  const tbody = document.getElementById("auditLogsTableBody");
  if (!tbody) return;

  const searchVal = (document.getElementById("auditSearchInput")?.value || "").toLowerCase().trim();

  let filtered = allAuditLogsList.filter(l => {
    if (!searchVal) return true;
    const actorMatch = (l.actor || l.user_name || "").toLowerCase().includes(searchVal);
    const actionMatch = (l.action || "").toLowerCase().includes(searchVal);
    const descMatch = (l.description || "").toLowerCase().includes(searchVal);
    const ipMatch = (l.ip_address || "").toLowerCase().includes(searchVal);
    return actorMatch || actionMatch || descMatch || ipMatch;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #9ca3af; padding: 40px;">No se encontraron registros de auditoría.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  filtered.forEach(l => {
    const tr = document.createElement("tr");
    
    let dateStr = l.timestamp ? new Date(l.timestamp).toLocaleString("es-AR") : "-";

    const actorStr = l.actor || l.user_name || "Encargado / Recepción";
    const isAdmin = actorStr.toLowerCase().includes("admin");
    const actorBadgeStyle = isAdmin 
      ? "background: rgba(210, 255, 0, 0.15); color: #d2ff00; border: 1px solid rgba(210, 255, 0, 0.3);"
      : "background: rgba(0, 242, 254, 0.15); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.3);";

    const act = (l.action || "").toUpperCase();
    let actBadgeStyle = "background: rgba(255, 255, 255, 0.1); color: #ffffff; border: 1px solid rgba(255,255,255,0.2);";
    if (act.includes("CREAR")) {
      actBadgeStyle = "background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);";
    } else if (act.includes("VENTA")) {
      actBadgeStyle = "background: rgba(210, 255, 0, 0.15); color: #d2ff00; border: 1px solid rgba(210, 255, 0, 0.3);";
    } else if (act.includes("MODIFICAR") || act.includes("EDITAR") || act.includes("STOCK")) {
      actBadgeStyle = "background: rgba(234, 179, 8, 0.15); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3);";
    } else if (act.includes("ELIMINAR") || act.includes("BORRADO") || act.includes("CANCELAR")) {
      actBadgeStyle = "background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);";
    }

    const descText = l.description || `${l.action} en módulo ${l.module || 'Productos'}`;

    tr.innerHTML = `
      <td><span style="font-family: monospace; font-size: 0.85rem; color: #94a3b8;">${escapeHtml(dateStr)}</span></td>
      <td>
        <span style="${actorBadgeStyle} padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-family: monospace; font-weight: bold;">
          ${escapeHtml(actorStr)}
        </span>
      </td>
      <td>
        <span style="${actBadgeStyle} padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-family: monospace; font-weight: bold;">
          ${escapeHtml(l.action)}
        </span>
      </td>
      <td>
        <strong style="color: #ffffff; font-size: 0.9rem;">${escapeHtml(descText)}</strong>
        ${l.new_value ? `<span style="display: block; font-size: 0.78rem; color: #64748b; margin-top: 2px;">Detalle: ${escapeHtml(l.new_value)}</span>` : ''}
      </td>
      <td>
        <span style="font-family: monospace; font-size: 0.8rem; color: #64748b;">${escapeHtml(l.ip_address || '127.0.0.1')}</span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterAuditLogsTable() {
  renderAuditLogsTable();
}

async function saveShopPromoSettings() {
  const s1Title = document.getElementById("promo_s1_title")?.value || "";
  const s1Sub = document.getElementById("promo_s1_subtitle")?.value || "";
  const s1Badge = document.getElementById("promo_s1_badge")?.value || "";
  const s1Coupon = document.getElementById("promo_s1_coupon")?.value || "";
  const s1Img = document.getElementById("promo_s1_image")?.value || "";

  const s2Title = document.getElementById("promo_s2_title")?.value || "";
  const s2Sub = document.getElementById("promo_s2_subtitle")?.value || "";
  const s2Badge = document.getElementById("promo_s2_badge")?.value || "";
  const s2Coupon = document.getElementById("promo_s2_coupon")?.value || "";
  const s2Img = document.getElementById("promo_s2_image")?.value || "";

  const slides = [
    { id: 1, title: s1Title, subtitle: s1Sub, badge: s1Badge, coupon: s1Coupon, image_url: s1Img },
    { id: 2, title: s2Title, subtitle: s2Sub, badge: s2Badge, coupon: s2Coupon, image_url: s2Img }
  ];

  const payload = {
    settings: {
      shop_banner_slides: JSON.stringify(slides)
    }
  };

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert("¡Configuración de Banners y Promociones del Shop guardada exitosamente!");
      await loadSettingsToForm();
    } else {
      const data = await res.json();
      alert(data.detail || "Error al guardar la configuración.");
    }
  } catch (e) {
    alert("Error de conexión con el servidor.");
  }
}
