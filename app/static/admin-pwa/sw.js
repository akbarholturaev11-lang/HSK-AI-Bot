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

/* Fixed, content-free labels for an allowlisted server event category.
   Ignore all other push fields. No sensitive details or untrusted copy are displayed.
   Safari requires a visible notification for each delivered push. */
self.addEventListener('push', event => {
  const labels = {
    payment: {title: '🧾 Yangi to‘lov cheki', body: 'Chekni tekshirish kerak.'},
    android: {title: '📱 Android xatoligi', body: 'Android ilovasidan xatolik hisoboti keldi.'},
    technical: {title: '⚠️ Texnik xatolik', body: 'Tizimda xatolik qayd etildi.'},
    bot: {title: '💬 Bot fikr-mulohazasi', body: 'Muhim belgilangan fikr keldi.'},
    release: {title: '🚀 Reliz xabari', body: 'Muhim reliz xabari keldi.'},
  };
  let source = null;
  try {
    const payload = event.data ? event.data.json() : null;
    if (payload && payload.kind === 'important' &&
        typeof payload.source === 'string' &&
        Object.prototype.hasOwnProperty.call(labels, payload.source)) {
      source = payload.source;
    }
  } catch (_) {
    // Old or malformed pushes still show a safe fallback notification.
  }
  const message = source ? labels[source] :
    {title: 'HSK AI Admin', body: 'Yangi admin bildirishnomasi.'};
  event.waitUntil(self.registration.showNotification(message.title, {
    body: message.body,
    icon: '/admin/assets/icon.png',
    badge: '/admin/assets/icon.png',
    // Do not share a single notification tag: iOS may replace a receipt alert
    // with an unrelated Android error instead of showing both.
    data: {path: '/admin/?inbox=1'},
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    // Fixed first-party link only, irrespective of notification or push data.
    const url = new URL('/admin/?inbox=1', self.location.origin).href;
    const open = await self.clients.matchAll({type: 'window', includeUncontrolled: true});
    for (const client of open) {
      const current = new URL(client.url);
      if (current.origin === self.location.origin && current.pathname === '/admin/' &&
          typeof client.navigate === 'function' && typeof client.focus === 'function') {
        await client.navigate(url);
        return client.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});
