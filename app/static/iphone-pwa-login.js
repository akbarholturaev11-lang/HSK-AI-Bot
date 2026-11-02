/* Source-parity Android LinkScreen port: PWA browser actor only; no fake Telegram login. */
(function () {
  "use strict";
  const language = document.getElementById("language");
  const title = document.getElementById("title");
  const subtitle = document.getElementById("subtitle");
  const tagline = document.getElementById("tagline");
  const status = document.getElementById("status");
  const actions = document.getElementById("actions");
  const buttons = Array.from(actions.querySelectorAll("[data-provider]"));
  const oauthButtons = buttons.filter((button) => button.dataset.provider !== "telegram");
  let locale = new URLSearchParams(location.search).get("lang");
  if (!["uz", "ru", "tj"].includes(locale)) locale = "uz";
  let statusKey = null;
  let statusError = false;
  language.value = locale;

  function label(key) {
    const catalog = window.HSKAI_COMMON_I18N;
    return catalog && catalog[locale] && catalog[locale][key] || "";
  }
  function message(key, error) {
    statusKey = key || null;
    statusError = !!error;
    status.textContent = key ? label(key) : "";
    if (statusError) status.setAttribute("role", "alert");
    else status.removeAttribute("role");
  }
  function render() {
    document.documentElement.lang = locale === "tj" ? "tg" : locale;
    title.textContent = label("pwaAuth.welcome") || "HSK AI";
    subtitle.textContent = label("pwaAuth.choose") || "";
    tagline.textContent = label("pwaAuth.tagline") || "";
    if (statusKey) message(statusKey, statusError);
  }
  language.addEventListener("change", () => {
    locale = language.value;
    render();
  });
  async function json(path, options) {
    const response = await fetch(path, Object.assign({
      credentials: "same-origin", cache: "no-store",
    }, options));
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error("request_failed");
    return payload;
  }
  async function bootstrap() {
    render();
    if (window.HSKCharacters && typeof window.HSKCharacters.mount === "function") {
      window.HSKCharacters.mount(document.getElementById("panda"), "panda", "loading");
    }
    try {
      const actor = await json("/api/v3/pwa-auth/session");
      if (["uz", "ru", "tj"].includes(actor.language)) {
        locale = actor.language;
        language.value = locale;
        render();
      }
      actions.hidden = true;
      message("desktopAuth.linked", false);
    } catch (_) {
      try {
        const payload = await json("/api/v3/pwa-auth/providers");
        const providers = Array.isArray(payload.providers) ? payload.providers : [];
        oauthButtons.forEach((button) => {
          button.hidden = !providers.includes(button.dataset.provider);
          button.disabled = false;
        });
        actions.hidden = false;
        if (!oauthButtons.some((button) => !button.hidden)) {
          message("desktopAuth.providerFailed", true);
        }
      } catch (_) {
        actions.hidden = true;
        message("desktopAuth.providerFailed", true);
      }
    }
  }
  async function start(button) {
    if (button.dataset.provider === "telegram") {
      // Android has a proof-poll Telegram flow; PWA has not yet implemented it.
      // Never substitute a Telegram deep-link for authenticated browser login.
      message("pwaAuth.telegramPending", false);
      return;
    }
    oauthButtons.forEach((b) => { b.disabled = true; });
    message("desktopAuth.starting", false);
    try {
      const payload = await json("/api/v3/pwa-auth/start", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: button.dataset.provider, language: locale }),
      });
      const url = new URL(payload.authorize_url);
      const expected = button.dataset.provider === "google"
        ? "accounts.google.com" : "appleid.apple.com";
      if (url.protocol !== "https:" || url.hostname !== expected) {
        throw new Error("untrusted_url");
      }
      location.assign(url.href);
    } catch (_) {
      message("desktopAuth.providerFailed", true);
      oauthButtons.forEach((b) => { if (!b.hidden) b.disabled = false; });
    }
  }
  buttons.forEach((button) => button.addEventListener("click", () => start(button)));
  bootstrap();
}());
