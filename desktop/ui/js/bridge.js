import { previewInvoke } from "./preview-mock.js";

const COMMANDS = Object.freeze({
  appInfo: "desktop_app_info",
  authStatus: "desktop_auth_status",
  linkStart: "desktop_link_start",
  linkPoll: "desktop_link_poll",
  linkOpenTelegram: "desktop_link_open_telegram",
  openExternalUrl: "desktop_open_external_url",
  bootstrap: "desktop_bootstrap",
  logout: "desktop_logout",
  courseMap: "desktop_course_map",
  lessonData: "desktop_lesson_data",
  lessonComplete: "desktop_lesson_complete",
  setLanguage: "desktop_set_language",
  setNotifications: "desktop_set_notifications",
  subscriptionOverview: "desktop_subscription_overview",
  subscriptionQuote: "desktop_subscription_quote",
  subscriptionSubmit: "desktop_subscription_submit",
  vocabularyState: "desktop_vocabulary_state",
  vocabularySave: "desktop_vocabulary_save",
  referralOverview: "desktop_referral_overview",
  goalState: "desktop_goal_state",
  goalSave: "desktop_goal_save",
  practiceStart: "desktop_practice_start",
  practiceComplete: "desktop_practice_complete",
  ratingLeaderboard: "desktop_rating_leaderboard",
  voiceStatus: "desktop_voice_status",
  voiceSessionStart: "desktop_voice_session_start",
  voiceMessage: "desktop_voice_message",
  voicePronounce: "desktop_voice_pronounce",
  voiceSessionEnd: "desktop_voice_session_end",
  ttsSpeak: "desktop_tts_speak",
  localAiModelStatus: "local_ai_model_status",
  localAiInstallStart: "local_ai_install_start",
  localAiInstallCancel: "local_ai_install_cancel",
  localAiPackRemove: "local_ai_pack_remove",
  localAiChat: "local_ai_chat",
  localAiChatCancel: "local_ai_chat_cancel",
  updateCheck: "desktop_update_check",
  updateInstall: "desktop_update_install",
});

const ALLOWED_COMMANDS = new Set(Object.values(COMMANDS));
const SUPPORTED_LANGUAGES = new Set(["uz", "ru", "tj"]);
const SUBSCRIPTION_PLANS = new Set(["10_days", "1_month", "3_months"]);
const SUBSCRIPTION_METHODS = new Set(["visa", "alipay", "wechat"]);
const CARD_COUNTRIES = new Set(["tj", "uz", "ru", "other"]);
// Mirrors GOAL_KINDS in src-tauri/src/lib.rs. Onboarding is the only writer.
export const GOAL_KINDS = Object.freeze(["conversation", "hsk", "study"]);
const SCREENSHOT_PREFIXES = new Set([
  "data:image/jpeg;base64",
  "data:image/jpg;base64",
  "data:image/png;base64",
  "data:image/webp;base64",
]);
const MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024;
const MAX_SCREENSHOT_BASE64_CHARS = Math.ceil(MAX_SCREENSHOT_BYTES / 3) * 4;
const VOICE_ROLES = new Set([
  "lily",
  "chen",
  "xiao_mei",
  "teacher_li",
  "manager_wang",
  "friend",
  "roommate",
  "seller",
  "classmate",
  "social",
]);
const VOICE_LEVELS = new Set([
  "beginner",
  "hsk1",
  "hsk2",
  "hsk3",
  "hsk4",
  "hsk1_2",
  "hsk3_4",
]);
const VOICE_VOICES = new Set(["female", "male"]);
// macOS WKWebView records audio/mp4, Windows WebView2 records audio/webm.
const AUDIO_PREFIXES = new Set([
  "data:audio/webm;base64",
  "data:audio/ogg;base64",
  "data:audio/mp4;base64",
  "data:audio/mpeg;base64",
  "data:audio/wav;base64",
]);
const MAX_VOICE_AUDIO_BYTES = 5 * 1024 * 1024;
const MAX_VOICE_AUDIO_BASE64_CHARS = Math.ceil(MAX_VOICE_AUDIO_BYTES / 3) * 4;
const VOICE_SESSION_ID_PATTERN = /^[A-Za-z0-9-]{8,64}$/;
const MAX_VOICE_TARGET_CHARS = 120;
const MAX_VOICE_PINYIN_CHARS = 240;
const EVENT_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{15,79}$/;
const CHECKOUT_ATTEMPT_PATTERN = /^[A-Za-z0-9_-]{16,80}$/;
const LOCAL_AI_EVENTS = new Set([
  "local-ai://pack-progress",
  "local-ai://runtime-status",
  "local-ai://chat-delta",
  "local-ai://chat-finished",
  "local-ai://error",
]);
const DESKTOP_UPDATE_EVENTS = new Set(["desktop-update://progress"]);
const LOCAL_AI_ROLES = new Set(["user", "assistant"]);
const MAX_LOCAL_AI_PROMPT_CHARS = 4_000;
const MAX_LOCAL_AI_HISTORY_MESSAGES = 12;

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
    /\b(desktop|course|auth|link|local_ai|practice|rating|notifications)_[a-z0-9_]{2,72}\b/,
  );
  if (stableMatch) {
    return stableMatch[0];
  }
  const accessMatch = normalized.match(
    /\b(free_feature_limit_reached|invalid_lesson_order|invalid_language|invalid_screenshot|invalid_practice_session|unknown_training_skill|payment_invalid_plan|payment_details_missing|qr_not_ready|admin_notification_failed|checkout_attempt_not_opened)\b/,
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

function hasOnlySearchKeys(parsed, allowed) {
  return [...parsed.searchParams.keys()].every((key) => allowed.includes(key));
}

function singleSearchValue(parsed, key) {
  const values = parsed.searchParams.getAll(key);
  return values.length === 1 ? values[0] : "";
}

function isAllowedReferralShareLink(value) {
  let parsed = null;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  const handle = parsed.pathname.replace(/^\/+|\/+$/g, "");
  const start = parsed.searchParams.get("start") || "";
  return (
    parsed.protocol === "https:" &&
    parsed.hostname === "t.me" &&
    !parsed.username &&
    !parsed.password &&
    !parsed.port &&
    !parsed.hash &&
    /^[A-Za-z0-9_]{5,32}$/.test(handle) &&
    /^ref_[A-Za-z0-9_-]{1,124}$/.test(start) &&
    parsed.searchParams.getAll("start").length === 1 &&
    [...parsed.searchParams.keys()].length === 1
  );
}

function isAllowedShareText(value) {
  const text = String(value || "");
  return (
    [...text].length <= 1000 &&
    !/[\u0000-\u0008\u000b-\u000c\u000e-\u001f\u007f]/.test(text) &&
    text.split(/\s+/).some(isAllowedReferralShareLink)
  );
}

function assertExternalUrl(value) {
  const url = String(value || "").trim();
  if (!url || url.length > 4096 || /[\u0000-\u001f\u007f]/.test(url)) {
    throw new DesktopBridgeError("desktop_external_url_invalid");
  }
  let parsed = null;
  try {
    parsed = new URL(url);
  } catch {
    throw new DesktopBridgeError("desktop_external_url_invalid");
  }
  if (parsed.username || parsed.password || parsed.port || parsed.hash) {
    throw new DesktopBridgeError("desktop_external_url_invalid");
  }
  const host = parsed.hostname;
  if (parsed.protocol === "tg:") {
    if (
      host === "msg_url" &&
      hasOnlySearchKeys(parsed, ["url", "text"]) &&
      isAllowedReferralShareLink(singleSearchValue(parsed, "url"))
    ) {
      return url;
    }
  } else if (parsed.protocol === "whatsapp:") {
    if (
      host === "send" &&
      hasOnlySearchKeys(parsed, ["text"]) &&
      isAllowedShareText(singleSearchValue(parsed, "text"))
    ) {
      return url;
    }
  } else if (parsed.protocol === "https:") {
    if (
      (host === "t.me" || host === "telegram.me") &&
      parsed.pathname === "/share/url" &&
      hasOnlySearchKeys(parsed, ["url", "text"]) &&
      isAllowedReferralShareLink(singleSearchValue(parsed, "url"))
    ) {
      return url;
    }
    if (
      host === "wa.me" &&
      (parsed.pathname === "" || parsed.pathname === "/") &&
      hasOnlySearchKeys(parsed, ["text"]) &&
      isAllowedShareText(singleSearchValue(parsed, "text"))
    ) {
      return url;
    }
    if (
      host === "api.whatsapp.com" &&
      parsed.pathname === "/send" &&
      hasOnlySearchKeys(parsed, ["text"]) &&
      isAllowedShareText(singleSearchValue(parsed, "text"))
    ) {
      return url;
    }
  }
  throw new DesktopBridgeError("desktop_external_url_invalid");
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

const PRACTICE_MODES = new Set(["placement", "mock", "training"]);
const TRAINING_SKILLS = new Set([
  "listening",
  "writing",
  "characters",
  "pronunciation",
  "pinyin",
]);
const MAX_PRACTICE_ANSWERS = 100;

const MAX_VOCABULARY_ENTRIES = 2_000;
const CJK_WORD_PATTERN = /^[\u4e00-\u9fff]{1,24}$/;

function assertVocabularyList(value) {
  if (!Array.isArray(value)) {
    throw new DesktopBridgeError("desktop_vocabulary_request_invalid");
  }
  const out = [];
  const seen = new Set();
  for (const item of value) {
    const word = String(item || "").trim();
    if (!CJK_WORD_PATTERN.test(word) || seen.has(word)) continue;
    seen.add(word);
    out.push(word);
    if (out.length >= MAX_VOCABULARY_ENTRIES) break;
  }
  return out;
}

function assertPracticeMode(value) {
  const mode = String(value || "").trim().toLowerCase();
  if (!PRACTICE_MODES.has(mode)) {
    throw new DesktopBridgeError("desktop_practice_request_invalid");
  }
  return mode;
}

function assertPracticeSkill(mode, value) {
  const skill = String(value || "").trim().toLowerCase();
  if (String(mode || "").trim().toLowerCase() !== "training") {
    if (skill) throw new DesktopBridgeError("desktop_practice_request_invalid");
    return "";
  }
  if (!TRAINING_SKILLS.has(skill)) {
    throw new DesktopBridgeError("unknown_training_skill");
  }
  return skill;
}

function assertPracticeLevel(value) {
  const level = String(value || "").trim().toLowerCase();
  if (!/^[a-z0-9_]{1,16}$/.test(level)) {
    throw new DesktopBridgeError("desktop_practice_request_invalid");
  }
  return level;
}

function assertPracticeSessionId(value) {
  const id = String(value || "").trim();
  if (id.length < 8 || id.length > 160) {
    throw new DesktopBridgeError("desktop_practice_request_invalid");
  }
  return id;
}

function assertPracticeAnswers(value) {
  if (!Array.isArray(value) || value.length > MAX_PRACTICE_ANSWERS) {
    throw new DesktopBridgeError("desktop_practice_request_invalid");
  }
  return value.map((item) => {
    const questionId = String(item?.question_id || "").trim();
    const selected = Number(item?.selected);
    if (
      !questionId ||
      questionId.length > 120 ||
      !Number.isInteger(selected) ||
      selected < -1 ||
      selected > 32
    ) {
      throw new DesktopBridgeError("desktop_practice_request_invalid");
    }
    return { question_id: questionId, selected };
  });
}

function assertVoiceSelection(role, level, voice) {
  if (!VOICE_ROLES.has(String(role || ""))) {
    throw new DesktopBridgeError("desktop_voice_role_invalid");
  }
  if (!VOICE_LEVELS.has(String(level || ""))) {
    throw new DesktopBridgeError("desktop_voice_level_invalid");
  }
  if (!VOICE_VOICES.has(String(voice || ""))) {
    throw new DesktopBridgeError("desktop_voice_request_invalid");
  }
}

function assertVoiceSessionId(value) {
  const normalized = String(value || "").trim();
  if (!VOICE_SESSION_ID_PATTERN.test(normalized)) {
    throw new DesktopBridgeError("desktop_voice_session_invalid");
  }
  return normalized;
}

function assertVoiceAudioDataUrl(value) {
  const source = String(value || "");
  const separator = source.indexOf(",");
  if (separator < 0) {
    throw new DesktopBridgeError("desktop_voice_audio_invalid");
  }
  const prefix = source.slice(0, separator);
  const encoded = source.slice(separator + 1);
  if (!AUDIO_PREFIXES.has(prefix) || !encoded) {
    throw new DesktopBridgeError("desktop_voice_audio_invalid");
  }
  if (encoded.length > MAX_VOICE_AUDIO_BASE64_CHARS) {
    throw new DesktopBridgeError("desktop_voice_audio_too_large");
  }
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(encoded)) {
    throw new DesktopBridgeError("desktop_voice_audio_invalid");
  }
  return source;
}

function assertVoiceTarget(value) {
  const normalized = String(value || "").trim();
  if (!normalized || [...normalized].length > MAX_VOICE_TARGET_CHARS) {
    throw new DesktopBridgeError("desktop_voice_request_invalid");
  }
  return normalized;
}

function assertVoicePinyin(value) {
  const normalized = String(value || "").trim();
  if ([...normalized].length > MAX_VOICE_PINYIN_CHARS) {
    throw new DesktopBridgeError("desktop_voice_request_invalid");
  }
  return normalized;
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

function assertLocalAiRequest(request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw new DesktopBridgeError("local_ai_request_invalid");
  }
  const requestId = String(request.requestId || "").trim();
  const prompt = String(request.prompt || "").trim();
  const language = assertLanguage(request.language);
  const history = Array.isArray(request.history) ? request.history : [];
  const maxTokens = Number(request.maxTokens ?? 384);
  if (
    !EVENT_ID_PATTERN.test(requestId) ||
    prompt.length === 0 ||
    [...prompt].length > MAX_LOCAL_AI_PROMPT_CHARS ||
    new TextEncoder().encode(prompt).length > 16 * 1024 ||
    history.length > MAX_LOCAL_AI_HISTORY_MESSAGES ||
    !Number.isInteger(maxTokens) ||
    maxTokens < 1 ||
    maxTokens > 512
  ) {
    throw new DesktopBridgeError("local_ai_request_invalid");
  }
  let historyBytes = 0;
  const normalizedHistory = history.map((message) => {
    const role = String(message?.role || "");
    const content = String(message?.content || "").trim();
    const encodedLength = new TextEncoder().encode(content).length;
    if (
      !LOCAL_AI_ROLES.has(role) ||
      content.length === 0 ||
      [...content].length > 8_000 ||
      encodedLength > 16 * 1024
    ) {
      throw new DesktopBridgeError("local_ai_request_invalid");
    }
    historyBytes += encodedLength;
    return { role, content };
  });
  if (historyBytes > 64 * 1024) {
    throw new DesktopBridgeError("local_ai_request_invalid");
  }
  return {
    requestId,
    prompt,
    language,
    history: normalizedHistory,
    maxTokens,
  };
}

function assertLocalAiRequestId(value) {
  const requestId = String(value || "").trim();
  if (!EVENT_ID_PATTERN.test(requestId)) {
    throw new DesktopBridgeError("local_ai_request_invalid");
  }
  return requestId;
}

export async function listenLocalAi(eventName, handler) {
  if (!LOCAL_AI_EVENTS.has(eventName) || typeof handler !== "function") {
    throw new DesktopBridgeError("desktop_operation_not_allowed");
  }
  const listen = globalThis.__TAURI__?.event?.listen;
  if (typeof listen !== "function") {
    return () => {};
  }
  try {
    return await listen(eventName, (event) => handler(event?.payload));
  } catch {
    throw new DesktopBridgeError("local_ai_event_unavailable");
  }
}

export async function listenDesktopUpdate(eventName, handler) {
  if (!DESKTOP_UPDATE_EVENTS.has(eventName) || typeof handler !== "function") {
    throw new DesktopBridgeError("desktop_operation_not_allowed");
  }
  const listen = globalThis.__TAURI__?.event?.listen;
  if (typeof listen !== "function") {
    return () => {};
  }
  try {
    return await listen(eventName, (event) => handler(event?.payload));
  } catch {
    throw new DesktopBridgeError("desktop_update_event_unavailable");
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

  openExternalUrl(url) {
    return invokeCommand(COMMANDS.openExternalUrl, {
      url: assertExternalUrl(url),
    });
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

  setNotifications(enabled) {
    if (typeof enabled !== "boolean") {
      return Promise.reject(
        new DesktopBridgeError("desktop_notifications_request_invalid"),
      );
    }
    return invokeCommand(COMMANDS.setNotifications, { enabled });
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

  vocabularyState() {
    return invokeCommand(COMMANDS.vocabularyState);
  },

  vocabularySave({ saved, review }) {
    return invokeCommand(COMMANDS.vocabularySave, {
      saved: assertVocabularyList(saved),
      review: assertVocabularyList(review),
    });
  },

  referralOverview(timezoneOffset) {
    const offset = Number(timezoneOffset);
    if (!Number.isInteger(offset) || offset < -720 || offset > 840) {
      throw new DesktopBridgeError("desktop_referral_request_invalid");
    }
    return invokeCommand(COMMANDS.referralOverview, { timezoneOffset: offset });
  },

  goalState() {
    return invokeCommand(COMMANDS.goalState);
  },

  goalSave(kind) {
    // The same whitelist lives in Rust; this copy only avoids a pointless IPC
    // round trip when the caller passes something the backend would reject.
    if (!GOAL_KINDS.includes(String(kind))) {
      throw new DesktopBridgeError("desktop_goal_request_invalid");
    }
    return invokeCommand(COMMANDS.goalSave, { kind: String(kind) });
  },

  practiceStart({ mode, level, language, skill }) {
    return invokeCommand(COMMANDS.practiceStart, {
      mode: assertPracticeMode(mode),
      level: assertPracticeLevel(level),
      language: assertLanguage(language),
      skill: assertPracticeSkill(mode, skill),
    });
  },

  practiceComplete({ sessionId, mode, level, language, skill, answers }) {
    return invokeCommand(COMMANDS.practiceComplete, {
      sessionId: assertPracticeSessionId(sessionId),
      mode: assertPracticeMode(mode),
      level: assertPracticeLevel(level),
      language: assertLanguage(language),
      skill: assertPracticeSkill(mode, skill),
      answers: assertPracticeAnswers(answers),
    });
  },

  ratingLeaderboard(timezoneOffset) {
    const offset = Number(timezoneOffset);
    if (!Number.isInteger(offset) || offset < -720 || offset > 840) {
      throw new DesktopBridgeError("desktop_rating_request_invalid");
    }
    return invokeCommand(COMMANDS.ratingLeaderboard, { timezoneOffset: offset });
  },

  voiceStatus() {
    return invokeCommand(COMMANDS.voiceStatus);
  },

  voiceSessionStart({ role, level, language, voice }) {
    assertVoiceSelection(role, level, voice);
    return invokeCommand(COMMANDS.voiceSessionStart, {
      role: String(role),
      level: String(level),
      language: assertLanguage(language),
      voice: String(voice),
    });
  },

  voiceMessage({ sessionId, audioDataUrl }) {
    return invokeCommand(COMMANDS.voiceMessage, {
      sessionId: assertVoiceSessionId(sessionId),
      audioDataUrl: assertVoiceAudioDataUrl(audioDataUrl),
    });
  },

  voicePronounce({ target, targetPinyin, language, level, audioDataUrl }) {
    if (!VOICE_LEVELS.has(String(level || ""))) {
      throw new DesktopBridgeError("desktop_voice_level_invalid");
    }
    return invokeCommand(COMMANDS.voicePronounce, {
      target: assertVoiceTarget(target),
      targetPinyin: assertVoicePinyin(targetPinyin),
      language: assertLanguage(language),
      level: String(level),
      audioDataUrl: assertVoiceAudioDataUrl(audioDataUrl),
    });
  },

  voiceSessionEnd(sessionId) {
    return invokeCommand(COMMANDS.voiceSessionEnd, {
      sessionId: assertVoiceSessionId(sessionId),
    });
  },

  localAiModelStatus() {
    return invokeCommand(COMMANDS.localAiModelStatus);
  },

  localAiInstallStart() {
    return invokeCommand(COMMANDS.localAiInstallStart);
  },

  localAiInstallCancel() {
    return invokeCommand(COMMANDS.localAiInstallCancel);
  },

  localAiPackRemove() {
    return invokeCommand(COMMANDS.localAiPackRemove);
  },

  localAiChat(request) {
    return invokeCommand(COMMANDS.localAiChat, {
      request: assertLocalAiRequest(request),
    });
  },

  localAiChatCancel(requestId) {
    return invokeCommand(COMMANDS.localAiChatCancel, {
      requestId: assertLocalAiRequestId(requestId),
    });
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
