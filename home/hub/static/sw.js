const CACHE = 'hub-v3';
const ASSETS = [
  '/',
  '/sw.js',
  '/static/hub-static.js?v=20260703-home',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  const isApi = url.pathname.startsWith('/api/');
  const isDocument = e.request.mode === 'navigate' || e.request.destination === 'document';
  e.respondWith(
    caches.match(e.request).then(async cached => {
      if (isDocument) {
        return fetch(e.request).catch(() => cached);
      }
      const networkFetch = fetch(e.request).then(resp => {
        if (resp.ok) caches.open(CACHE).then(c => c.put(e.request, resp.clone()));
        return resp;
      }).catch(() => cached);
      if (isApi && cached) return cached;
      return cached || networkFetch;
    })
  );
});
