/**
 * Admin Panel - Backups Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles database backups listing, on-demand creation, download, and safe restore with pre-backup.
 */

async function loadAdminBackups() {
  try {
    const res = await fetch("/api/admin/backups", { headers: authHeaders() });
    if (!res.ok) return;
    const backups = await res.json();
    const tbody = document.getElementById("backupsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    backups.forEach(b => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(b.filename)}</strong></td>
        <td>${(b.size_bytes / 1024).toFixed(1)} KB</td>
        <td>${b.created_at.replace("T", " ").substring(0, 19)}</td>
        <td>
          <a class="btn-admin btn-admin-sm btn-admin-secondary" href="/api/admin/backups/download/${encodeURIComponent(b.filename)}">Descargar</a>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="restoreBackup('${escapeHtml(b.filename)}')">Restaurar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Error al cargar backups:", e);
  }
}

async function triggerCreateBackup() {
  try {
    const res = await fetch("/api/admin/backups/create", { method: "POST", headers: authHeaders() });
    if (res.ok) {
      alert("Backup creado con éxito.");
      loadAdminBackups();
    } else {
      const data = await res.json();
      alert(data.detail || "Error al crear backup.");
    }
  } catch (e) {
    alert("Error de conexión al crear backup.");
  }
}

async function restoreBackup(filename) {
  if (!confirm(`¿Restaurar la base de datos desde '${filename}'? Se realizará una copia de seguridad automática previa antes de la restauración.`)) return;
  try {
    const res = await fetch(`/api/admin/backups/restore?filename=${encodeURIComponent(filename)}`, { method: "POST", headers: authHeaders() });
    if (res.ok) {
      alert("Base de datos restaurada exitosamente.");
      if (typeof loadAdminDashboard === "function") loadAdminDashboard();
    } else {
      const data = await res.json();
      alert(data.detail || "Error al restaurar backup.");
    }
  } catch (e) {
    alert("Error de conexión al restaurar backup.");
  }
}
