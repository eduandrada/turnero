/**
 * Shop Barber Controller - HiddenSYNC E-Commerce Engine 2026
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
  shopSettings: {},
  activeCoupon: null, // { code, type, value, description }
  bannerSlides: [],
  currentSlideIndex: 0,
  carouselTimer: null
};

document.addEventListener("DOMContentLoaded", async () => {
  loadCartFromStorage();
  await Promise.all([
    loadShopSettings(),
    loadShopCategories(),
    loadShopProducts(),
    loadDeliveryZones()
  ]);
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
    const stored = localStorage.getItem("hiddensync_shop_cart") || localStorage.getItem("bladesync_shop_cart");
    if (stored) shopState.cart = JSON.parse(stored);
    const savedCoupon = localStorage.getItem("hiddensync_shop_coupon");
    if (savedCoupon) shopState.activeCoupon = JSON.parse(savedCoupon);
  } catch (e) {
    shopState.cart = [];
  }
}

function saveCartToStorage() {
  localStorage.setItem("hiddensync_shop_cart", JSON.stringify(shopState.cart));
  if (shopState.activeCoupon) {
    localStorage.setItem("hiddensync_shop_coupon", JSON.stringify(shopState.activeCoupon));
  } else {
    localStorage.removeItem("hiddensync_shop_coupon");
  }
  updateCartUI();
}

async function loadShopSettings() {
  try {
    const res = await fetch("/api/public/settings");
    if (res.ok) {
      const s = await res.json();
      shopState.shopSettings = s;

      // Cargar slides del carrusel de banners
      if (s.shop_banner_slides) {
        try {
          shopState.bannerSlides = typeof s.shop_banner_slides === "string" ? JSON.parse(s.shop_banner_slides) : s.shop_banner_slides;
        } catch (e) {
          shopState.bannerSlides = [];
        }
      }

      renderPromoCarousel();

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

      const bName = s.barber_name || s.app_name || "SHOP BARBER";
      document.title = `${bName} // Shop Barber`;

      const shopBrandImg = document.getElementById("shopHeaderLogoImg");
      if (shopBrandImg) {
        shopBrandImg.src = "/static/img/barbershop.png";
      }

      const shopBrand = document.getElementById("shopHeaderBrandTitle");
      if (shopBrand) {
        shopBrand.innerHTML = `SHOP BARBER<span class="text-[#d4ff00]">_</span>`;
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

// CARRUSEL DE BANNERS PROMOCIONALES DINÁMICO
function renderPromoCarousel() {
  const slidesContainer = document.getElementById("promoCarouselSlides");
  const dotsContainer = document.getElementById("promoCarouselDots");
  if (!slidesContainer) return;

  slidesContainer.innerHTML = "";
  if (dotsContainer) dotsContainer.innerHTML = "";

  const slides = shopState.bannerSlides && shopState.bannerSlides.length > 0 ? shopState.bannerSlides : [
    {
      id: 1,
      title: "COMBO CUIDADO DE AUTOR",
      subtitle: "Pomada Mate + Aceite Esencial con 15% OFF",
      badge: "🔥 PROMO CLUB",
      image_url: "/static/img/fondo.png",
      coupon: "BARBER15"
    },
    {
      id: 2,
      title: "SERUMS & ACEITES ESENCIALES",
      subtitle: "Brillo natural e hidratación profunda 24 hs",
      badge: "⭐ RECOMENDADO",
      image_url: "/static/img/fondo3.png",
      coupon: "BARBER10"
    }
  ];

  shopState.bannerSlides = slides;

  slides.forEach((slide, idx) => {
    const slideDiv = document.createElement("div");
    slideDiv.className = "w-full shrink-0 p-6 flex flex-col justify-center relative overflow-hidden bg-cover bg-center min-h-[170px] sm:min-h-[200px]";
    slideDiv.style.backgroundImage = `linear-gradient(to right, rgba(19, 19, 24, 0.92) 35%, rgba(19, 19, 24, 0.45)), url('${slide.image_url || '/static/img/fondo.png'}')`;

    slideDiv.innerHTML = `
      <div class="relative z-10 flex flex-col items-start gap-1.5 max-w-sm">
        <span class="text-[10px] font-mono font-extrabold uppercase tracking-widest text-[#d4ff00] px-2.5 py-0.5 rounded-full bg-[#d4ff00]/15 border border-[#d4ff00]/30 shadow-sm">
          ${escapeHtml(slide.badge || 'OFERTA DESTACADA')}
        </span>
        <h2 class="text-lg sm:text-xl font-extrabold font-mono text-white tracking-tight leading-tight">${escapeHtml(slide.title)}</h2>
        <p class="text-xs text-gray-200 line-clamp-2">${escapeHtml(slide.subtitle || '')}</p>
        ${slide.coupon ? `
          <button type="button" onclick="applyCouponFromSlide('${escapeHtml(slide.coupon)}')" class="mt-1 px-3.5 py-1.5 rounded-full bg-[#d4ff00] text-black font-mono font-bold text-xs hover:bg-[#d4ff00]/90 transition shadow flex items-center gap-1.5">
            <span>🎟️ USAR CUPÓN ${escapeHtml(slide.coupon)}</span>
          </button>
        ` : ''}
      </div>
    `;
    slidesContainer.appendChild(slideDiv);

    if (dotsContainer) {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = `w-2.5 h-2.5 rounded-full transition-all ${idx === 0 ? 'bg-[#d4ff00] w-6' : 'bg-white/30 hover:bg-white/60'}`;
      dot.onclick = () => goToPromoSlide(idx);
      dotsContainer.appendChild(dot);
    }
  });

  goToPromoSlide(0);
  startPromoCarouselAutoPlay();
}

function goToPromoSlide(index) {
  const slidesContainer = document.getElementById("promoCarouselSlides");
  const dotsContainer = document.getElementById("promoCarouselDots");
  if (!slidesContainer) return;

  const total = shopState.bannerSlides.length;
  if (total === 0) return;

  shopState.currentSlideIndex = (index + total) % total;
  slidesContainer.style.transform = `translateX(-${shopState.currentSlideIndex * 100}%)`;

  if (dotsContainer) {
    const dots = dotsContainer.querySelectorAll("button");
    dots.forEach((dot, idx) => {
      if (idx === shopState.currentSlideIndex) {
        dot.className = "w-6 h-2.5 rounded-full bg-[#d4ff00] transition-all";
      } else {
        dot.className = "w-2.5 h-2.5 rounded-full bg-white/30 hover:bg-white/60 transition-all";
      }
    });
  }
}

function nextPromoSlide() {
  goToPromoSlide(shopState.currentSlideIndex + 1);
}

function prevPromoSlide() {
  goToPromoSlide(shopState.currentSlideIndex - 1);
}

function startPromoCarouselAutoPlay() {
  if (shopState.carouselTimer) clearInterval(shopState.carouselTimer);
  shopState.carouselTimer = setInterval(() => {
    nextPromoSlide();
  }, 6000);
}

function applyCouponFromSlide(code) {
  const input = document.getElementById("cartCouponInput");
  if (input) input.value = code;
  applyCartCoupon(code);
  toggleCartDrawer();
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

function applyCartCoupon(explicitCode = null) {
  const input = document.getElementById("cartCouponInput");
  const code = (explicitCode || (input ? input.value : "")).trim().toUpperCase();
  const msgEl = document.getElementById("couponMsg");

  if (!code) {
    shopState.activeCoupon = null;
    saveCartToStorage();
    if (msgEl) msgEl.textContent = "Ingresá un código de descuento arriba.";
    return;
  }

  // Cargar cupones disponibles
  let availableCoupons = [];
  if (shopState.shopSettings.shop_coupons) {
    try {
      availableCoupons = typeof shopState.shopSettings.shop_coupons === "string" ? JSON.parse(shopState.shopSettings.shop_coupons) : shopState.shopSettings.shop_coupons;
    } catch(e) {}
  }
  if (availableCoupons.length === 0) {
    availableCoupons = [
      { code: "BARBER10", type: "percent", value: 10, active: true, description: "10% de descuento en tu compra" },
      { code: "BARBER15", type: "percent", value: 15, active: true, description: "15% de descuento exclusivo Club" },
      { code: "CLUB20", type: "percent", value: 20, active: true, description: "20% de descuento socio VIP" },
      { code: "VIP500", type: "fixed", value: 500, active: true, description: "$500 de regalo en tu compra" }
    ];
  }

  const match = availableCoupons.find(c => c.code.toUpperCase() === code && (c.active === undefined || c.active === true));

  if (match) {
    shopState.activeCoupon = match;
    saveCartToStorage();
    if (msgEl) msgEl.textContent = `✅ ${match.description || '¡Descuento aplicado!'}`;
    UISound.play("success");
  } else {
    shopState.activeCoupon = null;
    saveCartToStorage();
    if (msgEl) msgEl.textContent = "❌ Código de descuento no válido o vencido.";
  }
}

function updateCartUI() {
  const badge = document.getElementById("cartCountBadge");
  const totalCount = shopState.cart.reduce((sum, item) => sum + item.quantity, 0);
  if (badge) badge.textContent = totalCount;

  const container = document.getElementById("cartItemsContainer");
  const subtotalEl = document.getElementById("cartSubtotal");
  const discountRow = document.getElementById("cartDiscountRow");
  const discountAmountEl = document.getElementById("cartDiscountAmount");
  const totalEl = document.getElementById("cartTotal");
  const badgeCoupon = document.getElementById("couponStatusBadge");

  if (!container) return;

  container.innerHTML = "";
  let subtotal = 0;

  if (shopState.cart.length === 0) {
    container.innerHTML = '<div class="text-center text-xs text-gray-500 py-12 font-mono">Tu carrito está vacío.</div>';
    if (subtotalEl) subtotalEl.textContent = "$0";
    if (totalEl) totalEl.textContent = "$0";
    if (discountRow) discountRow.classList.add("hidden");
    if (badgeCoupon) {
      badgeCoupon.textContent = "🏷️ Precio de Lista";
      badgeCoupon.className = "text-[10px] font-mono text-gray-400 font-bold px-2 py-0.5 rounded-full bg-black/60 border border-[#23232c]";
    }
    return;
  }

  shopState.cart.forEach(item => {
    const itemSub = item.product.price * item.quantity;
    subtotal += itemSub;

    const div = document.createElement("div");
    div.className = "flex items-center justify-between p-3 rounded-xl bg-[#1a1a22] border border-[#23232c]";
    div.innerHTML = `
      <div class="flex items-center gap-3">
        <img src="${item.product.image_url || 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=100&q=80'}" class="w-12 h-12 object-cover rounded-xl border border-[#23232c]">
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

  // Cálculo de Descuento
  let discountVal = 0;
  if (shopState.activeCoupon) {
    const c = shopState.activeCoupon;
    if (c.type === "percent") {
      discountVal = Math.round(subtotal * (c.value / 100));
    } else if (c.type === "fixed") {
      discountVal = Math.min(subtotal, c.value);
    }
  }

  const finalTotal = Math.max(0, subtotal - discountVal);

  if (subtotalEl) subtotalEl.textContent = `$${subtotal.toLocaleString("es-AR")}`;

  if (discountVal > 0 && shopState.activeCoupon) {
    if (discountRow) discountRow.classList.remove("hidden");
    if (discountAmountEl) discountAmountEl.textContent = `-$${discountVal.toLocaleString("es-AR")}`;
    if (badgeCoupon) {
      badgeCoupon.textContent = `🎟️ ${shopState.activeCoupon.code} (-${shopState.activeCoupon.type === 'percent' ? shopState.activeCoupon.value + '%' : '$' + shopState.activeCoupon.value})`;
      badgeCoupon.className = "text-[10px] font-mono text-emerald-400 font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30";
    }
  } else {
    if (discountRow) discountRow.classList.add("hidden");
    if (badgeCoupon) {
      badgeCoupon.textContent = "🏷️ Precio de Lista";
      badgeCoupon.className = "text-[10px] font-mono text-gray-400 font-bold px-2 py-0.5 rounded-full bg-black/60 border border-[#23232c]";
    }
  }

  if (totalEl) totalEl.textContent = `$${finalTotal.toLocaleString("es-AR")}`;
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

  let discountVal = 0;
  if (shopState.activeCoupon) {
    const c = shopState.activeCoupon;
    if (c.type === "percent") {
      discountVal = Math.round(subtotal * (c.value / 100));
    } else if (c.type === "fixed") {
      discountVal = Math.min(subtotal, c.value);
    }
  }

  const total = Math.max(0, subtotal - discountVal + deliveryCost);

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

  const idempotencyKey = "order_" + Date.now() + "_" + Math.random().toString(36).substring(2, 10);
  const payload = {
    client_name: name,
    client_phone: phone,
    delivery_type: type,
    delivery_zone_id: zoneId,
    address: address,
    payment_method: payment,
    idempotency_key: idempotencyKey,
    items: shopState.cart.map(i => ({ product_id: i.product.id, quantity: i.quantity }))
  };

  try {
    const res = await fetch("/api/shop/orders", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotencyKey
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      // Vaciar carrito y cupón
      const appliedCoupon = shopState.activeCoupon;
      shopState.cart = [];
      shopState.activeCoupon = null;
      saveCartToStorage();
      closeCheckoutModal();

      // Coordinar por WhatsApp
      coordinatingWhatsAppOrder(data, appliedCoupon);
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

function coordinatingWhatsAppOrder(order, coupon = null) {
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
  if (coupon) {
    msg += `🎟️ *Voucher Aplicado:* ${coupon.code} (${coupon.description || ''})\n`;
  }
  msg += `🚚 *Delivery:* $${order.delivery_cost.toLocaleString("es-AR")}\n`;
  msg += `⭐ *TOTAL FINAL:* $${order.total.toLocaleString("es-AR")}\n\n`;
  msg += `¡Hola! Acabo de realizar este pedido desde el Shop Barber. ¿Cómo coordinamos el pago/entrega?`;

  const waUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}`;
  window.open(waUrl, "_blank");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// ==============================================================================
// STAFF GATEKEEPER - CONTROL DE ACCESO A INVENTARIO
// ==============================================================================
async function openStaffGatekeeperModal() {
  const token = localStorage.getItem("hiddensync_admin_token") || localStorage.getItem("bladesync_admin_token");
  if (token) {
    try {
      const res = await fetch("/api/admin/me", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const user = await res.json();
        const role = (user.role || "").toLowerCase();
        if (role === "admin" || role === "encargado") {
          window.location.href = "/inventario.html";
          return;
        }
      } else {
        localStorage.removeItem("hiddensync_admin_token");
        localStorage.removeItem("bladesync_admin_token");
      }
    } catch (e) {
      console.warn("Verificación de sesión de staff falló:", e);
    }
  }

  // Si no está autenticado como ENCARGADO o ADMIN, abrir modal flotante
  const modal = document.getElementById("gatekeeperModal");
  const errBox = document.getElementById("gatekeeperErrorMsg");
  if (errBox) errBox.classList.add("hidden");
  if (modal) {
    modal.classList.remove("hidden");
    const userInput = document.getElementById("gatekeeperUser");
    if (userInput) {
      userInput.value = "";
      setTimeout(() => userInput.focus(), 60);
    }
    const passInput = document.getElementById("gatekeeperPass");
    if (passInput) passInput.value = "";
  }
}

function closeGatekeeperModal() {
  const modal = document.getElementById("gatekeeperModal");
  if (modal) modal.classList.add("hidden");
  const errBox = document.getElementById("gatekeeperErrorMsg");
  if (errBox) errBox.classList.add("hidden");
  
  // Devolver el foco al botón de inventario en la tienda
  const btn = document.getElementById("btnStaffInventoryAccess");
  if (btn) btn.focus();
}

async function handleGatekeeperSubmit(event) {
  if (event) event.preventDefault();
  const username = (document.getElementById("gatekeeperUser")?.value || "").trim();
  const password = (document.getElementById("gatekeeperPass")?.value || "").trim();
  const errBox = document.getElementById("gatekeeperErrorMsg");
  const errText = document.getElementById("gatekeeperErrorText");
  const submitBtn = document.getElementById("btnGatekeeperLogin");

  if (!username || !password) {
    if (errText) errText.textContent = "Por favor ingrese usuario y contraseña.";
    if (errBox) errBox.classList.remove("hidden");
    return;
  }

  try {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span>Verificando permisos...</span>';
    }

    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    const token = data.access_token || data.token;
    if (res.ok && token) {
      const role = (data.role || "").toLowerCase();
      if (role === "admin" || role === "encargado") {
        localStorage.setItem("hiddensync_admin_token", token);
        localStorage.setItem("bladesync_admin_token", token);
        window.location.href = "/inventario.html";
        return;
      } else {
        if (errText) {
          errText.textContent = "Acceso denegado: El usuario no cuenta con rol administrativo (ENCARGADO o ADMIN).";
        }
        if (errBox) errBox.classList.remove("hidden");
      }
    } else {
      if (errText) {
        errText.textContent = data.detail || "Credenciales incorrectas o usuario inactivo.";
      }
      if (errBox) errBox.classList.remove("hidden");
    }
  } catch (err) {
    if (errText) errText.textContent = "Error de conexión con el servidor.";
    if (errBox) errBox.classList.remove("hidden");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>🔓 Acceder al Inventario</span>';
    }
  }
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const gkModal = document.getElementById("gatekeeperModal");
    if (gkModal && !gkModal.classList.contains("hidden")) {
      closeGatekeeperModal();
      return;
    }
    if (typeof closeCart === "function") closeCart();
    const modal = document.getElementById("productModal");
    if (modal) modal.style.display = "none";
  }
});
