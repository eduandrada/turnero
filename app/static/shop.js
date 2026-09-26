/**
 * Shop Barber Controller - BladeSync E-Commerce Engine 2026
 */

// Web Audio API Micro-Sound Synthesizer
const UISound = {
  ctx: null,
  enabled: true,
  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  },
  play(type = "click") {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.ctx.destination);

      if (type === "click") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(600, now);
        osc.frequency.exponentialRampToValueAtTime(160, now + 0.04);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      } else if (type === "add_cart") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.setValueAtTime(659.25, now + 0.05);
        osc.frequency.setValueAtTime(783.99, now + 0.1);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        osc.start(now);
        osc.stop(now + 0.18);
      } else if (type === "success") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554.37, now + 0.08);
        osc.frequency.setValueAtTime(659.25, now + 0.16);
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === "tab") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(400, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.03);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);
        osc.start(now);
        osc.stop(now + 0.03);
      }
    } catch (e) {}
  }
};

function togglePunchiVideoMute() {
  const vid = document.getElementById("punchiVideo");
  const btn = document.getElementById("btnMutePunchi");
  if (!vid) return;
  vid.muted = !vid.muted;
  if (!vid.muted) {
    vid.play().catch(() => {});
    if (btn) btn.innerHTML = "🔊 Sonido ON";
    UISound.play("success");
  } else {
    if (btn) btn.innerHTML = "🔇 Mutear";
    UISound.play("tab");
  }
}

function togglePunchiVideoPlay() {
  const vid = document.getElementById("punchiVideo");
  const btn = document.getElementById("btnPlayPunchi");
  if (!vid) return;
  if (vid.paused) {
    vid.play();
    if (btn) btn.innerHTML = "⏸️ Pausa";
    UISound.play("click");
  } else {
    vid.pause();
    if (btn) btn.innerHTML = "▶️ Play";
    UISound.play("click");
  }
}

let shopState = {
  products: [],
  categories: [],
  deliveryZones: [],
  cart: [], // [{ product, quantity }]
  selectedCategory: null,
  shopSettings: {}
};

document.addEventListener("DOMContentLoaded", async () => {
  loadCartFromStorage();
  await loadShopSettings();
  await loadShopCategories();
  await loadShopProducts();
  await loadDeliveryZones();
  updateCartUI();

  // Bind UI sounds on button clicks
  document.body.addEventListener("click", (e) => {
    const btn = e.target.closest("button, a, select, input[type='submit']");
    if (btn && !btn.hasAttribute("data-no-sound")) {
      UISound.play("click");
    }
  });
});

function loadCartFromStorage() {
  try {
    const stored = localStorage.getItem("bladesync_shop_cart");
    if (stored) shopState.cart = JSON.parse(stored);
  } catch (e) {
    shopState.cart = [];
  }
}

function saveCartToStorage() {
  localStorage.setItem("bladesync_shop_cart", JSON.stringify(shopState.cart));
  updateCartUI();
}

async function loadShopSettings() {
  try {
    const res = await fetch("/api/public/settings");
    if (res.ok) {
      const s = await res.json();
      shopState.shopSettings = s;

      // CSS Theme Variables
      const root = document.documentElement;
      if (s.color_primary) {
        root.style.setProperty('--color-primary', s.color_primary);
        root.style.setProperty('--neon-volt', s.color_primary);
      }
      if (s.color_secondary) root.style.setProperty('--color-secondary', s.color_secondary);
      if (s.color_accent) root.style.setProperty('--color-accent', s.color_accent);
      if (s.color_background) {
        root.style.setProperty('--color-background', s.color_background);
        root.style.setProperty('--obsidian', s.color_background);
      }
      if (s.color_surface) {
        root.style.setProperty('--color-surface', s.color_surface);
        root.style.setProperty('--surface', s.color_surface);
      }
      if (s.color_text) root.style.setProperty('--color-text', s.color_text);
      if (s.color_muted) root.style.setProperty('--color-muted', s.color_muted);
      if (s.color_button) root.style.setProperty('--color-button', s.color_button);
      if (s.color_border) {
        root.style.setProperty('--color-border', s.color_border);
        root.style.setProperty('--surface-border', s.color_border);
      }

      const bName = s.barber_name || s.app_name || "Turnero";
      document.title = `${bName} // Shop Barber`;

      const shopBrand = document.getElementById("shopHeaderBrandTitle");
      if (shopBrand) {
        if (s.logo_url) {
          shopBrand.innerHTML = `<img src="${s.logo_url}" alt="${escapeHtml(bName)}" class="h-8 md:h-10 object-contain inline-block mr-2" /> <span class="hidden md:inline">${escapeHtml(bName.toUpperCase())}</span>`;
        } else {
          shopBrand.innerHTML = `${escapeHtml(bName.toUpperCase())}<span class="text-[#d4ff00]">_</span>`;
        }
      }

      const title = document.getElementById("shopTitle");
      const desc = document.getElementById("shopDescription");
      if (title && s.text_shop) {
        title.textContent = s.text_shop;
      }
      if (desc && s.description) {
        desc.textContent = s.description;
      }
    }
  } catch (e) {}
}

async function loadShopCategories() {
  try {
    const res = await fetch("/api/shop/categories");
    if (res.ok) {
      shopState.categories = await res.json();
      renderCategoryFilters();
    }
  } catch (e) {}
}

function renderCategoryFilters() {
  const container = document.getElementById("shopCategoriesFilter");
  if (!container) return;
  container.innerHTML = "";

  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.className = `px-3.5 py-1.5 rounded-full text-xs font-mono shrink-0 transition ${
    shopState.selectedCategory === null ? "bg-[#d4ff00] text-black font-bold" : "bg-[#1a1a22] text-gray-300 border border-[#23232c]"
  }`;
  allBtn.textContent = "Todos";
  allBtn.onclick = () => filterByCategory(null);
  container.appendChild(allBtn);

  shopState.categories.forEach(cat => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `px-3.5 py-1.5 rounded-full text-xs font-mono shrink-0 transition ${
      shopState.selectedCategory === cat.id ? "bg-[#d4ff00] text-black font-bold" : "bg-[#1a1a22] text-gray-300 border border-[#23232c]"
    }`;
    btn.textContent = cat.name;
    btn.onclick = () => filterByCategory(cat.id);
    container.appendChild(btn);
  });
}

function filterByCategory(catId) {
  shopState.selectedCategory = catId;
  renderCategoryFilters();
  renderProducts();
}

async function loadShopProducts() {
  try {
    const res = await fetch("/api/shop/products");
    if (res.ok) {
      shopState.products = await res.json();
      renderProducts();
    }
  } catch (e) {}
}

function renderProducts() {
  const grid = document.getElementById("shopProductsGrid");
  if (!grid) return;
  grid.innerHTML = "";

  let list = shopState.products;
  if (shopState.selectedCategory) {
    list = list.filter(p => p.category_id === shopState.selectedCategory);
  }

  if (list.length === 0) {
    grid.innerHTML = '<div class="col-span-1 sm:col-span-2 text-center text-xs text-gray-500 py-8 font-mono">No hay productos disponibles en esta categoría.</div>';
    return;
  }

  list.forEach(p => {
    const card = document.createElement("div");
    card.className = "product-card";

    const isOutOfStock = p.stock <= 0;
    const hasDiscount = p.previous_price && p.previous_price > p.price;

    card.innerHTML = `
      <div>
        <img src="${p.image_url || 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=400&q=80'}" alt="${escapeHtml(p.name)}" class="product-img">
        <span class="text-[10px] font-mono text-[#00f2fe] uppercase block mb-1">${escapeHtml(p.category_name || 'Shop')}</span>
        <h3 class="product-title">${escapeHtml(p.name)}</h3>
        <p class="text-xs text-gray-400 mb-3 line-clamp-2">${escapeHtml(p.description || '')}</p>
      </div>

      <div>
        <div class="flex items-baseline mb-3">
          <span class="product-price">$${p.price.toLocaleString("es-AR")}</span>
          ${hasDiscount ? `<span class="product-old-price">$${p.previous_price.toLocaleString("es-AR")}</span>` : ''}
        </div>

        <button onclick="addToCart(${p.id})" ${isOutOfStock ? 'disabled' : ''} class="w-full py-2.5 rounded-xl font-mono text-xs font-bold transition flex items-center justify-center gap-1.5 ${
          isOutOfStock ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-[#d4ff00] text-black hover:bg-[#d4ff00]/90 active:scale-95'
        }">
          <span>${isOutOfStock ? 'AGOTADO' : 'AGREGAR AL CARRITO'}</span>
        </button>
      </div>
    `;

    grid.appendChild(card);
  });
}

function addToCart(prodId) {
  const prod = shopState.products.find(p => p.id === prodId);
  if (!prod || prod.stock <= 0) return;

  const existing = shopState.cart.find(item => item.product.id === prodId);
  if (existing) {
    if (existing.quantity < prod.stock) {
      existing.quantity += 1;
      UISound.play("add_cart");
    } else {
      alert(`Alcanzaste el límite de stock disponible (${prod.stock} un.)`);
    }
  } else {
    shopState.cart.push({ product: prod, quantity: 1 });
    UISound.play("add_cart");
  }

  saveCartToStorage();
}

function removeFromCart(prodId) {
  shopState.cart = shopState.cart.filter(item => item.product.id !== prodId);
  saveCartToStorage();
}

function changeCartQty(prodId, delta) {
  const item = shopState.cart.find(i => i.product.id === prodId);
  if (!item) return;

  item.quantity += delta;
  if (item.quantity <= 0) {
    removeFromCart(prodId);
  } else if (item.quantity > item.product.stock) {
    item.quantity = item.product.stock;
    alert(`Stock máximo disponible: ${item.product.stock} un.`);
    saveCartToStorage();
  } else {
    saveCartToStorage();
  }
}

function updateCartUI() {
  const badge = document.getElementById("cartCountBadge");
  const totalCount = shopState.cart.reduce((sum, item) => sum + item.quantity, 0);
  if (badge) badge.textContent = totalCount;

  const container = document.getElementById("cartItemsContainer");
  const subtotalEl = document.getElementById("cartSubtotal");
  if (!container) return;

  container.innerHTML = "";
  let subtotal = 0;

  if (shopState.cart.length === 0) {
    container.innerHTML = '<div class="text-center text-xs text-gray-500 py-12 font-mono">Tu carrito está vacío.</div>';
    if (subtotalEl) subtotalEl.textContent = "$0";
    return;
  }

  shopState.cart.forEach(item => {
    const itemSub = item.product.price * item.quantity;
    subtotal += itemSub;

    const div = document.createElement("div");
    div.className = "flex items-center justify-between p-3 rounded-xl bg-[#1a1a22] border border-[#23232c]";
    div.innerHTML = `
      <div class="flex items-center gap-3">
        <img src="${item.product.image_url || ''}" class="w-10 h-10 object-cover rounded-lg">
        <div>
          <h4 class="text-xs font-bold text-white max-w-[140px] truncate">${escapeHtml(item.product.name)}</h4>
          <span class="text-[11px] font-mono text-[#d4ff00] font-bold">$${item.product.price.toLocaleString("es-AR")}</span>
        </div>
      </div>

      <div class="flex items-center gap-2 font-mono text-xs">
        <button onclick="changeCartQty(${item.product.id}, -1)" class="w-6 h-6 rounded bg-black text-gray-300 flex items-center justify-center font-bold">−</button>
        <span class="text-white font-bold px-1">${item.quantity}</span>
        <button onclick="changeCartQty(${item.product.id}, 1)" class="w-6 h-6 rounded bg-black text-gray-300 flex items-center justify-center font-bold">+</button>
        <button onclick="removeFromCart(${item.product.id})" class="text-red-400 hover:text-red-300 ml-2">✕</button>
      </div>
    `;
    container.appendChild(div);
  });

  if (subtotalEl) subtotalEl.textContent = `$${subtotal.toLocaleString("es-AR")}`;
}

function toggleCartDrawer() {
  const drawer = document.getElementById("cartDrawer");
  if (drawer) drawer.classList.toggle("hidden");
}

async function loadDeliveryZones() {
  try {
    const res = await fetch("/api/shop/delivery-zones");
    if (res.ok) {
      shopState.deliveryZones = await res.json();
      renderDeliveryZoneOptions();
    }
  } catch (e) {}
}

function renderDeliveryZoneOptions() {
  const sel = document.getElementById("chkDeliveryZone");
  if (!sel) return;
  sel.innerHTML = "";

  shopState.deliveryZones.forEach(dz => {
    const opt = document.createElement("option");
    opt.value = dz.id;
    opt.textContent = `${dz.name} (+$${dz.cost.toLocaleString("es-AR")})`;
    sel.appendChild(opt);
  });
}

function toggleDeliveryZoneSelect() {
  const type = document.getElementById("chkDeliveryType").value;
  const zoneGroup = document.getElementById("deliveryZoneGroup");
  const addressGroup = document.getElementById("addressGroup");

  if (type === "delivery") {
    if (zoneGroup) zoneGroup.classList.remove("hidden");
    if (addressGroup) addressGroup.classList.remove("hidden");
  } else {
    if (zoneGroup) zoneGroup.classList.add("hidden");
    if (addressGroup) addressGroup.classList.add("hidden");
  }

  updateCheckoutTotal();
}

function openCheckoutModal() {
  if (shopState.cart.length === 0) {
    alert("Agrega al menos un producto al carrito antes de hacer un pedido.");
    return;
  }
  toggleCartDrawer();
  const modal = document.getElementById("checkoutModal");
  if (modal) modal.classList.remove("hidden");
  updateCheckoutTotal();
}

function closeCheckoutModal() {
  const modal = document.getElementById("checkoutModal");
  if (modal) modal.classList.add("hidden");
}

function updateCheckoutTotal() {
  const subtotal = shopState.cart.reduce((sum, i) => sum + (i.product.price * i.quantity), 0);
  const type = document.getElementById("chkDeliveryType").value;

  let deliveryCost = 0;
  if (type === "delivery") {
    const zoneId = parseInt(document.getElementById("chkDeliveryZone").value || "0");
    const zone = shopState.deliveryZones.find(z => z.id === zoneId);
    if (zone) deliveryCost = zone.cost;
  }

  const total = subtotal + deliveryCost;

  document.getElementById("chkSubtotal").textContent = `$${subtotal.toLocaleString("es-AR")}`;
  document.getElementById("chkDeliveryCost").textContent = `$${deliveryCost.toLocaleString("es-AR")}`;
  document.getElementById("chkTotal").textContent = `$${total.toLocaleString("es-AR")}`;
}

async function submitShopOrder() {
  const name = document.getElementById("chkName").value.trim();
  const phone = document.getElementById("chkPhone").value.trim();
  const type = document.getElementById("chkDeliveryType").value;
  const zoneId = type === "delivery" ? parseInt(document.getElementById("chkDeliveryZone").value || "0") : null;
  const address = type === "delivery" ? document.getElementById("chkAddress").value.trim() : "";
  const payment = document.getElementById("chkPaymentMethod").value;

  if (!name || !phone) {
    alert("Por favor completa tu Nombre y WhatsApp.");
    return;
  }

  const btn = document.getElementById("btnSubmitOrder");
  btn.disabled = true;
  btn.textContent = "GENERANDO PEDIDO...";

  const payload = {
    client_name: name,
    client_phone: phone,
    delivery_type: type,
    delivery_zone_id: zoneId,
    address: address,
    payment_method: payment,
    items: shopState.cart.map(i => ({ product_id: i.product.id, quantity: i.quantity }))
  };

  try {
    const res = await fetch("/api/shop/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      // Vaciar carrito
      shopState.cart = [];
      saveCartToStorage();
      closeCheckoutModal();

      // Coordinar por WhatsApp
      coordinatingWhatsAppOrder(data);
    } else {
      alert(data.detail || "Error al generar pedido.");
    }
  } catch (e) {
    alert("Error de conexión al servidor.");
  } finally {
    btn.disabled = false;
    btn.textContent = "CONFIRMAR PEDIDO Y COORDINAR WHATSAPP →";
  }
}

function coordinatingWhatsAppOrder(order) {
  const barberPhone = shopState.shopSettings.whatsapp || "5493834123456";
  const cleanPhone = barberPhone.replace(/\D/g, "");

  let msg = `🛍️ *NUEVO PEDIDO DE SHOP BARBER #${order.order_number}*\n\n`;
  msg += `👤 *Cliente:* ${order.client_name}\n`;
  msg += `📱 *WhatsApp:* ${order.client_phone}\n`;
  msg += `🚚 *Forma de Entrega:* ${order.delivery_type === 'delivery' ? 'Delivery' : 'Retiro en Barbería'}\n`;
  if (order.address) msg += `📍 *Dirección:* ${order.address}\n`;
  msg += `💳 *Pago:* ${order.payment_method}\n\n`;

  msg += `📦 *Detalle del Pedido:*\n`;
  order.items.forEach(it => {
    msg += `• ${it.product_name} x${it.quantity} = $${it.subtotal.toLocaleString("es-AR")}\n`;
  });

  msg += `\n💰 *Subtotal:* $${order.subtotal.toLocaleString("es-AR")}\n`;
  msg += `🚚 *Delivery:* $${order.delivery_cost.toLocaleString("es-AR")}\n`;
  msg += `⭐ *TOTAL:* $${order.total.toLocaleString("es-AR")}\n\n`;
  msg += `¡Hola! Acabo de realizar este pedido desde el Shop. ¿Cómo coordinamos el pago/entrega?`;

  const waUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}`;
  window.open(waUrl, "_blank");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (typeof closeCart === "function") closeCart();
    const modal = document.getElementById("productModal");
    if (modal) modal.style.display = "none";
  }
});
