const CACHE_NAME = 'barberia-cache-v2';
const urlsToCache = [
  '/',
  '/admin.html',
  '/shop.html',
  '/static/index.html',
  '/static/app.js',
  '/static/admin.html',
  '/static/admin.js',
  '/static/admin.css',
  '/static/shop.html',
  '/static/shop.js',
  '/static/shop.css',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
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
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
