/* Login-only PWA host. No Telegram initData, payment or course API bypass. */
(function () {
  "use strict";
  const language = document.getElementById("language");
  const title = document.getElementById("title");
  const status = document.getElementById("status");
  const actions = document.getElementById("actions");
  const buttons = Array.from(actions.querySelectorAll("[data-provider]"));
  let locale = new URLSearchParams(location.search).get("lang");
  if (!["uz", "ru", "tj"].includes(locale)) locale = "uz";
  language.value = locale;
  function label(key) {
    const catalog = window.HSKAI_COMMON_I18N;
    return catalog && catalog[locale] && catalog[locale][key] || "";
  }
  function show(text, error) {
    status.textContent = text;
    if (error) status.setAttribute("role", "alert");
    else status.removeAttribute("role");
  }
  function render() {
    document.documentElement.lang = locale === "tj" ? "tg" : locale;
    title.textContent = label("desktopAuth.title") || "HSK AI";
    buttons.forEach((button) => {
      button.textContent = label("desktopAuth." + button.dataset.provider + "Continue");
    });
  }
  language.addEventListener("change", () => {
    locale = language.value;
    render();
  });
  async function json(path, options) {
    const response = await fetch(path, Object.assign({credentials: "same-origin", cache: "no-store"}, options));
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error("request_failed");
    return payload;
  }
  async function bootstrap() {
    render();
    try {
      const actor = await json("/api/v3/pwa-auth/session");
      if (["uz", "ru", "tj"].includes(actor.language)) {
        locale = actor.language;
        language.value = locale;
        render();
      }
      actions.hidden = true;
      show(label("desktopAuth.linked"), false);
    } catch (_) {
      try {
        const payload = await json("/api/v3/pwa-auth/providers");
        const providers = Array.isArray(payload.providers) ? payload.providers : [];
        buttons.forEach((button) => {
          button.hidden = !providers.includes(button.dataset.provider);
          button.disabled = false;
        });
        actions.hidden = !providers.length;
        if (!providers.length) show(label("desktopAuth.providerFailed"), true);
      } catch (_) {
        actions.hidden = true;
        show(label("desktopAuth.providerFailed"), true);
      }
    }
  }
  async function start(button) {
    buttons.forEach((b) => {b.disabled = true;});
    show(label("desktopAuth.starting"), false);
    try {
      const payload = await json("/api/v3/pwa-auth/start", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({provider: button.dataset.provider, language: locale})
      });
      const url = new URL(payload.authorize_url);
      const expected = button.dataset.provider === "google" ? "accounts.google.com" : "appleid.apple.com";
      if (url.protocol !== "https:" || url.hostname !== expected) throw new Error("untrusted_url");
      location.assign(url.href);
    } catch (_) {
      show(label("desktopAuth.providerFailed"), true);
      buttons.forEach((b) => {if (!b.hidden) b.disabled = false;});
    }
  }
  buttons.forEach((b) => b.addEventListener("click", () => start(b)));
  // The generated common catalog is a local file, loaded before this script.
  bootstrap();
}());
