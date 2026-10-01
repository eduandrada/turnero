/**
 * Admin Panel - Inventory & Products Module
 * HiddenSYNC Barber Ecosystem 2026
 * Handles product listing, critical stock alerts, fast stock adjustments, and product CRUD.
 */

let adminProductsList = [];

async function loadAdminProducts() {
  try {
    const res = await fetch("/api/admin/products", { headers: authHeaders() });
    if (!res.ok) return;
    adminProductsList = await res.json();
    const tbody = document.getElementById("productsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    adminProductsList.forEach(p => {
      const tr = document.createElement("tr");
      const isLow = p.stock <= p.min_stock;
      tr.innerHTML = `
        <td><img src="${p.image_url || '/static/products/cera.jpg'}" onerror="this.onerror=null; this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2236%22 height=%2236%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%239ca3af%22 stroke-width=%222%22><rect x=%222%22 y=%223%22 width=%2220%22 height=%2214%22 rx=%222%22/><path d=%22M6 21h12%22/><path d=%22M12 17v4%22/></svg>';" style="width: 36px; height: 36px; object-fit: cover; border-radius: 8px; background: #1a1a22;"></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${escapeHtml(p.category_name || '-')}</td>
        <td style="color: #d4ff00; font-weight: bold;">$${p.price.toLocaleString("es-AR")}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 6px;">
            <button class="btn-admin btn-admin-sm btn-admin-secondary" style="padding: 2px 8px; font-weight: bold;" onclick="quickAdjustStock(${p.id}, -1)">-</button>
            <strong style="color: ${isLow ? '#ef4444' : '#10b981'}; font-size: 0.9rem;">${p.stock} un.</strong>
            <button class="btn-admin btn-admin-sm btn-admin-secondary" style="padding: 2px 8px; font-weight: bold;" onclick="quickAdjustStock(${p.id}, 1)">+</button>
          </div>
          ${isLow ? '<span style="color: #ef4444; font-size: 0.65rem; font-weight: bold; display: block; margin-top: 2px;">⚠️ Stock Crítico</span>' : ''}
        </td>
        <td>${p.min_stock} un.</td>
        <td><span class="badge ${p.is_active ? 'badge-confirmed' : 'badge-canceled'}">${p.is_active ? 'DISPONIBLE' : 'OCULTO'}</span></td>
        <td>
          <button class="btn-admin btn-admin-sm btn-admin-secondary" onclick="editProductModal(${p.id})">Editar</button>
          <button class="btn-admin btn-admin-sm btn-admin-danger" onclick="deleteProduct(${p.id})">Eliminar</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) { console.error("Error al cargar productos:", e); }
}

async function uploadProductFileAdmin(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append("file", file);
  const statusEl = document.getElementById("admin_img_status");
  if (statusEl) statusEl.textContent = "Subiendo imagen...";
  try {
    const res = await fetch("/api/admin/upload", {
      method: "POST",
      headers: { "Authorization": `Bearer ${adminToken}` },
      body: formData
    });
    const data = await res.json();
    const url = data.file_url || data.url;
    if (res.ok && url) {
      document.getElementById("modal_product_image").value = url;
      const preview = document.getElementById("admin_img_preview");
      if (preview) { preview.src = url; preview.style.display = "block"; }
      if (statusEl) statusEl.textContent = "✅ Imagen subida con éxito";
    } else {
      alert(data.detail || "Error al subir imagen.");
      if (statusEl) statusEl.textContent = "Error al subir";
    }
  } catch (e) {
    alert("Error de conexión al subir imagen.");
    if (statusEl) statusEl.textContent = "Error de conexión";
  }
}

async function quickAdjustStock(productId, delta) {
  const prod = adminProductsList.find(p => p.id === productId);
  if (!prod) return;
  const newStock = Math.max(0, prod.stock + delta);
  try {
    const res = await fetch(`/api/admin/products/${productId}`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ stock: newStock })
    });
    if (res.ok) loadAdminProducts();
  } catch (e) { alert("Error al actualizar stock."); }
}

async function deleteProduct(id) {
  if (!confirm("¿Eliminar este producto? Esta acción no se puede deshacer.")) return;
  try {
    const res = await fetch(`/api/admin/products/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) {
      showAdminToast("Producto eliminado correctamente.", "success");
      loadAdminProducts();
    } else {
      const err = await res.json().catch(() => ({}));
      showAdminToast(err.detail || "Error al eliminar producto.", "error");
      loadAdminProducts();
    }
  } catch (e) {
    showAdminToast("Error de conexión al eliminar producto.", "error");
  }
}

function openProductModal() {
  currentModalType = "product";
  editingRecordId = null;
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = "+ AGREGAR PRODUCTO AL INVENTARIO";
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
      <div class="form-group">
        <label>NOMBRE DEL PRODUCTO</label>
        <input type="text" id="modal_product_name" class="form-control" placeholder="Ej: Cera Modeladora Matte" required>
      </div>
      <div class="form-group">
        <label>PRECIO DE VENTA ($)</label>
        <input type="number" step="0.01" id="modal_product_price" class="form-control" placeholder="12500" required>
      </div>
      <div class="form-group">
        <label>STOCK ACTUAL</label>
        <input type="number" id="modal_product_stock" class="form-control" value="15" required>
      </div>
      <div class="form-group">
        <label>STOCK MÍNIMO (ALERTA)</label>
        <input type="number" id="modal_product_min_stock" class="form-control" value="3" required>
      </div>
      <div class="form-group">
        <label>CATEGORÍA</label>
        <input type="text" id="modal_product_category" class="form-control" placeholder="Ej: Ceras & Pomadas, Cuidado Barba" value="Ceras & Pomadas">
      </div>
      <div class="form-group">
        <label>IMAGEN (SUBIR DESDE CELULAR/PC O PEGAR LINK URL)</label>
        <input type="file" accept="image/*" onchange="uploadProductFileAdmin(this)" class="form-control" style="padding: 6px; margin-bottom: 6px;">
        <input type="text" id="modal_product_image" class="form-control" placeholder="/static/products/cera.jpg u URL..." oninput="document.getElementById('admin_img_preview').src=this.value; document.getElementById('admin_img_preview').style.display=this.value?'block':'none';">
        <div style="display: flex; align-items: center; gap: 10px; margin-top: 6px;">
          <img id="admin_img_preview" src="" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px; display: none;">
          <span id="admin_img_status" style="font-size: 0.75rem; color: #9ca3af;">Foto de cámara/galería o link web.</span>
        </div>
      </div>
      <div class="form-group">
        <label>DESCRIPCIÓN</label>
        <input type="text" id="modal_product_desc" class="form-control" placeholder="Fijación fuerte efecto mate 100g">
      </div>
    `;
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}

async function editProductModal(id) {
  let p = adminProductsList.find(item => item.id == id);
  if (!p) {
    try {
      const res = await fetch("/api/admin/products", { headers: authHeaders() });
      if (res.ok) {
        adminProductsList = await res.json();
        p = adminProductsList.find(item => item.id == id);
      }
    } catch (e) {}
  }
  if (!p) {
    showAdminToast("No se encontró el producto en el servidor. Actualizando...", "warning");
    loadAdminProducts();
    return;
  }
  currentModalType = "product";
  editingRecordId = id;
  const initialImg = p.image_url || '';
  const titleEl = document.getElementById("modalAdminTitle");
  if (titleEl) titleEl.textContent = `✏️ EDITAR PRODUCTO #${id}`;
  const bodyEl = document.getElementById("modalAdminBody");
  if (bodyEl) {
    bodyEl.innerHTML = `
      <div class="form-group">
        <label>NOMBRE DEL PRODUCTO</label>
        <input type="text" id="modal_product_name" class="form-control" value="${escapeHtml(p.name)}" required>
      </div>
      <div class="form-group">
        <label>PRECIO DE VENTA ($)</label>
        <input type="number" step="0.01" id="modal_product_price" class="form-control" value="${p.price}" required>
      </div>
      <div class="form-group">
        <label>STOCK ACTUAL</label>
        <input type="number" id="modal_product_stock" class="form-control" value="${p.stock}" required>
      </div>
      <div class="form-group">
        <label>STOCK MÍNIMO (ALERTA CRÍTICA)</label>
        <input type="number" id="modal_product_min_stock" class="form-control" value="${p.min_stock}" required>
      </div>
      <div class="form-group">
        <label>CATEGORÍA</label>
        <input type="text" id="modal_product_category" class="form-control" value="${escapeHtml(p.category_name || 'Ceras & Pomadas')}">
      </div>
      <div class="form-group">
        <label>IMAGEN (SUBIR DESDE CELULAR/PC O PEGAR LINK URL)</label>
        <input type="file" accept="image/*" onchange="uploadProductFileAdmin(this)" class="form-control" style="padding: 6px; margin-bottom: 6px;">
        <input type="text" id="modal_product_image" class="form-control" value="${escapeHtml(initialImg)}" oninput="document.getElementById('admin_img_preview').src=this.value; document.getElementById('admin_img_preview').style.display=this.value?'block':'none';">
        <div style="display: flex; align-items: center; gap: 10px; margin-top: 6px;">
          <img id="admin_img_preview" src="${escapeHtml(initialImg)}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px; ${initialImg ? 'display:block;' : 'display:none;'}">
          <span id="admin_img_status" style="font-size: 0.75rem; color: #9ca3af;">Foto de cámara/galería o link web.</span>
        </div>
      </div>
      <div class="form-group">
        <label>DESCRIPCIÓN</label>
        <input type="text" id="modal_product_desc" class="form-control" value="${escapeHtml(p.description || '')}">
      </div>
    `;
  }
  const modalEl = document.getElementById("adminModal");
  if (modalEl) modalEl.style.display = "flex";
}
