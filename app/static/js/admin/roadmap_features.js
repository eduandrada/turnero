/**
 * Admin Panel - Roadmap Features Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles:
 * 1. 💳 Pasarela de Pagos (Mercado Pago / Stripe & Señas)
 * 2. ⭐ Programa de Fidelización Barber Club
 * 3. 🔔 Notificaciones Push PWA
 * 4. 📊 Reporte de Productividad e Incentivos por Barbero
 */

async function loadPaymentSettings() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    const enabled = data.payment_gateway_enabled === "1" || data.enable_deposit === "1";
    const elGateway = document.getElementById("cfg_payment_gateway_enabled");
    if (elGateway) elGateway.checked = enabled;

    const elProvider = document.getElementById("cfg_payment_provider");
    if (elProvider) elProvider.value = data.payment_provider || "mercadopago";

    const elPct = document.getElementById("cfg_deposit_percentage");
    if (elPct) elPct.value = data.deposit_percentage || "30";

    const elAlias = document.getElementById("cfg_deposit_mp_alias");
    if (elAlias) elAlias.value = data.deposit_mp_alias || "";

    const elTransfer = document.getElementById("cfg_checkout_alias_transferencia");
    if (elTransfer) elTransfer.value = data.checkout_alias_transferencia || data.deposit_mp_alias || "";

    const elTitular = document.getElementById("cfg_checkout_alias_titular");
    if (elTitular) elTitular.value = data.checkout_alias_titular || "Carmen Pereyra";

    const elPromo = document.getElementById("cfg_checkout_next_cut_promo_code");
    if (elPromo) elPromo.value = data.checkout_next_cut_promo_code || "VUELVO15";

    const elPromoPct = document.getElementById("cfg_checkout_next_cut_discount_percent");
    if (elPromoPct) elPromoPct.value = data.checkout_next_cut_discount_percent || "15";

    const elCustomMsg = document.getElementById("cfg_checkout_custom_message");
    if (elCustomMsg) elCustomMsg.value = data.checkout_custom_message || "¡Gracias por visitarnos en Pereyras Barbers! Esperamos verte pronto.";

    const elMpToken = document.getElementById("cfg_mp_access_token");
    if (elMpToken) elMpToken.value = data.mp_access_token || "";

    const elMpPub = document.getElementById("cfg_mp_public_key");
    if (elMpPub) elMpPub.value = data.mp_public_key || "";

    const elStripeSec = document.getElementById("cfg_stripe_secret_key");
    if (elStripeSec) elStripeSec.value = data.stripe_secret_key || "";

    const elStripePub = document.getElementById("cfg_stripe_publishable_key");
    if (elStripePub) elStripePub.value = data.stripe_publishable_key || "";

    togglePaymentFields();
  } catch (e) {
    console.error("Error cargando configuración de pagos:", e);
  }
}

function togglePaymentFields() {
  const provider = document.getElementById("cfg_payment_provider")?.value;
  const mpBox = document.getElementById("mpConfigBox");
  const stripeBox = document.getElementById("stripeConfigBox");
  if (mpBox) mpBox.style.display = provider === "mercadopago" ? "block" : "none";
  if (stripeBox) stripeBox.style.display = provider === "stripe" ? "block" : "none";
}

async function savePaymentSettings() {
  const enabled = document.getElementById("cfg_payment_gateway_enabled")?.checked ? "1" : "0";
  const provider = document.getElementById("cfg_payment_provider")?.value || "mercadopago";
  const depositPct = document.getElementById("cfg_deposit_percentage")?.value || "30";
  const alias = document.getElementById("cfg_deposit_mp_alias")?.value?.trim() || "";
  const mpToken = document.getElementById("cfg_mp_access_token")?.value?.trim() || "";
  const mpPub = document.getElementById("cfg_mp_public_key")?.value?.trim() || "";
  const stripeSecret = document.getElementById("cfg_stripe_secret_key")?.value?.trim() || "";
  const stripePub = document.getElementById("cfg_stripe_publishable_key")?.value?.trim() || "";

  const checkoutAlias = document.getElementById("cfg_checkout_alias_transferencia")?.value?.trim() || alias;
  const checkoutTitular = document.getElementById("cfg_checkout_alias_titular")?.value?.trim() || "Carmen Pereyra";
  const checkoutPromoCode = document.getElementById("cfg_checkout_next_cut_promo_code")?.value?.trim() || "VUELVO15";
  const checkoutPromoPct = document.getElementById("cfg_checkout_next_cut_discount_percent")?.value?.trim() || "15";
  const checkoutCustomMsg = document.getElementById("cfg_checkout_custom_message")?.value?.trim() || "";

  const payload = {
    settings: {
      payment_gateway_enabled: enabled,
      enable_deposit: enabled,
      payment_provider: provider,
      deposit_percentage: depositPct,
      deposit_mp_alias: alias,
      checkout_alias_transferencia: checkoutAlias,
      checkout_alias_titular: checkoutTitular,
      checkout_next_cut_promo_code: checkoutPromoCode,
      checkout_next_cut_discount_percent: checkoutPromoPct,
      checkout_custom_message: checkoutCustomMsg,
      mp_access_token: mpToken,
      mp_public_key: mpPub,
      stripe_secret_key: stripeSecret,
      stripe_publishable_key: stripePub
    }
  };

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      if (typeof UISound !== "undefined") UISound.play("success");
      alert("✅ Configuración de Pasarela de Pagos y Señas guardada correctamente.");
    } else {
      alert("Error al guardar la configuración.");
    }
  } catch (e) {
    alert("Error de conexión al servidor.");
  }
}

// -------------------------------------------------------------
// ⭐ BARBER CLUB & LOYALTY
// -------------------------------------------------------------
async function loadLoyaltySettings() {
  try {
    const resSettings = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (resSettings.ok) {
      const data = await resSettings.json();
      const elClub = document.getElementById("cfg_enable_barber_club");
      if (elClub) elClub.checked = data.enable_barber_club === "1";
      const elPoints = document.getElementById("cfg_points_per_amount");
      if (elPoints) elPoints.value = data.points_per_amount || "100";
    }

    const resRewards = await fetch("/api/loyalty/rewards");
    if (resRewards.ok) {
      const rewards = await resRewards.json();
      renderLoyaltyRewardsTable(rewards);
    }
  } catch (e) {
    console.error("Error cargando Barber Club:", e);
  }
}

function renderLoyaltyRewardsTable(rewards) {
  const tbody = document.getElementById("loyaltyRewardsTbody");
  if (!tbody) return;
  if (!rewards || rewards.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#9ca3af; padding:24px;">No hay premios registrados. Agregá el primero arriba.</td></tr>`;
    return;
  }

  tbody.innerHTML = rewards.map(r => `
    <tr>
      <td><strong>${escapeHtml(r.name)}</strong><br><small style="color:#9ca3af;">${escapeHtml(r.description || '')}</small></td>
      <td><span style="color:#d4ff00; font-weight:bold; font-family:monospace;">${r.points_required} pts</span></td>
      <td><span class="badge" style="background:rgba(255,255,255,0.08);">${escapeHtml(r.reward_type)}</span></td>
      <td>${r.is_active ? '🟢 Activo' : '🔴 Inactivo'}</td>
      <td>
        <button class="btn-admin btn-admin-danger btn-admin-sm" onclick="deleteLoyaltyReward(${r.id})">🗑️ Eliminar</button>
      </td>
    </tr>
  `).join("");
}

async function saveLoyaltySettings() {
  const enabled = document.getElementById("cfg_enable_barber_club")?.checked ? "1" : "0";
  const pointsRate = document.getElementById("cfg_points_per_amount")?.value || "100";

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({
        settings: {
          enable_barber_club: enabled,
          points_per_amount: pointsRate
        }
      })
    });
    if (res.ok) {
      if (typeof UISound !== "undefined") UISound.play("success");
      alert("✅ Reglas de Barber Club guardadas correctamente.");
    }
  } catch (e) {
    alert("Error al guardar.");
  }
}

async function createLoyaltyRewardModal() {
  const name = prompt("Nombre del Premio (ej. 50% OFF en próximo corte):");
  if (!name) return;
  const desc = prompt("Descripción breve del beneficio:");
  const ptsStr = prompt("Puntos requeridos (ej. 300):", "300");
  const pts = parseInt(ptsStr) || 300;

  try {
    const res = await fetch("/api/loyalty/rewards", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        name,
        description: desc,
        points_required: pts,
        reward_type: "DISCOUNT_PERCENT",
        reward_value: 50.0,
        is_active: true
      })
    });
    if (res.ok) {
      loadLoyaltySettings();
      if (typeof UISound !== "undefined") UISound.play("success");
    }
  } catch (e) {
    alert("Error al crear premio.");
  }
}

async function deleteLoyaltyReward(id) {
  if (!confirm("¿Seguro que deseas eliminar este premio del Barber Club?")) return;
  try {
    await fetch(`/api/loyalty/rewards/${id}`, { method: "DELETE", headers: authHeaders() });
    loadLoyaltySettings();
  } catch (e) {}
}

// -------------------------------------------------------------
// 🔔 PWA PUSH NOTIFICATIONS
// -------------------------------------------------------------
async function loadPushSettings() {
  try {
    const res = await fetch("/api/admin/settings", { headers: authHeaders() });
    if (res.ok) {
      const data = await res.json();
      const elPush = document.getElementById("cfg_pwa_push_enabled");
      if (elPush) elPush.checked = data.pwa_push_enabled === "1";
      const elHours = document.getElementById("cfg_pwa_push_hours_before");
      if (elHours) elHours.value = data.pwa_push_hours_before || "2";
      const elVapid = document.getElementById("cfg_vapid_public_key");
      if (elVapid) elVapid.value = data.vapid_public_key || "";
    }
  } catch (e) {
    console.error("Error cargando notificaciones Push:", e);
  }
}

async function savePushSettings() {
  const enabled = document.getElementById("cfg_pwa_push_enabled")?.checked ? "1" : "0";
  const hours = document.getElementById("cfg_pwa_push_hours_before")?.value || "2";
  const vapid = document.getElementById("cfg_vapid_public_key")?.value?.trim() || "";

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({
        settings: {
          pwa_push_enabled: enabled,
          pwa_push_hours_before: hours,
          vapid_public_key: vapid
        }
      })
    });
    if (res.ok) {
      if (typeof UISound !== "undefined") UISound.play("success");
      alert("✅ Configuración de Notificaciones Push PWA guardada.");
    }
  } catch (e) {
    alert("Error al guardar.");
  }
}

  try {
    const res = await fetch("/api/admin/settings", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({
        settings: {
          pwa_push_enabled: enabled,
          pwa_push_hours_before: hours,
          vapid_public_key: vapid
        }
      })
    });
    if (res.ok) {
      UISound.play("success");
      alert("✅ Configuración de Notificaciones Push PWA guardada.");
    }
  } catch (e) {
    alert("Error al guardar.");
  }
}

async function sendTestPushNotification() {
  try {
    const res = await fetch("/api/push/send-test", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        title: "💈 Prueba Push PWA // Barbería",
        message: "¡Excelente! Las notificaciones automáticas están funcionando en tu celular."
      })
    });
    const data = await res.json();
    alert(data.message || "Notificación de prueba procesada.");
  } catch (e) {
    alert("Error enviando prueba de Push.");
  }
}

// -------------------------------------------------------------
// 📊 BARBER PRODUCTIVITY & INCENTIVES REPORT
// -------------------------------------------------------------
async function loadBarberProductivity() {
  const startDate = document.getElementById("prod_start_date")?.value || "";
  const endDate = document.getElementById("prod_end_date")?.value || "";

  let url = "/api/admin/staff/productivity";
  const params = [];
  if (startDate) params.push(`start_date=${startDate}`);
  if (endDate) params.push(`end_date=${endDate}`);
  if (params.length > 0) url += "?" + params.join("&");

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    renderProductivityCards(data.summary);
    renderProductivityTable(data.barbers);
  } catch (e) {
    console.error("Error cargando métricas de productividad:", e);
  }
}

function renderProductivityCards(summary) {
  const container = document.getElementById("productivityStatsGrid");
  if (!container || !summary) return;

  container.innerHTML = `
    <div class="stat-card">
      <div class="stat-icon" style="background: rgba(212, 255, 0, 0.15); color: #d4ff00;">💈</div>
      <div class="stat-content">
        <span class="stat-label">Turnos Atendidos</span>
        <span class="stat-value">${summary.total_completed_appointments}</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">💵</div>
      <div class="stat-content">
        <span class="stat-label">Facturación Total</span>
        <span class="stat-value">$${summary.total_revenue.toLocaleString('es-AR')}</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">🪙</div>
      <div class="stat-content">
        <span class="stat-label">Propinas Totales</span>
        <span class="stat-value">$${summary.total_tips.toLocaleString('es-AR')}</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background: rgba(0, 242, 254, 0.15); color: #00f2fe;">🏆</div>
      <div class="stat-content">
        <span class="stat-label">Comisiones a Pagar</span>
        <span class="stat-value">$${summary.total_commissions.toLocaleString('es-AR')}</span>
      </div>
    </div>
  `;
}

function renderProductivityTable(barbers) {
  const tbody = document.getElementById("barberProductivityTbody");
  if (!tbody) return;
  if (!barbers || barbers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:#9ca3af; padding:24px;">No hay datos de barberos en este período.</td></tr>`;
    return;
  }

  tbody.innerHTML = barbers.map(b => `
    <tr>
      <td>
        <div style="display:flex; align-items:center; gap:10px;">
          <img src="${b.avatar_url || '/static/img/default-avatar.png'}" style="width:36px; height:36px; border-radius:50%; object-fit:cover;" onerror="this.src='/static/icon-192.png'">
          <div>
            <strong style="color:#fff;">${b.barber_name}</strong><br>
            <small style="color:#94a3b8;">${b.specialties || 'Master Barber'}</small>
          </div>
        </div>
      </td>
      <td><span style="font-weight:bold; color:#fff;">${b.completed_count}</span> <small style="color:#94a3b8;">/ ${b.total_appointments}</small></td>
      <td>
        <span style="font-weight:bold; color:${b.no_show_rate > 15 ? '#ef4444' : '#10b981'};">
          ${b.no_show_count} (${b.no_show_rate}%)
        </span>
      </td>
      <td><span style="font-family:monospace; color:#00f2fe; font-weight:bold;">${b.avg_min_per_cut} min</span></td>
      <td>$${b.services_revenue.toLocaleString('es-AR')}</td>
      <td>$${b.products_revenue.toLocaleString('es-AR')}</td>
      <td><span style="color:#f59e0b; font-weight:bold;">$${b.tips.toLocaleString('es-AR')}</span></td>
      <td>
        <small style="color:#94a3b8;">Cortes (${b.comm_services_pct}%): $${b.commission_services.toLocaleString('es-AR')}</small><br>
        <small style="color:#94a3b8;">Prod (${b.comm_products_pct}%): $${b.commission_products.toLocaleString('es-AR')}</small>
      </td>
      <td>
        <span style="color:#d4ff00; font-size:1.05rem; font-weight:bold; font-family:monospace;">
          $${b.total_compensation.toLocaleString('es-AR')}
        </span>
      </td>
    </tr>
  `).join("");
}
