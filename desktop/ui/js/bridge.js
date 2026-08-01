import { previewInvoke } from "./preview-mock.js";

const COMMANDS = Object.freeze({
  appInfo: "desktop_app_info",
  authStatus: "desktop_auth_status",
  linkStart: "desktop_link_start",
  linkPoll: "desktop_link_poll",
  linkOpenTelegram: "desktop_link_open_telegram",
  bootstrap: "desktop_bootstrap",
  logout: "desktop_logout",
  courseMap: "desktop_course_map",
  lessonData: "desktop_lesson_data",
  lessonComplete: "desktop_lesson_complete",
  setLanguage: "desktop_set_language",
  subscriptionOverview: "desktop_subscription_overview",
  subscriptionQuote: "desktop_subscription_quote",
  subscriptionSubmit: "desktop_subscription_submit",
  ttsSpeak: "desktop_tts_speak",
  localAiModelStatus: "local_ai_model_status",
  updateCheck: "desktop_update_check",
  updateInstall: "desktop_update_install",
});

const ALLOWED_COMMANDS = new Set(Object.values(COMMANDS));
const SUPPORTED_LANGUAGES = new Set(["uz", "ru", "tj"]);
const SUBSCRIPTION_PLANS = new Set(["10_days", "1_month", "3_months"]);
const SUBSCRIPTION_METHODS = new Set(["visa", "alipay", "wechat"]);
const CARD_COUNTRIES = new Set(["tj", "uz", "ru", "other"]);
const SCREENSHOT_PREFIXES = new Set([
  "data:image/jpeg;base64",
  "data:image/jpg;base64",
  "data:image/png;base64",
  "data:image/webp;base64",
]);
const MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024;
const MAX_SCREENSHOT_BASE64_CHARS = Math.ceil(MAX_SCREENSHOT_BYTES / 3) * 4;
const EVENT_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{15,79}$/;
const CHECKOUT_ATTEMPT_PATTERN = /^[A-Za-z0-9_-]{16,80}$/;

function explicitPreviewEnabled() {
  const location = globalThis.location;
  if (!location || !["localhost", "127.0.0.1"].includes(location.hostname)) {
    return false;
  }
  return new URLSearchParams(location.search).get("mock") === "1";
}

function nativeInvoke() {
  const tauri = globalThis.__TAURI__;
  const invoke = tauri?.core?.invoke ?? tauri?.invoke;
  return typeof invoke === "function" ? invoke.bind(tauri.core ?? tauri) : null;
}

function stableErrorCode(error) {
  const raw =
    typeof error === "string"
      ? error
      : typeof error?.message === "string"
        ? error.message
        : "";
  const normalized = raw.toLowerCase();
  const stableMatch = normalized.match(
    /\b(desktop|course|auth|link)_[a-z0-9_]{2,72}\b/,
  );
  if (stableMatch) {
    return stableMatch[0];
  }
  const accessMatch = normalized.match(
    /\b(free_feature_limit_reached|invalid_lesson_order|invalid_language|invalid_screenshot|payment_invalid_plan|payment_details_missing|qr_not_ready|admin_notification_failed|checkout_attempt_not_opened)\b/,
  );
  if (accessMatch) {
    return accessMatch[0];
  }
  if (
    normalized.includes("401") ||
    normalized.includes("unauthorized") ||
    normalized.includes("token")
  ) {
    return "desktop_unauthorized";
  }
  if (
    normalized.includes("network") ||
    normalized.includes("timeout") ||
    normalized.includes("connect")
  ) {
    return "desktop_network_unavailable";
  }
  return "desktop_request_failed";
}

export class DesktopBridgeError extends Error {
  constructor(code) {
    super(code);
    this.name = "DesktopBridgeError";
    this.code = code;
  }
}

function assertLessonOrder(value) {
  const lessonOrder = Number(value);
  if (!Number.isInteger(lessonOrder) || lessonOrder < 1 || lessonOrder > 500) {
    throw new DesktopBridgeError("desktop_lesson_order_invalid");
  }
  return lessonOrder;
}

function assertLanguage(value) {
  const language = String(value || "").trim().toLowerCase();
  if (!SUPPORTED_LANGUAGES.has(language)) {
    throw new DesktopBridgeError("desktop_language_invalid");
  }
  return language;
}

function normalizedSubscriptionValue(value) {
  return String(value || "").trim().toLowerCase();
}

function assertSubscriptionSelection(plan, method, country) {
  const normalizedPlan = normalizedSubscriptionValue(plan);
  const normalizedMethod = normalizedSubscriptionValue(method);
  if (!SUBSCRIPTION_PLANS.has(normalizedPlan)) {
    throw new DesktopBridgeError("desktop_subscription_request_invalid");
  }
  if (!SUBSCRIPTION_METHODS.has(normalizedMethod)) {
    throw new DesktopBridgeError("desktop_subscription_request_invalid");
  }

  if (normalizedMethod !== "visa") {
    if (country !== null && country !== undefined && country !== "") {
      throw new DesktopBridgeError("desktop_subscription_request_invalid");
    }
    return {
      plan: normalizedPlan,
      method: normalizedMethod,
      country: null,
    };
  }

  const normalizedCountry = normalizedSubscriptionValue(country);
  if (!CARD_COUNTRIES.has(normalizedCountry)) {
    throw new DesktopBridgeError("desktop_subscription_request_invalid");
  }
  return {
    plan: normalizedPlan,
    method: normalizedMethod,
    country: normalizedCountry,
  };
}

function assertScreenshotDataUrl(value) {
  const dataUrl = String(value || "");
  const separator = dataUrl.indexOf(",");
  if (separator < 0 || !SCREENSHOT_PREFIXES.has(dataUrl.slice(0, separator))) {
    throw new DesktopBridgeError("desktop_payment_file_type_invalid");
  }
  const encoded = dataUrl.slice(separator + 1);
  if (
    encoded.length === 0 ||
    encoded.length > MAX_SCREENSHOT_BASE64_CHARS ||
    encoded.length % 4 !== 0 ||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(encoded)
  ) {
    throw new DesktopBridgeError("desktop_payment_file_invalid");
  }
  const padding = encoded.endsWith("==") ? 2 : encoded.endsWith("=") ? 1 : 0;
  const decodedBytes = (encoded.length / 4) * 3 - padding;
  if (decodedBytes <= 0 || decodedBytes > MAX_SCREENSHOT_BYTES) {
    throw new DesktopBridgeError("desktop_payment_file_too_large");
  }
  return dataUrl;
}

function assertCheckoutAttemptId(value) {
  if (value === null || value === undefined || value === "") return null;
  const attemptId = String(value).trim();
  if (!CHECKOUT_ATTEMPT_PATTERN.test(attemptId)) {
    throw new DesktopBridgeError("desktop_subscription_request_invalid");
  }
  return attemptId;
}

function subscriptionPayload(value, kind) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new DesktopBridgeError("desktop_subscription_payload_invalid");
  }
  if (
    value.ok !== true ||
    value.source !== "desktop_subscription" ||
    value.mode !== "subscription"
  ) {
    throw new DesktopBridgeError("desktop_subscription_payload_invalid");
  }

  if (kind === "overview") {
    const access = value.access;
    if (
      !access ||
      typeof access !== "object" ||
      !["free", "paid", "blocked"].includes(access.state) ||
      typeof access.is_paid !== "boolean" ||
      !value.prices ||
      typeof value.prices !== "object" ||
      Array.isArray(value.prices)
    ) {
      throw new DesktopBridgeError("desktop_subscription_payload_invalid");
    }
  } else if (kind === "quote") {
    if (!value.quote || typeof value.quote !== "object" || Array.isArray(value.quote)) {
      throw new DesktopBridgeError("desktop_subscription_quote_invalid");
    }
  } else if (kind === "submit" && value.status !== "pending") {
    throw new DesktopBridgeError("desktop_subscription_submit_invalid");
  }
  return value;
}

function assertCompletion(eventId, mistakes) {
  if (!EVENT_ID_PATTERN.test(String(eventId || ""))) {
    throw new DesktopBridgeError("desktop_event_id_invalid");
  }
  if (!Array.isArray(mistakes) || mistakes.length > 50) {
    throw new DesktopBridgeError("desktop_mistakes_invalid");
  }
  let encoded;
  try {
    encoded = JSON.stringify(mistakes);
  } catch {
    throw new DesktopBridgeError("desktop_mistakes_invalid");
  }
  if (encoded.length > 64 * 1024) {
    throw new DesktopBridgeError("desktop_mistakes_invalid");
  }
}

async function invokeCommand(command, args = {}) {
  if (!ALLOWED_COMMANDS.has(command)) {
    throw new DesktopBridgeError("desktop_operation_not_allowed");
  }

  const invoke = nativeInvoke();
  if (!invoke && !explicitPreviewEnabled()) {
    throw new DesktopBridgeError("desktop_bridge_unavailable");
  }

  try {
    return invoke
      ? await invoke(command, args)
      : await previewInvoke(command, args);
  } catch (error) {
    if (error instanceof DesktopBridgeError) {
      throw error;
    }
    throw new DesktopBridgeError(stableErrorCode(error));
  }
}

export const desktopBridge = Object.freeze({
  preview: explicitPreviewEnabled(),

  appInfo() {
    return invokeCommand(COMMANDS.appInfo);
  },

  authStatus() {
    return invokeCommand(COMMANDS.authStatus);
  },

  linkStart() {
    return invokeCommand(COMMANDS.linkStart);
  },

  linkPoll() {
    return invokeCommand(COMMANDS.linkPoll);
  },

  linkOpenTelegram() {
    return invokeCommand(COMMANDS.linkOpenTelegram);
  },

  bootstrap() {
    return invokeCommand(COMMANDS.bootstrap);
  },

  logout() {
    return invokeCommand(COMMANDS.logout);
  },

  courseMap() {
    const timezoneOffsetMinutes = -new Date().getTimezoneOffset();
    if (
      !Number.isInteger(timezoneOffsetMinutes) ||
      timezoneOffsetMinutes < -720 ||
      timezoneOffsetMinutes > 840
    ) {
      return Promise.reject(
        new DesktopBridgeError("desktop_timezone_invalid"),
      );
    }
    return invokeCommand(COMMANDS.courseMap, { timezoneOffsetMinutes });
  },

  lessonData(lessonOrder) {
    return invokeCommand(COMMANDS.lessonData, {
      lessonOrder: assertLessonOrder(lessonOrder),
    });
  },

  lessonComplete(lessonOrder, eventId, mistakes) {
    const normalizedLessonOrder = assertLessonOrder(lessonOrder);
    assertCompletion(eventId, mistakes);
    return invokeCommand(COMMANDS.lessonComplete, {
      lessonOrder: normalizedLessonOrder,
      eventId: String(eventId),
      mistakes,
    });
  },

  setLanguage(language) {
    return invokeCommand(COMMANDS.setLanguage, {
      language: assertLanguage(language),
    });
  },

  async subscriptionOverview() {
    return subscriptionPayload(
      await invokeCommand(COMMANDS.subscriptionOverview),
      "overview",
    );
  },

  async subscriptionQuote(plan, method, country) {
    const selection = assertSubscriptionSelection(plan, method, country);
    const payload = subscriptionPayload(
      await invokeCommand(COMMANDS.subscriptionQuote, {
        plan: selection.plan,
        method: selection.method,
        country: selection.country,
      }),
      "quote",
    );
    if (
      payload.quote.plan_type !== selection.plan ||
      payload.quote.payment_method !== selection.method
    ) {
      throw new DesktopBridgeError("desktop_subscription_quote_invalid");
    }
    return payload;
  },

  async subscriptionSubmit(
    plan,
    method,
    country,
    screenshotDataUrl,
    attemptId = null,
  ) {
    const selection = assertSubscriptionSelection(plan, method, country);
    return subscriptionPayload(
      await invokeCommand(COMMANDS.subscriptionSubmit, {
        plan: selection.plan,
        method: selection.method,
        country: selection.country,
        screenshotDataUrl: assertScreenshotDataUrl(screenshotDataUrl),
        attemptId: assertCheckoutAttemptId(attemptId),
      }),
      "submit",
    );
  },

  ttsSpeak(text) {
    const normalized = String(text || "").trim();
    if (
      normalized.length === 0 ||
      normalized.length > 4_000 ||
      [...normalized].length > 1_000
    ) {
      return Promise.reject(
        new DesktopBridgeError("desktop_tts_text_invalid"),
      );
    }
    return invokeCommand(COMMANDS.ttsSpeak, { text: normalized });
  },

  localAiModelStatus() {
    return invokeCommand(COMMANDS.localAiModelStatus);
  },

  updateCheck() {
    return invokeCommand(COMMANDS.updateCheck);
  },

  updateInstall() {
    return invokeCommand(COMMANDS.updateInstall);
  },
});

export function isSessionError(error) {
  return [
    "desktop_unauthorized",
    "desktop_session_not_found",
    "desktop_session_revoked",
    "desktop_refresh_invalid",
    "desktop_refresh_reuse_detected",
    "desktop_access_invalid",
    "desktop_access_expired",
    "desktop_not_linked",
    "auth_session_expired",
  ].includes(error?.code);
}
