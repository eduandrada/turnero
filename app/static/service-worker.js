const CACHE_NAME = 'barberia-cache-v3';
const urlsToCache = [
  '/',
  '/admin.html',
  '/shop.html',
  '/live.html',
  '/display.html',
  '/static/app.js',
  '/static/admin.js',
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
