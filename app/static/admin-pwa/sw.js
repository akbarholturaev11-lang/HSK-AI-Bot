'use strict';
const VERSION = '__SHELL_VERSION__';
const CACHE = 'hsk-admin-public-' + VERSION;
const PUBLIC = ['/admin/', '/admin/assets/styles.css', '/admin/assets/catalog.js', '/admin/assets/app.js', '/admin/assets/icon.png', '/admin/assets/icon-large.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('hsk-admin-public-') && key !== CACHE).map(key => caches.delete(key)))));
});
self.addEventListener('message', event => {
  if (event.data === 'ACTIVATE_PUBLIC_SHELL') self.skipWaiting();
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // No API, receipt, attachment, auth, arbitrary navigation or query URL is
  // EVER cached/intercepted. Scope /admin/ excludes legacy /admin.html.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.search || !PUBLIC.includes(url.pathname)) return;
  event.respondWith(caches.open(CACHE).then(async cache => {
    const cached = await cache.match(url.pathname);
    return cached || fetch(event.request);
  }));
});
