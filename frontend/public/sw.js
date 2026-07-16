const CACHE_PREFIX = "insight";
const STATIC_CACHE = `${CACHE_PREFIX}-static-v2`;
const OFFLINE_CACHE = `${CACHE_PREFIX}-offline-v2`;
const PRECACHE = ["/offline.html", "/icon-192.png", "/icon-512.png"];
const CURRENT_CACHES = new Set([STATIC_CACHE, OFFLINE_CACHE]);

self.addEventListener("install", event => {
  event.waitUntil(caches.open(OFFLINE_CACHE).then(cache => cache.addAll(PRECACHE)));
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => (name === "insight-v1" || name.startsWith(`${CACHE_PREFIX}-`)) && !CURRENT_CACHES.has(name)).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || ["/api/", "/admin/", "/ws/", "/media/"].some(prefix => url.pathname.startsWith(prefix)) || url.pathname === "/sw.js" || url.pathname === "/manifest.webmanifest") return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline.html").then(response => response || Response.error())));
    return;
  }
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith((async () => {
      const cached = await caches.match(request);
      if (cached) return cached;
      const response = await fetch(request);
      if (response.ok) (await caches.open(STATIC_CACHE)).put(request, response.clone());
      return response;
    })());
  }
});
