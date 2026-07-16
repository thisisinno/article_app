const CACHE_PREFIX = "insight";
const STATIC_CACHE = `${CACHE_PREFIX}-static-v4`;
const OFFLINE_CACHE = `${CACHE_PREFIX}-offline-v4`;
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
  if (url.origin !== self.location.origin || ["/api/", "/admin/", "/ws/", "/media/", "/notifications", "/profile/"].some(prefix => url.pathname.startsWith(prefix)) || url.pathname === "/sw.js" || url.pathname === "/manifest.webmanifest") return;
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

const safeInternalUrl = value => {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) return "/notifications";
  return value === "/" || value.startsWith("/post/") || value.startsWith("/notifications") || value.startsWith("/profile/") ? value : "/notifications";
};

self.addEventListener("push", event => {
  let data = {};
  try { data = event.data?.json() || {}; } catch { data = {}; }
  const title = typeof data.title === "string" ? data.title : "Jesca Social Work";
  event.waitUntil(self.registration.showNotification(title, {
    body: typeof data.body === "string" ? data.body : "You have a new notification.",
    icon: "/icon-192.png", badge: "/icon-192.png",
    tag: typeof data.tag === "string" ? data.tag : "jesca:notification",
    data: {url: safeInternalUrl(data.url)}, renotify: Boolean(data.renotify),
  }));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const destination = new URL(safeInternalUrl(event.notification.data?.url), self.location.origin).href;
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({type:"window", includeUncontrolled:true});
    const client = windows.find(item => new URL(item.url).origin === self.location.origin);
    if (client) { await client.focus(); if ("navigate" in client) await client.navigate(destination); return; }
    await self.clients.openWindow(destination);
  })());
});
self.addEventListener("notificationclose", () => undefined);
self.addEventListener("pushsubscriptionchange", event => event.waitUntil(self.clients.matchAll({type:"window",includeUncontrolled:true}).then(items => Promise.all(items.map(item => item.postMessage({type:"PUSH_SUBSCRIPTION_CHANGE"}))))));
