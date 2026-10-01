const CACHE_NAME = 'barberia-cache-v3';
const urlsToCache = [
  '/',
  '/admin.html',
  '/shop.html',
  '/turnolive.html',
  '/gestion.html',
  '/inventario.html',
  '/voucher.html',
  '/display.html',
  '/static/app.js',
  '/static/admin.js',
  '/static/js/admin/core.js',
  '/static/js/admin/dashboard.js',
  '/static/js/admin/appointments.js',
  '/static/js/admin/staff.js',
  '/static/js/admin/services.js',
  '/static/js/admin/clients.js',
  '/static/js/admin/shop.js',
  '/static/js/admin/inventory.js',
  '/static/js/admin/finance.js',
  '/static/js/admin/users.js',
  '/static/js/admin/settings.js',
  '/static/js/admin/backups.js',
  '/static/admin.css',
  '/static/shop.js',
  '/static/shop.css',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    }).catch(err => console.warn("PWA Cache prefetch non-fatal error:", err))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Bypass cache completely for API endpoints and admin uploads
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/static/uploads/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache-First strategy for static assets
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).then(fetchResponse => {
        if (fetchResponse.status === 200 && event.request.url.startsWith('http')) {
          const responseToCache = fetchResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return fetchResponse;
      });
    })
  );
});

// PWA WEB PUSH NOTIFICATIONS
self.addEventListener('push', event => {
  let data = { title: '💈 Barbería // Recordatorio', body: 'Tenés un turno en 2 horas.' };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || 'Tu turno en la barbería se aproxima en 2 horas.',
    icon: data.icon || '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' }
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '💈 Recordatorio de Turno', options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url === targetUrl && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

