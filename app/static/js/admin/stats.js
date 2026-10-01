/**
 * Admin Panel - Attended Clients & Performance Stats Module
 * HiddenSYNC Barber Ecosystem 2026
 * Dedicated analytics, historical attended clients tracking, revenue calculation & CSV export.
 */

let statsState = {
  datePreset: "all",
  startDate: "",
  endDate: "",
  barberId: "",
  attendedList: [],
  barbers: []
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

    tr.innerHTML = `
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
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
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
