/**
 * Admin Panel - Appointments Module
 * HiddenSYNC Barber Ecosystem 2026
 * Manages appointment listing, date presets, barber filters, status transitions, and table rendering.
 */

let apptState = {
  datePreset: "today",
  selectedDate: typeof getLocalDateStr === "function" ? getLocalDateStr(0) : "",
  selectedStatus: "activos",
  selectedBarberId: "",
  allAppointments: []
};

function setApptDatePreset(preset) {
  apptState.datePreset = preset;
  
  document.getElementById("btnDateToday")?.classList.toggle("active", preset === "today");
  document.getElementById("btnDateTomorrow")?.classList.toggle("active", preset === "tomorrow");
  document.getElementById("btnDateAll")?.classList.toggle("active", preset === "all");

  const dateInput = document.getElementById("filterApptDate");
  if (preset === "today") {
    apptState.selectedDate = getLocalDateStr(0);
    if (dateInput) dateInput.value = apptState.selectedDate;
  } else if (preset === "tomorrow") {
    apptState.selectedDate = getLocalDateStr(1);
    if (dateInput) dateInput.value = apptState.selectedDate;
  } else if (preset === "all") {
    apptState.selectedDate = "";
    if (dateInput) dateInput.value = "";
  }

  loadAdminAppointments();
}

function viewAttendedHistorical() {
  apptState.datePreset = "all";
  apptState.selectedDate = "";
  apptState.selectedStatus = "completados";

  document.getElementById("btnDateToday")?.classList.remove("active");
  document.getElementById("btnDateTomorrow")?.classList.remove("active");
  document.getElementById("btnDateAll")?.classList.add("active");

  const dateInput = document.getElementById("filterApptDate");
  if (dateInput) dateInput.value = "";

  document.querySelectorAll(".appt-pill").forEach(pill => {
    pill.classList.toggle("active", pill.getAttribute("data-status") === "completados");
  });

  loadAdminAppointments();
}

function clickKpiCompletados() {
  const compCount = apptState.allAppointments.filter(a => 
    ["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes((a.status || "").toUpperCase())
  ).length;

  if (compCount > 0 || apptState.datePreset === "all") {
    setApptFilterStatus("completados");
  } else {
    // Si no hay completados hoy, llevar directamente al histórico de clientes atendidos
    viewAttendedHistorical();
    if (typeof showToast === "function") {
      showToast("Mostrando todos los clientes atendidos del historial", "info");
    }
  }
}

function onCustomDateChange() {
  const dateInput = document.getElementById("filterApptDate");
  if (!dateInput) return;
  apptState.selectedDate = dateInput.value;
  apptState.datePreset = "custom";

  document.getElementById("btnDateToday")?.classList.remove("active");
  document.getElementById("btnDateTomorrow")?.classList.remove("active");
  document.getElementById("btnDateAll")?.classList.remove("active");

  loadAdminAppointments();
}

function onApptBarberChange() {
  const barberSel = document.getElementById("filterApptBarber");
  apptState.selectedBarberId = barberSel ? barberSel.value : "";
  loadAdminAppointments();
}

function setApptFilterStatus(statusKey) {
  apptState.selectedStatus = statusKey;

  document.querySelectorAll(".appt-pill").forEach(pill => {
    const isAct = pill.getAttribute("data-status") === statusKey;
    pill.classList.toggle("active", isAct);
  });

  renderFilteredAppointmentsTable();
}

async function populateApptBarberOptions() {
  const select = document.getElementById("filterApptBarber");
  if (!select || select.options.length > 1) return;
  try {
    const res = await fetch("/api/admin/barbers", { headers: authHeaders() });
    if (res.ok) {
      const barbers = await res.json();
      barbers.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b.id;
        opt.textContent = `Barbero: ${b.name}`;
        select.appendChild(opt);
      });
    }
  } catch (_) {}
}

async function loadAdminAppointments() {
  const dateInput = document.getElementById("filterApptDate");
  if (dateInput && !dateInput.value && apptState.datePreset === "today") {
    dateInput.value = apptState.selectedDate;
  }

  await populateApptBarberOptions();

  let url = "/api/admin/appointments?";
  if (apptState.selectedDate) url += `date=${apptState.selectedDate}&`;
  if (apptState.selectedBarberId) url += `barber_id=${apptState.selectedBarberId}&`;

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const appts = await res.json();

    apptState.allAppointments = appts || [];

    // Calcular KPIs normalizados
    const activos = apptState.allAppointments.filter(a => 
      ["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"].includes((a.status || "").toUpperCase()) && !a.canceled
    );
    const completados = apptState.allAppointments.filter(a => 
      ["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes((a.status || "").toUpperCase())
    );
    const pendientes = apptState.allAppointments.filter(a => (a.status || "").toUpperCase() === "PENDIENTE" && !a.canceled);
    const confirmados = apptState.allAppointments.filter(a => (a.status || "").toUpperCase() === "CONFIRMADO" && !a.canceled);
    const cancelados = apptState.allAppointments.filter(a => ["CANCELADO", "NO_SHOW"].includes((a.status || "").toUpperCase()) || a.canceled);
    const enSala = apptState.allAppointments.filter(a => 
      a.is_checked_in && ["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"].includes((a.status || "").toUpperCase()) && !a.canceled
    );

    // Actualizar contadores KPI Cards
    const kpiAct = document.getElementById("kpiApptActivos");
    if (kpiAct) kpiAct.textContent = activos.length;
    const kpiComp = document.getElementById("kpiApptCompletados");
    if (kpiComp) kpiComp.textContent = completados.length;
    const kpiPend = document.getElementById("kpiApptPendientes");
    if (kpiPend) kpiPend.textContent = pendientes.length;
    const kpiCanc = document.getElementById("kpiApptCancelados");
    if (kpiCanc) kpiCanc.textContent = cancelados.length;

    // Actualizar contadores de las píldoras
    const pAct = document.getElementById("pillCountActivos");
    if (pAct) pAct.textContent = activos.length;
    const pSala = document.getElementById("pillCountEnSala");
    if (pSala) pSala.textContent = enSala.length;
    const pComp = document.getElementById("pillCountCompletados");
    if (pComp) pComp.textContent = completados.length;
    const pPend = document.getElementById("pillCountPendientes");
    if (pPend) pPend.textContent = pendientes.length;
    const pConf = document.getElementById("pillCountConfirmados");
    if (pConf) pConf.textContent = confirmados.length;
    const pCanc = document.getElementById("pillCountCancelados");
    if (pCanc) pCanc.textContent = cancelados.length;
    const pAll = document.getElementById("pillCountTodos");
    if (pAll) pAll.textContent = apptState.allAppointments.length;

    renderFilteredAppointmentsTable();

  } catch (e) {
    console.error("Error cargando turnos:", e);
    if (typeof showToast === "function") showToast("Error al cargar listado de turnos", "error");
  }
}

function renderFilteredAppointmentsTable() {
  const tbody = document.getElementById("appointmentsTableBody");
  const emptyState = document.getElementById("apptEmptyState");
  const table = tbody?.closest("table");
  if (!tbody) return;

  const searchInput = document.getElementById("searchApptClient");
  const term = (searchInput ? searchInput.value : "").trim().toLowerCase();

  let list = apptState.allAppointments;

  // Filtro por estado normalizado
  const st = apptState.selectedStatus;
  if (st === "activos") {
    list = list.filter(a => ["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"].includes((a.status || "").toUpperCase()) && !a.canceled);
  } else if (st === "en_sala") {
    list = list.filter(a => a.is_checked_in && ["PENDIENTE", "CONFIRMADO", "EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"].includes((a.status || "").toUpperCase()) && !a.canceled);
  } else if (st === "completados") {
    list = list.filter(a => ["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes((a.status || "").toUpperCase()));
  } else if (st === "cancelados") {
    list = list.filter(a => ["CANCELADO", "NO_SHOW"].includes((a.status || "").toUpperCase()) || a.canceled);
  } else if (st === "PENDIENTE") {
    list = list.filter(a => (a.status || "").toUpperCase() === "PENDIENTE" && !a.canceled);
  } else if (st === "CONFIRMADO") {
    list = list.filter(a => (a.status || "").toUpperCase() === "CONFIRMADO" && !a.canceled);
  }

  // Filtro por texto de búsqueda
  if (term) {
    list = list.filter(a => 
      (a.client_name || "").toLowerCase().includes(term) ||
      (a.client_phone || "").toLowerCase().includes(term) ||
      (a.barber_name || "").toLowerCase().includes(term) ||
      (a.service || "").toLowerCase().includes(term) ||
      String(a.id).includes(term) ||
      (a.checkin_token && String(a.checkin_token).includes(term))
    );
  }

  tbody.innerHTML = "";

  if (list.length === 0) {
    if (table) table.style.display = "none";
    if (emptyState) {
      emptyState.style.display = "block";
      const title = document.getElementById("emptyStateTitle");
      const desc = document.getElementById("emptyStateDesc");
      const actions = document.getElementById("emptyStateActions");
      
      const compCount = apptState.allAppointments.filter(a => ["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes((a.status || "").toUpperCase())).length;
      
      if (st === "activos") {
        if (title) title.textContent = "¡Bandeja activa al día! 🎉";
        if (desc) desc.textContent = "No hay turnos pendientes para la fecha seleccionada. Podés consultar los clientes atendidos o ver el histórico general.";
        if (actions) {
          actions.innerHTML = `
            <button type="button" class="btn-admin btn-admin-sm" onclick="setApptFilterStatus('completados')" style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; font-weight: bold;">
              ✅ Ver Atendidos (${compCount})
            </button>
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="viewAttendedHistorical()">
              📜 Ver Histórico de Atendidos
            </button>
          `;
        }
      } else if (st === "en_sala") {
        if (title) title.textContent = "Nadie esperando en sala actualmente";
        if (desc) desc.textContent = "Los clientes que hagan Check-In en el Totem o anuncien su llegada con su PIN o celular aparecerán aquí.";
        if (actions) {
          actions.innerHTML = `
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="setApptFilterStatus('activos')">
              ⚡ Ver Turnos Por Atender
            </button>
          `;
        }
      } else if (st === "completados") {
        if (title) title.textContent = "Sin clientes atendidos para esta fecha";
        if (desc) desc.textContent = "No hay turnos completados en la fecha seleccionada. Hacé click abajo para ver todos los clientes atendidos del historial completo.";
        if (actions) {
          actions.innerHTML = `
            <button type="button" class="btn-admin btn-admin-sm" onclick="viewAttendedHistorical()" style="background: #10b981; color: #000; font-weight: 800; padding: 8px 16px;">
              📜 Ver Clientes Atendidos en Histórico
            </button>
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="setApptFilterStatus('todos')">
              📋 Ver Todos los Turnos
            </button>
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="setApptDatePreset('today'); setApptFilterStatus('activos');">
              ⚡ Volver a Turnos de Hoy
            </button>
          `;
        }
      } else {
        if (title) title.textContent = "Sin resultados";
        if (desc) desc.textContent = "No se encontraron turnos con el filtro seleccionado.";
        if (actions) {
          actions.innerHTML = `
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="viewAttendedHistorical()">
              📜 Ver Historial Completo
            </button>
            <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="setApptDatePreset('today'); setApptFilterStatus('activos');">
              ⚡ Volver a Turnos de Hoy
            </button>
          `;
        }
      }
    }
    return;
  }

  if (table) table.style.display = "table";
  if (emptyState) emptyState.style.display = "none";

  list.forEach(a => {
    const tr = document.createElement("tr");
    
    // Formato de hora limpia
    const timeStr = a.appointment_time ? a.appointment_time.replace("T", " ").substring(11, 16) : "--:--";
    const dateStr = a.appointment_time ? a.appointment_time.substring(0, 10) : "";
    const cleanPhone = (a.client_phone || "").replace(/\D/g, "");
    const waText = encodeURIComponent(`¡Hola ${a.client_name}! Te saludamos de la Barbería por tu turno programado a las ${timeStr} hs.`);

    // Clase CSS del estado
    const statusClass = (a.status || "pendiente").toLowerCase();

    // Generar botones contextuales según el estado
    let actionButtonsHtml = "";

    const upperStatus = (a.status || "").toUpperCase();

    const checkinBtn = (!a.is_checked_in && ["PENDIENTE", "CONFIRMADO"].includes(upperStatus)) ? `
      <button type="button" class="btn-admin btn-admin-sm" onclick="manualAdminCheckin(${a.id})" style="background: rgba(0, 242, 254, 0.12); border: 1px solid rgba(0, 242, 254, 0.35); color: #00f2fe;" title="Marcar llegada del cliente a sala de espera (Check-in)">
        📍 Llegó
      </button>
    ` : '';

    if (upperStatus === "PENDIENTE") {
      actionButtonsHtml = `
        <div style="display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap;">
          ${checkinBtn}
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'CONFIRMADO')" style="background: rgba(0, 242, 254, 0.15); border: 1px solid rgba(0, 242, 254, 0.4); color: #00f2fe;" title="Confirmar turno">
            ✅ Confirmar
          </button>
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'EN_SILLA')" style="background: rgba(212, 255, 0, 0.15); border: 1px solid rgba(212, 255, 0, 0.4); color: #d4ff00;" title="Iniciar atención en sillón">
            💈 En Silla
          </button>
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'COMPLETADO')" style="background: #10b981; color: #000; font-weight: 800;" title="Marcar como atendido y archivar">
            🏁 Completar
          </button>
          <button type="button" class="btn-admin btn-admin-sm btn-admin-danger" onclick="changeApptStatus(${a.id}, 'CANCELADO')" title="Cancelar turno">
            ✕
          </button>
        </div>
      `;
    } else if (upperStatus === "CONFIRMADO") {
      actionButtonsHtml = `
        <div style="display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap;">
          ${checkinBtn}
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'EN_SILLA')" style="background: rgba(212, 255, 0, 0.15); border: 1px solid rgba(212, 255, 0, 0.4); color: #d4ff00;" title="Pasar al sillón de atención">
            💈 En Silla
          </button>
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'COMPLETADO')" style="background: #10b981; color: #000; font-weight: 800;" title="Marcar como atendido y archivar">
            🏁 Completar
          </button>
          <button type="button" class="btn-admin btn-admin-sm btn-admin-danger" onclick="changeApptStatus(${a.id}, 'CANCELADO')" title="Cancelar turno">
            ✕
          </button>
        </div>
      `;
    } else if (["EN_SILLA", "EN_ATENCION", "ATENDIENDO", "LLAMANDO"].includes(upperStatus)) {
      actionButtonsHtml = `
        <div style="display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap;">
          <button type="button" class="btn-admin btn-admin-sm" onclick="finishAndCallNextAppt(${a.id}, ${a.barber_id || 'null'})" style="background: #d4ff00; color: #000; font-weight: 900; padding: 6px 14px; box-shadow: 0 0 12px rgba(212, 255, 0, 0.4);" title="Finalizar corte actual y llamar inmediatamente al próximo en cola">
            ⚡ Finalizar y Llamar Próximo
          </button>
          <button type="button" class="btn-admin btn-admin-sm" onclick="changeApptStatus(${a.id}, 'COMPLETADO')" style="background: #10b981; color: #000; font-weight: 800; padding: 6px 12px;" title="Solo finalizar este corte">
            🏁 Solo Finalizar
          </button>
          <button type="button" class="btn-admin btn-admin-sm btn-admin-danger" onclick="changeApptStatus(${a.id}, 'CANCELADO')" title="Cancelar">
            ✕
          </button>
        </div>
      `;
    } else if (["COMPLETADO", "ATENDIDO", "FINALIZADO"].includes(upperStatus)) {
      actionButtonsHtml = `
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
          <span style="font-size: 0.75rem; color: #10b981; font-weight: 700; font-family: monospace;">✅ Atendido</span>
          ${a.checkout_data ? `
            <button type="button" class="btn-admin btn-admin-sm" onclick="viewVirtualTicketFromAdmin(${a.id})" style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; font-size: 0.7rem; padding: 3px 8px;" title="Ver ticket virtual y comprobante">
              🧾 Ticket
            </button>
          ` : ''}
          <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="changeApptStatus(${a.id}, 'CONFIRMADO')" title="Reabrir turno si fue completado por error" style="font-size: 0.7rem; padding: 3px 8px;">
            ↩️ Reabrir
          </button>
        </div>
      `;
    } else if (["CANCELADO", "NO_SHOW"].includes(upperStatus)) {
      actionButtonsHtml = `
        <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center;">
          <span style="font-size: 0.75rem; color: #ef4444; font-weight: 700; font-family: monospace;">❌ Cancelado</span>
          <button type="button" class="btn-admin btn-admin-sm btn-admin-secondary" onclick="changeApptStatus(${a.id}, 'PENDIENTE')" title="Reactivar turno" style="font-size: 0.7rem; padding: 3px 8px;">
            ↩️ Reactivar
          </button>
        </div>
      `;
    }

    const checkinTimeFormatted = a.checked_in_at ? (a.checked_in_at.includes("T") ? a.checked_in_at.split("T")[1].substring(0, 5) : a.checked_in_at.substring(11, 16)) : "";

    tr.innerHTML = `
      <td>
        <div style="display: flex; flex-direction: column;">
          <span style="font-family: monospace; font-weight: 800; font-size: 0.95rem; color: #d4ff00;">${timeStr} hs</span>
          ${apptState.datePreset === 'all' ? `<span style="font-size: 0.7rem; color: #9ca3af;">${dateStr}</span>` : ''}
        </div>
      </td>
      <td>
        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
          <strong style="color: #ffffff; font-size: 0.9rem;">${escapeHtml(a.client_name)}</strong>
          ${a.is_checked_in ? `
            <span style="background: rgba(0, 242, 254, 0.15); border: 1px solid #00f2fe; color: #00f2fe; font-size: 0.68rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3);" title="Cliente anunció su llegada al local">
              📍 EN SALA ${checkinTimeFormatted ? '(' + checkinTimeFormatted + ')' : ''}
            </span>
          ` : ''}
        </div>
        <div style="font-size: 0.72rem; color: #64748b; display: flex; gap: 8px; margin-top: 2px; align-items: center;">
          <span>#ID: ${a.id}</span>
          ${a.checkin_token ? `<span style="color: #38bdf8; font-family: monospace; font-weight: bold; background: rgba(56, 189, 248, 0.1); padding: 1px 5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.25);">🔑 PIN: ${a.checkin_token}</span>` : ''}
        </div>
      </td>
      <td>
        ${cleanPhone ? `
          <button class="btn-admin btn-admin-sm" onclick="openClientWhatsappModal('${escapeHtml(a.client_name)}', '${escapeHtml(a.client_phone)}', '${timeStr} hs (${dateStr})', '${escapeHtml(a.barber_name || 'tu barbero')}')" style="background: rgba(37, 211, 102, 0.12); color: #25D366; border: 1px solid rgba(37, 211, 102, 0.3); font-size: 0.75rem; font-family: monospace; cursor: pointer;" title="Abrir Centro de Comunicación WhatsApp">
            💬 ${escapeHtml(a.client_phone)}
          </button>
        ` : `<span style="color: #64748b;">-</span>`}
      </td>
      <td>
        <span style="display: inline-block; padding: 2px 8px; border-radius: 6px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.75rem; font-weight: 600; color: #e5e7eb;">
          💈 ${escapeHtml(a.barber_name || 'Sin asignar')}
        </span>
      </td>
      <td>
        <span style="font-size: 0.8rem; color: #e5e7eb;">${escapeHtml(a.service || 'Servicio de Barbería')}</span>
        ${a.duration_min ? `<span style="font-size: 0.7rem; color: #64748b; margin-left: 4px;">(${a.duration_min}m)</span>` : ''}
      </td>
      <td>
        <span class="badge badge-${statusClass}">
          ${escapeHtml(a.status)}
        </span>
      </td>
      <td style="text-align: right;">
        ${actionButtonsHtml}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function finishAndCallNextAppt(appointmentId, barberId) {
  try {
    const res = await fetch("/api/live-agenda/finish-and-next", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ appointment_id: appointmentId, barber_id: barberId })
    });
    if (res.ok) {
      const data = await res.json();
      if (typeof showToast === "function") {
        showToast(data.message || "Corte finalizado y próximo cliente llamado al sillón.", "success");
      } else {
        alert(data.message);
      }

      if (data.speech_text && 'speechSynthesis' in window) {
        try {
          const synth = window.speechSynthesis;
          synth.cancel();
          const utterance = new SpeechSynthesisUtterance(data.speech_text);
          utterance.lang = 'es-AR';
          utterance.rate = 0.95;
          synth.speak(utterance);
        } catch (_) {}
      }

      if (typeof loadAdminAppointments === "function") loadAdminAppointments();
      if (typeof loadLiveTurnosData === "function") loadLiveTurnosData();
    } else {
      const err = await res.json();
      if (typeof showToast === "function") showToast(err.detail || "Error al realizar el cierre de corte.", "error");
      else alert(err.detail || "Error al realizar el cierre de corte.");
    }
  } catch (e) {
    if (typeof showToast === "function") showToast("Error de conexión al procesar el cierre.", "error");
    else alert("Error de conexión al procesar el cierre.");
  }
}

async function manualAdminCheckin(id) {
  try {
    const res = await fetch("/api/public/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: String(id) })
    });
    if (res.ok) {
      const data = await res.json();
      if (typeof showToast === "function") {
        showToast(`📍 ${data.client_name} anunciado en sala de espera.`, "success");
      }
      loadAdminAppointments();
    } else {
      const err = await res.json();
      if (typeof showToast === "function") showToast(err.detail || "Error al registrar llegada.", "error");
    }
  } catch (e) {
    if (typeof showToast === "function") showToast("Error de conexión al registrar llegada.", "error");
  }
}

async function changeApptStatus(id, newStatus) {

  if (newStatus === "CANCELADO") {
    const ok = confirm(`¿Estás seguro de cancelar el Turno #${id}?\nEl horario quedará liberado en la agenda.`);
    if (!ok) return;
  }

  try {
    const res = await fetch(`/api/admin/appointments/${id}/status`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ status: newStatus })
    });

    if (res.ok) {
      if (typeof showToast === "function") {
        if (newStatus === "COMPLETADO") {
          showToast(`Turno #${id} completado. La vista activa queda limpia.`, "success");
        } else if (newStatus === "CONFIRMADO") {
          showToast(`Turno #${id} confirmado exitosamente.`, "success");
        } else if (newStatus === "EN_SILLA") {
          showToast(`Turno #${id} en atención en sillón.`, "success");
        } else if (newStatus === "CANCELADO") {
          showToast(`Turno #${id} cancelado y liberado.`, "warning");
        } else {
          showToast(`Turno #${id} actualizado a ${newStatus}.`, "success");
        }
      }
      loadAdminAppointments();
    } else {
      const err = await res.json();
      if (typeof showToast === "function") showToast(err.detail || "Error al actualizar estado del turno.", "error");
    }
  } catch (e) {
    if (typeof showToast === "function") showToast("Error de conexión al actualizar turno.", "error");
  }
}

async function viewVirtualTicketFromAdmin(id) {
  try {
    const res = await fetch(`/api/admin/appointments/${id}/checkout-prep`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    if (data.appointment && data.appointment.checkout_data) {
      const ticket = data.appointment.checkout_data;
      const cleanPhone = (ticket.client_phone || "").replace(/\D/g, "");
      const waText = encodeURIComponent(`✂️ Ticket Virtual Barbería\nCliente: ${ticket.client_name}\nTotal: $${ticket.total}\n¡Gracias por tu visita!`);
      const waUrl = cleanPhone ? `https://wa.me/${cleanPhone}?text=${waText}` : null;
      
      const modal = document.createElement("div");
      modal.className = "modal-overlay";
      modal.style.cssText = "display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 99999; justify-content: center; align-items: center; padding: 16px;";
      modal.innerHTML = `
        <div style="background: #111116; border: 1px solid #23232c; border-radius: 20px; width: 100%; max-width: 460px; padding: 24px; color: #fff; font-family: monospace;">
          <div style="text-align: center; border-bottom: 1px dashed #444; padding-bottom: 12px; margin-bottom: 12px;">
            <div style="font-size: 1.8rem;">💈</div>
            <h3 style="color: #d4ff00; margin: 0;">PEREYRAS BARBERS</h3>
            <div style="font-size: 0.75rem; color: #9ca3af;">TICKET VIRTUAL #${ticket.appointment_id} - ${ticket.checkout_at || ''}</div>
          </div>
          <div style="font-size: 0.82rem; line-height: 1.6; margin-bottom: 10px;">
            <div>👤 Cliente: <strong>${ticket.client_name}</strong></div>
            <div>💈 Barbero: <strong>${ticket.barber_name}</strong></div>
            <div>💳 Pago: <strong>${(ticket.payment_method || 'efectivo').toUpperCase()}</strong></div>
          </div>
          <div style="border-top: 1px dashed #444; padding: 8px 0;">
            <div style="display:flex; justify-content:space-between; font-weight:bold;">
              <span>${ticket.service_name}</span>
              <span style="color:#00f2fe;">$${(ticket.service_price || 0).toLocaleString("es-AR")}</span>
            </div>
            ${(ticket.products || []).map(p => `
              <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#cbd5e1;">
                <span>${p.quantity}x ${p.name}</span>
                <span>$${(p.subtotal || 0).toLocaleString("es-AR")}</span>
              </div>
            `).join("")}
          </div>
          <div style="border-top: 1px dashed #444; padding-top: 8px; margin-top: 8px;">
            <div style="display:flex; justify-content:space-between; font-size:1.15rem; font-weight:900;">
              <span>TOTAL:</span>
              <span style="color:#d4ff00;">$${(ticket.total || 0).toLocaleString("es-AR")}</span>
            </div>
          </div>
          ${ticket.promo_code ? `
            <div style="background:rgba(212,255,0,0.1); border:1px solid rgba(212,255,0,0.3); border-radius:6px; padding:8px; margin-top:10px; text-align:center; font-size:0.78rem; color:#d4ff00;">
              🎁 Cupón próximo corte: <strong>${ticket.promo_code}</strong> (${ticket.promo_percent || 15}% OFF)
            </div>
          ` : ''}
          <div style="display:flex; flex-direction:column; gap:8px; margin-top:16px;">
            ${waUrl ? `
              <a href="${waUrl}" target="_blank" onclick="this.closest('.modal-overlay').remove();" class="btn-admin" style="background:#25D366; color:#000; font-weight:bold; text-align:center; text-decoration:none; padding:10px;">
                💬 Enviar por WhatsApp
              </a>
            ` : ''}
            <button type="button" onclick="this.closest('.modal-overlay').remove();" class="btn-admin btn-admin-secondary" style="padding:8px;">
              Cerrar
            </button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }
  } catch (e) {
    console.error("Error al visualizar ticket:", e);
  }
}
