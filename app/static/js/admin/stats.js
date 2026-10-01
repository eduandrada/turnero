/**
 * Admin Panel - Attended Clients & Performance Stats Module
 * HiddenSYNC Barber Ecosystem 2026
 * Dedicated analytics, historical attended clients tracking, bulk deletion & full system restore.
 */

let statsState = {
  datePreset: "all",
  startDate: "",
  endDate: "",
  barberId: "",
  attendedList: [],
  barbers: [],
  selectedIds: new Set()
};

async function loadAttendedClientsStats() {
  await populateStatsBarbers();

  let url = "/api/admin/appointments?status=completados&limit=1000&";
  
  if (statsState.datePreset === "today") {
    const today = typeof getLocalDateStr === "function" ? getLocalDateStr(0) : new Date().toISOString().substring(0, 10);
    url += `date=${today}&`;
  } else if (statsState.startDate && statsState.endDate) {
    url += `start_date=${statsState.startDate}&end_date=${statsState.endDate}&`;
  }

  if (statsState.barberId) {
    url += `barber_id=${statsState.barberId}&`;
  }

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    
    // Filtrar estrictamente completados / atendidos
    statsState.attendedList = (data || []).filter(a => 
      ["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes((a.status || "").toUpperCase())
    );

    // Reset selecciones al recargar
    statsState.selectedIds.clear();
    updateStatsSelectionUI();

    updateStatsKPIs();
    renderAttendedClientsTable();
  } catch (e) {
    console.error("Error al cargar historial de atendidos:", e);
    if (typeof showToast === "function") showToast("Error al cargar historial de clientes atendidos", "error");
  }
}

async function populateStatsBarbers() {
  const sel = document.getElementById("statsFilterBarber");
  if (!sel || sel.options.length > 1) return;
  try {
    const res = await fetch("/api/admin/barbers", { headers: authHeaders() });
    if (res.ok) {
      statsState.barbers = await res.json();
      statsState.barbers.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b.id;
        opt.textContent = `Barbero: ${b.name}`;
        sel.appendChild(opt);
      });
    }
  } catch (_) {}
}

function updateStatsKPIs() {
  const list = statsState.attendedList;
  const totalCount = list.length;
  
  // Total facturación
  let totalRev = 0;
  let totalDur = 0;
  const barberCounts = {};

  list.forEach(a => {
    const price = parseFloat(a.service_price_snapshot || a.service_price || 0) || 0;
    totalRev += price;

    const dur = parseInt(a.actual_duration_min || a.duration_min || 40, 10);
    totalDur += dur;

    const bName = a.barber_name || "Sin asignar";
    barberCounts[bName] = (barberCounts[bName] || 0) + 1;
  });

  const avgDur = totalCount > 0 ? Math.round(totalDur / totalCount) : 0;

  let topBarber = "-";
  let topCount = 0;
  for (const [b, c] of Object.entries(barberCounts)) {
    if (c > topCount) {
      topCount = c;
      topBarber = b;
    }
  }

  const elCount = document.getElementById("statsTotalAttended");
  if (elCount) elCount.textContent = totalCount;

  const elRev = document.getElementById("statsTotalRevenue");
  if (elRev) elRev.textContent = `$${totalRev.toLocaleString("es-AR")}`;

  const elDur = document.getElementById("statsAvgDuration");
  if (elDur) elDur.textContent = `${avgDur} min`;

  const elTop = document.getElementById("statsTopBarber");
  if (elTop) elTop.textContent = topBarber;

  const elTopSub = document.getElementById("statsTopBarberSub");
  if (elTopSub) {
    elTopSub.textContent = topCount > 0 ? `${topCount} clientes atendidos` : "Mayor volumen de atenciones";
  }

  const elResultCount = document.getElementById("statsResultCount");
  if (elResultCount) elResultCount.textContent = `${totalCount} atenciones registradas`;
}

function renderAttendedClientsTable() {
  const tbody = document.getElementById("statsAttendedTableBody");
  const table = document.getElementById("statsTableElement");
  const emptyState = document.getElementById("statsEmptyState");
  if (!tbody) return;

  const query = (document.getElementById("statsSearchInput")?.value || "").toLowerCase().trim();

  let list = statsState.attendedList;
  if (query) {
    list = list.filter(a => 
      (a.client_name || "").toLowerCase().includes(query) ||
      (a.client_phone || "").toLowerCase().includes(query) ||
      (a.barber_name || "").toLowerCase().includes(query) ||
      (a.service || "").toLowerCase().includes(query) ||
      String(a.id).includes(query)
    );
  }

  tbody.innerHTML = "";

  if (list.length === 0) {
    if (table) table.style.display = "none";
    if (emptyState) emptyState.style.display = "block";
    return;
  }

  if (table) table.style.display = "table";
  if (emptyState) emptyState.style.display = "none";

  list.forEach(a => {
    const tr = document.createElement("tr");

    // Fecha y hora
    let dtFormatted = "--/--/---- --:-- hs";
    if (a.appointment_time) {
      const parts = a.appointment_time.replace("T", " ").split(" ");
      const dParts = parts[0].split("-");
      const datePretty = dParts.length === 3 ? `${dParts[2]}/${dParts[1]}/${dParts[0]}` : parts[0];
      const timePretty = parts[1] ? parts[1].substring(0, 5) : "--:--";
      dtFormatted = `${datePretty} • ${timePretty} hs`;
    }

    const cleanPhone = (a.client_phone || "").replace(/\D/g, "");
    const price = parseFloat(a.service_price_snapshot || a.service_price || 0) || 0;
    const priceStr = price > 0 ? `$${price.toLocaleString("es-AR")}` : "Incluido";

    const waFeedbackMsg = encodeURIComponent(
      `¡Hola ${a.client_name}! Te escribimos de la Barbería para agradecerte por tu visita. ¿Cómo quedó tu ${a.service || 'corte'} con ${a.barber_name || 'el equipo'}? Esperamos que hayas disfrutado la experiencia.`
    );

    const isChecked = statsState.selectedIds.has(a.id);

    tr.innerHTML = `
      <td style="text-align: center;">
        <input type="checkbox" class="stats-row-checkbox" value="${a.id}" ${isChecked ? 'checked' : ''} onchange="onStatsRowCheckboxChange(this, ${a.id})" style="width: 16px; height: 16px; accent-color: #ef4444; cursor: pointer;">
      </td>
      <td>
        <span style="font-family: monospace; font-size: 0.85rem; font-weight: 700; color: #00f2fe;">
          ${dtFormatted}
        </span>
      </td>
      <td>
        <strong style="color: #ffffff; font-size: 0.9rem;">${escapeHtml(a.client_name)}</strong>
      </td>
      <td>
        ${cleanPhone ? `
          <a href="https://wa.me/${cleanPhone}?text=${waFeedbackMsg}" target="_blank" class="btn-admin btn-admin-sm" style="background: rgba(37, 211, 102, 0.15); color: #25D366; border: 1px solid rgba(37, 211, 102, 0.4); text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" title="Enviar WhatsApp de satisfacción / fidelización">
            📱 ${escapeHtml(a.client_phone)}
          </a>
        ` : '<span style="color: #6b7280;">-</span>'}
      </td>
      <td>
        <span style="color: #d4ff00; font-weight: 600;">💈 ${escapeHtml(a.barber_name || 'Sin Asignar')}</span>
      </td>
      <td>
        <span style="color: #e2e8f0;">${escapeHtml(a.service || 'Corte Clásico')}</span>
      </td>
      <td>
        <span style="font-family: monospace; font-weight: 800; color: #10b981; font-size: 0.9rem;">
          ${priceStr}
        </span>
      </td>
      <td>
        <span class="status-pill status-COMPLETADO" style="font-size: 0.75rem; padding: 4px 8px;">
          ✅ Atendido
        </span>
      </td>
      <td style="text-align: right;">
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
          ${a.client_id ? `
            <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openClientProfileModal(${a.client_id})" title="Ver Historial CRM">
              👁️ Ficha
            </button>
          ` : ''}
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="reopenAttendedTurn(${a.id})" title="Reabrir turno si fue completado por error" style="font-size: 0.7rem; padding: 3px 8px;">
            ↩️ Reabrir
          </button>
          <button class="btn-admin btn-admin-sm" onclick="deleteSingleAttendedStat(${a.id})" title="Eliminar registro del historial" style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #ef4444; font-size: 0.7rem; padding: 3px 8px;">
            🗑️ Borrar
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  updateStatsSelectionUI();
}

function onStatsRowCheckboxChange(el, id) {
  if (el.checked) {
    statsState.selectedIds.add(id);
  } else {
    statsState.selectedIds.delete(id);
  }
  updateStatsSelectionUI();
}

function toggleSelectAllStats(headerEl) {
  const isChecked = headerEl.checked;
  const checkboxes = document.querySelectorAll(".stats-row-checkbox");
  
  checkboxes.forEach(cb => {
    cb.checked = isChecked;
    const id = parseInt(cb.value, 10);
    if (isChecked) {
      if (id) statsState.selectedIds.add(id);
    } else {
      if (id) statsState.selectedIds.delete(id);
    }
  });

  updateStatsSelectionUI();
}

function updateStatsSelectionUI() {
  const count = statsState.selectedIds.size;
  const countBadge = document.getElementById("statsSelectedCount");
  const btnBulkDelete = document.getElementById("btnStatsBulkDelete");
  const selectAllCb = document.getElementById("statsSelectAll");

  if (countBadge) {
    countBadge.style.display = count > 0 ? "inline-block" : "none";
    countBadge.textContent = `${count} seleccionado${count > 1 ? 's' : ''}`;
  }

  if (btnBulkDelete) {
    btnBulkDelete.style.display = count > 0 ? "inline-flex" : "none";
  }

  if (selectAllCb) {
    const totalVisible = document.querySelectorAll(".stats-row-checkbox").length;
    selectAllCb.checked = totalVisible > 0 && count === totalVisible;
  }
}

async function deleteSingleAttendedStat(id) {
  if (!confirm(`¿Estás seguro de eliminar el registro de atención #${id}? Esta acción no se puede deshacer.`)) return;
  try {
    const res = await fetch(`/api/admin/appointments/${id}`, {
      method: "DELETE",
      headers: authHeaders()
    });
    if (res.ok) {
      if (typeof showToast === "function") showToast(`Registro #${id} eliminado del historial`, "success");
      loadAttendedClientsStats();
      if (typeof loadAdminAppointments === "function") loadAdminAppointments();
    } else {
      const err = await res.json();
      alert(err.detail || "Error al eliminar el registro.");
    }
  } catch (e) {
    console.error("Error al eliminar atención:", e);
    alert("Error de conexión al eliminar registro.");
  }
}

async function deleteSelectedAttendedStats() {
  const ids = Array.from(statsState.selectedIds);
  if (ids.length === 0) {
    alert("No seleccionaste ninguna atención para eliminar.");
    return;
  }

  if (!confirm(`⚠️ ATENCIÓN: Estás por eliminar ${ids.length} registro(s) de atenciones del historial.\n\n¿Confirmás la eliminación masiva?`)) return;

  try {
    const res = await fetch("/api/admin/appointments/bulk-delete", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ appointment_ids: ids })
    });

    if (res.ok) {
      const data = await res.json();
      if (typeof showToast === "function") showToast(data.message || `Se eliminaron ${ids.length} registros`, "success");
      statsState.selectedIds.clear();
      loadAttendedClientsStats();
      if (typeof loadAdminAppointments === "function") loadAdminAppointments();
    } else {
      const err = await res.json();
      alert(err.detail || "Error al realizar la eliminación masiva.");
    }
  } catch (e) {
    console.error("Error en eliminación masiva de historial:", e);
    alert("Error de conexión durante la eliminación masiva.");
  }
}

// ==========================================
// MÓDULO DE PURGA Y RESTAURACIÓN DE LA APP
// ==========================================
function openSystemPurgeModal() {
  const modal = document.getElementById("systemPurgeModal");
  if (modal) {
    document.getElementById("chkPurgeAppts").checked = false;
    document.getElementById("chkPurgeClients").checked = false;
    document.getElementById("chkPurgeBarbers").checked = false;
    document.getElementById("chkPurgeMessages").checked = false;
    document.getElementById("chkPurgeImages").checked = false;
    document.getElementById("chkFactoryReset").checked = false;
    document.getElementById("purgeConfirmationInput").value = "";
    modal.style.display = "flex";
  }
}

function closeSystemPurgeModal() {
  const modal = document.getElementById("systemPurgeModal");
  if (modal) modal.style.display = "none";
}

function onFactoryResetToggle(el) {
  const isChecked = el.checked;
  document.getElementById("chkPurgeAppts").checked = isChecked;
  document.getElementById("chkPurgeClients").checked = isChecked;
  document.getElementById("chkPurgeBarbers").checked = isChecked;
  document.getElementById("chkPurgeMessages").checked = isChecked;
  document.getElementById("chkPurgeImages").checked = isChecked;
}

function onPurgeCheckboxChange() {
  const allChecked = 
    document.getElementById("chkPurgeAppts").checked &&
    document.getElementById("chkPurgeClients").checked &&
    document.getElementById("chkPurgeBarbers").checked &&
    document.getElementById("chkPurgeMessages").checked &&
    document.getElementById("chkPurgeImages").checked;

  document.getElementById("chkFactoryReset").checked = allChecked;
}

async function executeSystemPurge() {
  const purgeAppts = document.getElementById("chkPurgeAppts").checked;
  const purgeClients = document.getElementById("chkPurgeClients").checked;
  const purgeBarbers = document.getElementById("chkPurgeBarbers").checked;
  const purgeMessages = document.getElementById("chkPurgeMessages").checked;
  const purgeImages = document.getElementById("chkPurgeImages").checked;
  const factoryReset = document.getElementById("chkFactoryReset").checked;

  if (!purgeAppts && !purgeClients && !purgeBarbers && !purgeMessages && !purgeImages && !factoryReset) {
    alert("Seleccioná al menos una opción de purga o activá la restauración completa.");
    return;
  }

  const confInput = document.getElementById("purgeConfirmationInput").value.trim().toUpperCase();
  if (confInput !== "CONFIRMAR" && confInput !== "RESTAURAR") {
    alert("Para proceder, ingresá la palabra CONFIRMAR o RESTAURAR en el campo de texto.");
    document.getElementById("purgeConfirmationInput").focus();
    return;
  }

  const actionText = factoryReset ? "RESTAURACIÓN COMPLETA A ESTADO DE FÁBRICA" : "PURGA SELECCIONADA DE DATOS";
  if (!confirm(`🚨 ÚLTIMA ADVERTENCIA:\n\nVas a ejecutar una ${actionText}.\nEsta acción NO se puede deshacer.\n\n¿Estás completamente seguro de continuar?`)) return;

  try {
    const btn = document.getElementById("btnExecuteSystemPurge");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Procesando Limpieza...";
    }

    const payload = {
      purge_appointments: purgeAppts,
      purge_clients: purgeClients,
      purge_barbers: purgeBarbers,
      purge_notifications: purgeMessages,
      purge_images: purgeImages,
      factory_reset: factoryReset,
      confirmation: confInput
    };

    const res = await fetch("/api/admin/system/purge", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      closeSystemPurgeModal();
      alert(`✅ ${data.message}\n\nDetalles:\n• ${data.details.join("\n• ")}`);
      
      // Recargar datos globales de la administración
      loadAttendedClientsStats();
      if (typeof loadAdminAppointments === "function") loadAdminAppointments();
      if (typeof loadAdminBarbers === "function") loadAdminBarbers();
      if (typeof loadAdminClients === "function") loadAdminClients();
    } else {
      const err = await res.json();
      alert(err.detail || "Error al ejecutar la purga de datos.");
    }
  } catch (e) {
    console.error("Error en purga del sistema:", e);
    alert("Error de conexión al procesar la purga del sistema.");
  } finally {
    const btn = document.getElementById("btnExecuteSystemPurge");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "🚨 EJECUTAR PURGA / RESTAURAR →";
    }
  }
}

async function reopenAttendedTurn(id) {
  if (!confirm("¿Deseas reabrir este turno para volver a ponerlo en agenda?")) return;
  try {
    const res = await fetch(`/api/admin/appointments/${id}/status`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ status: "CONFIRMADO" })
    });
    if (res.ok) {
      if (typeof showToast === "function") showToast("Turno reabierto con éxito", "success");
      loadAttendedClientsStats();
      if (typeof loadAdminAppointments === "function") loadAdminAppointments();
    } else {
      if (typeof showToast === "function") showToast("Error al reabrir turno", "error");
    }
  } catch (e) {
    console.error("Error al reabrir turno:", e);
  }
}

function setStatsDatePreset(preset) {
  statsState.datePreset = preset;

  document.getElementById("btnStatsPresetToday")?.classList.toggle("active", preset === "today");
  document.getElementById("btnStatsPreset7d")?.classList.toggle("active", preset === "7d");
  document.getElementById("btnStatsPresetMonth")?.classList.toggle("active", preset === "month");
  document.getElementById("btnStatsPresetAll")?.classList.toggle("active", preset === "all");

  const startInput = document.getElementById("statsFilterStart");
  const endInput = document.getElementById("statsFilterEnd");

  const now = new Date();
  const formatD = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };

  if (preset === "today") {
    statsState.startDate = formatD(now);
    statsState.endDate = formatD(now);
  } else if (preset === "7d") {
    const past = new Date();
    past.setDate(past.getDate() - 7);
    statsState.startDate = formatD(past);
    statsState.endDate = formatD(now);
  } else if (preset === "month") {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    statsState.startDate = formatD(firstDay);
    statsState.endDate = formatD(now);
  } else if (preset === "all") {
    statsState.startDate = "";
    statsState.endDate = "";
  }

  if (startInput) startInput.value = statsState.startDate;
  if (endInput) endInput.value = statsState.endDate;

  loadAttendedClientsStats();
}

function onStatsCustomDateChange() {
  const startInput = document.getElementById("statsFilterStart");
  const endInput = document.getElementById("statsFilterEnd");

  if (!startInput || !endInput) return;
  statsState.startDate = startInput.value;
  statsState.endDate = endInput.value;
  statsState.datePreset = "custom";

  document.getElementById("btnStatsPresetToday")?.classList.remove("active");
  document.getElementById("btnStatsPreset7d")?.classList.remove("active");
  document.getElementById("btnStatsPresetMonth")?.classList.remove("active");
  document.getElementById("btnStatsPresetAll")?.classList.remove("active");

  loadAttendedClientsStats();
}

function onStatsBarberChange() {
  const sel = document.getElementById("statsFilterBarber");
  statsState.barberId = sel ? sel.value : "";
  loadAttendedClientsStats();
}

function exportAttendedClientsCSV() {
  const list = statsState.attendedList;
  if (!list || list.length === 0) {
    if (typeof showToast === "function") showToast("No hay registros para exportar", "warning");
    return;
  }

  let csv = "\uFEFF"; // UTF-8 BOM para Excel en español
  csv += "ID;Fecha;Hora;Cliente;Telefono;Barbero;Servicio;Importe;Estado\n";

  list.forEach(a => {
    let dt = a.appointment_time ? a.appointment_time.replace("T", " ") : "";
    let datePart = dt.substring(0, 10);
    let timePart = dt.substring(11, 16);
    let price = parseFloat(a.service_price_snapshot || a.service_price || 0) || 0;

    const row = [
      a.id,
      `"${datePart}"`,
      `"${timePart}"`,
      `"${(a.client_name || '').replace(/"/g, '""')}"`,
      `"${(a.client_phone || '').replace(/"/g, '""')}"`,
      `"${(a.barber_name || '').replace(/"/g, '""')}"`,
      `"${(a.service || '').replace(/"/g, '""')}"`,
      price,
      `"${a.status || 'COMPLETADO'}"`
    ];
    csv += row.join(";") + "\n";
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `reporte_clientes_atendidos_${new Date().toISOString().substring(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  if (typeof showToast === "function") showToast("Planilla CSV descargada con éxito", "success");
}

