/**
 * Admin Panel - Dashboard Module
 * HiddenSYNC Barber Ecosystem 2026
 * Loads KPIs, recent appointments, and recent shop orders.
 */

async function loadAdminDashboard() {
  try {
    const res = await fetch("/api/admin/dashboard/stats", { headers: authHeaders() });
    if (!res.ok) return;
    const stats = await res.json();

    const grid = document.getElementById("dashboardStatsGrid");
    if (grid) {
      grid.innerHTML = `
        <div class="stat-card">
          <span class="stat-card-label">Turnos de Hoy</span>
          <span class="stat-card-value">${stats.today_appointments}</span>
          <span class="stat-card-sub">${stats.pending_appointments} Pendientes</span>
        </div>
        <div class="stat-card">
          <span class="stat-card-label">Turnos Confirmados</span>
          <span class="stat-card-value" style="color: #10b981;">${stats.confirmed_appointments}</span>
          <span class="stat-card-sub">${stats.completed_appointments} Completados</span>
        </div>
        <div class="stat-card">
          <span class="stat-card-label">Clientes Totales</span>
          <span class="stat-card-value">${stats.total_clients}</span>
          <span class="stat-card-sub">${stats.total_barbers} Barberos</span>
        </div>
        <div class="stat-card">
          <span class="stat-card-label">Ventas Shop</span>
          <span class="stat-card-value" style="color: #d4ff00;">$${stats.total_orders_revenue.toLocaleString("es-AR")}</span>
          <span class="stat-card-sub">${stats.pending_orders} Pedidos Pendientes</span>
        </div>
      `;
    }

    // Recent appts
    const apptsBody = document.getElementById("dashRecentAppts");
    if (apptsBody) {
      apptsBody.innerHTML = "";
      (stats.recent_appointments || []).forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${escapeHtml(a.client_name)}</strong></td>
          <td>${escapeHtml(a.service)}</td>
          <td>${escapeHtml(a.barber_name)}</td>
          <td>${a.time.replace("T", " ").substring(0, 16)} hs</td>
          <td><span class="badge badge-${a.status.toLowerCase()}">${a.status}</span></td>
        `;
        apptsBody.appendChild(tr);
      });
    }

    // Recent orders
    const ordersBody = document.getElementById("dashRecentOrders");
    if (ordersBody) {
      ordersBody.innerHTML = "";
      (stats.recent_orders || []).forEach(o => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${escapeHtml(o.order_number)}</strong></td>
          <td>${escapeHtml(o.client_name)}</td>
          <td style="color: #d4ff00;">$${o.total.toLocaleString("es-AR")}</td>
          <td><span class="badge badge-pending">${o.status}</span></td>
        `;
        ordersBody.appendChild(tr);
      });
    }

  } catch (e) {
    console.error("Error al cargar dashboard:", e);
  }
}
