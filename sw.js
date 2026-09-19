/**
 * Sri Lanka FloodWatch — Service Worker (Phase 14 Low-Bandwidth & Emergency Shell)
 * 
 * Provides offline caching for core emergency UI assets and location-isolated API caching.
 * STRICT INVARIANT: Location identity is preserved in cache matching.
 */

const CACHE_NAME = 'floodwatch-emergency-v1';
const CORE_ASSETS = [
  '/',
  '/emergency.html',
  '/index.html',
  '/css/styles.css',
  '/js/common.js',
  '/js/api.js',
  '/js/i18n.js',
  '/js/emergency.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS.filter(url => true));
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Network-first for emergency API endpoints with location isolation
  if (url.pathname.includes('/api/v1/emergency/') || url.pathname.includes('/api/public/emergency/')) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.ok) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Fallback to cached response matching exact request URL (including location_id)
          return caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // Return JSON fallback error if no cache exists for location
            return new Response(
              JSON.stringify({
                status: 'error',
                code: 'OFFLINE_NO_CACHE',
                message: 'Current information could not be retrieved and no cached data exists for this location.'
              }),
              {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
              }
            );
          });
        })
    );
    return;
  }

  // Cache-first for core static assets, network fallback
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        // Fetch background refresh for static assets
        fetch(event.request).then((fresh) => {
          if (fresh && fresh.ok) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, fresh));
          }
        }).catch(() => {});
        return cached;
      }
      return fetch(event.request);
    })
  );
});
