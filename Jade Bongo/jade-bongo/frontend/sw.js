"use strict";
/* Jade Bɔngɔ́ — Service Worker (mode application Android)
   - App shell hors-ligne (ouverture instantanée)
   - API toujours en réseau (jamais de données figées pour un enfant)
*/
const CACHE = "jade-bongo-v2.1";
const SHELL = [
  "/", "/index.html", "/style.css", "/i18n.js", "/app.js",
  "/parent.html", "/parent.js", "/command.html", "/command.js",
  "/manifest.json", "/icons/icon-192.png", "/icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  // API : réseau d'abord, message clair si hors-ligne
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ detail: "Hors-ligne : reconnecte-toi à Internet 🌐" }), {
          status: 503, headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }

  // App shell : cache d'abord, mise à jour en arrière-plan
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const fresh = fetch(e.request)
        .then((res) => {
          if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
          return res;
        })
        .catch(() => cached);
      return cached || fresh;
    })
  );
});
