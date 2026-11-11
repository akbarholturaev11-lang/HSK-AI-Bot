/* Learner PWA worker.
 *
 * Push: localized event-specific notices that open the authenticated Inbox.
 *
 * Cache: Cache First ONLY for same-origin, version-pinned static assets
 * (.js/.css/fonts/images whose URL carries `?v=`). A new version is a new
 * URL; older versions of the same file are pruned. HTML documents, API
 * calls, lesson content, audio and anything without a version always go to
 * the network. iOS may evict this cache at any time, so every miss simply
 * falls back to the network: the cache is a speed-up, never the source of
 * truth and never an offline guarantee.
 */
"use strict";

var STATIC_CACHE = "hsk-pwa-static-v1";
var STATIC_PREFIX = "hsk-pwa-static-";
var VERSIONS_PER_FILE = 3;
var WARM_STAMP = "/__hsk-pwa-warm-stamp";
var WARM_EVERY_MS = 12 * 60 * 60 * 1000;
var WARM_MAX_ASSETS_PER_PAGE = 40;
// Pages whose static dependencies are fetched in the background, one at a
// time, after the course is idle. Their HTML is only read, never cached here.
var WARM_PAGES = [
  "/iphone-pwa/dictionary?embedded=1",
  "/iphone-pwa/phrases?embedded=1",
  "/iphone-pwa/practice/recognition?embedded=1",
  "/iphone-pwa/practice/pronunciation?embedded=1",
  "/iphone-pwa/practice/memorize?embedded=1",
  "/iphone-pwa/practice/test?embedded=1",
  "/iphone-pwa/practice/mistakes?embedded=1",
  "/iphone-pwa/checkout?embedded=1"
];
var ASSET_PATH = /\.(?:js|css|woff2?|webp|png|svg|jpe?g)$/;
var ASSET_REF = /["']((?:\/|\.{1,2}\/)?[A-Za-z0-9_\-./]+\.(?:js|css)\?v=[A-Za-z0-9_.\-]+)["']/g;

function isVersionedAsset(url) {
  return url.origin === self.location.origin &&
    ASSET_PATH.test(url.pathname) &&
    url.searchParams.has("v") &&
    url.pathname.indexOf("/api/") !== 0 &&
    url.pathname.indexOf("/iphone-pwa") !== 0;
}

/* Keep at most VERSIONS_PER_FILE versions of one path (insertion order).
   Two pages may legitimately pin different versions of a shared file. */
function prune(cache, href) {
  var path = new URL(href).pathname;
  return cache.keys().then(function (requests) {
    var same = requests.filter(function (request) {
      var url = new URL(request.url);
      return url.pathname === path && request.url !== href;
    });
    var extra = same.length - (VERSIONS_PER_FILE - 1);
    return Promise.all(same.slice(0, Math.max(0, extra)).map(function (request) {
      return cache.delete(request);
    }));
  });
}

function store(cache, href, response) {
  if (!response || response.status !== 200 || response.type !== "basic") return Promise.resolve();
  return cache.put(href, response).then(function () { return prune(cache, href); });
}

function cacheFirst(request) {
  return caches.open(STATIC_CACHE).then(function (cache) {
    return cache.match(request.url).then(function (hit) {
      if (hit) return hit;
      return fetch(request).then(function (response) {
        store(cache, request.url, response.clone()).catch(function () {});
        return response;
      });
    });
  }, function () {
    return fetch(request);
  });
}

self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (names) {
    return Promise.all(names.filter(function (name) {
      return name.indexOf(STATIC_PREFIX) === 0 && name !== STATIC_CACHE;
    }).map(function (name) { return caches.delete(name); }));
  }).catch(function () {}).then(function () {
    return self.clients.claim();
  }));
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET" || request.headers.has("range")) return;
  var url;
  try { url = new URL(request.url); } catch (_) { return; }
  if (!isVersionedAsset(url)) return;
  event.respondWith(cacheFirst(request));
});

function warmPage(cache, page) {
  var base = new URL(page, self.location.origin);
  return fetch(base.href, { credentials: "same-origin", redirect: "error" })
    .then(function (response) { return response.ok ? response.text() : ""; })
    .then(function (html) {
      var seen = {}, urls = [], match;
      ASSET_REF.lastIndex = 0;
      while ((match = ASSET_REF.exec(html)) && urls.length < WARM_MAX_ASSETS_PER_PAGE) {
        var url = new URL(match[1], base);
        if (isVersionedAsset(url) && !seen[url.href]) {
          seen[url.href] = true;
          urls.push(url.href);
        }
      }
      // Sequential: a background warm must not compete with the learner.
      return urls.reduce(function (chain, href) {
        return chain.then(function () {
          return cache.match(href).then(function (hit) {
            if (hit) return null;
            return fetch(href, { credentials: "same-origin" }).then(function (response) {
              return store(cache, href, response);
            });
          });
        }).catch(function () {});
      }, Promise.resolve());
    })
    .catch(function () {});
}

var warming = null;
function warm() {
  if (warming) return warming;
  warming = caches.open(STATIC_CACHE).then(function (cache) {
    return cache.match(WARM_STAMP)
      .then(function (stamp) { return stamp ? stamp.text() : "0"; })
      .then(function (text) {
        if (Date.now() - Number(text) < WARM_EVERY_MS) return null;
        return WARM_PAGES.reduce(function (chain, page) {
          return chain.then(function () { return warmPage(cache, page); });
        }, Promise.resolve()).then(function () {
          return cache.put(WARM_STAMP, new Response(String(Date.now())));
        });
      });
  }).catch(function () {}).then(function () { warming = null; });
  return warming;
}

self.addEventListener("message", function (event) {
  var data = event.data;
  if (!data || data.type !== "hsk-pwa-warm") return;
  event.waitUntil(warm());
});

// App-icon badge: a device-local count of pushes since the Inbox was last
// opened. The course page clears it. Unsupported browsers just skip it.
var BADGE_CACHE = "hsk-pwa-badge-v1", BADGE_KEY = "/__hsk-pwa-badge";
function bumpAppBadge() {
  if (!self.navigator || typeof self.navigator.setAppBadge !== "function" || !self.caches) {
    return Promise.resolve();
  }
  return caches.open(BADGE_CACHE).then(function (cache) {
    return cache.match(BADGE_KEY).then(function (hit) {
      return hit ? hit.text() : "0";
    }).then(function (text) {
      var next = Math.min(99, (parseInt(text, 10) || 0) + 1);
      return cache.put(BADGE_KEY, new Response(String(next))).then(function () {
        return self.navigator.setAppBadge(next);
      });
    });
  }).catch(function () {});
}

self.addEventListener("push", function (event) {
  var data = {};
  try {
    data = event.data ? event.data.json() : {};
    if (!data || typeof data !== "object") data = {};
  } catch (_) {
    data = {};
  }
  // iOS supplies the installed app name. Never repeat it as the headline.
  // Code-point slicing keeps supplementary Chinese characters/emoji intact.
  var title = typeof data.title === "string" ? data.title.trim() : "";
  if (!title || /^HSK\s+AI$/i.test(title)) title = "🔔";
  title = Array.from(title).slice(0, 80).join("");
  var body = typeof data.body === "string" ? Array.from(data.body).slice(0, 1000).join("") : "";
  var tag = typeof data.tag === "string" && /^[A-Za-z0-9_-]{1,48}$/.test(data.tag)
    ? data.tag : "hsk-pwa-notice";
  // iOS requires every push to show a notification; the badge is extra.
  event.waitUntil(Promise.all([self.registration.showNotification(title, {
    body: body,
    lang: /^(uz|ru|tj)$/.test(data.lang) ? (data.lang === "tj" ? "tg" : data.lang) : undefined,
    tag: tag,
    icon: "/assets/hsk-ai-logo-256.png",
    badge: "/assets/hsk-ai-logo-256.png",
    data: { url: "/iphone-pwa/course?notice=1" }
  }), bumpAppBadge()]));
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
