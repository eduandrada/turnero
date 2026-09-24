/**
 * Master Multi-Screen Booking Engine & Public App Controller - 2026
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

let state = {
  currentScreen: "screen-intro",
  services: [],
  barbers: [],
  styles: [],
  settings: {},
  selectedService: null,
  selectedBarber: null,
  selectedDate: null,
  selectedSlot: null,
  aiRecommendation: null,
  bgMusicPlaying: false
};

// ==========================================
// ==========================================
// MÚSICA DE FONDO (AUDIO ONLY) & CONTROL MUTE/UNMUTE
// ==========================================
function initAudio() {
  const audio = document.getElementById("bgMusicPlayer");
  const icon = document.getElementById("audioIcon");
  const text = document.getElementById("audioText");
  if (!audio) return;

  audio.volume = 0.6;
  audio.muted = false;

  // Estado por defecto: MÚSICA ON
  state.bgMusicPlaying = true;
  if (icon) icon.textContent = "🔊";
  if (text) text.textContent = "Música ON";

  const tryPlay = () => {
    audio.play().then(() => {
      state.bgMusicPlaying = true;
      if (icon) icon.textContent = "🔊";
      if (text) text.textContent = "Música ON";
    }).catch(() => {
      // Si el navegador bloquea autoplay por falta de interacción previa del usuario,
      // la primera interacción (click o toque) iniciará el audio con sonido activado.
      const enableAudioOnGesture = () => {
        audio.play().then(() => {
          state.bgMusicPlaying = true;
          if (icon) icon.textContent = "🔊";
          if (text) text.textContent = "Música ON";
        }).catch(e => console.warn(e));
        document.removeEventListener("click", enableAudioOnGesture);
        document.removeEventListener("touchstart", enableAudioOnGesture);
      };
      document.addEventListener("click", enableAudioOnGesture, { once: true });
      document.addEventListener("touchstart", enableAudioOnGesture, { once: true });
    });
  };

  tryPlay();
}

function toggleBgMusic() {
  const audio = document.getElementById("bgMusicPlayer");
  const icon = document.getElementById("audioIcon");
  const text = document.getElementById("audioText");
  if (!audio) return;

  if (audio.paused) {
    audio.play().then(() => {
      state.bgMusicPlaying = true;
      if (icon) icon.textContent = "🔊";
      if (text) text.textContent = "Música ON";
    }).catch(err => {
      console.warn("Autoplay diferido:", err);
    });
  } else {
    audio.pause();
    state.bgMusicPlaying = false;
    if (icon) icon.textContent = "🔇";
    if (text) text.textContent = "Música OFF";
  }
}

// ==========================================
// SCREEN NAVIGATION
// ==========================================
function navigateTo(screenId) {
  const target = document.getElementById(screenId);
  if (!target) return;

  document.querySelectorAll(".screen-view").forEach(s => {
    s.classList.add("hidden");
    s.classList.remove("animate-fade-in");
  });

  target.classList.remove("hidden");
  target.classList.add("animate-fade-in");
  state.currentScreen = screenId;

  const navigator = document.getElementById("stepNavigator");
  if (screenId === "screen-intro") {
    if (navigator) navigator.classList.add("hidden");
  } else {
    if (navigator) navigator.classList.remove("hidden");
    updateNavigationUI(screenId);
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateNavigationUI(screenId) {
  const counterText = document.getElementById("stepCounterText");
  const breadcrumbCurrent = document.getElementById("breadcrumbCurrentStep");
  const breadcrumbSelected = document.getElementById("breadcrumbSelectedItems");

  const p1 = document.getElementById("stepPill1");
  const p2 = document.getElementById("stepPill2");
  const p3 = document.getElementById("stepPill3");
  const p4 = document.getElementById("stepPill4");

  const activePillClass = "bg-neonVolt shadow-volt-sm";
  const inactivePillClass = "bg-surfaceBorder";

  [p1, p2, p3, p4].forEach(p => { if (p) p.className = `h-1.5 rounded-full ${inactivePillClass} transition-all`; });

  if (screenId === "screen-barber") {
    if (counterText) counterText.textContent = "PASO 1 DE 4";
    if (breadcrumbCurrent) breadcrumbCurrent.textContent = "1. Elige tu Barbero/a";
    if (breadcrumbSelected) breadcrumbSelected.textContent = state.selectedBarber ? state.selectedBarber.name : "Sin elegir";
    if (p1) p1.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
  } else if (screenId === "screen-service") {
    if (counterText) counterText.textContent = "PASO 2 DE 4";
    if (breadcrumbCurrent) breadcrumbCurrent.textContent = "2. Estilo de Corte & Precio";
    if (breadcrumbSelected) {
      const bName = state.selectedBarber ? state.selectedBarber.name : "";
      const sName = state.selectedService ? ` • ${state.selectedService.name.split(' ')[0]}` : "";
      breadcrumbSelected.textContent = `${bName}${sName}`;
    }
    if (p1) p1.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
    if (p2) p2.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
  } else if (screenId === "screen-agenda") {
    if (counterText) counterText.textContent = "PASO 3 DE 4";
    if (breadcrumbCurrent) breadcrumbCurrent.textContent = "3. Agenda en Tiempo Real";
    if (breadcrumbSelected) breadcrumbSelected.textContent = state.selectedSlot ? `${state.selectedSlot} hs` : "Elige hora";
    if (p1) p1.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
    if (p2) p2.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
    if (p3) p3.className = `h-1.5 rounded-full ${activePillClass} transition-all`;
  } else if (screenId === "screen-confirm") {
    if (counterText) counterText.textContent = "PASO 4 DE 4";
    if (breadcrumbCurrent) breadcrumbCurrent.textContent = "4. Confirmación";
    if (breadcrumbSelected) breadcrumbSelected.textContent = state.selectedService ? `$${state.selectedService.price.toLocaleString("es-AR")}` : "";
    [p1, p2, p3, p4].forEach(p => { if (p) p.className = `h-1.5 rounded-full ${activePillClass} transition-all`; });
  }
}

function goBack() {
  if (state.currentScreen === "screen-barber") navigateTo("screen-intro");
  else if (state.currentScreen === "screen-service") navigateTo("screen-barber");
  else if (state.currentScreen === "screen-agenda") navigateTo("screen-service");
  else if (state.currentScreen === "screen-confirm") navigateTo("screen-agenda");
  else navigateTo("screen-intro");
}

function continueToServices() {
  if (!state.selectedBarber) {
    if (state.barbers.length > 0) selectBarber(state.barbers[0].id, false);
    else { alert("Por favor selecciona un barbero."); return; }
  }
  navigateTo("screen-service");
}

function continueToAgenda() {
  if (!state.selectedService) {
    if (state.services.length > 0) selectService(state.services[0].id, false);
    else { alert("Por favor selecciona un servicio."); return; }
  }

  const agendaBarber = document.getElementById("agendaBarberName");
  if (agendaBarber && state.selectedBarber) agendaBarber.textContent = state.selectedBarber.name;
  
  const agendaService = document.getElementById("agendaServiceName");
  if (agendaService && state.selectedService) agendaService.textContent = state.selectedService.name;

  loadSlots();
  navigateTo("screen-agenda");
}

function continueToConfirm() {
  if (!state.selectedSlot) {
    alert("Por favor selecciona un horario disponible.");
    return;
  }
  updateBookingSummaryCard();
  navigateTo("screen-confirm");
}

function toggleAIAdvisor() {
  const panel = document.getElementById("aiAdvisorPanel");
  const icon = document.getElementById("aiToggleIcon");
  if (!panel || !icon) return;

  if (panel.classList.contains("hidden")) {
    panel.classList.remove("hidden");
    icon.textContent = "− OCULTAR IA";
  } else {
    panel.classList.add("hidden");
    icon.textContent = "+ CONSULTAR IA";
  }
}

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener("DOMContentLoaded", async () => {
  initClock();
  initDatePicker();
  initAudio();

  await loadPublicSettings();
  await loadBarbers();
  await loadServices();

  navigateTo("screen-intro");
});

function initClock() {
  const clockEl = document.getElementById("liveClock");
  function update() {
    const now = new Date();
    if (clockEl) clockEl.textContent = now.toTimeString().split(" ")[0] + " ART";
  }
  update();
  setInterval(update, 1000);
}

async function loadPublicSettings() {
  try {
    const res = await fetch("/api/public/settings");
    if (res.ok) {
      state.settings = await res.json();
      applySettingsToUI();
    }
  } catch (e) {
    console.warn("Error cargando settings públicas:", e);
  }
}

function applySettingsToUI() {
  const s = state.settings;
  if (!s) return;

  const bName = s.barber_name || s.app_name || "DON CARLOS";

  const brand = document.getElementById("appBrandTitle");
  if (brand) {
    brand.innerHTML = `${escapeHtml(bName.toUpperCase())}<span class="text-neonVolt animate-pulse">_</span>`;
  }

  const st = document.getElementById("splashTitleText");
  if (st) {
    st.textContent = s.splash_title ? s.splash_title : bName.toUpperCase();
  }

  document.title = s.browser_title ? s.browser_title : `${bName} // Turnero & Shop`;

  const ss = document.getElementById("splashSubText");
  if (ss && s.splash_subtitle) {
    ss.textContent = s.splash_subtitle;
  }

  const ft = document.getElementById("footerText");
  if (ft) {
    ft.textContent = s.text_footer ? s.text_footer : `${bName.toUpperCase()} // RESERVAS & SHOP © 2026`;
  }

  if (s.welcome_title) {
    const badgeSub = document.getElementById("badgeSub");
    if (badgeSub) badgeSub.textContent = s.welcome_title;
  }

  if (s.text_services) {
    const sd = document.getElementById("textServicesDesc");
    if (sd) sd.textContent = s.text_services;
  }
  if (s.text_barbers) {
    const bd = document.getElementById("textBarbersDesc");
    if (bd) bd.textContent = s.text_barbers;
  }
}

function getLocalDateString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function initDatePicker() {
  const dateInput = document.getElementById("bookingDate");
  const today = getLocalDateString(new Date());
  if (dateInput) {
    dateInput.value = today;
    dateInput.min = today;
  }
  state.selectedDate = today;
  highlightQuickDate(0);
}

function setQuickDate(offsetDays) {
  const target = new Date();
  target.setDate(target.getDate() + offsetDays);
  const dateStr = getLocalDateString(target);

  const dateInput = document.getElementById("bookingDate");
  if (dateInput) dateInput.value = dateStr;
  state.selectedDate = dateStr;
  highlightQuickDate(offsetDays);
  loadSlots();
}

function highlightQuickDate(offsetDays) {
  const buttons = [
    document.getElementById("quickDateToday"),
    document.getElementById("quickDateTomorrow"),
    document.getElementById("quickDateAfter")
  ];
  buttons.forEach((btn, idx) => {
    if (!btn) return;
    if (idx === offsetDays) {
      btn.classList.add("border-neonVolt", "bg-neonVolt/10", "text-neonVolt", "font-bold");
    } else {
      btn.classList.remove("border-neonVolt", "bg-neonVolt/10", "text-neonVolt", "font-bold");
    }
  });
}

function syncQuickDateFromInput(dateStr) {
  const today = getLocalDateString(new Date());
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = getLocalDateString(tomorrow);
  const after = new Date(); after.setDate(after.getDate() + 2);
  const afterStr = getLocalDateString(after);

  if (dateStr === today) highlightQuickDate(0);
  else if (dateStr === tomorrowStr) highlightQuickDate(1);
  else if (dateStr === afterStr) highlightQuickDate(2);
  else highlightQuickDate(-1);
}

// ==========================================
// PASO 1: BARBEROS
// ==========================================
async function loadBarbers() {
  try {
    const res = await fetch("/api/barbers");
    if (res.ok) state.barbers = await res.json();
  } catch (err) {}

  renderBarbers();
  if (state.barbers.length > 0 && !state.selectedBarber) {
    selectBarber(state.barbers[0].id, false);
  }
}

function renderBarbers() {
  const grid = document.getElementById("barbersGrid");
  if (!grid) return;
  grid.innerHTML = "";

  state.barbers.forEach(barber => {
    const isSelected = state.selectedBarber && state.selectedBarber.id === barber.id;
    const card = document.createElement("button");
    card.type = "button";
    card.className = `glass-card-interactive p-4 rounded-2xl border ${
      isSelected ? "neon-border-active shadow-volt-sm" : "border-surfaceBorder hover:border-white/20"
    } flex flex-col items-center text-center transition-all cursor-pointer`;

    card.innerHTML = `
      <div class="relative w-16 h-16 mb-2.5 rounded-full overflow-hidden border-2 ${
        isSelected ? "border-neonVolt" : "border-surfaceBorder"
      }">
        <img src="${barber.avatar_url || 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80'}" alt="${escapeHtml(barber.name)}" class="w-full h-full object-cover">
      </div>
      <span class="text-sm font-bold text-white block truncate max-w-full">${escapeHtml(barber.name)}</span>
      <span class="text-[10px] text-gray-400 font-mono truncate max-w-full mt-0.5">${escapeHtml(barber.specialties ? barber.specialties.split('//')[0] : 'Master Barber')}</span>
      <span class="mt-3 text-[9px] font-mono px-2.5 py-1 rounded-full ${
        isSelected ? 'bg-neonVolt text-obsidian font-extrabold' : 'bg-white/5 text-gray-400'
      }">
        ${isSelected ? '✓ SELECCIONADO' : 'ELEGIR'}
      </span>
    `;

    card.onclick = () => selectBarber(barber.id, true);
    grid.appendChild(card);
  });
}

function selectBarber(barberId, isUserClick = false) {
  const barber = state.barbers.find(b => b.id === barberId);
  if (!barber) return;
  state.selectedBarber = barber;

  renderBarbers();

  const btnBarberText = document.getElementById("btnBarberText");
  if (btnBarberText) btnBarberText.textContent = `CONTINUAR CON ${barber.name.toUpperCase()}`;

  const agendaBarber = document.getElementById("agendaBarberName");
  if (agendaBarber) agendaBarber.textContent = barber.name;

  const summaryBarber = document.getElementById("summaryBarberText");
  if (summaryBarber) summaryBarber.textContent = barber.name;

  updateNavigationUI(state.currentScreen);

  if (isUserClick) {
    setTimeout(() => { continueToServices(); }, 180);
  }
}

// ==========================================
// PASO 2: SERVICIOS
// ==========================================
async function loadServices() {
  try {
    const res = await fetch("/api/services");
    if (res.ok) state.services = await res.json();
  } catch (err) {}

  renderServices();
  if (state.services.length > 0 && !state.selectedService) {
    selectService(state.services[0].id, false);
  }
}

function renderServices() {
  const grid = document.getElementById("servicesGrid");
  if (!grid) return;
  grid.innerHTML = "";

  state.services.forEach(srv => {
    const isSelected = state.selectedService && state.selectedService.id === srv.id;
    const card = document.createElement("button");
    card.type = "button";
    card.className = `service-btn glass-card-interactive p-4 rounded-2xl text-left border ${
      isSelected ? "neon-border-active shadow-volt-sm" : "border-surfaceBorder hover:border-white/20"
    } flex flex-col justify-between transition-all cursor-pointer`;

    card.innerHTML = `
      <div>
        <div class="flex justify-between items-start gap-1 mb-1">
          <span class="text-sm font-bold text-white leading-tight">${escapeHtml(srv.name)}</span>
          <span class="text-[10px] font-mono text-gray-400 bg-white/5 px-2 py-0.5 rounded shrink-0">${srv.duration_min}m</span>
        </div>
        <p class="text-[11px] text-gray-400 mb-2 leading-snug">${escapeHtml(srv.description || "")}</p>
      </div>
      <div class="flex justify-between items-center mt-2 pt-2 border-t border-white/5">
        <span class="text-[10px] font-mono text-gray-500 uppercase">PRECIO</span>
        <span class="text-sm font-mono text-neonVolt font-bold">$${srv.price.toLocaleString("es-AR")}</span>
      </div>
    `;

    card.onclick = () => selectService(srv.id, true);
    grid.appendChild(card);
  });
}

function selectService(serviceId, isUserClick = false) {
  const srv = state.services.find(s => s.id === serviceId);
  if (!srv) return;
  state.selectedService = srv;

  renderServices();

  const btnServiceText = document.getElementById("btnServiceText");
  if (btnServiceText) btnServiceText.textContent = `CONTINUAR CON ${srv.name.toUpperCase()} ($${srv.price.toLocaleString("es-AR")})`;

  const agendaService = document.getElementById("agendaServiceName");
  if (agendaService) agendaService.textContent = srv.name;

  const summaryService = document.getElementById("summaryServiceText");
  if (summaryService) summaryService.textContent = srv.name;

  const summaryPrice = document.getElementById("summaryPriceText");
  if (summaryPrice) summaryPrice.textContent = `$${srv.price.toLocaleString("es-AR")}`;

  updateNavigationUI(state.currentScreen);

  if (isUserClick) {
    setTimeout(() => { continueToAgenda(); }, 180);
  }
}

// ==========================================
// PASO 3: AGENDA & SLOTS EN TIEMPO REAL
// ==========================================
async function loadSlots() {
  const dateInput = document.getElementById("bookingDate");
  const date = dateInput ? dateInput.value : state.selectedDate;
  state.selectedDate = date;
  state.selectedSlot = null;
  syncQuickDateFromInput(date);

  const container = document.getElementById("slotsContainer");
  if (!container) return;
  container.innerHTML = '<div class="col-span-4 sm:col-span-5 text-center text-xs text-gray-500 py-6 font-mono animate-pulse">Consultando disponibilidad...</div>';

  const barberIdParam = state.selectedBarber ? state.selectedBarber.id : "";
  const serviceIdParam = state.selectedService ? state.selectedService.id : "";

  try {
    const res = await fetch(`/api/available-slots?barber_id=${barberIdParam}&service_id=${serviceIdParam}&date=${date}`);
    if (!res.ok) throw new Error("Error slots");
    const data = await res.json();
    renderSlots(data.slots);
  } catch (err) {
    container.innerHTML = '<div class="col-span-4 sm:col-span-5 text-center text-xs text-red-400 py-4 font-mono">Error al consultar agenda.</div>';
  }
}

function renderSlots(slots) {
  const container = document.getElementById("slotsContainer");
  if (!container) return;
  container.innerHTML = "";

  if (!slots || slots.length === 0) {
    container.innerHTML = '<div class="col-span-4 sm:col-span-5 text-center text-xs text-gray-500 py-4 font-mono">No hay turnos disponibles para esta fecha.</div>';
    return;
  }

  slots.forEach(slot => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = slot.time;

    if (slot.available) {
      btn.className = "py-2.5 rounded-xl text-xs font-mono font-bold border border-surfaceBorder bg-surface text-gray-200 hover:border-neonVolt hover:text-white transition active:scale-95 cursor-pointer";
      btn.onclick = () => {
        document.querySelectorAll("#slotsContainer button").forEach(b => {
          if (!b.disabled) b.className = "py-2.5 rounded-xl text-xs font-mono font-bold border border-surfaceBorder bg-surface text-gray-200 hover:border-neonVolt hover:text-white transition active:scale-95 cursor-pointer";
        });

        btn.className = "py-2.5 rounded-xl text-xs font-mono font-bold bg-neonVolt text-obsidian border border-neonVolt shadow-volt-sm";
        state.selectedSlot = slot.time;

        const btnAgendaText = document.getElementById("btnAgendaText");
        if (btnAgendaText) btnAgendaText.textContent = `CONTINUAR CON HORARIO ${slot.time} HS`;

        updateNavigationUI(state.currentScreen);

        setTimeout(() => { continueToConfirm(); }, 220);
      };
    } else {
      btn.disabled = true;
      btn.className = "py-2.5 rounded-xl text-xs font-mono text-gray-600 bg-black/40 border border-transparent cursor-not-allowed line-through opacity-50";
    }

    container.appendChild(btn);
  });
}

function updateBookingSummaryCard() {
  const summaryBarber = document.getElementById("summaryBarberText");
  const summaryService = document.getElementById("summaryServiceText");
  const summaryTime = document.getElementById("summaryTimeText");
  const summaryPrice = document.getElementById("summaryPriceText");

  if (summaryBarber && state.selectedBarber) summaryBarber.textContent = state.selectedBarber.name;
  if (summaryService && state.selectedService) summaryService.textContent = state.selectedService.name;
  if (summaryTime && state.selectedDate && state.selectedSlot) {
    const [y, m, d] = state.selectedDate.split("-");
    summaryTime.textContent = `${d}/${m}/${y} a las ${state.selectedSlot} hs`;
  }
  if (summaryPrice && state.selectedService) summaryPrice.textContent = `$${state.selectedService.price.toLocaleString("es-AR")}`;
}

// ==========================================
// ASESOR DE VISAGISMO IA
// ==========================================
async function askAIAdvisor() {
  const face = document.getElementById("aiFace").value;
  const density = document.getElementById("aiDensity").value;
  const hairType = document.getElementById("aiHairType").value;

  const btn = document.getElementById("btnAskAI");
  const btnText = document.getElementById("aiBtnText");
  const resultCard = document.getElementById("aiResult");

  btn.disabled = true;
  btnText.textContent = "ANALIZANDO...";

  try {
    const res = await fetch("/api/ai-advisor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ face_shape: face, hair_density: density, hair_type: hairType, style_preference: "moderno" })
    });

    if (res.ok) {
      const data = await res.json();
      state.aiRecommendation = data;

      document.getElementById("aiResultCut").textContent = data.recommendation;
      document.getElementById("aiResultTip").textContent = data.styling_tips;
      document.getElementById("aiResultFade").textContent = `// ${data.fade_type.toUpperCase()}`;
      resultCard.classList.remove("hidden");
    }
  } catch (err) {
    alert("Error al consultar Asesor IA.");
  } finally {
    btn.disabled = false;
    btnText.textContent = "CALCULAR CORTE ÓPTIMO";
  }
}

function applyAISuggestion() {
  if (!state.aiRecommendation) return;
  const targetName = state.aiRecommendation.recommended_service;
  const foundService = state.services.find(s => s.name.toLowerCase().includes(targetName.toLowerCase()));

  if (foundService) selectService(foundService.id, true);
  else if (state.services.length > 0) selectService(state.services[0].id, true);
}

// ==========================================
// CONFIRMACIÓN Y RESERVA
// ==========================================
async function submitBooking() {
  const nameInput = document.getElementById("clientName");
  const phoneInput = document.getElementById("clientPhone");
  const name = nameInput ? nameInput.value.trim() : "";
  const phone = phoneInput ? phoneInput.value.trim() : "";

  if (!state.selectedBarber || !state.selectedService || !state.selectedSlot) {
    alert("Por favor completa los pasos previos.");
    return;
  }
  if (!name || name.length < 3) {
    alert("Ingresa tu Nombre y Apellido.");
    return;
  }
  if (!phone || phone.length < 8) {
    alert("Ingresa tu número de WhatsApp.");
    return;
  }

  const submitBtn = document.getElementById("btnSubmitBooking");
  submitBtn.disabled = true;
  submitBtn.textContent = "RESERVANDO TURNO...";

  const payload = {
    client_name: name,
    client_phone: phone,
    barber_id: state.selectedBarber.id,
    barber_name: state.selectedBarber.name,
    service_id: state.selectedService.id,
    service: state.selectedService.name,
    appointment_time: `${state.selectedDate}T${state.selectedSlot}:00`
  };

  try {
    const res = await fetch("/api/appointments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      showSuccessModal(data.appointment);
      state.selectedSlot = null;
    } else {
      alert(data.detail || "No fue posible agendar el turno.");
    }
  } catch (err) {
    alert("Error de conexión al servidor de reservas.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>CONFIRMAR RESERVA POR WHATSAPP</span> <span class="text-base">→</span>`;
  }
}

function showSuccessModal(appt) {
  UISound.play("success");
  const modal = document.getElementById("successModal");
  const title = document.getElementById("modalClientTitle");
  const msg = document.getElementById("modalClientMessage");

  const [datePart, timePart] = appt.appointment_time.split("T");
  const [y, m, d] = datePart.split("-");
  const timeFormatted = timePart.substring(0, 5);

  title.textContent = `¡Turno Asignado #${appt.id}!`;
  msg.innerHTML = `
    <strong>${escapeHtml(appt.client_name)}</strong>, tu cita para <strong>${escapeHtml(appt.service)}</strong> con <strong>${escapeHtml(appt.barber_name)}</strong> ha sido agendada para el <strong>${d}/${m}/${y} a las ${timeFormatted} hs</strong>.
  `;

  modal.classList.remove("hidden");
}

function closeModal() {
  UISound.play("click");
  const modal = document.getElementById("successModal");
  if (modal) modal.classList.add("hidden");
  navigateTo("screen-intro");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Escuchador global de sonidos en botones y elementos interactivos
document.addEventListener("DOMContentLoaded", () => {
  document.body.addEventListener("click", (e) => {
    const btn = e.target.closest("button, a, select, input[type='submit']");
    if (btn && !btn.hasAttribute("data-no-sound")) {
      UISound.play("click");
    }
  });
});
