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
  const telegramStorageKey = 'hskai.pwa.telegram.pending';
  let telegramPolling = null;
  let telegramClaimInFlight = false;
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
    if (!response.ok || !payload.ok) throw new Error(typeof payload.error === "string" ? payload.error : "request_failed");
    return payload;
  }
  function uuid(value) {
    return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  }
  function stopTelegramPolling() {
    if (telegramPolling !== null) window.clearInterval(telegramPolling);
    telegramPolling = null;
  }
  async function claimTelegram() {
    const linkId = sessionStorage.getItem(telegramStorageKey);
    if (!uuid(linkId) || document.visibilityState === "hidden" || telegramClaimInFlight) return;
    telegramClaimInFlight = true;
    try {
      const reply = await json("/api/v3/pwa-auth/telegram/claim", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({link_request_id: linkId}),
      });
      if (reply.status === "complete" && sessionStorage.getItem(telegramStorageKey) === linkId) {
        sessionStorage.removeItem(telegramStorageKey);
        stopTelegramPolling();
        actions.hidden = true;
        message("desktopAuth.linked", false);
      }
    } catch (error) {
      if (sessionStorage.getItem(telegramStorageKey) !== linkId) return;
      // A brief offline period or server error must not discard the
      // browser-bound Telegram request; the next poll can still claim it.
      const terminal = [
        "pwa_telegram_not_approved", "pwa_telegram_expired",
        "pwa_telegram_proof_invalid", "pwa_telegram_owner_invalid",
        "pwa_telegram_invalid",
      ].includes(error.message);
      if (!terminal) {
        message("desktopAuth.providerFailed", true);
        return;
      }
      sessionStorage.removeItem(telegramStorageKey);
      stopTelegramPolling();
      const key = error.message === "pwa_telegram_not_approved"
        ? "desktopAuth.cancelled"
        : error.message === "pwa_telegram_expired"
          ? "desktopAuth.expired" : "desktopAuth.providerFailed";
      message(key, true);
      buttons.forEach((b) => { if (!b.hidden) b.disabled = false; });
    } finally {
      telegramClaimInFlight = false;
    }
  }
  function resumeTelegram() {
    const linkId = sessionStorage.getItem(telegramStorageKey);
    if (!uuid(linkId)) return;
    actions.hidden = false;
    message("pwaAuth.telegramPending", false);
    if (telegramPolling === null) {
      telegramPolling = window.setInterval(claimTelegram, 2500);
    }
    claimTelegram();
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") claimTelegram();
  });
  window.addEventListener("focus", claimTelegram);

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
      // Authentication is complete: an older pending Telegram flow cannot
      // be resumed after the next logout or account switch.
      sessionStorage.removeItem(telegramStorageKey);
      stopTelegramPolling();
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
        resumeTelegram();
        if (new URLSearchParams(location.search).get("auth") === "cancelled" &&
            !uuid(sessionStorage.getItem(telegramStorageKey))) {
          message("desktopAuth.cancelled", true);
        }
      } catch (_) {
        actions.hidden = true;
        message("desktopAuth.providerFailed", true);
      }
    }
  }
  async function start(button) {
    if (button.dataset.provider === "telegram") {
      buttons.forEach((b) => { b.disabled = true; });
      message("desktopAuth.starting", false);
      try {
        const payload = await json("/api/v3/pwa-auth/telegram/start", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({language: locale}),
        });
        const link = new URL(payload.authorize_url);
        if (link.protocol !== "https:" || link.hostname !== "t.me" ||
            !uuid(payload.link_request_id) ||
            !link.searchParams.get("start")?.startsWith("pwa_link_" + payload.link_request_id)) {
          throw new Error("invalid_bot_link");
        }
        sessionStorage.setItem(telegramStorageKey, payload.link_request_id);
        message("pwaAuth.telegramPending", false);
        location.assign(link.href);
      } catch (_) {
        message("desktopAuth.providerFailed", true);
        buttons.forEach((b) => { if (!b.hidden) b.disabled = false; });
      }
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
