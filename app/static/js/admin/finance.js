/**
 * Admin Panel - Finance & Shift Closures Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles shift closures audit, cashier reconciliation, differences (surplus/deficit), and cash summaries.
 */

async function loadShiftClosuresData() {
  try {
    const res = await fetch("/api/admin/shift-closures", { headers: authHeaders() });
    if (!res.ok) return;
    const closures = await res.json();
    const tbody = document.getElementById("shiftClosuresTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (closures.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="12" style="text-align: center; padding: 40px; color: #9ca3af;">
            No hay registros de arqueo o cierre de caja.
          </td>
        </tr>
      `;
      return;
    }

    closures.forEach(c => {
      const tr = document.createElement("tr");
      const diff = c.diferencia || 0;
      let diffBadge = `<span class="badge badge-confirmed">$0.00</span>`;
      if (diff < 0) {
        diffBadge = `<span class="badge badge-canceled">-$${Math.abs(diff).toLocaleString("es-AR", {minimumFractionDigits: 2})} (FALTANTE)</span>`;
      } else if (diff > 0) {
        diffBadge = `<span class="badge badge-pending">+$${diff.toLocaleString("es-AR", {minimumFractionDigits: 2})} (SOBRANTE)</span>`;
      }

      tr.innerHTML = `
        <td>${c.fecha_cierre ? c.fecha_cierre.replace("T", " ").substring(0, 16) : '-'} hs</td>
        <td><strong style="color: #d4ff00;">${escapeHtml(c.encargado_name)}</strong></td>
        <td>$${c.fondo_inicial.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td>$${c.total_efectivo.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td>$${c.total_transferencia.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td>$${c.total_cortes.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td>$${c.total_productos.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td style="font-weight: bold; color: #ffffff;">$${c.total_calculado.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td style="font-weight: bold; color: #00f2fe;">$${c.balance_declarado.toLocaleString("es-AR", {minimumFractionDigits: 2})}</td>
        <td>${diffBadge}</td>
        <td><strong>${c.total_turnos_atendidos}</strong></td>
        <td style="font-size: 0.75rem; color: #9ca3af;">${escapeHtml(c.notas || '-')}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Error al cargar auditoría de cajas:", e);
  }
}
