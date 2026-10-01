/**
 * Admin Panel - Clients Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles client directory, CRM profile cards, WhatsApp Communication Center & templates.
 */

let allAdminClients = [];
let currentWaClient = { name: "", phone: "", rawPhone: "" };

async function loadAdminClients() {
  try {
    const res = await fetch("/api/admin/clients", { headers: authHeaders() });
    if (!res.ok) return;
    allAdminClients = await res.json();
    renderClientsTable(allAdminClients);
  } catch (e) {
    console.error("Error al cargar clientes:", e);
  }
}

function renderClientsTable(clientsList) {
  const tbody = document.getElementById("clientsTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!clientsList || clientsList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #9ca3af; padding: 24px; font-family: monospace;">No se encontraron clientes registrados.</td></tr>`;
    return;
  }

  clientsList.forEach(c => {
    const tr = document.createElement("tr");
    const cleanPhone = (c.phone || "").replace(/\D/g, "");
    
    tr.innerHTML = `
      <td>#${c.id}</td>
      <td><strong>${escapeHtml(c.name)}</strong></td>
      <td>
        <a href="https://wa.me/${cleanPhone}" target="_blank" style="color: #25D366; font-family: monospace; font-weight: bold; text-decoration: none;" title="Chat directo en WhatsApp">
          📱 ${escapeHtml(c.phone)}
        </a>
      </td>
      <td>
        <span style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; background: ${c.turnos_completados > 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(156, 163, 175, 0.15)'}; color: ${c.turnos_completados > 0 ? '#10b981' : '#9ca3af'}; border: 1px solid ${c.turnos_completados > 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(156, 163, 175, 0.3)'};">
          ✂️ ${c.turnos_completados || 0} cortes
        </span>
      </td>
      <td>
        <span style="font-family: monospace; font-size: 0.8rem; color: ${c.ultima_visita ? '#00f2fe' : '#6b7280'};">
          ${c.ultima_visita ? `📅 ${c.ultima_visita}` : 'Sin visitas'}
        </span>
      </td>
      <td style="text-align: right;">
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
          <button class="btn-admin btn-admin-sm" onclick="openClientWhatsappModal('${escapeHtml(c.name)}', '${escapeHtml(c.phone)}')" style="background: #25D366; color: #000; font-weight: 800; border: none; box-shadow: 0 2px 8px rgba(37, 211, 102, 0.35);" title="Abrir Centro de Comunicación WhatsApp">
            💬 WhatsApp
          </button>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openClientProfileModal(${c.id})" title="Ver Ficha e Historial CRM">
            👁️ Ficha CRM
          </button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteClient(${c.id}, '${escapeHtml(c.name)}')" title="Eliminar Cliente">
            🗑️
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterClientDirectory() {
  const q = (document.getElementById("searchClientDirectoryInput")?.value || "").toLowerCase().trim();
  if (!q) {
    renderClientsTable(allAdminClients);
    return;
  }
  const filtered = allAdminClients.filter(c => 
    (c.name && c.name.toLowerCase().includes(q)) || 
    (c.phone && c.phone.toLowerCase().includes(q)) ||
    (c.email && c.email.toLowerCase().includes(q))
  );
  renderClientsTable(filtered);
}

// ============================================================
// CENTRO DE COMUNICACIÓN WHATSAPP INTELIGENTE
// ============================================================

function ensureClientWhatsappModalExists() {
  if (document.getElementById("clientWhatsappModal")) return;

  const modalDiv = document.createElement("div");
  modalDiv.id = "clientWhatsappModal";
  modalDiv.className = "modal-overlay";
  modalDiv.style.cssText = "display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(8px); z-index: 99999; justify-content: center; align-items: center; padding: 16px;";

  modalDiv.innerHTML = `
    <div class="modal-content" style="background: #111116; border: 1px solid #23232c; border-radius: 16px; width: 100%; max-width: 650px; padding: 24px; color: #fff; box-shadow: 0 20px 50px rgba(0,0,0,0.8); font-family: 'Inter', sans-serif;">
      <!-- HEADER -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #23232c; padding-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 38px; height: 38px; border-radius: 10px; background: rgba(37, 211, 102, 0.15); border: 1px solid rgba(37, 211, 102, 0.4); display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
            💬
          </div>
          <div>
            <h3 style="margin: 0; font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; color: #fff; font-weight: 700;">Centro de Comunicación WhatsApp</h3>
            <p style="margin: 2px 0 0 0; color: #9ca3af; font-size: 0.8rem;">Opciones pre-redactadas e inteligentes para atención al cliente</p>
          </div>
        </div>
        <button onclick="closeClientWhatsappModal()" style="background: transparent; border: none; color: #9ca3af; font-size: 1.4rem; cursor: pointer; padding: 4px 8px; border-radius: 6px;">✕</button>
      </div>

      <!-- CLIENT INFO BADGE -->
      <div style="background: #09090c; border: 1px solid #1a1a22; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
          <span style="color: #9ca3af; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; font-family: monospace;">DESTINATARIO:</span>
          <strong id="waClientName" style="color: #d4ff00; font-size: 1rem; font-family: 'Space Grotesk', sans-serif;">Cliente</strong>
        </div>
        <div style="text-align: right;">
          <span style="color: #9ca3af; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; display: block; font-family: monospace;">TELÉFONO:</span>
          <span id="waClientPhone" style="color: #25D366; font-family: monospace; font-weight: bold; font-size: 0.95rem;">-</span>
        </div>
      </div>

      <!-- TEMPLATE SELECTOR & QUICK BUTTONS -->
      <div style="margin-bottom: 16px;">
        <label style="color: #cbd5e1; font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 8px; font-family: 'Space Grotesk', monospace;">
          SELECCIONAR PLANTILLA PRE-REDACTADA:
        </label>
        <select id="waTemplateSelect" onchange="applyWaTemplate()" style="width: 100%; padding: 10px 14px; background: #09090c; border: 1px solid #23232c; border-radius: 10px; color: #fff; font-size: 0.9rem; outline: none; margin-bottom: 10px;">
          <option value="recordatorio">📅 Recordatorio de Turno</option>
          <option value="demora">⏳ Aviso de Demora Estimada</option>
          <option value="ausente_barbero">⚠️ Barbero No Disponible / Reasignar</option>
          <option value="reprogramar">🔄 Coordinar Cambio / Reprogramación</option>
          <option value="disponibles">📋 Horarios Disponibles</option>
          <option value="voucher">🎁 Enviar Voucher Promo</option>
          <option value="personalizado">✍️ Mensaje Personalizado / Libre</option>
        </select>

        <!-- CHIPS RAPIDOS -->
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          <button type="button" class="wa-preset-chip" onclick="selectWaTemplatePreset('recordatorio')" style="padding: 5px 10px; background: rgba(255,255,255,0.05); border: 1px solid #23232c; border-radius: 20px; color: #cbd5e1; font-size: 0.75rem; cursor: pointer;">📅 Recordatorio</button>
          <button type="button" class="wa-preset-chip" onclick="selectWaTemplatePreset('demora')" style="padding: 5px 10px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 20px; color: #f59e0b; font-size: 0.75rem; cursor: pointer;">⏳ Aviso Demora</button>
          <button type="button" class="wa-preset-chip" onclick="selectWaTemplatePreset('ausente_barbero')" style="padding: 5px 10px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 20px; color: #ef4444; font-size: 0.75rem; cursor: pointer;">⚠️ Reasignar Barbero</button>
          <button type="button" class="wa-preset-chip" onclick="selectWaTemplatePreset('reprogramar')" style="padding: 5px 10px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 20px; color: #60a5fa; font-size: 0.75rem; cursor: pointer;">🔄 Reprogramar</button>
          <button type="button" class="wa-preset-chip" onclick="selectWaTemplatePreset('personalizado')" style="padding: 5px 10px; background: rgba(212, 255, 0, 0.1); border: 1px solid rgba(212, 255, 0, 0.3); border-radius: 20px; color: #d4ff00; font-size: 0.75rem; cursor: pointer;">✍️ Mensaje Libre</button>
        </div>
      </div>

      <!-- VARIABLES FORM -->
      <div id="waVariablesBox" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-bottom: 16px; background: #09090c; padding: 12px; border-radius: 10px; border: 1px solid #1a1a22;">
        <div>
          <label style="font-size: 0.72rem; color: #9ca3af; display: block; margin-bottom: 4px; font-family: monospace;" id="lblWaVarTime">FECHA / HORA:</label>
          <input type="text" id="waVarTime" oninput="buildWaDraftText()" value="Hoy 17:00 hs" style="width: 100%; padding: 8px 10px; background: #111116; border: 1px solid #23232c; border-radius: 6px; color: #fff; font-size: 0.85rem; box-sizing: border-box;">
        </div>
        <div>
          <label style="font-size: 0.72rem; color: #9ca3af; display: block; margin-bottom: 4px; font-family: monospace;" id="lblWaVarBarber">BARBERO:</label>
          <input type="text" id="waVarBarber" oninput="buildWaDraftText()" value="tu barbero" style="width: 100%; padding: 8px 10px; background: #111116; border: 1px solid #23232c; border-radius: 6px; color: #fff; font-size: 0.85rem; box-sizing: border-box;">
        </div>
        <div>
          <label style="font-size: 0.72rem; color: #9ca3af; display: block; margin-bottom: 4px; font-family: monospace;" id="lblWaVarDetail">DEMORA / OPCIONAL:</label>
          <input type="text" id="waVarDetail" oninput="buildWaDraftText()" value="15-20 min" style="width: 100%; padding: 8px 10px; background: #111116; border: 1px solid #23232c; border-radius: 6px; color: #fff; font-size: 0.85rem; box-sizing: border-box;">
        </div>
      </div>

      <!-- FINAL EDITABLE DRAFT -->
      <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <label style="color: #cbd5e1; font-size: 0.8rem; font-weight: 600; font-family: 'Space Grotesk', monospace;">
            VISTA DEL MENSAJE COMPLETO REDACTADO (EDITABLE):
          </label>
          <span style="font-size: 0.7rem; color: #9ca3af;">Ajustá libremente el texto antes de enviar</span>
        </div>
        <textarea id="waFinalMessageText" oninput="updateWaHrefFromTextarea()" rows="5" style="width: 100%; padding: 12px; background: #09090c; border: 1px solid #23232c; border-radius: 10px; color: #fff; font-size: 0.88rem; line-height: 1.5; outline: none; resize: vertical; box-sizing: border-box; font-family: sans-serif;"></textarea>
      </div>

      <!-- FOOTER ACTIONS -->
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;">
        <button type="button" onclick="copyWaTextToClipboard()" style="padding: 10px 16px; background: #1f1f28; color: #cbd5e1; border: 1px solid #323242; border-radius: 10px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 0.88rem;">
          📋 Copiar Texto
        </button>
        <div style="display: flex; gap: 10px; align-items: center;">
          <button type="button" onclick="closeClientWhatsappModal()" style="padding: 10px 16px; background: transparent; color: #9ca3af; border: 1px solid #23232c; border-radius: 10px; cursor: pointer; font-size: 0.88rem;">
            Cancelar
          </button>
          <a id="btnSendWhatsappDirect" href="#" target="_blank" onclick="trackWaSend()" style="padding: 10px 20px; background: #25D366; color: #000; font-weight: 800; border-radius: 10px; text-decoration: none; display: flex; align-items: center; gap: 8px; font-size: 0.95rem; border: none; box-shadow: 0 4px 14px rgba(37, 211, 102, 0.4);">
            📲 ABRIR EN WHATSAPP Y ENVIAR MENSAJE →
          </a>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modalDiv);
}

function selectWaTemplatePreset(presetName) {
  ensureClientWhatsappModalExists();
  const select = document.getElementById("waTemplateSelect");
  if (select) {
    select.value = presetName;
    applyWaTemplate();
  }
}

function openClientWhatsappModal(clientName, clientPhone, defaultTime = "Hoy 17:00 hs", defaultBarber = "tu barbero") {
  ensureClientWhatsappModalExists();
  const modal = document.getElementById("clientWhatsappModal");
  if (!modal) return;

  const cleanPhone = (clientPhone || "").replace(/\D/g, "");
  currentWaClient = {
    name: clientName,
    phone: clientPhone,
    rawPhone: cleanPhone
  };

  const nameEl = document.getElementById("waClientName");
  const phoneEl = document.getElementById("waClientPhone");
  if (nameEl) nameEl.textContent = clientName || "Cliente";
  if (phoneEl) phoneEl.textContent = clientPhone || "Sin teléfono";

  // Cargar variables iniciales
  const timeInput = document.getElementById("waVarTime");
  const barberInput = document.getElementById("waVarBarber");
  const detailInput = document.getElementById("waVarDetail");
  if (timeInput) timeInput.value = defaultTime;
  if (barberInput) barberInput.value = defaultBarber;
  if (detailInput) detailInput.value = "15-20 min";

  // Reset selector plantilla
  const select = document.getElementById("waTemplateSelect");
  if (select) select.value = "recordatorio";

  applyWaTemplate();
  modal.style.display = "flex";
}

function closeClientWhatsappModal() {
  const modal = document.getElementById("clientWhatsappModal");
  if (modal) modal.style.display = "none";
}

function applyWaTemplate() {
  const templateType = document.getElementById("waTemplateSelect")?.value || "recordatorio";
  const varBox = document.getElementById("waVariablesBox");
  if (varBox) {
    varBox.style.display = (templateType === "personalizado") ? "none" : "grid";
  }

  // Ajustar labels dinámicamente según la plantilla elegida
  const lblDetail = document.getElementById("lblWaVarDetail");
  const detailInput = document.getElementById("waVarDetail");

  if (lblDetail && detailInput) {
    if (templateType === "demora") {
      lblDetail.textContent = "DEMORA ESTIMADA:";
      if (detailInput.value === "15-20 min" || !detailInput.value) detailInput.value = "15-20 min";
    } else if (templateType === "ausente_barbero") {
      lblDetail.textContent = "OPCIONES / BARBERO:";
      if (detailInput.value === "15-20 min" || !detailInput.value) detailInput.value = "otro barbero disponible";
    } else if (templateType === "disponibles") {
      lblDetail.textContent = "HORARIOS DISPONIBLES:";
      if (detailInput.value === "15-20 min" || !detailInput.value) detailInput.value = "16:00, 17:30, 19:00 hs";
    } else if (templateType === "voucher") {
      lblDetail.textContent = "DESCUENTO:";
      if (detailInput.value === "15-20 min" || !detailInput.value) detailInput.value = "15% OFF";
    } else {
      lblDetail.textContent = "DETALLE / ADICIONAL:";
    }
  }

  buildWaDraftText();
}

function buildWaDraftText() {
  const templateType = document.getElementById("waTemplateSelect")?.value || "recordatorio";
  const clientName = currentWaClient.name || "estimado/a";
  const timeStr = document.getElementById("waVarTime")?.value || "[Fecha/Hora]";
  const barberStr = document.getElementById("waVarBarber")?.value || "[Barbero]";
  const detailStr = document.getElementById("waVarDetail")?.value || "[15-20 min]";

  let draft = "";

  switch (templateType) {
    case "recordatorio":
      draft = `💈 ¡Hola ${clientName}! Te recordamos desde la Barbería tu próximo turno agendado para ${timeStr} con ${barberStr}. Por favor confirmanos si podrás asistir o si necesitas reprogramar. ¡Te esperamos!`;
      break;
    case "demora":
      draft = `💈 ¡Hola ${clientName}! Te contactamos para informarte que tenemos una ligera demora estimada de ${detailStr} en la atención de hoy. Disculpá la molestia...`;
      break;
    case "ausente_barbero":
      draft = `💈 ¡Hola ${clientName}! Te comentamos que tu barbero ${barberStr} tuvo una eventualidad imprevista. ¿Te gustaría atenderte hoy con otro de nuestros profesionales disponibles o prefieres que coordinemos para cambiar tu turno?`;
      break;
    case "reprogramar":
      draft = `💈 ¡Hola ${clientName}! Nos comunicamos para coordinar una reprogramación de tu turno agendado para ${timeStr}. Por favor respondenos a este mensaje...`;
      break;
    case "disponibles":
      draft = `💈 ¡Hola ${clientName}! Te compartimos nuestros próximos turnos disponibles para hoy: ${detailStr}. Por favor avísanos cuál te queda mejor para asignártelo.`;
      break;
    case "voucher":
      const hostUrl = window.location.origin || "http://127.0.0.1:8000";
      draft = `🎁 ¡Hola ${clientName}! Queremos regalarte un Voucher Especial (${detailStr}) para tu próximo servicio en la Barbería. Ingresá aquí para reclamarlo: ${hostUrl}/voucher.html ¡Te esperamos!`;
      break;
    case "personalizado":
      const currentText = document.getElementById("waFinalMessageText")?.value;
      if (!currentText || currentText.trim().length === 0) {
        draft = `💈 ¡Hola ${clientName}! `;
      } else {
        draft = currentText;
      }
      break;
    default:
      draft = `💈 ¡Hola ${clientName}! Te contactamos desde la Barbería...`;
  }

  const textarea = document.getElementById("waFinalMessageText");
  if (textarea && templateType !== "personalizado") {
    textarea.value = draft;
  }

  updateWaHrefFromTextarea();
}

function updateWaHrefFromTextarea() {
  const textarea = document.getElementById("waFinalMessageText");
  const sendBtn = document.getElementById("btnSendWhatsappDirect");
  if (!textarea || !sendBtn) return;

  const text = textarea.value.trim();
  const encoded = encodeURIComponent(text);
  const cleanPhone = currentWaClient.rawPhone;

  if (cleanPhone) {
    sendBtn.href = `https://wa.me/${cleanPhone}?text=${encoded}`;
  } else {
    sendBtn.href = `https://api.whatsapp.com/send?text=${encoded}`;
  }
}

function copyWaTextToClipboard() {
  const textarea = document.getElementById("waFinalMessageText");
  if (!textarea || !textarea.value) return;

  navigator.clipboard.writeText(textarea.value).then(() => {
    if (window.showToast) showToast("Texto copiado al portapapeles", "success");
    else alert("Texto copiado al portapapeles");
  }).catch(() => {
    textarea.select();
    document.execCommand("copy");
    alert("Texto copiado al portapapeles");
  });
}

function trackWaSend() {
  if (window.showToast) showToast("Abriendo WhatsApp...", "info");
}

// ============================================================
// FICHA DE PERFIL CRM DEL CLIENTE
// ============================================================

async function openClientProfileModal(clientId) {
  const modal = document.getElementById("clientProfileModal");
  const body = document.getElementById("crmClientProfileBody");
  if (!modal || !body) return;

  modal.style.display = "flex";
  body.innerHTML = `<div style="text-align: center; color: #9ca3af; padding: 30px;" class="animate-pulse">Cargando ficha CRM del cliente #${clientId}...</div>`;

  try {
    const res = await fetch(`/api/admin/clients/${clientId}/profile`, { headers: authHeaders() });
    if (!res.ok) throw new Error("Error al obtener perfil");
    const data = await res.json();

    const title = document.getElementById("crmClientProfileTitle");
    if (title) title.textContent = `Ficha CRM: ${data.name}`;

    const apptsHtml = (data.turnos_recientes && data.turnos_recientes.length > 0)
      ? data.turnos_recientes.map(a => `
        <tr style="border-bottom: 1px solid #1a1a22;">
          <td style="padding: 8px;">#${a.id}</td>
          <td style="padding: 8px;"><strong>${escapeHtml(a.service)}</strong></td>
          <td style="padding: 8px;">${escapeHtml(a.barber_name || '-')}</td>
          <td style="padding: 8px; font-family: monospace;">${a.date}</td>
          <td style="padding: 8px;"><span class="status-pill status-${a.status}">${a.status}</span></td>
        </tr>
      `).join('')
      : `<tr><td colspan="5" style="text-align: center; color: #9ca3af; padding: 12px;">Sin turnos registrados aún.</td></tr>`;

    body.innerHTML = `
      <!-- CLIENT HEADER BANNER -->
      <div style="background: #09090c; border: 1px solid #23232c; border-radius: 12px; padding: 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h4 style="font-family: 'Space Grotesk', monospace; color: #fff; margin: 0; font-size: 1.2rem;">${escapeHtml(data.name)}</h4>
          <p style="color: #9ca3af; font-size: 0.8rem; margin: 2px 0 0 0;">Email: ${escapeHtml(data.email || 'No registrado')}</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button onclick="closeClientProfileModal(); openClientWhatsappModal('${escapeHtml(data.name)}', '${escapeHtml(data.phone)}')" class="btn-admin btn-admin-sm" style="background: #25D366; color: #000; font-weight: bold;">
            💬 Contactar por WhatsApp
          </button>
        </div>
      </div>

      <!-- KPIS CRM DE ACTIVIDAD -->
      <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 16px;">
        <div class="kpi-card" style="padding: 12px;">
          <div class="kpi-title">TOTAL TURNOS</div>
          <div class="kpi-value" style="font-size: 1.3rem;">${data.total_turnos}</div>
        </div>
        <div class="kpi-card" style="padding: 12px;">
          <div class="kpi-title">COMPLETADOS</div>
          <div class="kpi-value" style="font-size: 1.3rem; color: #10b981;">${data.cumplidos}</div>
        </div>
        <div class="kpi-card" style="padding: 12px;">
          <div class="kpi-title">CANCELADOS / NO SHOW</div>
          <div class="kpi-value" style="font-size: 1.3rem; color: #ef4444;">${data.cancelados + data.no_show}</div>
        </div>
        <div class="kpi-card" style="padding: 12px;">
          <div class="kpi-title">BARBERO HABITUAL</div>
          <div class="kpi-value" style="font-size: 0.95rem; color: #d4ff00; text-transform: uppercase;">${escapeHtml(data.barbero_habitual)}</div>
        </div>
      </div>

      <!-- NOTAS INTERNAS DEL CLIENTE -->
      <div style="margin-bottom: 16px; background: #09090c; border: 1px solid #23232c; border-radius: 12px; padding: 14px;">
        <label style="color: #cbd5e1; font-size: 0.75rem; font-family: 'Space Grotesk', monospace; font-weight: 700; display: block; margin-bottom: 6px;">
          📝 NOTAS INTERNAS Y PREFERENCIAS DEL CLIENTE (STAFF):
        </label>
        <textarea id="crmNotesInput" rows="3" placeholder="Observaciones de corte, bebidas preferidas, puntualidad, etc..." class="admin-menu-search" style="width: 100%; box-sizing: border-box; border-color: #23232c; margin-bottom: 8px;">${escapeHtml(data.notes || '')}</textarea>
        <div style="display: flex; justify-content: flex-end;">
          <button onclick="saveClientNotes(${data.id})" class="btn-admin btn-admin-sm">
            💾 Guardar Notas
          </button>
        </div>
      </div>

      <!-- HISTORIAL RECIENTE DE TURNOS -->
      <div>
        <h5 style="font-family: 'Space Grotesk', monospace; color: #fff; margin: 0 0 8px 0; font-size: 0.9rem;">📅 Historial Reciente de Citas</h5>
        <div style="max-height: 200px; overflow-y: auto; border: 1px solid #23232c; border-radius: 10px; background: #09090c;">
          <table style="width: 100%; text-align: left; font-size: 0.8rem; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 1px solid #23232c; color: #9ca3af; font-family: monospace;">
                <th style="padding: 8px;">#ID</th>
                <th style="padding: 8px;">Servicio</th>
                <th style="padding: 8px;">Barbero</th>
                <th style="padding: 8px;">Fecha</th>
                <th style="padding: 8px;">Estado</th>
              </tr>
            </thead>
            <tbody>
              ${apptsHtml}
            </tbody>
          </table>
        </div>
      </div>
    `;

  } catch (err) {
    body.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 20px;">Error al cargar la ficha del cliente.</div>`;
  }
}

function closeClientProfileModal() {
  const modal = document.getElementById("clientProfileModal");
  if (modal) modal.style.display = "none";
}

async function saveClientNotes(clientId) {
  const notes = document.getElementById("crmNotesInput")?.value || "";
  try {
    const res = await fetch(`/api/admin/clients/${clientId}/notes`, {
      method: "PUT",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ notes: notes })
    });
    if (res.ok) {
      if (window.showToast) showToast("Notas del cliente guardadas correctamente", "success");
      else alert("Notas guardadas correctamente.");
    } else {
      alert("Error al guardar notas.");
    }
  } catch (e) {
    alert("Error de conexión al guardar notas.");
  }
}

async function deleteClient(clientId, clientName) {
  if (!confirm(`¿Deseas eliminar al cliente '${clientName}'? Se desvinculará de sus turnos pasados sin romper el historial.`)) return;

  try {
    const res = await fetch(`/api/admin/clients/${clientId}`, {
      method: "DELETE",
      headers: authHeaders()
    });
    if (res.ok) {
      if (window.showToast) showToast(`Cliente '${clientName}' eliminado`, "success");
      else alert(`Cliente '${clientName}' eliminado correctamente.`);
      loadAdminClients();
    } else {
      const data = await res.json();
      alert(data.detail || "Error al eliminar cliente.");
    }
  } catch (e) {
    alert("Error de conexión al eliminar cliente.");
  }
}
