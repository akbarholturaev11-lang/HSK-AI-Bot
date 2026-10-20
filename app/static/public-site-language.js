/* Shared language preference for the public information site and download page. */
(function () {
  "use strict";
  var KEY = "hskai.public.language";
  var HOME = {tg:"/tj/", ru:"/ru/", uz:"/uz/"};
  var PAGES = {
    courses: {tg:"/tj/hsk/", ru:"/ru/hsk/", uz:"/uz/hsk/"},
    features: {tg:"/tj/guide/features/", ru:"/ru/guide/features/", uz:"/uz/guide/features/"},
    guide: {tg:"/tj/guide/", ru:"/ru/guide/", uz:"/uz/guide/"},
    home: HOME
  };
  function normalize(value) {
    if (value === "tj") return "tg";
    return value === "tg" || value === "ru" || value === "uz" ? value : "";
  }
  function read() {
    try { return normalize(window.localStorage.getItem(KEY)); } catch (error) { return ""; }
  }
  function save(lang) {
    lang = normalize(lang);
    if (!lang) return;
    try { window.localStorage.setItem(KEY, lang); } catch (error) {}
  }
  function fromPath() {
    var match = /^\/(tj|ru|uz)(?:\/|$)/.exec(window.location.pathname);
    return match ? normalize(match[1]) : "";
  }
  function updateLinks(lang) {
    lang = normalize(lang);
    if (!lang) return;
    document.querySelectorAll("[data-site-nav]").forEach(function (link) {
      var key = link.getAttribute("data-site-nav");
      var dest = PAGES[key] && PAGES[key][lang];
      if (key === "download") dest = "/download?lang=" + (lang === "tg" ? "tj" : lang);
      if (!dest) return;
      var old = new URL(link.href, window.location.href);
      var next = new URL(dest, window.location.origin);
      // Keep only existing, explicitly allowlisted campaign tags. Do not copy
      // sign-in tokens, account identifiers, or arbitrary query parameters.
      ["utm_source","utm_medium","utm_campaign","utm_term","utm_content","source"].forEach(function (name) {
        if (old.searchParams.has(name)) next.searchParams.set(name, old.searchParams.get(name));
      });
      link.href = next.pathname + next.search;
    });
  }
  var site = {get: read, set: function(lang) { save(lang); updateLinks(lang); }, syncLinks: updateLinks, normalize: normalize};
  window.HSKSiteLanguage = site;
  // The root is the default Tajik entry for crawlers and first visits. Only
  // visitors with an explicit stored preference are sent to their own home.
  var remembered = read();
  if (window.location.pathname === "/" && remembered && remembered !== "tg") {
    var preferred = new URL(HOME[remembered], window.location.origin);
    var incoming = new URL(window.location.href);
    ["utm_source","utm_medium","utm_campaign","utm_term","utm_content","source"].forEach(function (key) {
      if (incoming.searchParams.has(key)) preferred.searchParams.set(key, incoming.searchParams.get(key));
    });
    window.location.replace(preferred.pathname + preferred.search);
    return;
  }
  var current = fromPath();
  if (current) site.set(current);
  document.querySelectorAll("[data-site-lang]").forEach(function (link) {
    link.addEventListener("click", function () { save(link.getAttribute("data-site-lang")); });
  });
  updateLinks(current || read() || "tg");
})();
