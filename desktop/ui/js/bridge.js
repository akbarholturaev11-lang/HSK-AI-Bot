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
  ttsSpeak: "desktop_tts_speak",
  localAiModelStatus: "local_ai_model_status",
  updateCheck: "desktop_update_check",
  updateInstall: "desktop_update_install",
});

const ALLOWED_COMMANDS = new Set(Object.values(COMMANDS));
const SUPPORTED_LANGUAGES = new Set(["uz", "ru", "tj"]);
const EVENT_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{15,79}$/;

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
    /\b(free_feature_limit_reached|invalid_lesson_order|invalid_language)\b/,
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
