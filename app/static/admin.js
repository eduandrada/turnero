/**
 * Admin Panel - Modular Architecture Coordinator
 * HiddenSYNC Barber Ecosystem 2026
 *
 * This file coordinates and verifies the modular JavaScript components in /static/js/admin/:
 * - core.js (Session, auth, navigation, modals, utilities)
 * - dashboard.js (KPI stats, recent activity)
 * - appointments.js (Turnos agenda, filtering, state transitions)
 * - staff.js (Barberos & schedules)
 * - services.js (Services, styles, delivery zones)
 * - clients.js (CRM clients directory)
 * - shop.js (Orders, deliveries, WhatsApp coordination)
 * - inventory.js (Product stock, quick adjustments, alerts)
 * - finance.js (Shift closures, cash reconciliation)
 * - users.js (Staff accounts & role permissions)
 * - settings.js (Branding, theme, logo, notifications, audit logs)
 * - backups.js (Database backups & safe restoration)
 */

(function () {
  const REQUIRED_MODULES = [
    { name: "core", path: "/static/js/admin/core.js", check: () => typeof switchSection === "function" },
    { name: "dashboard", path: "/static/js/admin/dashboard.js", check: () => typeof loadAdminDashboard === "function" },
    { name: "appointments", path: "/static/js/admin/appointments.js", check: () => typeof loadAdminAppointments === "function" },
    { name: "staff", path: "/static/js/admin/staff.js", check: () => typeof loadAdminBarbers === "function" },
    { name: "services", path: "/static/js/admin/services.js", check: () => typeof loadAdminServices === "function" },
    { name: "clients", path: "/static/js/admin/clients.js", check: () => typeof loadAdminClients === "function" },
    { name: "shop", path: "/static/js/admin/shop.js", check: () => typeof loadAdminOrders === "function" },
    { name: "inventory", path: "/static/js/admin/inventory.js", check: () => typeof loadAdminProducts === "function" },
    { name: "finance", path: "/static/js/admin/finance.js", check: () => typeof loadShiftClosuresData === "function" },
    { name: "users", path: "/static/js/admin/users.js", check: () => typeof loadStaffData === "function" },
    { name: "settings", path: "/static/js/admin/settings.js", check: () => typeof loadSettingsToForm === "function" },
    { name: "backups", path: "/static/js/admin/backups.js", check: () => typeof loadAdminBackups === "function" },
    { name: "stats", path: "/static/js/admin/stats.js", check: () => typeof loadAttendedClientsStats === "function" },
    { name: "roadmap_features", path: "/static/js/admin/roadmap_features.js", check: () => typeof loadPaymentSettings === "function" }
  ];

  // Check if any modules need dynamic loading (fallback when admin.js is imported standalone)
  const missingModules = REQUIRED_MODULES.filter(m => !m.check());

  if (missingModules.length > 0) {
    console.info(`[AdminCoordinator] Dynamically loading ${missingModules.length} modular components...`);
    let loadedCount = 0;
    missingModules.forEach(m => {
      const script = document.createElement("script");
      script.src = m.path;
      script.async = false;
      script.onload = () => {
        loadedCount++;
        if (loadedCount === missingModules.length) {
          console.info("[AdminCoordinator] All modular admin scripts loaded successfully.");
          if (typeof verifyAdminSession === "function" && (localStorage.getItem("hiddensync_admin_token") || localStorage.getItem("bladesync_admin_token"))) {
            verifyAdminSession();
          }
        }
      };
      script.onerror = () => {
        console.error(`[AdminCoordinator] Failed to load module ${m.name} from ${m.path}`);
      };
      document.head.appendChild(script);
    });
  } else {
    console.info("[AdminCoordinator] All modular admin components loaded and verified.");
  }

  // Expose registry for debugging/testing
  window.AdminArchitecture = {
    version: "2026.2.0-modular",
    modules: REQUIRED_MODULES.map(m => m.name),
    status: "active"
  };
})();
