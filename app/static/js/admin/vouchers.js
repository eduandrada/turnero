/**
 * Admin Panel - Vouchers, Promotions & QR Digital Vouchers Module
 * HiddenSYNC Barber Ecosystem 2026
 */

let cachedVouchers = [];
let cachedRedemptions = [];

document.addEventListener("DOMContentLoaded", () => {
  const observer = new MutationObserver(() => {
    const section = document.getElementById("section-promotions");
    if (section && section.style.display !== "none") {
      loadAdminVouchers();
      loadAdminVoucherRedemptions();
    }
  });
  const secEl = document.getElementById("section-promotions");
  if (secEl) observer.observe(secEl, { attributes: true, attributeFilter: ["style"] });
});

async function loadAdminVouchers() {
  try {
    const res = await fetch("/api/admin/vouchers", { headers: authHeaders() });
    if (!res.ok) return;
    cachedVouchers = await res.json();
    renderVouchersTable(cachedVouchers);
    updateVoucherKPIs();
  } catch (e) {
    console.error("Error al cargar promociones:", e);
  }
}

async function loadAdminVoucherRedemptions() {
  try {
    const res = await fetch("/api/admin/vouchers/redemptions", { headers: authHeaders() });
    if (!res.ok) return;
    cachedRedemptions = await res.json();
    renderVoucherRedemptionsTable(cachedRedemptions);
    updateVoucherKPIs();
  } catch (e) {
    console.error("Error al cargar canjes de vouchers:", e);
  }
}

function updateVoucherKPIs() {
  const activeCount = cachedVouchers.filter(v => v.is_active).length;
  const redemptionsCount = cachedRedemptions.length;
  const totalDiscount = cachedRedemptions.reduce((acc, r) => acc + (r.discount_applied || r.discount_amount || 0), 0);

  const elActive = document.getElementById("kpiVouchersActiveCount");
  const elRed = document.getElementById("kpiVouchersRedemptionsCount");
  const elDisc = document.getElementById("kpiVouchersDiscountTotal");

  if (elActive) elActive.textContent = activeCount;
  if (elRed) elRed.textContent = redemptionsCount;
  if (elDisc) elDisc.textContent = "$" + totalDiscount.toLocaleString("es-AR");
}

function renderVouchersTable(list) {
  const tbody = document.getElementById("vouchersTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!list || list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: #9ca3af; padding: 30px;">
          No hay cupones ni promociones registradas. ¡Creá la primera con el botón de arriba!
        </td>
      </tr>
    `;
    return;
  }

  list.forEach(v => {
    const tr = document.createElement("tr");

    let typeBadge = "";
    if (v.discount_type === "PERCENTAGE") {
      typeBadge = v.discount_value >= 100 
        ? `<span class="badge" style="background: rgba(210, 255, 0, 0.2); color: #d4ff00; border: 1px solid #d4ff00;">🎁 PASE LIBRE 100%</span>`
        : `<span class="badge" style="background: rgba(0, 242, 254, 0.15); color: #00f2fe;">🔥 ${v.discount_value}% OFF</span>`;
    } else if (v.discount_type === "FIXED_AMOUNT") {
      typeBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">💰 $${v.discount_value} OFF</span>`;
    } else if (v.discount_type === "FREE_ITEM") {
      typeBadge = `<span class="badge" style="background: rgba(210, 255, 0, 0.2); color: #d4ff00;">🎁 SERVICIO GRATIS</span>`;
    } else {
      typeBadge = `<span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc;">🏷️ PRECIO FIJO</span>`;
    }

    let valStr = v.discount_type === "PERCENTAGE" ? `${v.discount_value}%` : `$${v.discount_value}`;

    let usesStr = `${v.current_uses || 0} / ${v.max_total_uses || '∞'}`;
    let expStr = v.valid_to ? new Date(v.valid_to).toLocaleDateString("es-AR") : "Sin vencimiento";

    tr.innerHTML = `
      <td>
        <div style="display: flex; align-items: center; gap: 6px;">
          <strong style="font-family: monospace; font-size: 0.95rem; color: #d4ff00;">${escapeHtml(v.code)}</strong>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" title="Copiar Código" onclick="copyVoucherCode('${v.code}')">📋</button>
        </div>
      </td>
      <td>${typeBadge}</td>
      <td style="font-family: monospace; font-weight: bold; color: #fff;">${valStr}</td>
      <td><span style="font-size: 0.75rem; color: #9ca3af;">${escapeHtml(v.scope || 'TOTAL_TICKET')}</span></td>
      <td style="font-family: monospace;">${usesStr}</td>
      <td style="font-size: 0.8rem; color: #cbd5e1;">${expStr}</td>
      <td>
        <span class="badge ${v.is_active ? 'badge-confirmed' : 'badge-canceled'}">
          ${v.is_active ? 'ACTIVADO' : 'INACTIVO'}
        </span>
      </td>
      <td>
        <div style="display: flex; gap: 6px;">
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openVoucherQRModal('${v.code}')" title="Ver QR & Link">📱 QR</button>
          <button class="btn-admin btn-admin-sm" style="background: #25D366; color: #000; font-weight: bold;" onclick="quickSendVoucherWA('${v.code}')" title="Enviar WhatsApp">💬 WA</button>
          ${v.is_active ? `<button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteVoucher(${v.id})">Desactivar</button>` : ''}
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderVoucherRedemptionsTable(list) {
  const tbody = document.getElementById("voucherRedemptionsTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!list || list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: #9ca3af; padding: 24px;">
          No hay canjes de vouchers registrados.
        </td>
      </tr>
    `;
    return;
  }

  list.forEach(r => {
    const tr = document.createElement("tr");
    const dtStr = r.created_at ? new Date(r.created_at).toLocaleString("es-AR") : "-";
    const orig = r.original_amount ? `$${r.original_amount.toLocaleString("es-AR")}` : "-";
    const disc = r.discount_applied || r.discount_amount ? `$${(r.discount_applied || r.discount_amount).toLocaleString("es-AR")}` : "$0";
    const fin = r.final_amount !== undefined ? `$${r.final_amount.toLocaleString("es-AR")}` : "-";

    tr.innerHTML = `
      <td style="font-size: 0.8rem; color: #cbd5e1;">${dtStr}</td>
      <td><strong style="font-family: monospace; color: #d4ff00;">${escapeHtml(r.voucher_code || '-')}</strong></td>
      <td style="font-family: monospace;">${escapeHtml(r.client_phone || 'Online')}</td>
      <td style="font-size: 0.85rem; color: #9ca3af;">${escapeHtml(r.staff_username || 'Sistema')}</td>
      <td style="font-family: monospace; color: #9ca3af;">${orig}</td>
      <td style="font-family: monospace; color: #10b981; font-weight: bold;">-${disc}</td>
      <td style="font-family: monospace; color: #00f2fe; font-weight: bold;">${fin}</td>
    `;
    tbody.appendChild(tr);
  });
}

function filterVouchersTable(query) {
  const q = query.trim().toUpperCase();
  if (!q) {
    renderVouchersTable(cachedVouchers);
    return;
  }
  const filtered = cachedVouchers.filter(v => (v.code || '').toUpperCase().includes(q) || (v.description || '').toUpperCase().includes(q));
  renderVouchersTable(filtered);
}

function copyVoucherCode(code) {
  navigator.clipboard.writeText(code);
  showAdminToast(`¡Código '${code}' copiado al portapapeles!`, "success");
}

async function deleteVoucher(id) {
  if (!confirm("¿Desactivar este cupón promocional?")) return;
  try {
    const res = await fetch(`/api/admin/vouchers/${id}`, {
      method: "DELETE",
      headers: authHeaders()
    });
    if (res.ok) {
      showAdminToast("Cupón desactivado correctamente.", "success");
      loadAdminVouchers();
    } else {
      showAdminToast("Error al desactivar el cupón.", "error");
    }
  } catch (e) {
    showAdminToast("Error de conexión.", "error");
  }
}

// --- CREAR NUEVA REGLA PROMOCIONAL ---
function openCreateVoucherModal() {
  fillRandomCodeInCreateForm();
  document.getElementById("createVoucherModal").style.display = "flex";
}

function closeCreateVoucherModal() {
  document.getElementById("createVoucherModal").style.display = "none";
}

function generateRandomPromoCode(prefix = "PROMO") {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let randomStr = "";
  for (let i = 0; i < 5; i++) {
    randomStr += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `${prefix}-${randomStr}`;
}

function fillRandomCodeInCreateForm() {
  const type = document.getElementById("cv_type").value;
  let prefix = "PROMO";
  if (type === "PERCENTAGE") {
    const val = document.getElementById("cv_value").value;
    prefix = val == "100" ? "FREEPASS" : `OFF${val}`;
  } else if (type === "FIXED_AMOUNT") {
    prefix = "DESC";
  } else if (type === "FREE_ITEM") {
    prefix = "FREEPASS";
  }
  document.getElementById("cv_code").value = generateRandomPromoCode(prefix);
}

async function submitCreateVoucherForm() {
  const code = document.getElementById("cv_code").value.trim().toUpperCase();
  const type = document.getElementById("cv_type").value;
  const value = parseFloat(document.getElementById("cv_value").value || "0");
  const scope = document.getElementById("cv_scope").value;
  const maxUses = parseInt(document.getElementById("cv_max_uses").value || "100");
  const validDays = parseInt(document.getElementById("cv_valid_days").value || "30");
  const desc = document.getElementById("cv_desc").value.trim();

  if (!code) {
    alert("Por favor ingresá un código promocional.");
    return;
  }

  const validToDate = new Date();
  validToDate.setDate(validToDate.getDate() + validDays);

  const payload = {
    code: code,
    discount_type: type,
    discount_value: value,
    max_discount_amount: null,
    scope: scope,
    commission_impact: "BUSINESS_ABSORBED",
    min_ticket_amount: 0.0,
    start_date: new Date().toISOString(),
    end_date: validToDate.toISOString(),
    allowed_days: null,
    allowed_start_time: null,
    allowed_end_time: null,
    max_total_uses: maxUses,
    max_uses_per_client: 1,
    required_role: "public",
    is_active: true,
    description: desc || `Cupón ${code} - Descuento ${value}`
  };

  try {
    const res = await fetch("/api/admin/vouchers", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      closeCreateVoucherModal();
      showAdminToast(`¡Cupón '${code}' creado exitosamente!`, "success");
      loadAdminVouchers();
    } else {
      alert(data.detail || "Error al crear el cupón.");
    }
  } catch (e) {
    alert("Error de conexión al servidor.");
  }
}

// --- GENERADOR DIRECTO DE VOUCHER CLIENTE (QR + WA) ---
function openGenerateClientVoucherModal() {
  document.getElementById("gc_code").value = generateRandomPromoCode("FREEPASS");
  updateClientVoucherPreview();
  document.getElementById("generateClientVoucherModal").style.display = "flex";
}

function closeGenerateClientVoucherModal() {
  document.getElementById("generateClientVoucherModal").style.display = "none";
}

function setPresetVoucherType(type, value, desc) {
  document.getElementById("gc_type").value = type;
  document.getElementById("gc_value").value = value;
  document.getElementById("gc_desc").value = desc;

  let prefix = "PROMO";
  if (value == 100 || type === "FREE_ITEM") prefix = "FREEPASS";
  else if (type === "PERCENTAGE") prefix = `OFF${value}`;
  else if (type === "FIXED_AMOUNT") prefix = `DESC${value}`;

  document.getElementById("gc_code").value = generateRandomPromoCode(prefix);
  updateClientVoucherPreview();
}

function updateClientVoucherPreview() {
  const code = document.getElementById("gc_code").value.trim().toUpperCase() || "PROMO-SAMPLE";
  const clientName = document.getElementById("gc_client_name").value.trim() || "Estimado Cliente";
  const desc = document.getElementById("gc_desc").value.trim() || "Descuento Especial en Pereyras Barbers";

  const host = window.location.origin;
  const voucherUrl = `${host}/voucher.html?code=${encodeURIComponent(code)}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(voucherUrl)}`;

  const imgEl = document.getElementById("gc_qr_img");
  if (imgEl) imgEl.src = qrUrl;

  const linkEl = document.getElementById("gc_voucher_url");
  if (linkEl) {
    linkEl.href = voucherUrl;
    linkEl.textContent = voucherUrl;
  }

  const waMsg = `¡Hola ${clientName}! 💈 Te regalamos un VÓUCHER EXCLUSIVO de regalo para tu próximo turno en *Pereyras Barbers*:\n\n` +
    `🎁 *${desc}*\n` +
    `🔑 Código de Descuento: *${code}*\n\n` +
    `📲 Abrí tu voucher digital y presentá tu QR en recepción:\n` +
    `${voucherUrl}\n\n` +
    `¡Te esperamos! ✂️`;

  const waPreviewEl = document.getElementById("gc_wa_preview");
  if (waPreviewEl) waPreviewEl.value = waMsg;
}

async function createAndSendClientVoucherWA() {
  const code = document.getElementById("gc_code").value.trim().toUpperCase();
  const phone = document.getElementById("gc_phone").value.replace(/\D/g, "");
  const type = document.getElementById("gc_type").value;
  const value = parseFloat(document.getElementById("gc_value").value || "0");
  const desc = document.getElementById("gc_desc").value.trim();

  if (!code) {
    alert("Por favor ingresá o generá un código.");
    return;
  }

  const validToDate = new Date();
  validToDate.setDate(validToDate.getDate() + 30);

  const payload = {
    code: code,
    discount_type: type,
    discount_value: value,
    max_discount_amount: null,
    scope: "TOTAL_TICKET",
    commission_impact: "BUSINESS_ABSORBED",
    min_ticket_amount: 0.0,
    start_date: new Date().toISOString(),
    end_date: validToDate.toISOString(),
    allowed_days: null,
    allowed_start_time: null,
    allowed_end_time: null,
    max_total_uses: 1,
    max_uses_per_client: 1,
    required_role: "public",
    is_active: true,
    description: desc || `Voucher exclusivo cliente - ${code}`
  };

  try {
    const res = await fetch("/api/admin/vouchers", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });
    loadAdminVouchers();
  } catch (e) { console.error("Error al registrar voucher", e); }

  const text = encodeURIComponent(document.getElementById("gc_wa_preview").value);
  if (phone) {
    window.open(`https://wa.me/${phone}?text=${text}`, "_blank");
  } else {
    navigator.clipboard.writeText(document.getElementById("gc_wa_preview").value);
    showAdminToast("Mensaje y link del Voucher copiado al portapapeles.", "success");
  }

  closeGenerateClientVoucherModal();
}

function openVoucherQRModal(code) {
  const host = window.location.origin;
  const voucherUrl = `${host}/voucher.html?code=${encodeURIComponent(code)}`;
  
  const existing = cachedVouchers.find(v => v.code === code);
  if (existing) {
    document.getElementById("gc_code").value = existing.code;
    document.getElementById("gc_type").value = existing.discount_type;
    document.getElementById("gc_value").value = existing.discount_value;
    document.getElementById("gc_desc").value = existing.description || "";
  } else {
    document.getElementById("gc_code").value = code;
  }

  document.getElementById("gc_phone").value = "";
  updateClientVoucherPreview();
  document.getElementById("generateClientVoucherModal").style.display = "flex";
}

function quickSendVoucherWA(code) {
  openVoucherQRModal(code);
}
