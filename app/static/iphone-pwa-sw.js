/* Push-only worker: it never caches or intercepts learner/course requests. */
"use strict";

self.addEventListener("push", function (event) {
  var data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_) {
    data = {};
  }
  var title = typeof data.title === "string" ? data.title.slice(0, 80) : "HSK AI";
  var body = typeof data.body === "string" ? data.body.slice(0, 160) : "";
  var tag = typeof data.tag === "string" && /^[A-Za-z0-9_-]{1,48}$/.test(data.tag)
    ? data.tag : "hsk-pwa-notice";
  event.waitUntil(self.registration.showNotification(title, {
    body: body,
    tag: tag,
    icon: "/assets/hsk-ai-logo-256.png",
    badge: "/assets/hsk-ai-logo-256.png",
    data: { url: "/iphone-pwa/course?notice=1" }
  }));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var target = new URL("/iphone-pwa/course?notice=1", self.location.origin);
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true })
    .then(function (clients) {
      for (var i = 0; i < clients.length; i += 1) {
        var client = clients[i];
        try {
          var current = new URL(client.url);
          if (current.origin === self.location.origin &&
              current.pathname.indexOf("/iphone-pwa/") === 0) {
            return client.navigate(target.href).then(function (navigated) {
              return (navigated || client).focus();
            });
          }
        } catch (_) { /* Ignore non-window or malformed clients. */ }
      }
      return self.clients.openWindow(target.href);
    }));
});
