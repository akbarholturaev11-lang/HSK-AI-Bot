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
  // The server renders the root in Russian, including for no-JavaScript crawlers.
  // Respect a previously chosen language without overriding the Russian default.
  var remembered = read();
  if (window.location.pathname === "/" && remembered && remembered !== "ru") {
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
  updateLinks(current || read() || "ru");

  // Exclusive mobile header menus. Without this, both anchored overlays can
  // cover each other after a quick globe/menu sequence on narrow screens.
  var headerMenus = ".site-header details.language-switch, .site-header details.mobile-nav";
  function compactHeader() {
    return window.matchMedia ? window.matchMedia("(max-width: 850px)").matches : window.innerWidth <= 850;
  }
  document.addEventListener("toggle", function (event) {
    var menu = event.target;
    if (!compactHeader() || !menu.matches || !menu.matches(headerMenus) || !menu.open) return;
    document.querySelectorAll(headerMenus).forEach(function (other) {
      if (other !== menu) other.open = false;
    });
  }, true);
  document.addEventListener("keydown", function (event) {
    if (!compactHeader() || event.key !== "Escape") return;
    document.querySelectorAll(headerMenus).forEach(function (menu) {
      if (menu.open) {
        menu.open = false;
        var summary = menu.querySelector("summary");
        if (summary) summary.focus();
      }
    });
  });
  document.addEventListener("click", function (event) {
    if (!compactHeader() || (event.target.closest && event.target.closest(headerMenus))) return;
    document.querySelectorAll(headerMenus).forEach(function (menu) { menu.open = false; });
  });
})();
