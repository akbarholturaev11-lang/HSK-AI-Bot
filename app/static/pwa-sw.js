/* v1: install foundation only. No course, account, lesson, audio,
 * answer keys, checkout or authenticated API data is stored offline.
 */
"use strict";
const BRAND_CACHE = "hsk-ai-pwa-brand-v1";
const BRAND_PREFIX = "hsk-ai-pwa-brand-";
const PUBLIC_BRANDING = new Set([
  "/assets/hsk-ai-logo-256.png",
  "/assets/hsk-ai-avatar.webp"
]);

self.addEventListener("install", function (event) {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key.startsWith(BRAND_PREFIX) && key !== BRAND_CACHE;
      }).map(function (key) { return caches.delete(key); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.search ||
      !PUBLIC_BRANDING.has(url.pathname)) return;
  // Authenticated HTML/API and learner-specific assets stay network-only.
  event.respondWith(
    caches.match(request).then(function (cached) {
      if (cached) return cached;
      return fetch(request).then(function (response) {
        if (response.ok && response.type === "basic") {
          const copy = response.clone();
          event.waitUntil(caches.open(BRAND_CACHE).then(function (cache) {
            return cache.put(request, copy);
          }));
        }
        return response;
      });
    })
  );
});
