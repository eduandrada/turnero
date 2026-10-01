/**
 * Admin Panel - Shop & Orders Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles online shop orders, dispatch coordination, WhatsApp messaging, and delivery details.
 */

let adminOrdersList = [];

async function loadAdminOrders() {
  try {
    const res = await fetch("/api/admin/orders", { headers: authHeaders() });
    if (!res.ok) return;
    adminOrdersList = await res.json();
    const tbody = document.getElementById("ordersTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    adminOrdersList.forEach(o => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(o.order_number)}</strong></td>
        <td>${escapeHtml(o.client_name)}</td>
        <td><a href="https://wa.me/${o.client_phone.replace(/\D/g, '')}" target="_blank" style="color: #00f2fe;">${escapeHtml(o.client_phone)}</a></td>
        <td>${o.delivery_type === 'delivery' ? '🚚 Delivery' : '💈 Retiro'}</td>
        <td style="color: #d4ff00; font-weight: bold;">$${o.total.toLocaleString("es-AR")}</td>
        <td><span class="badge badge-pending">${o.status}</span></td>
        <td style="display: flex; gap: 6px; align-items: center;">
          <select class="form-control" style="padding: 4px; font-size: 0.75rem;" onchange="updateOrderStatus(${o.id}, this.value)">
            <option value="NUEVO" ${o.status==='NUEVO'?'selected':''}>NUEVO</option>
            <option value="CONFIRMADO" ${o.status==='CONFIRMADO'?'selected':''}>CONFIRMADO</option>
            <option value="PREPARANDO" ${o.status==='PREPARANDO'?'selected':''}>PREPARANDO</option>
            <option value="LISTO" ${o.status==='LISTO'?'selected':''}>LISTO</option>
            <option value="EN_CAMINO" ${o.status==='EN_CAMINO'?'selected':''}>EN CAMINO</option>
            <option value="ENTREGADO" ${o.status==='ENTREGADO'?'selected':''}>ENTREGADO</option>
            <option value="CANCELADO" ${o.status==='CANCELADO'?'selected':''}>CANCELADO</option>
          </select>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="openOrderDetailsModal(${o.id})">🔍 Coordinar / Detalle</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error("Error al cargar pedidos:", e); }
}

async function updateOrderStatus(id, newStatus) {
  try {
    await fetch(`/api/admin/orders/${id}/status`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ status: newStatus })
    });
    loadAdminOrders();
    if (typeof loadAdminProducts === "function") loadAdminProducts(); // Actualiza inventario si fue cancelado
  } catch (e) { alert("Error al actualizar pedido."); }
}

function closeOrderDetailModal() {
  const m = document.getElementById("orderDetailModal");
  if (m) m.style.display = "none";
}

function openOrderDetailsModal(orderId) {
  const o = adminOrdersList.find(item => item.id === orderId);
  if (!o) return;

  const titleEl = document.getElementById("orderDetailTitle");
  if (titleEl) titleEl.textContent = `Pedido #${o.order_number}`;

  let itemsHtml = "";
  if (o.items && o.items.length > 0) {
    itemsHtml = `
      <table class="admin-table" style="margin-top: 10px; font-size: 0.8rem;">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cant.</th>
            <th>Precio U.</th>
            <th>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          ${o.items.map(it => `
            <tr>
              <td><strong>${escapeHtml(it.product_name)}</strong></td>
              <td>${it.quantity} un.</td>
              <td>$${it.unit_price.toLocaleString("es-AR")}</td>
              <td style="color: #d4ff00; font-weight: bold;">$${it.subtotal.toLocaleString("es-AR")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } else {
    itemsHtml = `<p style="font-size: 0.8rem; color: #9ca3af;">Sin ítems detallados registrados.</p>`;
  }

  const cleanPhone = (o.client_phone || "").replace(/\D/g, "");
  const waMsg = encodeURIComponent(
    `¡Hola ${o.client_name}! Te contactamos de la Barbería por tu pedido #${o.order_number}.\n\n` +
    `📋 Resumen: Total $${o.total.toLocaleString("es-AR")} (${o.delivery_type === 'delivery' ? 'Envío a domicilio: ' + (o.address || 'Dirección de envío') : 'Retiro en barbería'}).\n\n` +
    `¿Coordinamos el envío / entrega de tu compra?`
  );

  const contentEl = document.getElementById("orderDetailContent");
  if (contentEl) {
    contentEl.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div style="background: #1a1a22; padding: 12px; border-radius: 12px; border: 1px solid #23232c;">
          <span style="font-size: 0.7rem; color: #d4ff00; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">DATOS DEL CLIENTE</span>
          <p style="color: #fff; font-weight: bold; margin: 4px 0 2px 0;">${escapeHtml(o.client_name)}</p>
          <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">📱 <a href="https://wa.me/${cleanPhone}" target="_blank" style="color: #00f2fe;">${escapeHtml(o.client_phone)}</a></p>
          ${o.client_email ? `<p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">✉️ ${escapeHtml(o.client_email)}</p>` : ''}
        </div>

        <div style="background: #1a1a22; padding: 12px; border-radius: 12px; border: 1px solid #23232c;">
          <span style="font-size: 0.7rem; color: #00f2fe; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">LOGÍSTICA DE ENTREGA</span>
          <p style="color: #fff; font-weight: bold; margin: 4px 0 2px 0;">${o.delivery_type === 'delivery' ? '🚚 Delivery a Domicilio' : '💈 Retiro en Barbería'}</p>
          ${o.address ? `<p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">📍 ${escapeHtml(o.address)} ${o.neighborhood ? '('+escapeHtml(o.neighborhood)+')' : ''}</p>` : ''}
          <p style="font-size: 0.8rem; color: #d4ff00; font-weight: bold; margin-top: 4px;">Costo Delivery: $${o.delivery_cost.toLocaleString("es-AR")}</p>
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <span style="font-size: 0.75rem; color: #9ca3af; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">PRODUCTOS COMPRADOS</span>
        ${itemsHtml}
      </div>

      <div style="background: #1a1a22; padding: 16px; border-radius: 12px; border: 1px solid #23232c; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div>
          <span style="font-size: 0.75rem; color: #9ca3af;">TOTAL DE LA COMPRA</span>
          <h3 style="font-family: 'Space Grotesk', monospace; color: #d4ff00; margin: 0; font-size: 1.5rem;">$${o.total.toLocaleString("es-AR")}</h3>
        </div>
        <div>
          <a href="https://wa.me/${cleanPhone}?text=${waMsg}" target="_blank" class="btn-admin" style="background: #25D366; color: #000; font-weight: bold; padding: 10px 16px; font-size: 0.85rem;">
            💬 Coordinar Despacho por WhatsApp →
          </a>
        </div>
      </div>
    `;
  }

  const modalEl = document.getElementById("orderDetailModal");
  if (modalEl) modalEl.style.display = "flex";
}
