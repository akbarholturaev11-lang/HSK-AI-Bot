import {
  desktopBridge,
  GOAL_KINDS,
  isSessionError,
  listenDesktopUpdate,
  listenLocalAi,
} from "./bridge.js";
import {
  getLanguage,
  languageOptions,
  normalizeLanguage,
  pick,
  setLanguage as setUiLanguage,
  t,
} from "./i18n.js";
import { LessonController } from "./lesson.js";
import { DesktopSubscriptionController } from "./subscription.js";
import { DesktopPracticeController } from "./practice.js";
import { DesktopVocabularyController } from "./vocabulary.js";
import { DesktopVoiceController } from "./voice.js";
import { createPandaMascot, hydratePandaMascot } from "./mascot.js";

const $ = (selector) => document.querySelector(selector);

const dom = {
  boot: $("#boot-state"),
  bootMessage: $("#boot-message"),
  auth: $("#auth-screen"),
  authTitle: $("#auth-title"),
  authDescription: $("#auth-description"),
  authCodeWrap: $("#auth-code-wrap"),
  authCodeLabel: $("#auth-code-label"),
  authCode: $("#auth-code"),
  authExpiry: $("#auth-expiry"),
  authStatus: $("#auth-status"),
  authError: $("#auth-error"),
  authStep1: $("#auth-step-1"),
  authStep2: $("#auth-step-2"),
  authStep3: $("#auth-step-3"),
  startLink: $("#start-link"),
  openTelegram: $("#open-telegram"),
  retryLink: $("#retry-link"),
  copyCode: $("#copy-code"),
  workspace: $("#workspace"),
  offlinePill: $("#offline-pill"),
  rail: $("#course-rail"),
  railScrim: $("#rail-scrim"),
  railToggle: $("#rail-toggle"),
  railAvatar: $("#rail-avatar"),
  railUserName: $("#rail-user-name"),
  railPlan: $("#rail-plan"),
  railLevelLabel: $("#rail-level-label"),
  railCompleted: $("#rail-completed"),
  navigation: $("#course-navigation"),
  showToday: $("#show-today"),
  showCourse: $("#show-course"),
  showPractice: $("#show-practice"),
  showVoice: $("#show-voice"),
  showVocabulary: $("#show-vocabulary"),
  showRating: $("#show-rating"),
  showSubscription: $("#show-subscription"),
  showProfile: $("#show-profile"),
  todayLabel: $("#today-label"),
  courseLabel: $("#course-label"),
  practiceLabel: $("#practice-label"),
  voiceLabel: $("#voice-label"),
  vocabularyLabel: $("#vocabulary-label"),
  ratingLabel: $("#rating-label"),
  subscriptionLabel: $("#subscription-label"),
  subscriptionBadge: $("#subscription-badge"),
  profileLabel: $("#profile-label"),
  contentTitle: $("#content-title"),
  contentSubtitle: $("#content-subtitle"),
  content: $("#content-inner"),
  globalSearch: $("#global-search"),
  headerStreak: $("#header-streak"),
  headerXp: $("#header-xp"),
  railProfileButton: $("#rail-profile-button"),
  refreshMap: $("#refresh-map"),
  updateBanner: $("#update-banner"),
  updateStatus: $("#update-status"),
  updateTitle: $("#update-title"),
  updateMessage: $("#update-message"),
  updateNotes: $("#update-notes"),
  updateProgress: $("#update-progress"),
  updateProgressBar: $("#update-progress-bar"),
  updateProgressDetail: $("#update-progress-detail"),
  updateAction: $("#update-action"),
  aiLauncher: $("#ai-launcher"),
  aiDrawer: $("#ai-drawer"),
  closeAi: $("#close-ai"),
  aiTitle: $("#ai-title"),
  aiSubtitle: $("#ai-subtitle"),
  aiBody: $("#ai-body"),
  aiFileInput: $("#ai-file-input"),
  aiAttach: $("#ai-attach"),
  aiAttachments: $("#ai-attachments"),
  aiInput: $("#ai-input"),
  aiEmoji: $("#ai-emoji"),
  aiRecord: $("#ai-record"),
  aiSend: $("#ai-send"),
  aiFooterStatus: $("#ai-footer-status"),
  aiShortcut: $("#ai-shortcut"),
  searchShortcut: $("#search-shortcut"),
  railCollapse: $("#rail-collapse"),
  railResizer: $("#rail-resizer"),
  notificationsButton: $("#notifications-button"),
  notificationsDot: $("#notifications-dot"),
  notificationsPanel: $("#notifications-panel"),
  notificationsBody: $("#notifications-body"),
  closeNotifications: $("#close-notifications"),
  toast: $("#toast"),
  closeLesson: $("#close-lesson"),
  onboardingLayer: $("#onboarding-layer"),
  onboardingTitle: $("#onboarding-title"),
  onboardingSubtitle: $("#onboarding-subtitle"),
  onboardingSteps: $("#onboarding-steps"),
  onboardingBody: $("#onboarding-body"),
  onboardingBack: $("#onboarding-back"),
  onboardingLater: $("#onboarding-later"),
  onboardingStart: $("#onboarding-start"),
};

const state = {
  bootstrap: null,
  map: null,
  appVersion: "",
  view: "today",
  searchQuery: "",
  authDeadline: 0,
  authCountdownTimer: null,
  authPollTimer: null,
  authPolling: false,
  authLinkedPending: false,
  telegramOpened: false,
  pendingBootstrap: null,
  railOpen: false,
  aiOpen: false,
  aiPreviousFocus: null,
  aiLoaded: false,
  aiStatus: null,
  aiMessages: [],
  aiAttachments: [],
  aiBusy: false,
  aiRecording: false,
  aiRecorder: null,
  aiRecordStream: null,
  aiRecordStartedAt: 0,
  aiRecordType: null,
  aiRecordDiscard: false,
  aiRecordingTimer: null,
  aiInstallBusy: false,
  aiRequestId: null,
  aiStreamText: "",
  aiListenersReady: false,
  aiUnlisten: [],
  aiOpenedByLesson: false,
  reduceMotion: false,
  referral: null,
  referralError: "",
  referralModalOpen: false,
  referralPreviousFocus: null,
  referralCopied: false,
  goal: null,
  onboardingOpen: false,
  onboardingStep: 0,
  onboardingChoice: "",
  onboardingPreviousFocus: null,
  railCollapsed: false,
  railWidth: 0,
  notificationsOpen: false,
  notificationsSaving: false,
  notificationInitialized: false,
  notificationRefreshTimer: null,
  seenNotificationIds: new Set(),
  notificationPermission: "unsupported",
  ratingRequest: 0,
  ratingBoard: null,
  ratingError: "",
  updateStatus: "idle",
  updateInfo: null,
  updateErrorStage: "check",
  updateShowChecking: false,
  updateProgress: null,
  updateUnlisten: null,
  toastTimer: null,
};

const LESSON_AI_DOCK_QUERY = "(min-width: 1100px)";
const NOTIFICATION_REFRESH_MS = 60_000;
const SEEN_NOTIFICATIONS_STORAGE_KEY = "pomp-hsk-seen-notifications";
const MAX_SEEN_NOTIFICATION_IDS = 80;
const AI_MAX_ATTACHMENTS = 4;
const AI_MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const AI_MAX_AUDIO_BYTES = 5 * 1024 * 1024;
const AI_MAX_RECORDING_MS = 30_000;
const AI_MIN_RECORDING_MS = 700;
const AI_RECORDER_TYPES = [
  { mime: "audio/webm;codecs=opus", extension: "webm" },
  { mime: "audio/webm", extension: "webm" },
  { mime: "audio/mp4", extension: "mp4" },
  { mime: "audio/ogg;codecs=opus", extension: "ogg" },
  { mime: "audio/ogg", extension: "ogg" },
];

const lesson = new LessonController({
  bridge: desktopBridge,
  onCompleted: async () => {
    await loadCourseMap({ keepView: true });
  },
  onSessionExpired: () => showAuth({ expired: true }),
  onAccessRequired: () => {
    state.view = "subscription";
    renderActiveView();
    showToast(t("manageSubscription"));
  },
  onOpen: () => handleLessonOpened(),
  onClose: () => handleLessonClosed(),
  onContextChanged: () => refreshAiContextPanel(),
});

const subscription = new DesktopSubscriptionController({
  host: dom.content,
  bridge: desktopBridge,
  t,
  language: getLanguage(),
  onSessionExpired: (error) => {
    if (!isSessionError(error)) return false;
    showAuth({ expired: true });
    return true;
  },
  onAccessChanged: async (access) => {
    if (state.map?.user) {
      state.map.user.is_paid = Boolean(access?.is_paid);
      state.map.user.access_state = String(access?.state || "free");
    }
    await loadCourseMap({ keepView: true });
  },
  onToast: showToast,
});

const voice = new DesktopVoiceController({
  host: null,
  bridge: desktopBridge,
  t,
  language: getLanguage(),
  onSessionExpired: () => showAuth({ expired: true }),
  onToast: showToast,
  onOpenSubscription: () => routeTo("subscription"),
  speak: (text, button) => void speakChinese(text, button),
  onContextChanged: () => refreshAiContextPanel(),
});

const vocabulary = new DesktopVocabularyController({
  host: null,
  bridge: desktopBridge,
  t,
  language: getLanguage(),
  onToast: showToast,
  speak: (text, button) => void speakChinese(text, button),
  onAskAi: (prompt) => openAiWithPrompt(prompt),
  onContextChanged: () => refreshAiContextPanel(),
});

const practice = new DesktopPracticeController({
  host: null,
  bridge: desktopBridge,
  t,
  language: getLanguage(),
  level: "hsk1",
  onSessionExpired: () => showAuth({ expired: true }),
  onToast: showToast,
  onOpenSubscription: () => routeTo("subscription"),
  speak: (text, button) => void speakChinese(text, button),
  onContextChanged: () => refreshAiContextPanel(),
});

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== "") {
    node.textContent = String(text);
  }
  return node;
}

function readSavedLanguage() {
  try {
    return normalizeLanguage(localStorage.getItem("pomp-hsk-language"));
  } catch {
    return "uz";
  }
}

function saveLanguage(language) {
  try {
    localStorage.setItem("pomp-hsk-language", language);
  } catch {
    // Language persistence is optional; the server remains authoritative.
  }
}

function applyStaticText() {
  dom.bootMessage.textContent = t("appPreparing");
  dom.authTitle.textContent = t("authTitle");
  dom.authDescription.textContent = t("authDescription");
  dom.authCodeLabel.textContent = t("authCodeLabel");
  dom.authStep1.textContent = t("authStep1");
  dom.authStep2.textContent = t("authStep2");
  dom.authStep3.textContent = t("authStep3");
  dom.startLink.textContent = t("authStart");
  dom.openTelegram.textContent = t("authOpen");
  dom.retryLink.textContent = t("authRetry");
  dom.copyCode.setAttribute("aria-label", t("copyCode"));
  dom.todayLabel.textContent = t("today");
  dom.courseLabel.textContent = t("course");
  dom.practiceLabel.textContent = t("practice");
  dom.voiceLabel.textContent = t("voice");
  dom.vocabularyLabel.textContent = t("vocabulary");
  dom.ratingLabel.textContent = t("rating");
  dom.subscriptionLabel.textContent = t("subscription");
  dom.profileLabel.textContent = t("profile");
  dom.refreshMap.setAttribute("aria-label", t("refresh"));
  dom.aiTitle.textContent = t("aiTitle");
  dom.aiSubtitle.textContent = t("aiSubtitle");
  dom.aiLauncher.setAttribute("aria-label", t("openAi"));
  dom.closeAi.setAttribute("aria-label", t("closeAi"));
  dom.aiAttach.setAttribute("aria-label", t("aiAttachMedia"));
  dom.aiEmoji.setAttribute("aria-label", t("aiEmoji"));
  dom.aiRecord.setAttribute("aria-label", t("aiRecord"));
  dom.aiSend.setAttribute("aria-label", t("aiSend"));
  dom.closeLesson.setAttribute("aria-label", t("lessonClose"));
  updateAiComposer();
  dom.globalSearch.placeholder = t("searchLessons");
  dom.offlinePill.textContent = t("offline");
  subscription.setLanguage(getLanguage());
  updateRailToggleLabel();
  renderUpdateBanner();
}

function hydrateStaticMascots() {
  document
    .querySelectorAll(".panda-mascot")
    .forEach((mascot) => hydratePandaMascot(mascot));
}

function showOnly(section) {
  dom.boot.hidden = section !== "boot";
  dom.auth.hidden = section !== "auth";
  dom.workspace.hidden = section !== "workspace";
}

function setContentLoading() {
  const wrap = element("div", "loading-card");
  wrap.append(
    element("div", "spinner"),
    element("p", "", t("loadingCourse")),
  );
  dom.content.replaceChildren(wrap);
}

function setProgress(fill, numerator, denominator) {
  const safeDenominator = Math.max(1, Number(denominator) || 1);
  const ratio = Math.max(
    0,
    Math.min(1, (Number(numerator) || 0) / safeDenominator),
  );
  const step = Math.round(ratio * 20);
  fill.dataset.progress = String(step);
  fill.parentElement?.setAttribute("aria-valuenow", String(Math.round(ratio * 100)));
}

function showToast(message) {
  clearTimeout(state.toastTimer);
  dom.toast.textContent = String(message || "");
  dom.toast.classList.add("is-visible");
  state.toastTimer = setTimeout(() => {
    dom.toast.classList.remove("is-visible");
  }, 2800);
}

function desktopNotificationPermission() {
  if (!("Notification" in globalThis)) return "unsupported";
  return globalThis.Notification.permission || "default";
}

function readSeenNotificationIds() {
  try {
    const raw = JSON.parse(
      localStorage.getItem(SEEN_NOTIFICATIONS_STORAGE_KEY) || "[]",
    );
    if (!Array.isArray(raw)) return new Set();
    return new Set(
      raw
        .map((item) => String(item || "").trim())
        .filter((item) => item.length > 0 && item.length <= 120)
        .slice(0, MAX_SEEN_NOTIFICATION_IDS),
    );
  } catch {
    return new Set();
  }
}

function saveSeenNotificationIds() {
  try {
    localStorage.setItem(
      SEEN_NOTIFICATIONS_STORAGE_KEY,
      JSON.stringify([...state.seenNotificationIds].slice(-MAX_SEEN_NOTIFICATION_IDS)),
    );
  } catch {
    // Notification dedupe is a convenience; the real feed still comes from the server.
  }
}

function restoreNotificationState() {
  state.notificationPermission = desktopNotificationPermission();
  state.seenNotificationIds = readSeenNotificationIds();
}

function notificationMasterEnabled() {
  return state.map?.notify?.enabled !== false;
}

function lessonAiShouldAutoOpen() {
  try {
    return globalThis.matchMedia?.(LESSON_AI_DOCK_QUERY).matches === true;
  } catch {
    return globalThis.innerWidth >= 1100;
  }
}

function syncLessonChrome() {
  const lessonOpen = lesson.isOpen;
  document.documentElement.classList.toggle("lesson-active", lessonOpen);
  document.documentElement.classList.toggle(
    "lesson-ai-open",
    lessonOpen && state.aiOpen,
  );
}

function trapFocusWithin(root, event) {
  const focusable = [
    ...root.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
  if (focusable.length === 0) {
    event.preventDefault();
    return;
  }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (!focusable.includes(document.activeElement)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function handleLessonOpened() {
  state.aiOpenedByLesson = false;
  syncLessonChrome();
  if (lessonAiShouldAutoOpen() && !state.aiOpen) {
    state.aiOpenedByLesson = true;
    openAi({ focus: false });
  }
}

function handleLessonClosed() {
  const shouldCloseAi = state.aiOpenedByLesson && state.aiOpen;
  state.aiOpenedByLesson = false;
  syncLessonChrome();
  if (shouldCloseAi) {
    closeAi({ restoreFocus: false });
  }
}

function updateNetworkState() {
  dom.offlinePill.hidden = navigator.onLine !== false;
  if (state.aiOpen && state.aiStatus && !aiIsReady()) {
    renderAiInstaller();
    updateAiComposer();
  }
}

function normalizedUpdateText(value, maxLength) {
  return [...String(value ?? "").trim()].slice(0, maxLength).join("");
}

function normalizeUpdatePayload(payload) {
  if (!payload || typeof payload.available !== "boolean") {
    throw new Error("desktop_update_payload_invalid");
  }
  const currentVersion = normalizedUpdateText(payload.currentVersion, 64);
  const version = normalizedUpdateText(payload.version, 64);
  if (!currentVersion || (payload.available && !version)) {
    throw new Error("desktop_update_payload_invalid");
  }
  return {
    available: payload.available,
    currentVersion,
    version,
    notes: normalizedUpdateText(payload.notes, 500),
  };
}

function normalizeUpdateProgress(payload) {
  if (!payload || typeof payload !== "object") return null;
  const downloadedBytes = Number(payload.downloadedBytes);
  const totalBytes =
    payload.totalBytes === undefined || payload.totalBytes === null
      ? null
      : Number(payload.totalBytes);
  const percent =
    payload.percent === undefined || payload.percent === null
      ? null
      : Number(payload.percent);
  if (
    !Number.isFinite(downloadedBytes) ||
    downloadedBytes < 0 ||
    downloadedBytes > 20_000_000_000 ||
    (totalBytes !== null &&
      (!Number.isFinite(totalBytes) ||
        totalBytes <= 0 ||
        totalBytes > 20_000_000_000)) ||
    (percent !== null &&
      (!Number.isFinite(percent) || percent < 0 || percent > 100))
  ) {
    return null;
  }
  return {
    downloadedBytes,
    totalBytes,
    percent: percent === null ? null : Math.round(percent),
    state: normalizedUpdateText(payload.state, 32),
  };
}

function updateBytesLabel(value) {
  const megabytes = Number(value || 0) / (1024 * 1024);
  return `${megabytes >= 10 ? megabytes.toFixed(0) : megabytes.toFixed(1)} MB`;
}

function renderUpdateProgress() {
  const progress = state.updateProgress;
  const visible = state.updateStatus === "installing" && progress;
  dom.updateProgress.hidden = !visible;
  if (!visible) {
    dom.updateProgressBar.removeAttribute("value");
    dom.updateProgressDetail.textContent = "";
    return;
  }
  if (progress.percent === null) {
    dom.updateProgressBar.removeAttribute("value");
  } else {
    dom.updateProgressBar.value = progress.percent;
  }
  dom.updateProgressDetail.textContent = progress.totalBytes
    ? `${updateBytesLabel(progress.downloadedBytes)} / ${updateBytesLabel(progress.totalBytes)} · ${progress.percent ?? 0}%`
    : updateBytesLabel(progress.downloadedBytes);
}

function renderUpdateBanner() {
  const status = state.updateStatus;
  const hiddenStatus =
    status === "idle" ||
    status === "current" ||
    (status === "checking" && !state.updateShowChecking);
  const shouldHide = dom.workspace.hidden || hiddenStatus;

  if (shouldHide) {
    const hadFocus = dom.updateBanner.contains(document.activeElement);
    dom.updateBanner.hidden = true;
    if (hadFocus && !dom.workspace.hidden) {
      dom.contentTitle.focus();
    }
    return;
  }

  dom.updateBanner.hidden = false;
  dom.updateBanner.className = "update-banner";
  dom.updateBanner.classList.toggle(
    "is-loading",
    ["checking", "installing", "ready"].includes(status),
  );
  dom.updateBanner.classList.toggle("is-error", status === "error");
  dom.updateStatus.setAttribute(
    "aria-busy",
    String(["checking", "installing"].includes(status)),
  );
  dom.updateNotes.hidden = true;
  dom.updateNotes.textContent = "";
  dom.updateAction.hidden = false;
  dom.updateAction.disabled = false;
  renderUpdateProgress();

  if (status === "checking") {
    dom.updateTitle.textContent = t("updateCheckingTitle");
    dom.updateMessage.textContent = t("updateCheckingBody");
    dom.updateAction.textContent = t("updateRetry");
    dom.updateAction.disabled = true;
    return;
  }

  if (status === "available") {
    dom.updateTitle.textContent = t("updateAvailableTitle", {
      version: state.updateInfo?.version || "—",
    });
    dom.updateMessage.textContent = t("updateAvailableBody");
    dom.updateAction.textContent = t("updateInstall");
    if (state.updateInfo?.notes) {
      dom.updateNotes.textContent = state.updateInfo.notes;
      dom.updateNotes.hidden = false;
    }
    return;
  }

  if (status === "installing") {
    dom.updateTitle.textContent = t("updateInstallingTitle");
    dom.updateMessage.textContent = t("updateInstallingBody");
    dom.updateAction.textContent = t("updateInstall");
    dom.updateAction.disabled = true;
    return;
  }

  if (status === "ready") {
    dom.updateTitle.textContent = t("updateReadyTitle");
    dom.updateMessage.textContent = t("updateReadyBody");
    dom.updateAction.hidden = true;
    return;
  }

  dom.updateTitle.textContent =
    state.updateErrorStage === "install"
      ? t("updateInstallFailedTitle")
      : t("updateCheckFailedTitle");
  dom.updateMessage.textContent = t("updateErrorBody");
  dom.updateAction.textContent = t("updateRetry");
}

async function checkForUpdates({ showProgress = false } = {}) {
  if (["checking", "installing", "ready"].includes(state.updateStatus)) {
    return;
  }
  state.updateStatus = "checking";
  state.updateInfo = null;
  state.updateProgress = null;
  state.updateErrorStage = "check";
  state.updateShowChecking = showProgress;
  renderUpdateBanner();

  try {
    const result = normalizeUpdatePayload(
      await desktopBridge.updateCheck(),
    );
    state.updateInfo = result;
    state.updateStatus = result.available ? "available" : "current";
  } catch {
    state.updateStatus = "error";
    state.updateErrorStage = "check";
  } finally {
    state.updateShowChecking = false;
    renderUpdateBanner();
  }
}

function updateActivityInProgress() {
  return (
    lesson.isOpen ||
    state.aiBusy ||
    state.aiInstallBusy ||
    state.view === "subscription"
  );
}

async function installUpdate() {
  if (state.updateStatus !== "available" && !(
    state.updateStatus === "error" &&
    state.updateErrorStage === "install"
  )) {
    return;
  }
  if (updateActivityInProgress()) {
    showToast(t("updateLessonActive"));
    return;
  }

  state.updateProgress = {
    downloadedBytes: 0,
    totalBytes: null,
    percent: null,
    state: "starting",
  };
  state.updateStatus = "installing";
  state.updateErrorStage = "install";
  renderUpdateBanner();
  try {
    await desktopBridge.updateInstall();
    state.updateStatus = "ready";
  } catch {
    state.updateStatus = "error";
    state.updateErrorStage = "install";
  }
  renderUpdateBanner();
}

function handleUpdateAction() {
  if (state.updateStatus === "error" && state.updateErrorStage === "check") {
    checkForUpdates({ showProgress: true });
    return;
  }
  void installUpdate();
}

function openLesson(lessonOrder) {
  if (["installing", "ready"].includes(state.updateStatus)) {
    showToast(t("updateInstallInProgress"));
    return;
  }
  lesson.open(lessonOrder);
}

function clearAuthTimers() {
  if (state.authCountdownTimer) {
    clearInterval(state.authCountdownTimer);
  }
  if (state.authPollTimer) {
    clearTimeout(state.authPollTimer);
  }
  state.authCountdownTimer = null;
  state.authPollTimer = null;
  state.authPolling = false;
}

function resetAuthForm() {
  clearAuthTimers();
  state.authDeadline = 0;
  state.authLinkedPending = false;
  state.telegramOpened = false;
  state.pendingBootstrap = null;
  dom.authCodeWrap.hidden = true;
  dom.authCode.textContent = "";
  dom.authExpiry.textContent = "";
  dom.authStatus.textContent = "";
  dom.authError.textContent = "";
  dom.startLink.hidden = false;
  dom.startLink.disabled = false;
  dom.openTelegram.hidden = true;
  dom.openTelegram.disabled = false;
  dom.retryLink.hidden = true;
  dom.retryLink.disabled = false;
}

function resetAiSession() {
  const requestId = state.aiRequestId;
  state.aiLoaded = false;
  state.aiStatus = null;
  state.aiBusy = false;
  cancelAiRecording();
  clearAiAttachments({ includeMessages: true });
  state.aiMessages = [];
  state.aiInstallBusy = false;
  state.aiRequestId = null;
  state.aiStreamText = "";
  dom.aiInput.value = "";
  dom.aiBody.replaceChildren();
  dom.aiFooterStatus.textContent = "";
  updateAiComposer();
  if (requestId) {
    void desktopBridge.localAiChatCancel(requestId).catch(() => {});
  }
}

function showAuth({ expired = false } = {}) {
  if (lesson.isOpen) {
    lesson.close();
  }
  // A dropped session must never leave the goal dialog floating over the
  // login screen.
  closeOnboarding();
  closeReferralModal({ restoreFocus: false });
  closeAi();
  stopNotificationRefresh();
  resetAiSession();
  voice.dispose();
  practice.dispose();
  vocabulary.dispose();
  closeRail();
  state.bootstrap = null;
  state.map = null;
  state.ratingBoard = null;
  state.ratingError = "";
  state.notificationInitialized = false;
  subscription.overview = null;
  subscription.setUser(null);
  resetAuthForm();
  applyStaticText();
  if (expired) {
    dom.authError.textContent = t("sessionExpired");
  }
  showOnly("auth");
  dom.startLink.focus();
}

function formatCountdown(seconds) {
  const safe = Math.max(0, Math.ceil(seconds));
  const minutes = Math.floor(safe / 60);
  const remainder = String(safe % 60).padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function updateAuthCountdown() {
  const remaining = Math.ceil((state.authDeadline - Date.now()) / 1000);
  if (remaining <= 0) {
    expireLink(t("authExpired"));
    return;
  }
  dom.authExpiry.textContent = t("authExpires", {
    time: formatCountdown(remaining),
  });
}

function expireLink(message) {
  clearAuthTimers();
  dom.authExpiry.textContent = "";
  dom.authStatus.textContent = "";
  dom.authError.textContent = message;
  dom.openTelegram.hidden = true;
  dom.retryLink.hidden = false;
  dom.retryLink.disabled = false;
}

async function startLink() {
  clearAuthTimers();
  state.telegramOpened = false;
  dom.authError.textContent = "";
  dom.authStatus.textContent = t("authStarting");
  dom.startLink.disabled = true;
  dom.retryLink.disabled = true;

  try {
    const result = await desktopBridge.linkStart();
    if (
      result?.status !== "pending" ||
      !result.displayCode ||
      !Number.isFinite(Number(result.expiresIn))
    ) {
      throw new Error("desktop_link_payload_invalid");
    }
    dom.authCode.textContent = String(result.displayCode);
    dom.authCodeWrap.hidden = false;
    dom.startLink.hidden = true;
    dom.openTelegram.hidden = false;
    dom.retryLink.hidden = false;
    dom.retryLink.disabled = false;
    dom.authStatus.textContent = t("authWaiting");
    state.authDeadline =
      Date.now() + Math.max(1, Number(result.expiresIn)) * 1000;
    updateAuthCountdown();
    state.authCountdownTimer = setInterval(updateAuthCountdown, 1000);
    scheduleLinkPoll(900);
  } catch (error) {
    dom.startLink.disabled = false;
    dom.retryLink.disabled = false;
    dom.authStatus.textContent = "";
    dom.authError.textContent = errorMessage(error);
  }
}

function scheduleLinkPoll(delay = 2500) {
  if (!state.authDeadline || Date.now() >= state.authDeadline) {
    expireLink(t("authExpired"));
    return;
  }
  state.authPollTimer = setTimeout(pollLink, delay);
}

async function pollLink() {
  if (state.authPolling || !state.authDeadline) {
    return;
  }
  state.authPolling = true;
  try {
    const result = await desktopBridge.linkPoll();
    if (result?.status === "linked") {
      clearAuthTimers();
      dom.authError.textContent = "";
      dom.authStatus.textContent = t("authLinked");
      state.authLinkedPending = true;
      state.pendingBootstrap = result.bootstrap || null;
      dom.openTelegram.hidden = true;
      dom.retryLink.hidden = false;
      dom.retryLink.textContent = t("retry");
      await resumeLinkedBootstrap();
      return;
    }
    if (result?.status === "cancelled") {
      expireLink(t("authCancelled"));
      return;
    }
    if (result?.status === "expired") {
      expireLink(t("authExpired"));
      return;
    }
    scheduleLinkPoll();
  } catch (error) {
    if (
      error?.code === "desktop_link_expired" ||
      Date.now() >= state.authDeadline
    ) {
      expireLink(t("authExpired"));
    } else if (
      error?.code === "desktop_link_invalid" ||
      error?.code === "desktop_link_consumed"
    ) {
      expireLink(t("authCancelled"));
    } else {
      dom.authError.textContent = errorMessage(error);
      scheduleLinkPoll(3500);
    }
  } finally {
    state.authPolling = false;
  }
}

async function resumeLinkedBootstrap() {
  dom.retryLink.disabled = true;
  try {
    const bootstrap =
      state.pendingBootstrap || (await desktopBridge.bootstrap());
    state.pendingBootstrap = null;
    state.authLinkedPending = false;
    await enterWorkspace(bootstrap);
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    dom.authStatus.textContent = t("authLinked");
    dom.authError.textContent = errorMessage(error);
    dom.retryLink.hidden = false;
    dom.retryLink.disabled = false;
    dom.retryLink.textContent = t("retry");
  }
}

async function openTelegram() {
  if (state.telegramOpened) {
    return;
  }
  dom.openTelegram.disabled = true;
  try {
    await desktopBridge.linkOpenTelegram();
    state.telegramOpened = true;
    dom.openTelegram.hidden = true;
    dom.authError.textContent = "";
    dom.authStatus.textContent = t("authTelegramOpened");
  } catch (error) {
    dom.authStatus.textContent = "";
    dom.authError.textContent = errorMessage(error);
    dom.openTelegram.disabled = false;
  }
}

async function copyAuthCode() {
  const code = dom.authCode.textContent.trim();
  if (!code) {
    return;
  }
  try {
    await navigator.clipboard.writeText(code);
    showToast(t("copied"));
  } catch {
    showToast(t("requestFailed"));
  }
}

async function enterWorkspace(bootstrap) {
  if (!bootstrap?.user) {
    throw new Error("desktop_bootstrap_invalid");
  }
  state.bootstrap = bootstrap;
  subscription.setUser(bootstrap.user);
  const serverLanguage = normalizeLanguage(bootstrap.user.language);
  setUiLanguage(serverLanguage);
  saveLanguage(serverLanguage);
  applyStaticText();
  showOnly("workspace");
  renderUpdateBanner();
  dom.contentTitle.focus();
  await loadCourseMap();
  startNotificationRefresh();
  // Asked here and nowhere else: the profile only displays the result.
  await maybeOpenOnboarding();
}

async function loadCourseMap({ keepView = false } = {}) {
  if (!keepView) {
    state.view = "today";
  }
  // XP and the weekly league change after a lesson, so the cached board is
  // dropped and refetched the next time the rating screen opens.
  state.ratingBoard = null;
  state.ratingError = "";
  dom.refreshMap.disabled = true;
  setContentLoading();
  try {
    const map = await desktopBridge.courseMap();
    if (
      !map ||
      map.ok !== true ||
      !Array.isArray(map.units) ||
      !map.user ||
      !map.progress
    ) {
      throw new Error("desktop_course_map_invalid");
    }
    state.map = map;
    subscription.setUser(map.user);
    syncServerNotifications({ initial: !state.notificationInitialized });
    const serverLanguage = normalizeLanguage(map.user.language);
    if (serverLanguage !== getLanguage()) {
      setUiLanguage(serverLanguage);
      saveLanguage(serverLanguage);
      applyStaticText();
    }
    renderRail();
    renderActiveView();
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    renderCourseError(error);
  } finally {
    dom.refreshMap.disabled = false;
  }
}

function allLessons() {
  if (!state.map?.units) {
    return [];
  }
  return state.map.units.flatMap((unit) =>
    Array.isArray(unit.lessons) ? unit.lessons : [],
  );
}

function lessonAccessible(item) {
  return (
    ["done", "current"].includes(String(item?.status || "")) &&
    !item?.locked_premium
  );
}

function currentLesson() {
  const lessons = allLessons();
  return (
    lessons.find(
      (item) => item.status === "current" && lessonAccessible(item),
    ) ||
    [...lessons]
      .reverse()
      .find((item) => item.status === "done" && lessonAccessible(item)) ||
    null
  );
}

function renderRail() {
  renderNotifications();
  const map = state.map;
  const user = map.user || {};
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);

  dom.railUserName.textContent = String(user.name || t("unknownUser"));
  dom.railPlan.textContent = user.is_paid ? t("planPaid") : t("planFree");
  renderUserAvatar(dom.railAvatar, user);
  dom.subscriptionBadge.textContent = user.is_paid ? t("active") : "PLUS";
  dom.headerXp.textContent = String(Number(progress.xp || 0));
  dom.headerStreak.textContent = String(Number(progress.streak || 0));
  dom.railLevelLabel.textContent =
    String(map.label || "") || levelLabel(map.level);
  dom.railCompleted.textContent = `${completed} / ${lessons.length}`;

  dom.navigation.replaceChildren();
  map.units.forEach((unit, unitIndex) => {
    const unitNumber = Number(unit.no ?? unit.n ?? unitIndex + 1);
    const unitLessons = Array.isArray(unit.lessons) ? unit.lessons : [];
    const hasCurrent = unitLessons.some((item) => item.status === "current");

    const wrap = element(
      "section",
      `course-unit${hasCurrent || unitIndex === 0 ? " is-open" : ""}`,
    );
    const toggle = element("button", "unit-button");
    toggle.type = "button";
    const lessonListId = `unit-lessons-${unitIndex + 1}`;
    toggle.setAttribute("aria-controls", lessonListId);
    toggle.setAttribute("aria-expanded", String(wrap.classList.contains("is-open")));
    toggle.append(
      element("span", "unit-number", String(unitNumber)),
      element("span", "unit-title", pick(unit.title, t("unit", { number: unitNumber }))),
      element("span", "", "⌄"),
    );
    toggle.addEventListener("click", () => {
      const open = wrap.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });

    const list = element("div", "unit-lessons");
    list.id = lessonListId;
    unitLessons.forEach((item) => {
      list.append(renderRailLesson(item));
    });
    wrap.append(toggle, list);
    dom.navigation.append(wrap);
  });
}

function renderRailLesson(item) {
  const status = String(item.status || "locked");
  const accessible = lessonAccessible(item);
  const button = element("button", "lesson-row");
  button.type = "button";
  if (status === "done") {
    button.classList.add("is-done");
  }
  if (status === "current") {
    button.classList.add("is-current");
  }
  button.append(
    element("span", "lesson-dot", status === "done" ? "✓" : ""),
    element("span", "lesson-hanzi", String(item.zh || item.n || "—")),
    element(
      "span",
      "lesson-subtitle",
      [String(item.py || ""), pick(item.tr)].filter(Boolean).join(" · "),
    ),
  );

  if (accessible) {
    button.addEventListener("click", () => {
      closeRail();
      openLesson(Number(item.n));
    });
  } else if (item.preview_half || item.locked_premium) {
    button.title = t("manageSubscription");
    button.addEventListener("click", () => {
      state.view = "subscription";
      renderActiveView();
      closeRail();
      showToast(t("manageSubscription"));
    });
  } else {
    button.disabled = true;
    button.title = t("lockedLesson");
  }
  return button;
}

function renderActiveView() {
  const views = {
    today: dom.showToday,
    course: dom.showCourse,
    practice: dom.showPractice,
    voice: dom.showVoice,
    vocabulary: dom.showVocabulary,
    rating: dom.showRating,
    subscription: dom.showSubscription,
    profile: dom.showProfile,
  };
  Object.entries(views).forEach(([name, button]) => {
    button.setAttribute("aria-current", state.view === name ? "page" : "false");
  });
  dom.content.dataset.view = state.view;

  // Several call sites set state.view directly instead of going through
  // routeTo, so the microphone is released here: whenever the rendered view is
  // not AI Voice, no capture may stay open on macOS or Windows.
  if (state.view !== "voice") {
    voice.dispose();
  }
  if (state.view !== "practice") {
    practice.dispose();
  }
  if (state.view !== "vocabulary") {
    vocabulary.dispose();
  }
  if (state.view !== "course") {
    disposeCourseTrack();
  }

  if (state.view === "today") renderToday();
  else if (state.view === "course") renderCourseHome();
  else if (state.view === "practice") renderPractice();
  else if (state.view === "voice") renderVoice();
  else if (state.view === "vocabulary") void renderVocabulary();
  else if (state.view === "rating") void renderRating();
  else if (state.view === "subscription") renderSubscription();
  else {
    renderProfile();
    if (!state.referral && !state.referralError) void loadProfileExtras();
  }
  refreshAiContextPanel();
}

function viewHeading(title, subtitle, tag = "") {
  const heading = element("header", "view-heading pageHead");
  const copy = element("div");
  copy.append(element("h2", "", title), element("p", "", subtitle));
  heading.append(copy);
  if (tag) heading.append(element("span", "view-tag", tag));
  return heading;
}

function progressPercent(done, total) {
  return Math.round(
    (Math.max(0, Number(done) || 0) / Math.max(1, Number(total) || 1)) * 100,
  );
}

const RAIL_MIN_WIDTH = 190;
const RAIL_MAX_WIDTH = 340;

function applyRailWidth(width) {
  // Width lives on a data attribute in 10px steps: the strict CSP forbids
  // inline styles, so CSS carries one rule per step.
  const clamped = Math.min(RAIL_MAX_WIDTH, Math.max(RAIL_MIN_WIDTH, Math.round(width)));
  state.railWidth = clamped;
  document.documentElement.dataset.railWidth = String(Math.round(clamped / 10) * 10);
  try {
    localStorage.setItem("pomp-hsk-rail-width", String(clamped));
  } catch {
    // A blocked storage quota must not break resizing.
  }
}

function restoreRailWidth() {
  let stored = 0;
  try {
    stored = Number(localStorage.getItem("pomp-hsk-rail-width") || 0);
  } catch {
    stored = 0;
  }
  if (stored >= RAIL_MIN_WIDTH && stored <= RAIL_MAX_WIDTH) applyRailWidth(stored);
}

function setRailCollapsed(collapsed) {
  state.railCollapsed = Boolean(collapsed);
  document.documentElement.dataset.railCollapsed = state.railCollapsed ? "1" : "0";
  dom.railCollapse.setAttribute("aria-expanded", state.railCollapsed ? "false" : "true");
  try {
    localStorage.setItem("pomp-hsk-rail-collapsed", state.railCollapsed ? "1" : "0");
  } catch {
    // Ignore storage failures.
  }
}

function restoreRailCollapsed() {
  try {
    setRailCollapsed(localStorage.getItem("pomp-hsk-rail-collapsed") === "1");
  } catch {
    setRailCollapsed(false);
  }
}

function startRailResize(event) {
  event.preventDefault();
  const move = (moveEvent) => applyRailWidth(moveEvent.clientX);
  const stop = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
}

function runNotificationAction(item) {
  const action = String(item?.actionName || item?.action || "");
  if (action === "subscription") {
    routeTo("subscription");
    return;
  }
  if (action === "rating") {
    routeTo("rating");
    return;
  }
  if (action === "profile") {
    routeTo("profile");
    return;
  }
  const lessonOrder = Number(item?.lessonOrder || item?.lesson_order || 0);
  routeTo("course");
  if (lessonOrder > 0) {
    const lessonItem = allLessons().find((lesson) => Number(lesson.n) === lessonOrder);
    if (lessonItem && lessonAccessible(lessonItem)) {
      requestAnimationFrame(() => openLesson(lessonOrder));
    }
  }
}

function serverNotificationRows() {
  const rows = Array.isArray(state.map?.notifications)
    ? state.map.notifications
    : [];
  return rows
    .filter((item) => item && typeof item === "object")
    .slice(0, 8)
    .map((item, index) => ({
      id: String(
        item.id ?? `${item.key || "notification"}:${item.created_at || index}`,
      ).slice(0, 120),
      key: String(item.key || ""),
      glyph: String(item.glyph || "铃").slice(0, 2),
      title: String(item.title || t("notificationsTitle")).slice(0, 160),
      body: String(item.body || "").slice(0, 420),
      actionName: String(item.action || "course"),
      level: String(item.level || ""),
      lessonOrder: Number(item.lesson_order || 0),
      createdAt: String(item.created_at || ""),
      raw: item,
    }));
}

function serverNotificationItems() {
  return serverNotificationRows().map((item) => ({
    ...item,
    action: () => runNotificationAction(item),
    isServer: true,
  }));
}

/**
 * Only real, already-known items appear here: server-saved Telegram reminders
 * plus current update/plan/streak facts the client already holds.
 */
function notificationItems() {
  const items = [...serverNotificationItems()];
  const user = state.map?.user;
  const progress = state.map?.progress || {};
  if (state.updateStatus === "available" && state.updateInfo?.version) {
    items.push({
      glyph: "新",
      title: t("updateAvailableTitle"),
      body: `v${String(state.updateInfo.version)}`,
      action: () => routeTo("today"),
    });
  }
  if (user && user.is_paid !== true) {
    items.push({
      glyph: "会",
      title: t("freePlan"),
      body: t("freeAccessDescription"),
      action: () => routeTo("subscription"),
    });
  }
  const streak = Number(progress.streak || 0);
  const activeToday = Array.isArray(progress.week_activity_dates)
    && progress.week_activity_dates.includes(String(progress.local_date || ""));
  if (notificationMasterEnabled() && streak > 0 && !activeToday) {
    items.push({
      glyph: "火",
      title: t("keepRhythm"),
      body: t("streakAtRisk", { days: streak }),
      action: () => routeTo("course"),
    });
  }
  return items;
}

function renderNotifications() {
  const items = notificationItems();
  dom.notificationsDot.hidden = items.length === 0;
  dom.notificationsBody.replaceChildren();
  if (!items.length) {
    dom.notificationsBody.append(element("p", "muted", t("notificationsEmpty")));
    return;
  }
  items.forEach((item) => {
    const row = element("button", "notification-row");
    row.type = "button";
    row.append(element("span", "notification-mark", item.glyph));
    const copy = element("div");
    copy.append(element("strong", "", item.title), element("p", "muted", item.body));
    row.append(copy);
    row.addEventListener("click", () => {
      closeNotifications();
      item.action();
    });
    dom.notificationsBody.append(row);
  });
}

function showDesktopNotification(item) {
  if (!notificationMasterEnabled()) return;
  if (desktopNotificationPermission() !== "granted") return;
  try {
    const notification = new globalThis.Notification(item.title, {
      body: item.body,
      tag: `hsk-ai-${item.id}`,
    });
    notification.onclick = () => {
      try {
        globalThis.focus();
      } catch {
        // Focus is best effort; the in-app action still runs.
      }
      runNotificationAction(item);
      notification.close();
    };
  } catch {
    // Some desktop webviews expose Notification but reject construction.
  }
}

function syncServerNotifications({ initial = false } = {}) {
  const rows = serverNotificationRows();
  if (!rows.length) {
    state.notificationInitialized = true;
    return;
  }
  const newRows = rows.filter((item) => item.id && !state.seenNotificationIds.has(item.id));
  rows.forEach((item) => {
    if (item.id) state.seenNotificationIds.add(item.id);
  });
  if (state.seenNotificationIds.size > MAX_SEEN_NOTIFICATION_IDS) {
    state.seenNotificationIds = new Set(
      [...state.seenNotificationIds].slice(-MAX_SEEN_NOTIFICATION_IDS),
    );
  }
  saveSeenNotificationIds();
  if (initial || !state.notificationInitialized) {
    state.notificationInitialized = true;
    return;
  }
  state.notificationInitialized = true;
  newRows.reverse().forEach(showDesktopNotification);
}

function startNotificationRefresh() {
  stopNotificationRefresh();
  state.notificationRefreshTimer = setInterval(() => {
    if (dom.workspace.hidden || lesson.isOpen) return;
    void refreshCourseMapSilently();
  }, NOTIFICATION_REFRESH_MS);
}

function stopNotificationRefresh() {
  if (!state.notificationRefreshTimer) return;
  clearInterval(state.notificationRefreshTimer);
  state.notificationRefreshTimer = null;
}

async function refreshCourseMapSilently() {
  try {
    const map = await desktopBridge.courseMap();
    if (
      !map ||
      map.ok !== true ||
      !Array.isArray(map.units) ||
      !map.user ||
      !map.progress
    ) {
      return;
    }
    state.map = map;
    subscription.setUser(map.user);
    syncServerNotifications();
    renderRail();
    if (["today", "course", "profile"].includes(state.view)) {
      renderActiveView();
    }
  } catch (error) {
    if (isSessionError(error)) showAuth({ expired: true });
  }
}

function openNotifications() {
  state.notificationsOpen = true;
  renderNotifications();
  dom.notificationsPanel.hidden = false;
  dom.notificationsButton.setAttribute("aria-expanded", "true");
}

function closeNotifications() {
  state.notificationsOpen = false;
  dom.notificationsPanel.hidden = true;
  dom.notificationsButton.setAttribute("aria-expanded", "false");
}

function toggleNotifications() {
  if (state.notificationsOpen) closeNotifications();
  else openNotifications();
}

function routeTo(view) {
  state.view = view;
  renderActiveView();
  closeRail();
}

function languageLocale() {
  return { uz: "uz-UZ", ru: "ru-RU", tj: "tg-TJ" }[getLanguage()] || "uz-UZ";
}

function parseIsoDay(value) {
  const normalized = String(value || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) return null;
  const date = new Date(`${normalized}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function isoDay(date) {
  return date.toISOString().slice(0, 10);
}

function weekSnapshot(progress = {}) {
  let start = parseIsoDay(progress.week_start);
  const today = parseIsoDay(progress.local_date) || new Date();
  if (!start) {
    start = new Date(today);
    const weekday = (start.getUTCDay() + 6) % 7;
    start.setUTCDate(start.getUTCDate() - weekday);
  }
  const active = new Set(
    (Array.isArray(progress.week_activity_dates)
      ? progress.week_activity_dates
      : []
    ).map(String),
  );
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start);
    date.setUTCDate(start.getUTCDate() + index);
    const value = isoDay(date);
    return {
      value,
      label: new Intl.DateTimeFormat(languageLocale(), {
        weekday: "short",
        timeZone: "UTC",
      })
        .format(date)
        .replace(".", ""),
      day: date.getUTCDate(),
      active: active.has(value),
      today: value === String(progress.local_date || isoDay(today)),
    };
  });
}

function weekActivity(progress, compact = false) {
  const wrap = element("div", `week-activity${compact ? " is-compact" : ""}`);
  weekSnapshot(progress).forEach((day) => {
    const item = element(
      "div",
      `week-day${day.active ? " is-active" : ""}${day.today ? " is-today" : ""}`,
    );
    item.setAttribute("aria-label", `${day.label} ${day.day}`);
    item.append(
      element("small", "", day.label),
      element("span", "week-day-mark", day.active ? "✓" : String(day.day)),
    );
    wrap.append(item);
  });
  return wrap;
}

function formattedToday(progress = {}) {
  const date = parseIsoDay(progress.local_date) || new Date();
  return new Intl.DateTimeFormat(languageLocale(), {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: progress.local_date ? "UTC" : undefined,
  }).format(date);
}

function progressTrack(numerator, denominator, className = "summary-progress") {
  const track = element("div", className);
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  const fill = element("span", "progress-fill");
  track.append(fill);
  setProgress(fill, numerator, denominator);
  return track;
}

function lessonMetaPill(item) {
  if (!item) return t("learningPart");
  if (item.checkpoint) return t("checkpoint");
  if (Number(item.part_count || 0) > 1) {
    return t("partProgress", {
      part: Number(item.part || 1),
      total: Number(item.part_count),
    });
  }
  return t("learningPart");
}

function todayReviewItems(lessons, current) {
  const completed = [...lessons]
    .reverse()
    .filter((item) => item.status === "done" && lessonAccessible(item));
  if (completed.length) return completed.slice(0, 5);
  return current ? [current] : [];
}

function activeDaysThisWeek(progress) {
  return weekSnapshot(progress).filter((day) => day.active).length;
}

function renderDemoWeek(progress) {
  const wrap = element("div", "week");
  weekSnapshot(progress).forEach((day) => {
    const item = element(
      "div",
      `day${day.active ? " done" : ""}${day.today ? " today" : ""}`,
    );
    item.setAttribute("aria-label", `${day.label} ${day.day}`);
    item.append(
      element("i", "", day.active ? "✓" : day.today ? "•" : "·"),
      element("span", "", day.label),
    );
    wrap.append(item);
  });
  return wrap;
}

function renderToday() {
  const map = state.map;
  if (!map) return;
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);
  const current = currentLesson();
  const percent = progressPercent(completed, lessons.length);
  const level = String(map.label || levelLabel(map.level));
  const activeDays = activeDaysThisWeek(progress);
  const reviewItems = todayReviewItems(lessons, current);

  dom.contentTitle.textContent = t("today");
  dom.contentSubtitle.textContent = formattedToday(progress);
  dom.content.replaceChildren(
    viewHeading(t("todayTitle"), formattedToday(progress), level),
  );

  const grid = element("div", "gridToday today-grid");
  const main = element("div", "leftStack today-main");
  const side = element("aside", "rightStack today-side");

  if (current) {
    const glyph =
      Array.from(String(current.zh || "课").replace(/[·\s]+/g, ""))[0] || "课";
    const resume = element("article", "card hero resume-card today-lesson-hero");
    resume.dataset.watermark = glyph;

    const top = element("div", "heroTop");
    const topCopy = element("div");
    const meta = element("div", "meta");
    meta.append(
      element("span", "tag red", level),
      element("span", "", t("lessonNumber", { number: current.n })),
      element("span", "", "•"),
      element("span", "", lessonMetaPill(current)),
    );
    topCopy.append(element("div", "eyebrow", t("nextStep")), meta);
    top.append(
      topCopy,
      element("span", "tag", `${Number(progress.daily_xp || 0)} XP`),
    );

    const copy = element("div", "resume-copy");
    copy.append(
      top,
      element(
        "h3",
        "",
        [t("lessonNumber", { number: current.n }), pick(current.tr)]
          .filter(Boolean)
          .join(" · "),
      ),
      element("p", "resume-chinese", String(current.zh || glyph)),
      element("p", "resume-pinyin", String(current.py || "")),
    );

    const progressRow = element("div", "heroProgress resume-progress");
    progressRow.append(
      element("span", "", t("courseProgress")),
      element("strong", "", `${percent}%`),
    );
    progressRow.append(progressTrack(completed, lessons.length));

    const actions = element("div", "heroFoot hero-actions");
    actions.append(progressRow);
    const action = element(
      "button",
      "btn primary-button",
      current.status === "done" ? t("startLesson") : t("continueLesson"),
    );
    action.type = "button";
    action.addEventListener("click", () => openLesson(Number(current.n)));
    actions.append(action);
    copy.append(actions);

    const mascot = element("figure", "today-hero-mascot");
    mascot.append(
      element("figcaption", "mascot-note", t("mascotReady")),
      createPandaMascot("today-panda"),
    );
    resume.append(copy, mascot);
    main.append(resume);
  } else {
    const empty = element("section", "empty-state card-panel card cardPad");
    empty.append(element("p", "", t("courseEmpty")));
    main.append(empty);
  }

  const quickGrid = element("section", "today-quick-grid");
  const completedLesson = [...lessons]
    .reverse()
    .find((item) => item.status === "done" && lessonAccessible(item));
  const reviewCard = element("article", "card cardPad today-quick-card");
  const reviewHead = element("div", "sectionTitle");
  reviewHead.append(
    element("h3", "", t("todayReviewEyebrow")),
    element("span", "tag red", reviewItems.length ? String(reviewItems.length) : NO_VALUE),
  );
  reviewCard.append(
    reviewHead,
    element(
      "p",
      "muted small",
      completedLesson ? t("reviewLessonTitle", { number: completedLesson.n }) : t("reviewCourseBody"),
    ),
  );
  const reviewWords = element("div", "reviewWords");
  reviewItems.forEach((item) => {
    const chip = element("div", "wordChip");
    chip.append(
      element("b", "hanzi", String(item.zh || "课")),
      element("span", "", String(item.py || "")),
    );
    reviewWords.append(chip);
  });
  if (!reviewItems.length) reviewWords.append(element("div", "wordChip", NO_VALUE));
  reviewCard.append(reviewWords);
  const reviewAction = element(
    "button",
    "btn secondary secondary-button",
    completedLesson ? t("repeatLesson") : t("openPractice"),
  );
  reviewAction.type = "button";
  reviewAction.addEventListener("click", () => {
    if (completedLesson) openLesson(Number(completedLesson.n));
    else routeTo("practice");
  });
  reviewCard.append(reviewAction);

  quickGrid.append(reviewCard);
  main.append(quickGrid);

  const dailyGoal = element("article", "card cardPad today-progress-card");
  const dailyHead = element("div", "sectionTitle");
  dailyHead.append(
    element("h3", "", t("todayGoalTitle")),
    element("span", "tag", `${NO_VALUE} / ${NO_VALUE}`),
  );
  const dailyRow = element("div", "goalRow");
  const ring = element("div", "progress-ring ring");
  ring.dataset.progress = "0";
  ring.setAttribute("role", "progressbar");
  ring.setAttribute("aria-valuemin", "0");
  ring.setAttribute("aria-valuemax", "100");
  ring.setAttribute("aria-valuenow", "0");
  const ringCopy = element("div", "ringText");
  const ringText = element("div");
  ringText.append(element("b", "", NO_VALUE), element("span", "", t("minutesShort")));
  ringCopy.append(ringText);
  ring.append(ringCopy);
  const dailyCopy = element("div");
  dailyCopy.append(
    element("b", "", t("todayGoalUnavailableTitle")),
    element("p", "muted small", t("todayGoalUnavailableBody")),
  );
  dailyRow.append(ring, dailyCopy);
  dailyGoal.append(dailyHead, dailyRow);
  side.append(soonBlock(dailyGoal));

  const streakCard = element("article", "card cardPad");
  const streakHead = element("div", "sectionTitle");
  streakHead.append(
    element("h3", "", t("todayStreakTitle")),
    element("b", "today-streak-count", `${Number(progress.streak || 0)} ${t("days")}`),
  );
  streakCard.append(streakHead, renderDemoWeek(progress));
  streakCard.append(
    element(
      "p",
      "muted small",
      t(activeDays ? "todayStreakActive" : "todayStreakInactive"),
    ),
  );
  side.append(streakCard);

  const phraseCard = element("article", "card cardPad wordToday today-phrase");
  const phraseCopy = element("div");
  phraseCopy.append(
    element("div", "eyebrow", t("todayPhraseEyebrow")),
    element("div", "zh hanzi today-phrase-zh", String(current?.zh || "你好")),
    element("div", "py pinyin", String(current?.py || "nǐ hǎo")),
    element(
      "div",
      "muted small translation",
      current ? pick(current.tr) : t("todayPhraseFallback"),
    ),
  );
  const phraseAction = element("button", "audioBtn listen-button", "▶");
  phraseAction.type = "button";
  phraseAction.setAttribute("aria-label", t("listen"));
  phraseAction.addEventListener("click", () =>
    speakChinese(String(current?.zh || "你好"), phraseAction),
  );
  const example = element("div", "example");
  example.append(element("span", "hanzi", String(current?.zh || "你好")));
  phraseCard.append(phraseCopy, phraseAction, example);
  side.append(phraseCard);

  const weekPlan = element("article", "card cardPad today-plan-card");
  const weekHead = element("div", "sectionTitle");
  weekHead.append(
    element("h3", "", t("todayWeekPlanTitle")),
    element("span", "tag green", `${activeDays} / 7`),
  );
  weekPlan.append(
    weekHead,
    progressTrack(activeDays, 7),
    element("p", "muted small", t("todayWeekPlanBody", { count: activeDays })),
  );
  side.append(weekPlan);
  grid.append(main, side);
  dom.content.append(grid);
}

function lessonMatches(item, query) {
  if (!query) return true;
  return [item?.n, item?.zh, item?.py, pick(item?.tr)]
    .join(" ")
    .toLocaleLowerCase()
    .includes(query);
}

function renderCourseHome() {
  const map = state.map;
  if (!map) return;
  disposeCourseTrack();
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);
  const percent = progressPercent(completed, lessons.length);
  const query = state.searchQuery.trim().toLocaleLowerCase();
  const level = String(map.label || levelLabel(map.level));

  dom.contentTitle.textContent = t("course");
  dom.contentSubtitle.textContent = level;
  dom.content.replaceChildren(
    viewHeading(
      t("courseTitle"),
      t("courseSubtitle"),
      t("lessons", { done: completed, total: lessons.length }),
    ),
  );
  const layout = element("div", "courseLayout course-layout");
  const units = element("div", "course-units");
  let renderedLessons = 0;

  map.units.forEach((unit, unitIndex) => {
    const allUnitLessons = Array.isArray(unit.lessons) ? unit.lessons : [];
    const unitLessons = allUnitLessons.filter((item) => lessonMatches(item, query));
    if (!unitLessons.length) return;
    renderedLessons += unitLessons.length;
    const unitNumber = Number(unit.no ?? unit.n ?? unitIndex + 1);
    const unitDone = allUnitLessons.filter((item) => item.status === "done").length;
    const unitPercent = progressPercent(unitDone, allUnitLessons.length);
    const hasCurrent = allUnitLessons.some((item) => item.status === "current");
    const card = element(
      "section",
      `coursePathUnit course-unit-card${hasCurrent ? " is-current-unit" : ""}`,
    );
    const head = element("header", "pathHead course-unit-head");
    const copy = element("div");
    copy.append(
      element(
        "h3",
        "",
        `${t("unit", { number: unitNumber })} · ${pick(unit.title, t("unit", { number: unitNumber }))}`,
      ),
      element(
        "p",
        "",
        t("unitProgress", {
          done: unitDone,
          total: allUnitLessons.length,
        }),
      ),
    );
    const unitProgress = element("div", "unit-progress-copy");
    unitProgress.append(
      element("strong", "", `${unitPercent}%`),
      element("small", "", hasCurrent ? t("currentUnit") : t("unit", { number: unitNumber })),
    );
    head.append(element("span", "unitNo course-unit-number", unitNumber), copy, unitProgress);
    const trail = element("div", "lessonPath lesson-trail");
    trail.dataset.progress = String(Math.round(unitPercent / 5));
    trail.setAttribute("role", "progressbar");
    trail.setAttribute("aria-valuemin", "0");
    trail.setAttribute("aria-valuemax", "100");
    trail.setAttribute("aria-valuenow", String(unitPercent));
    trail.append(createCourseTrack(trail));
    unitLessons.forEach((item, lessonIndex) => {
      trail.append(renderLessonNode(item, lessonIndex));
    });
    card.append(head, trail);
    units.append(card);
  });

  if (!renderedLessons) {
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("searchEmpty")));
    units.append(empty);
  }

  const aside = element("aside", "courseAside course-aside");
  const summary = element("article", "card cardPad courseSummary card-panel");
  const pandaWrap = element("div", "coursePandaWrap");
  const panda = createPandaMascot("coursePanda");
  const pandaCopy = element("div");
  pandaCopy.append(
    element("b", "", t("courseSummaryTitle")),
    element("small", "", t("courseSummaryBody")),
  );
  pandaWrap.append(panda, pandaCopy);
  summary.append(
    pandaWrap,
    element("span", "tag red", level),
    element("div", "big course-percent", `${percent}%`),
    element("p", "muted small", t("courseProgress")),
    progressTrack(completed, lessons.length),
  );
  [
    [t("courseCompletedLabel"), completed],
    [t("xpTotal"), Number(progress.xp || 0)],
    [t("streakDays"), Number(progress.streak || 0)],
    [t("league"), String(progress.league || t("notAvailable"))],
    [t("accountAccess"), map.user?.is_paid ? t("paidPlan") : t("freePlan")],
  ].forEach(([label, value]) => {
    const row = element("div", "miniStat course-aside-stat");
    row.append(element("span", "", label), element("b", "", value));
    summary.append(row);
  });
  [
    [t("courseWordsLabel"), NO_VALUE],
    [t("courseTimeLabel"), NO_VALUE],
  ].forEach(([label, value]) => {
    const row = element("div", "miniStat course-aside-stat");
    row.append(element("span", "", label), element("b", "", value));
    summary.append(soonBlock(row));
  });
  const legend = element("div", "courseLegend");
  [
    `✓ ${t("courseLegendDone")}`,
    `▶ ${t("courseLegendCurrent")}`,
    `◇ ${t("courseLegendReview")}`,
    `★ ${t("courseLegendMilestone")}`,
  ].forEach((label) => legend.append(element("span", "", label)));
  summary.append(legend);
  if (currentLesson()) {
    const continueButton = element("button", "btn primary-button", t("continueLesson"));
    continueButton.type = "button";
    continueButton.addEventListener("click", () => openLesson(Number(currentLesson().n)));
    summary.append(continueButton);
  }
  const download = element("button", "downloadCourseBtn");
  download.type = "button";
  download.append(
    element("span", "dlIcon", "↓"),
    element("span", "dlLabel", t("courseOfflineSave")),
    element("span", "dlMeta", NO_VALUE),
  );
  const downloadBar = element("span", "dlBar");
  downloadBar.append(element("i", ""));
  download.append(downloadBar);
  summary.append(soonBlock(download));
  if (!map.user?.is_paid) {
    const action = element("button", "btn primary-button", t("unlockCourse"));
    action.type = "button";
    action.addEventListener("click", () => routeTo("subscription"));
    summary.append(action);
  }
  aside.append(summary);
  layout.append(units, aside);
  dom.content.append(layout);
  watchCourseTrack();
}

function renderLessonNode(item, lessonIndex = 0) {
  const status = String(item?.status || "locked");
  const accessible = lessonAccessible(item);
  const row = element(
    "div",
    `pathNodeRow is-${status}${accessible ? " is-accessible" : ""}${
      item?.checkpoint ? " milestone" : ""
    } lesson-node-row`,
  );
  row.dataset.pathStep = String((Number(lessonIndex) % 4) + 1);
  row.dataset.lessonNo = String(item?.n || "");
  const button = element(
    "button",
    `pathNode lesson-node ${status} is-${status}${item?.checkpoint ? " is-checkpoint" : ""}`,
  );
  button.type = "button";
  button.dataset.status = status;
  const nodeIcon = status === "done" ? "✓" : item?.checkpoint ? "★" : accessible ? "▶" : "⌁";
  button.append(
    element("span", "nodeNo", String(item.n || "")),
    element("span", "nodeIcon", nodeIcon),
  );
  if (status === "current") {
    button.append(element("span", "currentBubble current-location", t("youAreHere")));
  }
  if (accessible) {
    button.addEventListener("click", () => openLesson(Number(item.n)));
  } else if (item.preview_half || item.locked_premium) {
    button.classList.add("is-locked");
    button.addEventListener("click", () => routeTo("subscription"));
  } else {
    button.classList.add("is-locked");
    button.disabled = true;
  }
  const label = element("div", "pathLabel lesson-node-copy");
  label.append(
    element("b", "", t("lessonNumber", { number: item.n })),
    element(
      "span",
      "",
      [
        String(item.zh || "课"),
        String(item.py || ""),
        pick(item.tr),
      ].filter(Boolean).join(" · "),
    ),
  );
  row.append(button, label);
  return row;
}

// The lesson trail road is drawn from the measured node centres instead of
// guessed CSS offsets, so the segments always meet whatever the card width,
// zig-zag amplitude or label wrapping ends up being.
const SVG_NS = "http://www.w3.org/2000/svg";
const courseTrack = { observer: null, frame: 0, trails: [] };

function disposeCourseTrack() {
  if (courseTrack.observer) {
    courseTrack.observer.disconnect();
    courseTrack.observer = null;
  }
  if (courseTrack.frame) {
    cancelAnimationFrame(courseTrack.frame);
    courseTrack.frame = 0;
  }
  courseTrack.trails = [];
}

function createCourseTrack(trail) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "pathTrack");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  courseTrack.trails.push({ trail, svg });
  return svg;
}

function courseTrackShape(points) {
  if (points.length < 2) return "";
  const at = (value) => Math.round(value * 10) / 10;
  const parts = [`M ${at(points[0].x)} ${at(points[0].y)}`];
  for (let index = 1; index < points.length; index += 1) {
    const from = points[index - 1];
    const to = points[index];
    // Vertical tangents at every node keep neighbouring segments joined
    // smoothly and make sideways overshoot impossible.
    const bend = (to.y - from.y) * 0.5;
    parts.push(
      `C ${at(from.x)} ${at(from.y + bend)} ${at(to.x)} ${at(to.y - bend)} ${at(to.x)} ${at(to.y)}`,
    );
  }
  return parts.join(" ");
}

function courseTrackLine(shape, className) {
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("class", className);
  path.setAttribute("d", shape);
  return path;
}

function drawCourseTrack(entry) {
  const { trail, svg } = entry;
  if (!trail.isConnected) return;
  const rows = Array.from(trail.querySelectorAll(".pathNodeRow"));
  if (rows.length < 2) {
    svg.replaceChildren();
    return;
  }
  const base = trail.getBoundingClientRect();
  const points = rows.map((row) => {
    const box = (row.querySelector(".pathNode") || row).getBoundingClientRect();
    return {
      x: box.left - base.left + box.width / 2,
      y: box.top - base.top + box.height / 2,
      done: row.classList.contains("is-done"),
      current: row.classList.contains("is-current"),
    };
  });

  let lastDone = -1;
  let current = -1;
  points.forEach((point, index) => {
    if (point.done) lastDone = index;
    if (point.current && current < 0) current = index;
  });

  const layers = [];
  const full = courseTrackShape(points);
  layers.push(courseTrackLine(full, "trackEdge"), courseTrackLine(full, "trackBase"));
  if (lastDone >= 1) {
    const done = courseTrackShape(points.slice(0, lastDone + 1));
    layers.push(courseTrackLine(done, "trackDoneEdge"), courseTrackLine(done, "trackDone"));
  }
  if (current >= 1) {
    const step = courseTrackShape(points.slice(current - 1, current + 1));
    layers.push(courseTrackLine(step, "trackCurrentEdge"), courseTrackLine(step, "trackCurrent"));
  }
  layers.push(courseTrackLine(full, "trackCentre"));
  svg.replaceChildren(...layers);
}

function scheduleCourseTrackDraw() {
  if (courseTrack.frame) return;
  courseTrack.frame = requestAnimationFrame(() => {
    courseTrack.frame = 0;
    courseTrack.trails.forEach(drawCourseTrack);
  });
}

function watchCourseTrack() {
  if (!courseTrack.trails.length) return;
  if (typeof ResizeObserver === "function") {
    courseTrack.observer = new ResizeObserver(scheduleCourseTrackDraw);
    courseTrack.trails.forEach((entry) => courseTrack.observer.observe(entry.trail));
  }
  scheduleCourseTrackDraw();
  // Label wrapping shifts row heights once the Chinese webfont lands.
  if (document.fonts?.ready) {
    void document.fonts.ready.then(scheduleCourseTrackDraw).catch(() => {});
  }
}

function renderPractice() {
  const map = state.map;
  if (!map) return;
  dom.contentTitle.textContent = t("practice");
  dom.contentSubtitle.textContent = t("practiceSubtitle");
  const host = element("div", "practice-view");
  dom.content.replaceChildren(
    viewHeading(
      t("practiceTitle"),
      t("practiceSubtitle"),
      String(map.label || levelLabel(map.level)),
    ),
    host,
  );
  practice.host = host;
  practice.setLanguage(getLanguage());
  const level = String(map.level || "").toLowerCase();
  if (level) practice.setLevel(level);
  practice.render();
}

function renderVoice() {
  const map = state.map;
  if (!map) return;
  dom.contentTitle.textContent = t("voice");
  dom.contentSubtitle.textContent = t("voiceSubtitle");
  const host = element("div", "voice-host voice-v3-root");
  dom.content.replaceChildren(
    viewHeading(t("voiceTitle"), t("voiceSubtitle"), t("voiceLiveTag")),
    host,
  );
  voice.host = host;
  voice.setLanguage(getLanguage());
  const level = String(map.level || "").toLowerCase();
  if (level) voice.setLevel(level.startsWith("hsk4") ? "hsk4" : level);
  // A course refresh or a language change re-renders the active view. During a
  // live call that must repaint into the new host without asking the server for
  // the quota again and without interrupting the recording.
  void voice.open({ refresh: !voice.sessionId });
}

async function renderVocabulary() {
  dom.contentTitle.textContent = t("vocabulary");
  dom.contentSubtitle.textContent = t("vocabularySubtitle");
  const host = element("div", "vocabulary-host");
  dom.content.replaceChildren(
    viewHeading(t("vocabularyTitle"), t("vocabularySubtitle"), "词"),
    host,
  );
  vocabulary.host = host;
  vocabulary.setLanguage(getLanguage());
  await vocabulary.load();
}

function browserSpeakChinese(text) {
  if (
    typeof globalThis.SpeechSynthesisUtterance !== "function" ||
    !globalThis.speechSynthesis
  ) {
    return Promise.resolve(false);
  }
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(String(text || "").trim());
    utterance.lang = "zh-CN";
    utterance.rate = 0.86;
    utterance.onend = () => resolve(true);
    utterance.onerror = () => resolve(false);
    globalThis.speechSynthesis.cancel();
    globalThis.speechSynthesis.speak(utterance);
  });
}

async function speakChinese(text, button) {
  // AI Voice plays replies without a trigger button, so the button is optional.
  if (button) button.disabled = true;
  try {
    const result = await desktopBridge.ttsSpeak(text);
    if (result?.ok !== true && !(await browserSpeakChinese(text))) {
      showToast(t("audioUnavailable"));
    }
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    if (!(await browserSpeakChinese(text))) showToast(t("audioUnavailable"));
  } finally {
    if (button) button.disabled = false;
  }
}

function ratingHeading(league) {
  return viewHeading(t("ratingTitle"), t("ratingSubtitle"), league);
}

function renderLeaderboard(board) {
  const rows = Array.isArray(board?.leaderboard) ? board.leaderboard : [];
  const panel = element("section", "leaderboard card-panel");
  const head = element("header", "leaderboard-head");
  const copy = element("div");
  copy.append(
    element("p", "eyebrow", t("weeklyLeaderboard")),
    element("h3", "", t("weeklyLeaderboardBody")),
  );
  head.append(
    copy,
    element(
      "span",
      "leaderboard-size",
      t("leagueSize", { count: Number(board?.league_size || rows.length) }),
    ),
  );
  panel.append(head);

  if (!rows.length) {
    panel.append(element("p", "muted", t("leaderboardEmpty")));
    return panel;
  }

  const list = element("ol", "leaderboard-rows");
  rows.forEach((entry) => {
    const row = element(
      "li",
      `leaderboard-row${entry.is_current_user ? " is-current" : ""}`,
    );
    const identity = element("div", "leaderboard-identity");
    identity.append(
      element("strong", "", String(entry.name || t("unknownUser"))),
      element(
        "small",
        "muted",
        entry.username ? `@${entry.username}` : String(entry.course_level || ""),
      ),
    );
    row.append(
      element("span", "leaderboard-rank", `#${Number(entry.rank || 0)}`),
      identity,
      element("strong", "leaderboard-xp", `${Number(entry.league_points || 0)} XP`),
    );
    list.append(row);
  });
  panel.append(list);
  return panel;
}

function renderRatingContent(board) {
  if (state.view !== "rating") return;
  const map = state.map;
  if (!map) return;
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);
  const percent = progressPercent(completed, lessons.length);
  const league = String(board?.league || progress.league || t("notAvailable"));
  const rank = Number(board?.rank || 0);
  const weeklyXp = Number(board?.weekly_xp ?? progress.weekly_xp ?? 0);
  const rows = Array.isArray(board?.leaderboard) ? board.leaderboard : [];
  const leagueSize = Number(board?.league_size || rows.length || 0);

  dom.content.replaceChildren(ratingHeading(league));

  const hero = element("section", "ratingHero rating-hero");
  const leagueCard = element("article", "card ratingLeagueCard card-panel");
  const leagueTop = element("div", "leagueTop");
  const leagueIdentity = element("div", "leagueIdentity");
  leagueIdentity.append(
    element("div", "leagueEmblem league-emblem", "级"),
    element("div", "", ""),
  );
  leagueIdentity.lastElementChild.append(
    element("h3", "", league),
    element(
      "p",
      "",
      leagueSize ? t("ratingLeagueSub", { count: leagueSize }) : t("ratingTruthfulBody"),
    ),
  );
  leagueTop.append(leagueIdentity, element("span", "seasonTag", t("ratingSeason")));
  const leagueRank = element("div", "leagueRank");
  leagueRank.append(
    element("strong", "", rank > 0 ? `#${rank}` : NO_VALUE),
    element("span", "", t("ratingCurrentPlace")),
  );
  const rankProgress = element("div", "rankProgress");
  const rankHead = element("div", "rankProgressHead");
  rankHead.append(
    element("b", "", `${weeklyXp} XP`),
    element("span", "", t("ratingNextUnavailable")),
  );
  const rankTrack = element("div", "summary-progress progress");
  rankTrack.append(element("span", "progress-fill is-placeholder"));
  rankProgress.append(rankHead, rankTrack);
  leagueCard.append(leagueTop, leagueRank, soonBlock(rankProgress));

  const pandaCard = element("article", "card ratingPandaCard card-panel");
  const pandaTop = element("div", "ratingPandaTop");
  const pandaCopy = element("div");
  pandaCopy.append(
    element("b", "", t("ratingPromotionTitle")),
    element("small", "", t("ratingPromotionSub")),
  );
  pandaTop.append(pandaCopy, element("span", "tag", NO_VALUE));
  const pandaStage = element("div", "ratingPanda");
  const panda = createPandaMascot("pandaMini");
  pandaStage.append(panda);
  const strip = element("div", "promotionStrip");
  [
    [NO_VALUE, t("ratingPromote")],
    [NO_VALUE, t("ratingStay")],
    [NO_VALUE, t("ratingDrop")],
  ].forEach(([value, label]) => {
    const cell = element("div", "promotionCell");
    cell.append(element("b", "", value), element("span", "", label));
    strip.append(cell);
  });
  pandaCard.append(pandaTop, pandaStage, strip);
  hero.append(leagueCard, soonBlock(pandaCard));

  const layout = element("div", "ratingLayout rating-layout");
  const leaderboard = element("article", "card leaderboardCard card-panel");
  const leaderHead = element("div", "leaderboardHead");
  const leaderCopy = element("div");
  leaderCopy.append(
    element("h3", "", t("ratingWeeklyTitle")),
    element("p", "muted small", t("ratingWeeklySub")),
  );
  const tabs = element("div", "leaderboardTabs");
  tabs.append(element("button", "ratingTab active", t("ratingTabLeague")));
  const friends = element("button", "ratingTab", t("ratingTabFriends"));
  friends.type = "button";
  friends.disabled = true;
  friends.title = t("comingSoon");
  tabs.append(friends);
  leaderHead.append(leaderCopy, tabs);
  const leaderRows = element("div", "leaderRows");
  if (!rows.length) {
    leaderRows.append(element("p", "muted", t("leaderboardEmpty")));
  } else {
    rows.forEach((entry, index) => {
      const row = element("div", `leaderRow${entry.is_current_user ? " me" : ""}`);
      const position = Number(entry.rank || index + 1);
      row.append(
        element("div", `leaderPos${position <= 3 ? " medal" : ""}`, position <= 3 ? ["🥇", "🥈", "🥉"][position - 1] : String(position)),
        element("div", "leaderAvatar", String(entry.name || t("unknownUser")).slice(0, 1)),
      );
      const info = element("div", "leaderInfo");
      info.append(
        element("b", "", `${String(entry.name || t("unknownUser"))}${entry.is_current_user ? ` · ${t("voiceYou")}` : ""}`),
        element("small", "", entry.username ? `@${entry.username}` : String(entry.course_level || "")),
      );
      const xp = element("div", "leaderXp");
      xp.append(
        element("b", "", `${Number(entry.league_points || 0)} XP`),
        element("small", "", position <= 3 ? t("ratingTopPerformer") : ""),
      );
      row.append(info, xp);
      leaderRows.append(row);
    });
  }
  leaderboard.append(leaderHead, leaderRows);

  const side = element("aside", "ratingSide");
  const missions = element("article", "card card-panel");
  const missionHead = element("div", "sectionTitle");
  missionHead.append(
    element("h3", "", t("ratingMissions")),
    element("span", "tag", NO_VALUE),
  );
  missions.append(missionHead);
  [
    ["课", t("ratingMissionLesson"), t("courseProgress")],
    ["音", t("ratingMissionVoice"), t("voice")],
    ["字", t("ratingMissionVocab"), t("vocabulary")],
  ].forEach(([glyph, title, sub]) => {
    const mission = element("div", "xpMission");
    mission.append(
      element("div", "xpMissionIcon hanzi", glyph),
      element("div", "", ""),
      element("span", "xpReward", NO_VALUE),
    );
    mission.children[1].append(element("b", "", title), element("small", "", sub));
    missions.append(mission);
  });
  const history = element("article", "card card-panel");
  const historyHead = element("div", "sectionTitle");
  historyHead.append(
    element("h3", "", t("ratingHistory")),
    element("span", "delta", NO_VALUE),
  );
  const historyBars = element("div", "leagueHistory");
  for (let index = 0; index < 6; index += 1) {
    historyBars.append(element("div", `historyBar${index === 5 ? " current" : ""}`));
  }
  history.append(historyHead, historyBars, element("p", "muted small", t("ratingHistoryUnavailable")));
  side.append(soonBlock(missions), soonBlock(history));

  layout.append(leaderboard, side);

  dom.content.append(hero, layout);

  if (state.ratingError) {
    const note = element("p", "muted rating-note", state.ratingError);
    dom.content.append(note);
  }
}

function ratingFallbackBoard() {
  const map = state.map || {};
  const progress = map.progress || {};
  const user = map.user || {};
  const weeklyXp = Number(progress.weekly_xp ?? progress.xp ?? 0);
  const totalXp = Number(progress.xp ?? weeklyXp);
  const completed = Number(progress.completed || 0);
  return {
    ok: true,
    rank: 1,
    league: String(progress.league || t("notAvailable")),
    league_size: 1,
    xp: totalXp,
    weekly_xp: weeklyXp,
    daily_xp: Number(progress.daily_xp || 0),
    streak: Number(progress.streak || 0),
    longest_streak: Number(progress.longest_streak || 0),
    week_start: String(progress.week_start || ""),
    week_activity_dates: Array.isArray(progress.week_activity_dates)
      ? progress.week_activity_dates
      : [],
    weekly_reset_day: "monday",
    weekly_reset_seconds: 0,
    leaderboard: [
      {
        rank: 1,
        name: String(user.name || t("unknownUser")),
        username: "",
        xp: weeklyXp,
        league_points: weeklyXp,
        total_xp: totalXp,
        course_level: String(map.level || ""),
        completed_lessons: completed,
        is_paid: Boolean(user.is_paid),
        is_current_user: true,
      },
    ],
  };
}

async function renderRating() {
  const map = state.map;
  if (!map) return;
  dom.contentTitle.textContent = t("rating");
  dom.contentSubtitle.textContent = t("ratingSubtitle");

  if (state.ratingBoard) {
    renderRatingContent(state.ratingBoard);
    return;
  }

  dom.content.replaceChildren(
    ratingHeading(String(map.progress?.league || t("notAvailable"))),
  );
  const loading = element("section", "loading-card");
  loading.append(element("div", "spinner"), element("p", "", t("ratingLoading")));
  dom.content.append(loading);

  const request = ++state.ratingRequest;
  try {
    const board = await desktopBridge.ratingLeaderboard(
      -new Date().getTimezoneOffset(),
    );
    if (request !== state.ratingRequest || state.view !== "rating") return;
    state.ratingBoard = board;
    state.ratingError = "";
    renderRatingContent(board);
  } catch (error) {
    if (request !== state.ratingRequest || state.view !== "rating") return;
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    // The league is a nice-to-have: personal progress still renders from the
    // course map so the screen is never empty when the endpoint is down.
    const code = error?.code;
    const detail = code && t(code) !== code ? t(code) : t("leaderboardUnavailable");
    state.ratingError = detail;
    renderRatingContent(ratingFallbackBoard());
  }
}

function renderSubscription() {
  dom.contentTitle.textContent = t("subscription");
  dom.contentSubtitle.textContent = t("subscriptionSubtitle");
  const host = element("div", "subscription-host");
  dom.content.replaceChildren(
    viewHeading(
      t("subscriptionTitle"),
      t("subscriptionSubtitle"),
      t("securePayment"),
    ),
    host,
  );
  subscription.host = host;
  subscription.setUser(state.map?.user);
  void subscription.open({ refresh: true });
}

/**
 * A demo block the backend does not serve yet.
 *
 * The block keeps the demo layout down to the buttons so the screen looks
 * finished, but every control inside is inert and hovering (or reaching it
 * with the keyboard) reveals a "coming soon" veil. Values are never invented:
 * callers pass a dash where the demo shows a number. When the endpoint lands,
 * only this wrapper has to go away.
 */
function soonBlock(node) {
  const wrap = element("div", "soon-block");
  node
    .querySelectorAll("button, input, select, textarea, a[href]")
    .forEach((control) => {
      control.disabled = true;
      control.tabIndex = -1;
      control.setAttribute("aria-hidden", "true");
    });
  const veil = element("div", "soon-veil");
  veil.append(element("span", "soon-badge", t("comingSoon")));
  wrap.append(node, veil);
  wrap.title = t("comingSoonHint");
  return wrap;
}

/** The placeholder used wherever the demo prints a figure we do not have. */
const NO_VALUE = "—";

function userInitials(name) {
  // The demo uses initials, not another copy of the app logo.
  const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "HSK";
  return parts
    .slice(0, 2)
    .map((part) => [...part][0].toUpperCase())
    .join("");
}

function safeImageUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw, globalThis.location?.href || "http://localhost/");
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function userAvatarSource(user) {
  const direct = safeImageUrl(user?.avatar_url || user?.photo_url || "");
  if (direct) return direct;
  const telegramId = Number(user?.telegram_id || 0);
  if (
    Number.isInteger(telegramId) &&
    telegramId > 0 &&
    globalThis.location?.protocol?.startsWith("http")
  ) {
    return `/api/v3/avatar/${telegramId}`;
  }
  return "";
}

function renderUserAvatar(container, user) {
  if (!container) return;
  container.replaceChildren(
    document.createTextNode(userInitials(user?.name || user?.avatar)),
  );
  const src = userAvatarSource(user);
  if (!src) return;
  const image = document.createElement("img");
  image.alt = "";
  image.loading = "lazy";
  image.addEventListener("load", () => container.replaceChildren(image), {
    once: true,
  });
  image.addEventListener("error", () => image.remove(), { once: true });
  image.src = src;
}

function profileStatCard(value, label, delta = "") {
  const card = element("article", "profile-stat card-panel");
  card.append(
    element("div", "eyebrow", label),
    element("div", "profile-stat-value", value),
  );
  if (delta) card.append(element("div", "profile-stat-delta muted", delta));
  return card;
}

/**
 * A statistic the server does not report yet. It keeps the demo card shape and
 * shows a dash where the figure would be, so nobody reads a placeholder as a
 * measurement.
 */
function comingSoonStatCard(label) {
  const card = element("article", "profile-stat card-panel");
  card.append(
    element("div", "eyebrow", label),
    element("div", "profile-stat-value", NO_VALUE),
    element("div", "profile-stat-delta muted", `${NO_VALUE} ${t("statThisWeek")}`),
  );
  return soonBlock(card);
}

/** The demo card head: a title on the left, a pill or note on the right. */
function chartCard(title, badge) {
  const card = element("article", "chart-card card-panel");
  const head = element("div", "card-heading-row");
  head.append(element("h3", "", title));
  if (badge) head.append(badge);
  card.append(head);
  return card;
}

/**
 * The demo draws study minutes per weekday. The server only records which days
 * had activity, so a day is either a full bar or an empty stub — the shape is
 * the demo's, the data is real, and no minute count is invented.
 */
function weekBarChart(progress) {
  const chart = element("div", "bar-chart");
  weekSnapshot(progress).forEach((day) => {
    const column = element("div", `bar-column${day.active ? " is-active" : ""}`);
    if (day.today) column.classList.add("is-today");
    column.append(element("i", ""), element("span", "", day.label));
    chart.append(column);
  });
  return chart;
}

/** HSK 1-4 completion. Only the active level is tracked, so all rows are dashed. */
function levelProgressCard(levelLabelText) {
  const card = chartCard(
    t("levelProgressTitle"),
    element("span", "muted small", levelLabelText),
  );
  [1, 2, 3, 4].forEach((level) => {
    const line = element("div", "level-line");
    const track = element("div", "summary-progress");
    track.append(element("span", "progress-fill is-placeholder"));
    line.append(
      element("b", "", t("levelLabel", { level })),
      track,
      element("span", "muted", NO_VALUE),
    );
    card.append(line);
  });
  return soonBlock(card);
}

/** Mistake analytics are not aggregated anywhere yet. */
function weakAreasCard() {
  const card = chartCard(
    t("weakAreasTitle"),
    element("span", "tag red", NO_VALUE),
  );
  [t("weakArea1"), t("weakArea2"), t("weakArea3")].forEach((label) => {
    const item = element("div", "weak-item");
    const head = element("div", "weak-head");
    head.append(element("b", "", label), element("span", "muted", NO_VALUE));
    const track = element("div", "summary-progress");
    track.append(element("span", "progress-fill is-placeholder"));
    item.append(head, track);
    card.append(item);
  });
  return soonBlock(card);
}

/** No accuracy history is stored, so the chart draws a flat baseline. */
function accuracyTrendCard() {
  const card = chartCard(
    t("accuracyTrendTitle"),
    element("span", "tag green", NO_VALUE),
  );
  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", "0 0 360 140");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "140");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("class", "trend-chart");
  const baseline = document.createElementNS(svgNs, "path");
  baseline.setAttribute("d", "M10 125 L350 125");
  baseline.setAttribute("fill", "none");
  baseline.setAttribute("stroke-width", "4");
  baseline.setAttribute("stroke-linecap", "round");
  svg.append(baseline);
  card.append(svg);
  return soonBlock(card);
}

/** The demo's three summary chips. Every figure behind them is missing. */
function insightChips() {
  const row = element("div", "progress-insight");
  [t("insightListening"), t("insightRhythm"), t("insightGrammar")].forEach(
    (label) => {
      const chip = element("div", "insight-chip card-panel");
      chip.append(element("b", "", NO_VALUE), element("span", "muted", label));
      row.append(chip);
    },
  );
  return soonBlock(row);
}

function settingRow(title, description, control) {
  const row = element("div", "setting-row");
  const copy = element("div");
  copy.append(element("b", "", title), element("small", "", description));
  row.append(copy, control);
  return row;
}

/**
 * One preference the demo shows but nothing implements yet. The real control
 * is rendered so the row looks finished, then made inert behind the veil.
 */
function comingSoonSettingRow(title, description, control) {
  const wrap = soonBlock(settingRow(title, description, control));
  wrap.classList.add("is-row");
  return wrap;
}

function selectControl(options, value, onChange) {
  const select = document.createElement("select");
  select.className = "setting-select";
  options.forEach((option) => {
    const node = document.createElement("option");
    node.value = String(option.value);
    node.textContent = option.label;
    if (String(option.value) === String(value)) node.selected = true;
    select.append(node);
  });
  if (onChange) {
    select.addEventListener("change", () => onChange(select.value));
  }
  return select;
}

function timeControl(value) {
  const input = document.createElement("input");
  input.type = "time";
  input.className = "setting-time";
  input.value = value;
  return input;
}

function notificationPermissionText(permission) {
  if (permission === "granted") return t("notifyDesktopGranted");
  if (permission === "denied") return t("notifyDesktopDenied");
  if (permission === "default") return t("notifyDesktopDefault");
  return t("notifyDesktopUnsupported");
}

async function requestDesktopNotificationPermission() {
  if (!("Notification" in globalThis)) {
    state.notificationPermission = "unsupported";
    showToast(t("notifyDesktopUnsupported"));
    renderActiveView();
    return;
  }
  try {
    state.notificationPermission = await globalThis.Notification.requestPermission();
  } catch {
    state.notificationPermission = desktopNotificationPermission();
  }
  showToast(
    state.notificationPermission === "granted"
      ? t("notifyDesktopEnabled")
      : t("notifyDesktopBlocked"),
  );
  renderActiveView();
}

async function setNotificationEnabled(enabled) {
  if (state.notificationsSaving) return;
  state.notificationsSaving = true;
  renderActiveView();
  try {
    const result = await desktopBridge.setNotifications(Boolean(enabled));
    const nextEnabled = Boolean(
      result?.notify?.enabled ?? result?.notifications ?? enabled,
    );
    state.map = {
      ...(state.map || {}),
      notify: {
        ...(state.map?.notify || {}),
        enabled: nextEnabled,
      },
    };
    showToast(t("notifySaved"));
  } catch {
    showToast(t("notifySaveFailed"));
  } finally {
    state.notificationsSaving = false;
    renderRail();
    renderActiveView();
  }
}

function renderNotificationsCard() {
  const card = element("article", "profile-settings card-panel");
  const rows = serverNotificationRows();
  const latest = rows[0] || null;
  const enabled = notificationMasterEnabled();
  const permission = desktopNotificationPermission();
  state.notificationPermission = permission;
  card.append(element("h3", "", t("notificationsTitle")));
  const masterSwitch = toggleButton(enabled, (nextEnabled) => {
    void setNotificationEnabled(nextEnabled);
  });
  masterSwitch.disabled = state.notificationsSaving;
  card.append(
    settingRow(
      t("notifyMaster"),
      enabled ? t("notifyMasterOnBody") : t("notifyMasterOffBody"),
      masterSwitch,
    ),
  );

  const permissionControl =
    permission === "default"
      ? element("button", "secondary-button compact-button", t("notifyDesktopAllow"))
      : element("strong", "setting-value", notificationPermissionText(permission));
  if (permission === "default") {
    permissionControl.type = "button";
    permissionControl.addEventListener("click", () => {
      void requestDesktopNotificationPermission();
    });
  }
  card.append(
    settingRow(
      t("notifyDesktopTitle"),
      notificationPermissionText(permission),
      permissionControl,
    ),
  );

  card.append(
    settingRow(
      t("notifyRecentTitle"),
      latest ? latest.body || latest.title : t("notificationsEmpty"),
      element("strong", "setting-value", t("notifyRecentCount", { count: rows.length })),
    ),
  );

  const openButton = element("button", "secondary-button", t("notifyOpenCenter"));
  openButton.type = "button";
  openButton.addEventListener("click", openNotifications);
  card.append(openButton);
  return card;
}

function toggleButton(active, onChange) {
  const button = element("button", `setting-switch${active ? " is-on" : ""}`);
  button.type = "button";
  button.setAttribute("role", "switch");
  button.setAttribute("aria-checked", active ? "true" : "false");
  button.append(element("i", ""));
  button.addEventListener("click", () => onChange(!active));
  return button;
}

function referralBotUsername() {
  const handle = String(state.map?.bot_username || "darsi_chini_bot")
    .trim()
    .replace(/^@+/, "");
  return /^[A-Za-z0-9_]{5,32}$/.test(handle) ? handle : "darsi_chini_bot";
}

function referralStartCode(code) {
  const normalized = String(code || "").trim();
  if (!normalized) return "";
  return normalized.startsWith("ref_") ? normalized : `ref_${normalized}`;
}

function referralLinkFrom(value, code) {
  const link = String(value || "").trim();
  if (/^https:\/\/t\.me\/[A-Za-z0-9_]{5,32}\?start=ref_[A-Za-z0-9_-]+$/.test(link)) {
    return link;
  }
  const start = referralStartCode(code);
  if (!start) return "";
  return `https://t.me/${referralBotUsername()}?start=${encodeURIComponent(start)}`;
}

function currentReferralData() {
  const raw = state.referral && typeof state.referral === "object" ? state.referral : {};
  const code = String(raw.code || state.map?.user?.referral_code || "").trim();
  const link = referralLinkFrom(raw.link, code);
  const required = Math.max(1, Number(raw.trial_required || 5) || 5);
  const progress = Math.max(0, Math.min(required, Number(raw.trial_progress || 0) || 0));
  return {
    code,
    link,
    invited: Math.max(0, Number(raw.invited || 0) || 0),
    activated: Math.max(0, Number(raw.activated || 0) || 0),
    trial_progress: progress,
    trial_required: required,
    items: Array.isArray(raw.items) ? raw.items : [],
  };
}

function referralShareText() {
  return t("inviteShareText");
}

function referralShareMessage(link) {
  return `${referralShareText()}\n${link}`;
}

async function openExternalUrl(url, { fallbackUrl = "", copyText = "", copyToast = "" } = {}) {
  const targets = [url, fallbackUrl]
    .map((target) => String(target || "").trim())
    .filter((target, index, list) => target && list.indexOf(target) === index);
  for (const target of targets) {
    try {
      await desktopBridge.openExternalUrl(target);
      return true;
    } catch {
      // Try the next target, then copy the prepared share message if needed.
    }
  }
  if (copyText) {
    try {
      await writeClipboardText(copyText);
      showToast(copyToast || t("inviteAppShareCopied"));
    } catch {
      showToast(t("inviteCopyFailed"));
    }
  }
  return false;
}

async function writeClipboardText(value) {
  const text = String(value || "");
  if (!text) throw new Error("clipboard_empty");
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    // Fall back to the legacy command below.
  }
  const proxy = element("textarea", "clipboard-proxy");
  proxy.value = text;
  proxy.setAttribute("readonly", "true");
  document.body.append(proxy);
  proxy.select();
  const copied = document.execCommand("copy");
  proxy.remove();
  if (!copied) throw new Error("clipboard_unavailable");
}

async function copyReferralLink(link, button = null) {
  try {
    await writeClipboardText(link);
    state.referralCopied = true;
    if (button) {
      button.classList.add("is-copied");
      button.textContent = t("inviteCopiedButton");
    }
    showToast(t("inviteCopied"));
  } catch {
    showToast(t("inviteCopyFailed"));
  }
}

async function shareReferralToTelegram(link) {
  const message = referralShareMessage(link);
  const fallbackUrl =
    "https://t.me/share/url?url=" +
    encodeURIComponent(link) +
    "&text=" +
    encodeURIComponent(referralShareText());
  const url =
    "tg://msg_url?url=" +
    encodeURIComponent(link) +
    "&text=" +
    encodeURIComponent(referralShareText());
  await openExternalUrl(url, {
    fallbackUrl,
    copyText: message,
    copyToast: t("inviteAppShareCopied"),
  });
}

async function shareReferralToWhatsapp(link) {
  const message = referralShareMessage(link);
  const url =
    "whatsapp://send?text=" +
    encodeURIComponent(message);
  await openExternalUrl(url, {
    copyText: message,
    copyToast: t("inviteAppShareCopied"),
  });
}

async function shareReferralWithSystem(link) {
  const payload = {
    title: "HSK AI",
    text: referralShareText(),
    url: link,
  };
  try {
    if (navigator.share) {
      await navigator.share(payload);
      return;
    }
  } catch {
    return;
  }
  await copyReferralLink(link);
  showToast(t("inviteSystemShareCopied"));
}

function isMacDesktop() {
  const devicePlatform = String(state.bootstrap?.device?.platform || "");
  if (/mac/i.test(devicePlatform)) return true;
  if (/win/i.test(devicePlatform)) return false;
  return /mac/i.test(String(navigator.platform || ""));
}

function referralSystemShareTitle() {
  return isMacDesktop() ? t("inviteShareMacTitle") : t("inviteShareComputerTitle");
}

function referralSystemShareBody() {
  return isMacDesktop() ? t("inviteShareMacBody") : t("inviteShareComputerBody");
}

function referralDestination(iconText, title, body, onClick, extraClass = "") {
  const button = element("button", `referral-destination ${extraClass}`.trim());
  button.type = "button";
  button.append(element("span", "referral-destination-icon", iconText));
  const copy = element("span", "referral-destination-copy");
  copy.append(element("b", "", title), element("small", "", body));
  button.append(copy, element("span", "referral-destination-arrow", "↗"));
  button.addEventListener("click", onClick);
  return button;
}

function highlightReferralQr(qrCard) {
  qrCard.scrollIntoView({ block: "center", behavior: state.reduceMotion ? "auto" : "smooth" });
  qrCard.classList.add("is-highlighted");
  qrCard.focus();
  window.setTimeout(() => qrCard.classList.remove("is-highlighted"), 1300);
}

function closeReferralModal({ restoreFocus = true } = {}) {
  document.querySelector(".referral-layer")?.remove();
  const shouldRestore = state.referralModalOpen && restoreFocus;
  state.referralModalOpen = false;
  if (shouldRestore) {
    const target = state.referralPreviousFocus?.isConnected
      ? state.referralPreviousFocus
      : dom.showProfile;
    target.focus();
  }
  state.referralPreviousFocus = null;
}

function openReferralModal(referral = currentReferralData()) {
  if (!referral.link) {
    showToast(state.referralError || t("inviteUnavailable"));
    return;
  }
  closeReferralModal({ restoreFocus: false });
  state.referralPreviousFocus =
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : dom.showProfile;
  state.referralModalOpen = true;
  state.referralCopied = false;

  const layer = element("div", "referral-layer");
  layer.addEventListener("click", (event) => {
    if (event.target === layer) closeReferralModal();
  });

  const shell = element("section", "referral-shell");
  shell.setAttribute("role", "dialog");
  shell.setAttribute("aria-modal", "true");
  shell.setAttribute("aria-label", t("inviteModalTitle"));

  const close = element("button", "icon-button referral-close", "×");
  close.type = "button";
  close.setAttribute("aria-label", t("close"));
  close.addEventListener("click", () => closeReferralModal());

  const hero = element("header", "referral-hero");
  const heroCopy = element("div");
  heroCopy.append(
    element("p", "eyebrow", t("inviteModalEyebrow")),
    element("h2", "", t("inviteModalTitle")),
    element("p", "muted", t("inviteModalSubtitle")),
  );
  hero.append(heroCopy, close);

  const active = Number(referral.trial_progress || 0);
  const required = Number(referral.trial_required || 5);
  const remaining = Math.max(0, required - active);
  const bonus = element("section", "referral-bonus");
  const mascot = createPandaMascot("referral-mascot");
  const bonusCopy = element("div", "referral-bonus-copy");
  bonusCopy.append(
    element("span", "referral-bonus-pill", t("inviteBonusLabel")),
    element(
      "h3",
      "",
      t("inviteBonusTitle", { count: required }),
    ),
    element("p", "muted", t("inviteBonusBody")),
  );
  const bonusProgress = element("div", "referral-progress");
  bonusProgress.append(
    element(
      "b",
      "",
      t("inviteActiveCount", { done: active, total: required }),
    ),
    element("span", "", t("inviteRemaining", { count: remaining })),
  );
  const track = element("div", "summary-progress");
  const fill = element("span", "progress-fill");
  track.append(fill);
  setProgress(fill, active, required);
  bonusProgress.append(track);
  bonusCopy.append(bonusProgress);
  bonus.append(mascot, bonusCopy);

  const destinations = element("section", "referral-section");
  const destinationsHead = element("div", "referral-section-head");
  destinationsHead.append(
    element("h3", "", t("inviteDestinationTitle")),
    element("span", "", t("inviteDestinationHint")),
  );
  const grid = element("div", "referral-destination-grid");
  const qrCard = element("section", "referral-qr-card");
  qrCard.tabIndex = -1;
  grid.append(
    referralDestination(
      "TG",
      t("inviteDestinationTelegram"),
      t("inviteDestinationTelegramBody"),
      () => void shareReferralToTelegram(referral.link),
    ),
    referralDestination(
      "WA",
      t("inviteDestinationWhatsapp"),
      t("inviteDestinationWhatsappBody"),
      () => void shareReferralToWhatsapp(referral.link),
    ),
    referralDestination(
      "⌘",
      referralSystemShareTitle(),
      referralSystemShareBody(),
      () => void shareReferralWithSystem(referral.link),
    ),
    referralDestination(
      "▦",
      t("inviteQrTitle"),
      t("inviteQrBody"),
      () => highlightReferralQr(qrCard),
      "is-qr",
    ),
  );
  destinations.append(destinationsHead, grid);

  const linkBlock = element("section", "referral-section");
  const linkHead = element("div", "referral-section-head");
  linkHead.append(element("h3", "", t("invitePersonalLink")), element("span", "", t("invitePrivate")));
  const linkRow = element("div", "referral-link-row");
  linkRow.append(element("span", "referral-link-icon", "⌁"));
  const linkText = element("p", "", referral.link);
  const copyButton = element("button", "primary-button referral-copy-button", t("inviteCopyButton"));
  copyButton.type = "button";
  copyButton.addEventListener("click", () => void copyReferralLink(referral.link, copyButton));
  linkRow.append(linkText, copyButton);
  linkBlock.append(linkHead, linkRow);

  const qrImage = element("img", "referral-qr-image");
  qrImage.alt = t("inviteQrAlt");
  qrImage.src = makeReferralQrDataUrl(referral.link);
  const qrText = element("div", "referral-qr-copy");
  qrText.append(
    element("h3", "", t("inviteQrScanTitle")),
    element("p", "muted", t("inviteQrScanBody")),
  );
  qrCard.append(qrImage, qrText);

  const note = element("p", "referral-note");
  note.append(element("span", "", "✓"), document.createTextNode(t("inviteBonusNote")));

  shell.append(hero, bonus, destinations, linkBlock, qrCard, note);
  layer.append(shell);
  document.body.append(layer);
  close.focus();
}

function makeReferralQrDataUrl(text) {
  const matrix = referralQrMatrix(String(text || ""));
  if (!matrix) return "";
  const quiet = 4;
  const size = matrix.length + quiet * 2;
  const rects = [];
  for (let row = 0; row < matrix.length; row += 1) {
    for (let col = 0; col < matrix.length; col += 1) {
      if (matrix[row][col]) {
        rects.push(`<rect x="${col + quiet}" y="${row + quiet}" width="1" height="1"/>`);
      }
    }
  }
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges">` +
    `<rect width="${size}" height="${size}" fill="#fff"/>` +
    `<g fill="#211d17">${rects.join("")}</g></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function referralQrMatrix(text) {
  const bytes = new TextEncoder().encode(text);
  const dataCodewords = 80;
  const errorCodewords = 20;
  const totalBits = dataCodewords * 8;
  const bits = [];
  const pushBits = (value, count) => {
    for (let i = count - 1; i >= 0; i -= 1) bits.push((value >>> i) & 1);
  };
  pushBits(4, 4);
  pushBits(bytes.length, 8);
  bytes.forEach((byte) => pushBits(byte, 8));
  if (bits.length > totalBits) return null;
  for (let i = 0; i < Math.min(4, totalBits - bits.length); i += 1) bits.push(0);
  while (bits.length % 8) bits.push(0);
  const codewords = [];
  for (let i = 0; i < bits.length; i += 8) {
    codewords.push(bits.slice(i, i + 8).reduce((value, bit) => (value << 1) | bit, 0));
  }
  for (let pad = 0; codewords.length < dataCodewords; pad += 1) {
    codewords.push(pad % 2 === 0 ? 0xec : 0x11);
  }
  const payload = [...codewords, ...reedSolomonRemainder(codewords, errorCodewords)];
  const payloadBits = [];
  payload.forEach((byte) => pushCodewordBits(payloadBits, byte));

  const base = referralQrBaseMatrix();
  let best = null;
  let bestPenalty = Number.POSITIVE_INFINITY;
  for (let mask = 0; mask < 8; mask += 1) {
    const matrix = base.matrix.map((row) => [...row]);
    referralQrPlaceData(matrix, base.reserved, payloadBits, mask);
    referralQrWriteFormat(matrix, mask);
    const penalty = referralQrPenalty(matrix);
    if (penalty < bestPenalty) {
      bestPenalty = penalty;
      best = matrix;
    }
  }
  return best;
}

function pushCodewordBits(bits, byte) {
  for (let i = 7; i >= 0; i -= 1) bits.push((byte >>> i) & 1);
}

function referralQrBaseMatrix() {
  const size = 33;
  const matrix = Array.from({ length: size }, () => Array(size).fill(false));
  const reserved = Array.from({ length: size }, () => Array(size).fill(false));
  const set = (row, col, value, reserve = true) => {
    if (row < 0 || row >= size || col < 0 || col >= size) return;
    matrix[row][col] = Boolean(value);
    if (reserve) reserved[row][col] = true;
  };
  const finder = (row, col) => {
    for (let y = -1; y <= 7; y += 1) {
      for (let x = -1; x <= 7; x += 1) {
        const inner = x >= 0 && x <= 6 && y >= 0 && y <= 6;
        const dark =
          inner &&
          (x === 0 || x === 6 || y === 0 || y === 6 || (x >= 2 && x <= 4 && y >= 2 && y <= 4));
        set(row + y, col + x, dark);
      }
    }
  };
  finder(0, 0);
  finder(0, size - 7);
  finder(size - 7, 0);
  for (let y = -2; y <= 2; y += 1) {
    for (let x = -2; x <= 2; x += 1) {
      const distance = Math.max(Math.abs(x), Math.abs(y));
      set(26 + y, 26 + x, distance !== 1);
    }
  }
  for (let i = 0; i < size; i += 1) {
    if (!reserved[6][i]) set(6, i, i % 2 === 0);
    if (!reserved[i][6]) set(i, 6, i % 2 === 0);
  }
  for (let i = 0; i < 9; i += 1) {
    if (i !== 6) {
      set(8, i, false);
      set(i, 8, false);
    }
  }
  for (let i = size - 8; i < size; i += 1) set(8, i, false);
  for (let i = size - 7; i < size; i += 1) set(i, 8, false);
  set(size - 8, 8, true);
  return { matrix, reserved };
}

function referralQrMask(mask, row, col) {
  switch (mask) {
    case 0:
      return (row + col) % 2 === 0;
    case 1:
      return row % 2 === 0;
    case 2:
      return col % 3 === 0;
    case 3:
      return (row + col) % 3 === 0;
    case 4:
      return (Math.floor(row / 2) + Math.floor(col / 3)) % 2 === 0;
    case 5:
      return ((row * col) % 2) + ((row * col) % 3) === 0;
    case 6:
      return (((row * col) % 2) + ((row * col) % 3)) % 2 === 0;
    default:
      return (((row + col) % 2) + ((row * col) % 3)) % 2 === 0;
  }
}

function referralQrPlaceData(matrix, reserved, bits, mask) {
  let index = 0;
  let upward = true;
  for (let right = matrix.length - 1; right > 0; right -= 2) {
    if (right === 6) right -= 1;
    for (let offset = 0; offset < matrix.length; offset += 1) {
      const row = upward ? matrix.length - 1 - offset : offset;
      for (let col = right; col >= right - 1; col -= 1) {
        if (reserved[row][col]) continue;
        const bit = index < bits.length ? bits[index] : 0;
        matrix[row][col] = Boolean(bit) !== referralQrMask(mask, row, col);
        index += 1;
      }
    }
    upward = !upward;
  }
}

function referralQrWriteFormat(matrix, mask) {
  const size = matrix.length;
  const bits = referralQrFormatBits(mask);
  const bit = (index) => Boolean((bits >>> index) & 1);
  for (let i = 0; i <= 5; i += 1) matrix[8][i] = bit(i);
  matrix[8][7] = bit(6);
  matrix[8][8] = bit(7);
  matrix[7][8] = bit(8);
  for (let i = 9; i < 15; i += 1) matrix[14 - i][8] = bit(i);
  for (let i = 0; i < 8; i += 1) matrix[size - 1 - i][8] = bit(i);
  for (let i = 8; i < 15; i += 1) matrix[8][size - 15 + i] = bit(i);
  matrix[size - 8][8] = true;
}

function referralQrFormatBits(mask) {
  const data = (1 << 3) | mask;
  let remainder = data;
  for (let i = 0; i < 10; i += 1) {
    remainder = (remainder << 1) ^ (((remainder >>> 9) & 1) ? 0x537 : 0);
  }
  return ((data << 10) | (remainder & 0x3ff)) ^ 0x5412;
}

function referralQrPenalty(matrix) {
  let penalty = 0;
  const size = matrix.length;
  const runPenalty = (values) => {
    let score = 0;
    let runColor = values[0];
    let runLength = 1;
    for (let i = 1; i < values.length; i += 1) {
      if (values[i] === runColor) {
        runLength += 1;
      } else {
        if (runLength >= 5) score += runLength - 2;
        runColor = values[i];
        runLength = 1;
      }
    }
    return score + (runLength >= 5 ? runLength - 2 : 0);
  };
  for (let row = 0; row < size; row += 1) penalty += runPenalty(matrix[row]);
  for (let col = 0; col < size; col += 1) {
    penalty += runPenalty(matrix.map((row) => row[col]));
  }
  for (let row = 0; row < size - 1; row += 1) {
    for (let col = 0; col < size - 1; col += 1) {
      const color = matrix[row][col];
      if (
        color === matrix[row][col + 1] &&
        color === matrix[row + 1][col] &&
        color === matrix[row + 1][col + 1]
      ) {
        penalty += 3;
      }
    }
  }
  const dark = matrix.flat().filter(Boolean).length;
  const percent = (dark * 100) / (size * size);
  penalty += Math.floor(Math.abs(percent - 50) / 5) * 10;
  return penalty;
}

function reedSolomonRemainder(data, degree) {
  const divisor = reedSolomonDivisor(degree);
  const result = Array(degree).fill(0);
  data.forEach((byte) => {
    const factor = byte ^ result.shift();
    result.push(0);
    divisor.forEach((coefficient, index) => {
      result[index] ^= reedSolomonMultiply(coefficient, factor);
    });
  });
  return result;
}

function reedSolomonDivisor(degree) {
  const result = Array(degree).fill(0);
  result[degree - 1] = 1;
  let root = 1;
  for (let i = 0; i < degree; i += 1) {
    for (let j = 0; j < result.length; j += 1) {
      result[j] = reedSolomonMultiply(result[j], root);
      if (j + 1 < result.length) result[j] ^= result[j + 1];
    }
    root = reedSolomonMultiply(root, 2);
  }
  return result;
}

function reedSolomonMultiply(a, b) {
  if (a === 0 || b === 0) return 0;
  let value = 0;
  for (let i = 7; i >= 0; i -= 1) {
    value = (value << 1) ^ ((value >>> 7) * 0x11d);
    value ^= ((b >>> i) & 1) * a;
  }
  return value & 0xff;
}

/** The real invite button opens a native-feeling share modal with app routes. */
function inviteMorph(link) {
  const referral = currentReferralData();
  const inviteLink = link || referral.link;
  const morph = element("div", "invite-morph");
  const main = element("button", "invite-main", t("inviteAddFriend"));
  main.type = "button";
  main.disabled = !inviteLink;
  main.addEventListener("click", () => openReferralModal({ ...referral, link: inviteLink }));
  morph.append(main);
  return morph;
}

function renderInviteCard() {
  const card = element("article", "invite-card card-panel");
  const copy = element("div");
  copy.append(
    element("p", "eyebrow", t("inviteEyebrow")),
    element("h3", "", t("inviteFriendsTitle")),
    element("p", "muted", t("inviteFriendsBody")),
  );
  card.append(copy);

  const referral = currentReferralData();
  if (!referral.link) {
    card.append(
      element("p", "muted small", state.referralError || t("inviteLoading")),
    );
    return card;
  }

  card.append(inviteMorph(referral.link));
  if (state.referralError) {
    card.append(element("p", "muted small", state.referralError));
  }

  // The demo shows two invitee avatars beside the counters; ours are the real
  // initials the referral service returns.
  const status = element("div", "invite-status");
  const people = Array.isArray(referral.items) ? referral.items.slice(0, 2) : [];
  people.forEach((person) => {
    status.append(
      element("span", "mini-avatar", userInitials(person?.name).slice(0, 1)),
    );
  });
  const counters = element("div", "invite-counters");
  counters.append(
    element("b", "", t("inviteSent", { count: Number(referral.invited || 0) })),
    element(
      "small",
      "muted",
      t("inviteJoined", { count: Number(referral.activated || 0) }),
    ),
  );
  status.append(counters);
  card.append(status);

  const required = Number(referral.trial_required || 0);
  if (required > 0) {
    const track = element("div", "summary-progress");
    const fill = element("span", "progress-fill");
    track.append(fill);
    setProgress(fill, Number(referral.trial_progress || 0), required);
    card.append(
      element(
        "p",
        "muted small",
        t("inviteTrialProgress", {
          done: Number(referral.trial_progress || 0),
          total: required,
        }),
      ),
      track,
    );
  }
  return card;
}

/** The demo's sync card. No sync endpoint exists, so the whole card is veiled. */
function renderSyncCard() {
  const card = element("article", "sync-card card-panel");
  card.append(element("div", "sync-icon", "☁"));
  const copy = element("div");
  copy.append(
    element("h3", "", t("syncTitle")),
    element("p", "muted", t("syncBody")),
  );
  const action = element("button", "secondary-button", t("syncNow"));
  action.type = "button";
  card.append(copy, action);
  return soonBlock(card);
}

// The study goal is a single choice made once, in onboarding. Hanzi marks are
// used instead of emoji so the cards match the rest of the desktop UI.
const GOAL_KIND_META = {
  conversation: {
    glyph: "话",
    titleKey: "goalKindConversation",
    bodyKey: "goalKindConversationBody",
  },
  hsk: { glyph: "试", titleKey: "goalKindHsk", bodyKey: "goalKindHskBody" },
  study: { glyph: "学", titleKey: "goalKindStudy", bodyKey: "goalKindStudyBody" },
};

function goalKindTitle(kind) {
  const meta = GOAL_KIND_META[kind];
  return meta ? t(meta.titleKey) : "";
}

function goalKindBody(kind) {
  const meta = GOAL_KIND_META[kind];
  return meta ? t(meta.bodyKey) : "";
}

async function ensureGoalState() {
  if (state.goal) return state.goal;
  try {
    state.goal = await desktopBridge.goalState();
  } catch {
    // A goal that cannot be read counts as unset, so onboarding asks again
    // instead of the profile showing an empty card with no way out.
    state.goal = { kind: "", configured: false };
  }
  return state.goal;
}

async function maybeOpenOnboarding() {
  if (state.onboardingOpen) return;
  if (dom.workspace.hidden || lesson.isOpen) return;
  const goal = await ensureGoalState();
  if (goal?.configured) return;
  openOnboarding();
}

const ONBOARDING_STEPS = 2;

function openOnboarding() {
  if (state.onboardingOpen) return;
  state.onboardingOpen = true;
  state.onboardingStep = 0;
  state.onboardingChoice = String(state.goal?.kind || "");
  state.onboardingPreviousFocus = document.activeElement;
  dom.onboardingLayer.hidden = false;
  renderOnboarding();
  dom.onboardingBody.querySelector(".goal-choice")?.focus();
}

function closeOnboarding() {
  if (!state.onboardingOpen) return;
  state.onboardingOpen = false;
  dom.onboardingLayer.hidden = true;
  dom.onboardingBody.replaceChildren();
  const previous = state.onboardingPreviousFocus;
  state.onboardingPreviousFocus = null;
  if (previous instanceof HTMLElement && document.contains(previous)) {
    previous.focus();
  } else {
    dom.contentTitle.focus();
  }
}

function onboardingGoalStep() {
  const slide = element("div", "onboarding-slide");
  const intro = element("div", "onboarding-intro");
  intro.append(
    element("p", "eyebrow", t("onboardingStepOne")),
    element("h3", "", t("onboardingGoalTitle")),
    element("p", "muted", t("onboardingGoalBody")),
  );

  const choices = element("div", "goal-choices");
  GOAL_KINDS.forEach((kind) => {
    const meta = GOAL_KIND_META[kind];
    if (!meta) return;
    const active = state.onboardingChoice === kind;
    const card = element("button", `goal-choice${active ? " is-active" : ""}`);
    card.type = "button";
    card.setAttribute("aria-pressed", active ? "true" : "false");
    card.append(
      element("span", "goal-choice-mark hanzi", meta.glyph),
      element("b", "", t(meta.titleKey)),
      element("span", "muted", t(meta.bodyKey)),
    );
    card.addEventListener("click", () => {
      state.onboardingChoice = kind;
      renderOnboarding();
      dom.onboardingBody.querySelector(".goal-choice.is-active")?.focus();
    });
    choices.append(card);
  });

  slide.append(intro, choices);
  return slide;
}

/**
 * The demo's second step introduces a macOS Smart Widget. No WidgetKit target
 * exists in this project and the bundle is ad-hoc signed, so an extension
 * would not load at all — and Windows ships an NSIS installer with no
 * equivalent. The step keeps the demo layout and stays behind the veil.
 */
function onboardingWidgetStep() {
  const slide = element("div", "onboarding-slide");
  const intro = element("div", "onboarding-intro");
  intro.append(
    element("p", "eyebrow", t("onboardingStepTwo")),
    element("h3", "", t("onboardingWidgetTitle")),
    element("p", "muted", t("onboardingWidgetBody")),
  );

  const layout = element("div", "widget-intro");
  const copy = element("div", "widget-copy");
  copy.append(
    element("h4", "", t("widgetOneButtonTitle")),
    element("p", "muted", t("widgetOneButtonBody")),
  );
  const features = element("div", "widget-features");
  [
    ["☀", t("widgetFeatureMorning")],
    ["字", t("widgetFeatureDay")],
    ["🔥", t("widgetFeatureEvening")],
    ["✓", t("widgetFeatureAfterLesson")],
  ].forEach(([mark, label]) => {
    const row = element("span", "");
    row.append(element("i", "", mark), document.createTextNode(label));
    features.append(row);
  });
  const install = element("button", "primary-button widget-install", t("widgetInstall"));
  install.type = "button";
  copy.append(features, install);

  const preview = element("div", "widget-preview");
  const card = element("div", "widget-preview-card");
  const streak = Number(state.map?.progress?.streak || 0);
  card.append(
    element("strong", "", `${streak} 🔥`),
    element("p", "", t("widgetPreviewNote")),
    element("small", "muted", t("widgetPreviewCaption")),
  );
  preview.append(card);

  layout.append(copy, preview);
  slide.append(intro, layout);
  return soonBlock(slide);
}

function renderOnboarding() {
  const step = state.onboardingStep;
  const chosen = GOAL_KINDS.includes(state.onboardingChoice);
  dom.onboardingTitle.textContent = t("onboardingTitle");
  dom.onboardingSubtitle.textContent = t("onboardingSubtitle");
  dom.onboardingLater.textContent = t("onboardingLater");
  dom.onboardingBack.textContent = t("onboardingBack");
  dom.onboardingBack.hidden = step === 0;
  dom.onboardingStart.textContent =
    step === ONBOARDING_STEPS - 1 ? t("onboardingStart") : t("onboardingNext");
  // The goal is what onboarding exists for, so the first step gates the rest.
  dom.onboardingStart.disabled = !chosen;
  [...dom.onboardingSteps.children].forEach((dot, index) => {
    dot.classList.toggle("is-on", index <= step);
  });

  dom.onboardingBody.replaceChildren(
    step === 0 ? onboardingGoalStep() : onboardingWidgetStep(),
  );
  dom.onboardingBody.scrollTop = 0;
}

function onboardingBack() {
  if (state.onboardingStep === 0) return;
  state.onboardingStep -= 1;
  renderOnboarding();
}

async function confirmOnboarding() {
  const kind = state.onboardingChoice;
  if (!GOAL_KINDS.includes(kind)) return;
  if (state.onboardingStep < ONBOARDING_STEPS - 1) {
    state.onboardingStep += 1;
    renderOnboarding();
    return;
  }
  dom.onboardingStart.disabled = true;
  const saved = await saveGoal(kind);
  if (!saved) {
    dom.onboardingStart.disabled = false;
    return;
  }
  closeOnboarding();
}

async function saveGoal(kind) {
  try {
    state.goal = await desktopBridge.goalSave(kind);
    showToast(t("goalSaved"));
  } catch {
    showToast(t("goalSaveFailed"));
    return false;
  }
  if (state.view === "profile") renderProfile();
  return true;
}

async function loadProfileExtras() {
  await ensureGoalState();
  try {
    state.referral = await desktopBridge.referralOverview(
      -new Date().getTimezoneOffset(),
    );
    state.referralError = "";
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    state.referral = null;
    state.referralError = t("inviteUnavailable");
  }
  if (state.view === "profile") renderProfile();
}

function renderProfile() {
  const map = state.map;
  if (!map) return;
  const user = map.user || {};
  const progress = map.progress || {};
  const completed = Number(progress.completed || 0);
  const lessons = allLessons();
  const percent = progressPercent(completed, lessons.length);
  const league = String(progress.league || t("notAvailable"));
  const levelLabelText = String(map.label || levelLabel(map.level));
  dom.contentTitle.textContent = t("profileTitle");
  dom.contentSubtitle.textContent = t("profileSubtitle");
  dom.content.replaceChildren(
    viewHeading(t("profileTitle"), t("profileSubtitle"), levelLabelText),
  );

  // --- row 1: identity + study goal ----------------------------------------
  const topRow = element("div", "profile-two-cols");

  const hero = element("article", "profile-hero card-panel");
  const avatar = element("div", "profile-initials");
  renderUserAvatar(avatar, user);
  const heroCopy = element("div");
  heroCopy.append(
    element("h3", "", String(user.name || t("unknownUser"))),
    element(
      "p",
      "muted",
      `${levelLabelText} · ${percent}% · ${Number(progress.streak || 0)} 🔥`,
    ),
  );
  // The demo shows learned words and study minutes here. Neither is reported
  // by the server, so the pills keep their place with a dash inside them.
  const chips = element("div", "profile-chips");
  chips.append(
    element("span", "tag", `${NO_VALUE} ${t("profileWordsUnit")}`),
    element("span", "tag", `${NO_VALUE} ${t("profileMinutesUnit")}`),
  );
  heroCopy.append(soonBlock(chips));
  const panda = createPandaMascot("profile-panda");
  hero.append(avatar, heroCopy, panda);

  // The goal itself is picked in onboarding; this card only reports it.
  const goalKind = String(state.goal?.kind || "");
  const goalSet = GOAL_KINDS.includes(goalKind);
  const goal = element("article", "profile-goal card-panel");
  const goalHead = element("div", "card-heading-row");
  goalHead.append(element("h3", "", t("myGoalTitle")));
  if (goalSet) goalHead.append(element("span", "tag green", t("goalActive")));
  goal.append(goalHead);
  if (goalSet) {
    goal.append(
      element("p", "", goalKindTitle(goalKind)),
      element("p", "muted small", goalKindBody(goalKind)),
    );
  } else {
    goal.append(element("p", "muted", t("goalNotSet")));
  }
  // Daily-goal completion needs study minutes, which nothing records yet, so
  // the bar and the "N min / day" line keep their place behind the veil.
  const dailyWrap = element("div", "profile-goal-daily");
  const track = element("div", "summary-progress profile-progress-track");
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  track.append(element("span", "progress-fill is-placeholder"));
  dailyWrap.append(
    track,
    element("p", "muted small", t("goalPerDay", { minutes: NO_VALUE })),
  );
  goal.append(soonBlock(dailyWrap));
  // The goal has no server column, so it stays a device-local preference.
  goal.append(element("p", "muted small", t("goalLocalNote")));
  if (!goalSet) {
    const chooseGoal = element("button", "secondary-button", t("goalChoose"));
    chooseGoal.type = "button";
    chooseGoal.addEventListener("click", () => openOnboarding());
    goal.append(chooseGoal);
  }
  topRow.append(hero, goal);

  // --- row 2: invites (real) + sync (no endpoint yet) -----------------------
  const actionsRow = element("div", "profile-actions");
  actionsRow.append(renderInviteCard(), renderSyncCard());

  // --- row 3: progress ------------------------------------------------------
  const statsHead = element("div", "profile-section-head");
  const statsCopy = element("div");
  statsCopy.append(
    element("h3", "", t("learningProgress")),
    element("p", "muted", t("realServerActivityBody")),
  );
  statsHead.append(statsCopy, element("span", "tag green", league));

  const stats = element("div", "profile-stats-grid");
  stats.append(
    profileStatCard(
      Number(progress.streak || 0),
      t("streakDays"),
      t("bestStreakDelta", { days: Number(progress.longest_streak || 0) }),
    ),
    comingSoonStatCard(t("statWordsLearned")),
    profileStatCard(
      completed,
      t("completedLessons"),
      t("lessons", { done: completed, total: lessons.length }),
    ),
    comingSoonStatCard(t("statStudyMinutes")),
  );

  const activeDays = weekSnapshot(progress).filter((day) => day.active).length;
  const activity = chartCard(
    t("weeklyActivity"),
    element("span", "tag", t("activeDaysOfWeek", { done: activeDays })),
  );
  activity.append(weekBarChart(progress));

  const progressGrid = element("div", "profile-progress-grid");
  const leftStack = element("div", "profile-stack");
  leftStack.append(activity, levelProgressCard(levelLabelText));
  const rightStack = element("div", "profile-stack");
  rightStack.append(weakAreasCard(), accuracyTrendCard());
  progressGrid.append(leftStack, rightStack);

  const insights = insightChips();

  // --- row 4: settings ------------------------------------------------------
  const settingsHead = element("div", "profile-section-head");
  const settingsCopy = element("div");
  settingsCopy.append(
    element("h3", "", t("settings")),
    element("p", "muted", t("settingsSubtitle")),
  );
  settingsHead.append(settingsCopy);

  const settingsRow = element("div", "profile-two-cols");

  const studyCard = element("article", "profile-settings card-panel");
  studyCard.append(element("h3", "", t("studyInterfaceSection")));
  const languageSelect = selectControl(
    languageOptions.map((option) => ({
      value: option.code,
      label: option.label,
    })),
    getLanguage(),
    (code) => void changeLanguage(code),
  );
  languageSelect.dataset.role = "language";
  const reopen = element("button", "secondary-button", t("onboardingReset"));
  reopen.type = "button";
  reopen.addEventListener("click", () => openOnboarding());
  studyCard.append(
    settingRow(
      t("interfaceLanguage"),
      t("interfaceLanguageBody"),
      languageSelect,
    ),
    // The level is decided by the server, so the demo select is inert here.
    comingSoonSettingRow(
      t("courseLevelTitle"),
      t("courseLevelBody"),
      selectControl(
        [1, 2, 3, 4].map((level) => ({
          value: level,
          label: t("levelLabel", { level }),
        })),
        map.level,
      ),
    ),
    comingSoonSettingRow(
      t("audioAutoplayTitle"),
      t("audioAutoplayBody"),
      toggleButton(false, () => {}),
    ),
    comingSoonSettingRow(
      t("pinyinToggleTitle"),
      t("pinyinToggleBody"),
      toggleButton(true, () => {}),
    ),
    settingRow(
      t("reduceMotionTitle"),
      t("reduceMotionBody"),
      toggleButton(state.reduceMotion, (next) => {
        setReduceMotion(next);
        renderProfile();
      }),
    ),
    settingRow(t("onboardingReopen"), t("onboardingReopenBody"), reopen),
  );

  settingsRow.append(renderNotificationsCard(), studyCard);

  // --- row 5: what the desktop needs and the demo has no place for ---------
  const accountHead = element("div", "profile-section-head");
  const accountCopy = element("div");
  accountCopy.append(
    element("h3", "", t("accountSectionTitle")),
    element("p", "muted", t("accountSectionBody")),
  );
  accountHead.append(accountCopy);

  const accountCard = element("article", "profile-account card-panel");
  const manage = element("button", "secondary-button", t("manageSubscription"));
  manage.type = "button";
  manage.addEventListener("click", () => routeTo("subscription"));
  const updateCheck = element("button", "secondary-button", t("checkUpdatesNow"));
  updateCheck.type = "button";
  updateCheck.disabled = ["checking", "installing", "ready"].includes(
    state.updateStatus,
  );
  updateCheck.addEventListener("click", () => {
    void checkForUpdates({ showProgress: true });
  });
  const logout = element("button", "secondary-button is-danger", t("logout"));
  logout.type = "button";
  logout.addEventListener("click", () => logoutDesktop(logout));
  accountCard.append(
    settingRow(
      user.is_paid ? t("paidPlan") : t("freePlan"),
      user.is_paid ? t("paidAccessDescription") : t("freeAccessDescription"),
      manage,
    ),
    settingRow(t("desktopApp"), t("automaticUpdatesBody"), updateCheck),
    settingRow(t("logout"), t("logoutBody"), logout),
  );
  // The version sits quietly in the corner instead of the toolbar.
  accountCard.append(
    element(
      "p",
      "profile-version",
      state.appVersion ? `v${state.appVersion}` : "",
    ),
  );

  dom.content.append(
    topRow,
    actionsRow,
    statsHead,
    stats,
    progressGrid,
    insights,
    settingsHead,
    settingsRow,
    accountHead,
    accountCard,
  );
}

function setReduceMotion(enabled) {
  state.reduceMotion = Boolean(enabled);
  document.documentElement.dataset.reduceMotion = state.reduceMotion ? "1" : "0";
  try {
    localStorage.setItem("pomp-hsk-reduce-motion", state.reduceMotion ? "1" : "0");
  } catch {
    // Ignore storage failures.
  }
}

function restoreReduceMotion() {
  try {
    setReduceMotion(localStorage.getItem("pomp-hsk-reduce-motion") === "1");
  } catch {
    setReduceMotion(false);
  }
}

async function changeLanguage(language) {
  if (language === getLanguage()) {
    return;
  }
  // The picker is a select now, like the demo. Only the language one is
  // touched: the level select next to it is inert by design.
  const pickers = dom.content.querySelectorAll('[data-role="language"]');
  pickers.forEach((picker) => {
    picker.disabled = true;
  });
  try {
    const result = await desktopBridge.setLanguage(language);
    if (result?.ok !== true) {
      throw new Error("desktop_language_save_failed");
    }
    setUiLanguage(result.language || language);
    saveLanguage(getLanguage());
    if (state.map?.user) {
      state.map.user.language = getLanguage();
    }
    applyStaticText();
    renderRail();
    renderActiveView();
    showToast(t("languageSaved"));
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    pickers.forEach((picker) => {
      picker.disabled = false;
    });
    showToast(errorMessage(error));
  }
}

async function logoutDesktop(button) {
  button.disabled = true;
  try {
    await desktopBridge.logout();
  } catch {
    // Native logout clears local credentials even if server revoke is offline.
  }
  showAuth();
}

function renderCourseError(error) {
  dom.contentTitle.textContent = t("course");
  dom.contentSubtitle.textContent = "";
  const wrap = element("div", "error-state");
  wrap.append(
    element("h2", "", errorMessage(error)),
    element("p", "muted", t("noConnection")),
  );
  const retry = element("button", "primary-button", t("retry"));
  retry.type = "button";
  retry.addEventListener("click", () => loadCourseMap({ keepView: true }));
  wrap.append(retry);
  dom.content.replaceChildren(wrap);
}

function errorMessage(error) {
  if (error?.code === "desktop_bridge_unavailable") {
    return t("bridgeUnavailable");
  }
  if (isSessionError(error)) {
    return t("sessionExpired");
  }
  if (error?.code === "desktop_network_unavailable") {
    return t("noConnection");
  }
  return t("requestFailed");
}

function levelLabel(value) {
  const normalized = String(value || "hsk1").toUpperCase().replace("HSK", "");
  return t("levelLabel", { level: normalized || "1" });
}

function openRail() {
  state.railOpen = true;
  dom.rail.classList.add("is-open");
  dom.railScrim.hidden = false;
  updateRailToggleLabel();
}

function closeRail() {
  state.railOpen = false;
  dom.rail.classList.remove("is-open");
  dom.railScrim.hidden = true;
  updateRailToggleLabel();
}

function updateRailToggleLabel() {
  dom.railToggle.setAttribute(
    "aria-label",
    state.railOpen ? t("closeCourseMenu") : t("openCourseMenu"),
  );
  dom.railToggle.setAttribute("aria-expanded", String(state.railOpen));
}

function toggleRail() {
  state.railOpen ? closeRail() : openRail();
}

function openAi({ focus = true } = {}) {
  if (!state.aiOpen) {
    state.aiPreviousFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : dom.aiLauncher;
  }
  state.aiOpen = true;
  dom.aiDrawer.classList.add("is-open");
  dom.aiDrawer.setAttribute("aria-hidden", "false");
  dom.aiLauncher.setAttribute("aria-expanded", "true");
  if (!state.aiLoaded) {
    loadAiStatus();
  }
  syncLessonChrome();
  if (focus) {
    dom.closeAi.focus();
  }
}

function openAiWithPrompt(prompt = "") {
  const value = String(prompt || "").trim();
  if (value) dom.aiInput.value = value;
  openAi();
  updateAiComposer();
}

function closeAi({ restoreFocus = true } = {}) {
  const shouldRestoreFocus = state.aiOpen && restoreFocus;
  if (lesson.isOpen) {
    state.aiOpenedByLesson = false;
  }
  if (state.aiRecording) cancelAiRecording();
  state.aiOpen = false;
  dom.aiDrawer.classList.remove("is-open");
  dom.aiDrawer.setAttribute("aria-hidden", "true");
  dom.aiLauncher.setAttribute("aria-expanded", "false");
  syncLessonChrome();
  if (shouldRestoreFocus) {
    const target = state.aiPreviousFocus?.isConnected
      ? state.aiPreviousFocus
      : dom.aiLauncher;
    target.focus();
  }
  state.aiPreviousFocus = null;
}

function toggleAi() {
  if (lesson.isOpen && !state.aiOpen) {
    state.aiOpenedByLesson = false;
  }
  state.aiOpen ? closeAi() : openAi();
}

async function loadAiStatus() {
  state.aiLoaded = true;
  renderAiLoading();
  try {
    const result = await desktopBridge.localAiModelStatus();
    state.aiStatus = normalizeAiStatus(result);
    state.aiInstallBusy = aiInstallIsActive(state.aiStatus);
    renderAiPanel();
  } catch (error) {
    state.aiLoaded = false;
    renderAiError(error?.code || "local_ai_state_unavailable");
  }
}

function normalizeAiStatus(value) {
  const status = value && typeof value === "object" ? value : {};
  const expected = Math.max(0, Number(status.expectedSizeBytes) || 0);
  return {
    modelId: String(status.modelId || "qwen3-4b-q4-k-m"),
    installed: status.installed === true,
    sizeBytes: Math.max(0, Number(status.sizeBytes) || 0),
    expectedSizeBytes: expected,
    downloadedBytes: Math.min(
      expected || Number.MAX_SAFE_INTEGER,
      Math.max(0, Number(status.downloadedBytes) || 0),
    ),
    state: String(status.state || "unavailable"),
    runtimeAvailable: status.runtimeAvailable === true,
    runtimeState: String(status.runtimeState || "stopped"),
  };
}

function aiInstallIsActive(status) {
  return ["starting", "downloading", "verifying"].includes(status?.state);
}

function aiIsReady() {
  return Boolean(
    state.aiStatus?.installed && state.aiStatus?.runtimeAvailable,
  );
}

function formatAiBytes(value) {
  const bytes = Math.max(0, Number(value) || 0);
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${Math.round(bytes / 1024 ** 2)} MB`;
  return `${Math.round(bytes / 1024)} KB`;
}

function boundedAiText(value, limit = 240) {
  return [...String(value ?? "").trim()].slice(0, limit).join("");
}

function aiPromptSuggestion(labelKey, promptKey, variables = {}) {
  return {
    label: t(labelKey, variables),
    prompt: t(promptKey, variables),
  };
}

function currentCourseAiContext() {
  const current = currentLesson();
  const level = boundedAiText(state.map?.label || levelLabel(state.map?.level), 64);
  const lessonNumber = current ? Number(current.n) || 0 : 0;
  const lessonLine = current
    ? [
        t("lessonNumber", { number: lessonNumber }),
        boundedAiText(current.zh, 48),
        boundedAiText(current.py, 80),
        boundedAiText(pick(current.tr), 120),
      ].filter(Boolean).join(" · ")
    : "";
  return {
    level,
    lessonNumber,
    lessonLine,
    promptLines: [
      `Current course: ${level}`,
      `Course level: ${level}`,
      current
        ? [
            `Current course lesson: ${lessonNumber}`,
            `Chinese: ${boundedAiText(current.zh)}`,
            `Pinyin: ${boundedAiText(current.py)}`,
            `Translation: ${boundedAiText(pick(current.tr))}`,
          ].join("\n")
        : "",
    ].filter(Boolean),
  };
}

function activeViewLabel() {
  if (lesson.isOpen) {
    const number = lesson.lessonOrder || currentLesson()?.n || "";
    return t("lessonNumber", { number: number || "—" });
  }
  const labels = {
    today: t("today"),
    course: t("course"),
    practice: t("practice"),
    voice: t("voice"),
    vocabulary: t("vocabulary"),
    rating: t("rating"),
    subscription: t("subscription"),
    profile: t("profile"),
  };
  return labels[state.view] || t("course");
}

function defaultAiSuggestions() {
  return [
    aiPromptSuggestion("aiSuggestExplainVisible", "aiSuggestExplainVisiblePrompt"),
    aiPromptSuggestion("aiSuggestExamplesForScreen", "aiSuggestExamplesForScreenPrompt"),
    aiPromptSuggestion("aiSuggestContinueLesson", "aiSuggestContinueLessonPrompt"),
  ];
}

function buildAiScreenContext() {
  const course = currentCourseAiContext();
  const context = {
    screen: activeViewLabel(),
    badge: course.level,
    title: t("aiContextGenericTitle"),
    details: course.lessonLine ? [course.lessonLine] : [t("aiContextNoDetail")],
    promptLines: [
      `Active HSK AI screen: ${activeViewLabel()}`,
      ...course.promptLines,
    ],
    suggestions: defaultAiSuggestions(),
  };

  if (lesson.isOpen && typeof lesson.aiContext === "function") {
    const visible = lesson.aiContext();
    if (visible) {
      context.screen = t("lessonNumber", { number: visible.lessonOrder || course.lessonNumber || "—" });
      context.badge = `${Number(visible.index || 0)} / ${Number(visible.total || 0)}`;
      context.title = boundedAiText(visible.title || context.screen, 80);
      context.details = [
        boundedAiText(visible.sectionTitle, 90),
        boundedAiText(visible.summary, 140),
      ].filter(Boolean);
      context.promptLines.push("Visible lesson card:");
      context.promptLines.push(...visible.promptLines);
      context.suggestions = [
        visible.isExercise
          ? aiPromptSuggestion("aiSuggestPracticeHint", "aiSuggestPracticeHintPrompt")
          : aiPromptSuggestion("aiSuggestExplainVisible", "aiSuggestExplainVisiblePrompt"),
        aiPromptSuggestion("aiSuggestExamplesForScreen", "aiSuggestExamplesForScreenPrompt"),
        aiPromptSuggestion("aiSuggestionQuiz", "aiSuggestionQuizPrompt"),
      ];
    }
    return context;
  }

  if (state.view === "practice" && typeof practice.aiContext === "function") {
    const visible = practice.aiContext();
    context.title = boundedAiText(visible?.title || t("practiceTitle"), 80);
    context.details = [
      boundedAiText(visible?.progress, 90),
      boundedAiText(visible?.summary, 140),
    ].filter(Boolean);
    context.promptLines.push("Visible practice screen:");
    context.promptLines.push(...(visible?.promptLines || []));
    context.suggestions = visible?.isRunning
      ? [
          aiPromptSuggestion("aiSuggestPracticeHint", "aiSuggestPracticeHintPrompt"),
          aiPromptSuggestion("aiSuggestExplainVisible", "aiSuggestExplainVisiblePrompt"),
          aiPromptSuggestion("aiSuggestExamplesForScreen", "aiSuggestExamplesForScreenPrompt"),
        ]
      : [
          aiPromptSuggestion("aiSuggestionQuiz", "aiSuggestionQuizPrompt"),
          aiPromptSuggestion("aiSuggestPracticeReview", "aiSuggestPracticeReviewPrompt"),
          aiPromptSuggestion("aiSuggestContinueLesson", "aiSuggestContinueLessonPrompt"),
        ];
    return context;
  }

  if (state.view === "vocabulary" && typeof vocabulary.aiContext === "function") {
    const visible = vocabulary.aiContext();
    if (visible?.word) {
      context.title = `${boundedAiText(visible.word, 32)} · ${boundedAiText(visible.pinyin, 64)}`;
      context.badge = boundedAiText(visible.level || course.level, 24);
      context.details = [
        boundedAiText(visible.translation, 120),
        boundedAiText(visible.example, 140),
      ].filter(Boolean);
      context.promptLines.push("Visible vocabulary word:");
      context.promptLines.push(...visible.promptLines);
      context.suggestions = [
        aiPromptSuggestion("aiSuggestVocabMemory", "aiSuggestVocabMemoryPrompt", { word: visible.word }),
        aiPromptSuggestion("aiSuggestExamplesForScreen", "aiSuggestExamplesForScreenPrompt"),
        aiPromptSuggestion("aiSuggestVocabCompare", "aiSuggestVocabComparePrompt", { word: visible.word }),
      ];
    }
    return context;
  }

  if (state.view === "voice" && typeof voice.aiContext === "function") {
    const visible = voice.aiContext();
    context.title = boundedAiText(visible?.title || t("voiceTitle"), 80);
    context.details = [
      boundedAiText(visible?.summary, 140),
      boundedAiText(visible?.latestTurn, 140),
    ].filter(Boolean);
    context.promptLines.push("Visible AI Voice screen:");
    context.promptLines.push(...(visible?.promptLines || []));
    context.suggestions = [
      aiPromptSuggestion("aiSuggestVoicePrep", "aiSuggestVoicePrepPrompt"),
      aiPromptSuggestion("aiSuggestExplainVisible", "aiSuggestExplainVisiblePrompt"),
      aiPromptSuggestion("aiSuggestExamplesForScreen", "aiSuggestExamplesForScreenPrompt"),
    ];
    return context;
  }

  if (state.view === "subscription") {
    context.title = t("subscriptionTitle");
    context.details = [t("subscriptionSubtitle")];
    context.promptLines.push(`User access: ${state.map?.user?.is_paid ? "paid" : "free"}`);
    context.suggestions = [
      aiPromptSuggestion("aiSuggestSubscriptionPlan", "aiSuggestSubscriptionPlanPrompt"),
      aiPromptSuggestion("aiSuggestContinueLesson", "aiSuggestContinueLessonPrompt"),
      aiPromptSuggestion("aiSuggestExplainVisible", "aiSuggestExplainVisiblePrompt"),
    ];
    return context;
  }

  if (state.view === "profile" || state.view === "rating") {
    const progress = state.map?.progress || {};
    context.title = state.view === "rating" ? t("ratingTitle") : t("profile");
    context.details = [
      `${t("xpTotal")}: ${Number(progress.xp || 0)} XP`,
      `${t("streakDays")}: ${Number(progress.streak || 0)}`,
    ];
    context.promptLines.push(
      `Progress XP: ${Number(progress.xp || 0)}`,
      `Progress streak: ${Number(progress.streak || 0)}`,
    );
    context.suggestions = [
      aiPromptSuggestion("aiSuggestProfileReview", "aiSuggestProfileReviewPrompt"),
      aiPromptSuggestion("aiSuggestContinueLesson", "aiSuggestContinueLessonPrompt"),
      aiPromptSuggestion("aiSuggestionQuiz", "aiSuggestionQuizPrompt"),
    ];
  }

  return context;
}

function refreshAiContextPanel() {
  if (!state.aiOpen || !aiIsReady()) return;
  renderAiChat();
  updateAiComposer();
}

function fillAiPrompt(prompt) {
  const value = boundedAiText(prompt, 1000);
  if (!value) return;
  dom.aiInput.value = value;
  updateAiComposer();
  dom.aiInput.focus();
}

function renderAiContextCard(context) {
  const card = element("section", "ai-context-card");
  const head = element("div", "ai-context-head");
  const copy = element("div");
  copy.append(
    element("span", "eyebrow", t("aiContextEyebrow")),
    element("h3", "", context.title || t("aiContextGenericTitle")),
  );
  head.append(copy, element("span", "tag", context.badge || context.screen));
  card.append(head);

  const meta = element("div", "ai-context-meta");
  meta.append(element("span", "", t("aiContextScreen", { screen: context.screen })));
  (context.details || []).slice(0, 3).forEach((detail) => {
    meta.append(element("span", "", detail));
  });
  card.append(meta);
  return card;
}

function renderAiHintStrip(context) {
  const suggestions = element("div", "ai-hint-strip");
  (context.suggestions || defaultAiSuggestions()).slice(0, 3).forEach((suggestion) => {
    const button = element("button", "ai-hint-pill", suggestion.label);
    button.type = "button";
    button.addEventListener("click", () => fillAiPrompt(suggestion.prompt));
    suggestions.append(button);
  });
  return suggestions;
}

function cleanAiContent(value) {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .replace(/<think>[\s\S]*?(?:<\/think>|$)/gi, "")
    .replace(/<\/?think>/gi, "")
    .trim();
}

function appendAiHanziText(parent, value) {
  const parts = String(value || "").split(/([\u3400-\u9fff]+)/u);
  for (const part of parts) {
    if (!part) continue;
    if (/^[\u3400-\u9fff]+$/u.test(part)) {
      parent.append(element("span", "ai-hanzi", part));
    } else {
      parent.append(document.createTextNode(part));
    }
  }
}

function appendInlineAiText(parent, value) {
  const tokens = String(value || "").split(/(`[^`\n]+`|\*\*[^*\n]+?\*\*)/g);
  for (const token of tokens) {
    if (!token) continue;
    if (token.startsWith("`") && token.endsWith("`")) {
      parent.append(element("code", "ai-inline-code", token.slice(1, -1)));
    } else if (token.startsWith("**") && token.endsWith("**")) {
      const strong = element("strong");
      appendAiHanziText(strong, token.slice(2, -2));
      parent.append(strong);
    } else {
      appendAiHanziText(parent, token);
    }
  }
}

function appendAiParagraph(parent, value) {
  const paragraph = element("p", "ai-answer-paragraph");
  appendInlineAiText(paragraph, value);
  parent.append(paragraph);
}

function appendAiHeading(parent, value) {
  const heading = element("h4", "ai-answer-heading");
  appendInlineAiText(heading, value.replace(/[:：]\s*$/, ""));
  parent.append(heading);
}

function appendAiSection(parent, title, body = "") {
  const section = element("section", "ai-answer-section");
  const heading = element("h4", "ai-answer-section-title");
  appendInlineAiText(heading, title.replace(/[:：]\s*$/, ""));
  section.append(heading);
  if (body) appendAiParagraph(section, body);
  parent.append(section);
}

function aiTableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isAiTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function appendAiTable(parent, lines, start) {
  const tableLines = [];
  let index = start;
  while (
    index < lines.length &&
    lines[index].includes("|") &&
    lines[index].trim()
  ) {
    tableLines.push(lines[index]);
    index += 1;
  }
  const [headerLine, separatorLine, ...bodyLines] = tableLines;
  if (!separatorLine || !isAiTableSeparator(separatorLine)) return start;

  const tableWrap = element("div", "ai-table-wrap");
  const table = element("table", "ai-table");
  const thead = element("thead");
  const headRow = element("tr");
  for (const cellText of aiTableCells(headerLine)) {
    const cell = element("th");
    appendInlineAiText(cell, cellText);
    headRow.append(cell);
  }
  thead.append(headRow);
  table.append(thead);

  const tbody = element("tbody");
  for (const rowLine of bodyLines) {
    const row = element("tr");
    for (const cellText of aiTableCells(rowLine)) {
      const cell = element("td");
      appendInlineAiText(cell, cellText);
      row.append(cell);
    }
    tbody.append(row);
  }
  table.append(tbody);
  tableWrap.append(table);
  parent.append(tableWrap);
  return index;
}

function isAiSpecialLine(line, nextLine = "") {
  const trimmed = line.trim();
  return (
    !trimmed ||
    /^```/.test(trimmed) ||
    /^#{1,4}\s+/.test(trimmed) ||
    /^>\s?/.test(trimmed) ||
    /^\s*[-*]\s+/.test(line) ||
    /^\s*\d+[.)]\s+/.test(line) ||
    (trimmed.includes("|") && isAiTableSeparator(nextLine))
  );
}

function renderAiFormattedAnswer(content, { pending = false, plain = false } = {}) {
  const formatted = element(
    "div",
    pending ? "ai-message-text is-thinking" : "ai-message-text",
  );
  const clean = plain ? String(content || "").trim() : cleanAiContent(content);
  if (!clean) {
    formatted.append(element("p", "ai-answer-paragraph", t("aiThinking")));
    return formatted;
  }
  if (plain) {
    appendAiParagraph(formatted, clean);
    return formatted;
  }

  const lines = clean.split("\n");
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();
    if (!trimmed) {
      index += 1;
      continue;
    }

    if (/^```/.test(trimmed)) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^```/.test(lines[index].trim())) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const pre = element("pre", "ai-code-block");
      pre.append(element("code", "", codeLines.join("\n").trimEnd()));
      formatted.append(pre);
      continue;
    }

    if (trimmed.includes("|") && isAiTableSeparator(lines[index + 1] || "")) {
      const nextIndex = appendAiTable(formatted, lines, index);
      if (nextIndex !== index) {
        index = nextIndex;
        continue;
      }
    }

    const heading = trimmed.match(/^#{1,4}\s+(.+)$/);
    if (heading) {
      appendAiHeading(formatted, heading[1]);
      index += 1;
      continue;
    }

    const section = trimmed.match(/^\*\*([^*:\n]{1,56}[:：])\*\*\s*(.*)$/);
    if (section) {
      appendAiSection(formatted, section[1], section[2]);
      index += 1;
      continue;
    }

    if (/^>\s?/.test(trimmed)) {
      const quote = element("blockquote", "ai-answer-quote");
      const quoteLines = [];
      while (index < lines.length && /^>\s?/.test(lines[index].trim())) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      appendAiParagraph(quote, quoteLines.join(" "));
      formatted.append(quote);
      continue;
    }

    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const list = element(ordered ? "ol" : "ul", "ai-answer-list");
      const pattern = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*]\s+/;
      while (index < lines.length && pattern.test(lines[index])) {
        const item = element("li");
        appendInlineAiText(item, lines[index].replace(pattern, "").trim());
        list.append(item);
        index += 1;
      }
      formatted.append(list);
      continue;
    }

    if (
      trimmed.length <= 72 &&
      /[:：]$/.test(trimmed) &&
      !/^https?:\/\//.test(trimmed)
    ) {
      appendAiHeading(formatted, trimmed);
      index += 1;
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;
    while (
      index < lines.length &&
      !isAiSpecialLine(lines[index], lines[index + 1] || "")
    ) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    appendAiParagraph(formatted, paragraphLines.join(" "));
  }
  return formatted;
}

function renderAiLoading() {
  const panel = element("section", "ai-pack-state");
  panel.append(element("div", "spinner"), element("p", "", t("aiChecking")));
  dom.aiBody.replaceChildren(panel);
  dom.aiFooterStatus.textContent = t("aiChecking");
  updateAiComposer();
}

function renderAiError(code) {
  const panel = element("section", "ai-pack-state is-error");
  panel.append(
    element("h3", "", t("aiUnavailableTitle")),
    element("p", "", t(code) === code ? t("aiUnavailableBody") : t(code)),
  );
  const retry = element("button", "secondary-button", t("retry"));
  retry.type = "button";
  retry.addEventListener("click", loadAiStatus);
  panel.append(retry);
  dom.aiBody.replaceChildren(panel);
  dom.aiFooterStatus.textContent = t("aiUnavailableBody");
  updateAiComposer();
}

function renderAiPanel() {
  if (aiIsReady()) {
    renderAiChat();
  } else {
    renderAiInstaller();
  }
  updateAiComposer();
}

function renderAiInstaller() {
  const status = state.aiStatus || normalizeAiStatus(null);
  const panel = element("section", "ai-pack-state");
  const badge = element("span", "pack-status");
  const title = status.installed
    ? t("aiRuntimeMissingTitle")
    : status.state === "paused"
      ? t("aiPausedTitle")
      : status.state === "invalid"
        ? t("aiInvalidTitle")
        : t("aiMissingTitle");
  const body = status.installed
    ? t("aiRuntimeMissingBody")
    : status.state === "paused"
      ? t("aiPausedBody")
      : status.state === "invalid"
        ? t("aiInvalidBody")
        : t("aiMissingBody");
  badge.textContent = aiInstallIsActive(status)
    ? t(`aiState_${status.state}`)
    : t("aiNotReady");
  panel.append(
    element("p", "eyebrow", t("aiPackEyebrow")),
    element("h3", "", title),
    element("p", "", body),
    element("p", "ai-pack-meta", t("aiPackMeta")),
  );

  const expected = status.expectedSizeBytes || 2_497_280_256;
  if (status.downloadedBytes > 0 || aiInstallIsActive(status)) {
    const progress = element("progress", "ai-pack-progress");
    progress.max = expected;
    progress.value = Math.min(expected, status.downloadedBytes);
    progress.setAttribute("aria-label", t("aiDownloadProgress"));
    panel.append(
      progress,
      element(
        "small",
        "ai-progress-copy",
        `${formatAiBytes(status.downloadedBytes)} / ${formatAiBytes(expected)}`,
      ),
    );
  }

  const actions = element("div", "ai-pack-actions");
  if (aiInstallIsActive(status)) {
    const cancel = element("button", "secondary-button", t("aiCancelDownload"));
    cancel.type = "button";
    cancel.addEventListener("click", cancelAiInstall);
    actions.append(cancel);
  } else if (!status.installed) {
    const install = element(
      "button",
      "primary-button",
      status.state === "paused" ? t("aiResumeDownload") : t("aiInstall"),
    );
    install.type = "button";
    install.disabled = !navigator.onLine;
    install.addEventListener("click", startAiInstall);
    actions.append(install);
  }
  if (status.installed || status.state === "invalid") {
    const remove = element("button", "text-button danger-text", t("aiRemove"));
    remove.type = "button";
    remove.addEventListener("click", removeAiPack);
    actions.append(remove);
  }
  panel.append(actions, badge);
  dom.aiBody.replaceChildren(panel);
  dom.aiFooterStatus.textContent = navigator.onLine
    ? t("aiInstallNote")
    : t("aiInstallNeedsInternet");
}

async function startAiInstall() {
  if (state.aiInstallBusy || !navigator.onLine) return;
  state.aiInstallBusy = true;
  if (state.aiStatus) state.aiStatus.state = "starting";
  renderAiInstaller();
  try {
    const result = await desktopBridge.localAiInstallStart();
    state.aiStatus = normalizeAiStatus(result);
    state.aiInstallBusy = true;
    renderAiInstaller();
  } catch (error) {
    state.aiInstallBusy = false;
    renderAiError(error?.code || "local_ai_install_failed");
  }
}

async function cancelAiInstall() {
  if (!state.aiInstallBusy) return;
  try {
    const result = await desktopBridge.localAiInstallCancel();
    state.aiStatus = normalizeAiStatus(result);
    state.aiStatus.state = "paused";
    state.aiInstallBusy = false;
    renderAiInstaller();
  } catch (error) {
    renderAiError(error?.code || "local_ai_install_cancelled");
  }
}

async function removeAiPack() {
  if (!globalThis.confirm(t("aiRemoveConfirm"))) return;
  clearAiAttachments({ includeMessages: true });
  state.aiMessages = [];
  state.aiBusy = false;
  state.aiRequestId = null;
  renderAiLoading();
  try {
    const result = await desktopBridge.localAiPackRemove();
    state.aiStatus = normalizeAiStatus(result);
    state.aiInstallBusy = false;
    renderAiInstaller();
  } catch (error) {
    renderAiError(error?.code || "local_ai_remove_failed");
  }
}

function supportedAiRecorder() {
  if (typeof MediaRecorder !== "function") return null;
  for (const candidate of AI_RECORDER_TYPES) {
    try {
      if (MediaRecorder.isTypeSupported(candidate.mime)) return candidate;
    } catch {
      // Older engines can throw while probing. Keep trying known containers.
    }
  }
  return { mime: "", extension: "mp4" };
}

function newAiAttachmentId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `ai-attachment-${globalThis.crypto.randomUUID()}`;
  }
  return `ai-attachment-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function aiAttachmentKind(file) {
  const type = String(file?.type || "").toLowerCase();
  if (type.startsWith("image/")) return "image";
  if (type.startsWith("audio/")) return "audio";
  return "";
}

function aiAttachmentLimit(kind) {
  return kind === "image" ? AI_MAX_IMAGE_BYTES : AI_MAX_AUDIO_BYTES;
}

function formatAiAttachmentSize(bytes) {
  const size = Math.max(0, Number(bytes || 0));
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  if (size >= 1024) return `${Math.ceil(size / 1024)} KB`;
  return `${size} B`;
}

function aiAttachmentLabel(attachment) {
  return attachment.kind === "image" ? t("aiImageAttachment") : t("aiAudioAttachment");
}

function revokeAiAttachment(attachment) {
  const url = String(attachment?.url || "");
  if (url.startsWith("blob:")) URL.revokeObjectURL(url);
}

function clearAiAttachments({ includeMessages = false } = {}) {
  state.aiAttachments.forEach(revokeAiAttachment);
  state.aiAttachments = [];
  if (includeMessages) {
    for (const message of state.aiMessages) {
      (message.attachments || []).forEach(revokeAiAttachment);
    }
  }
  renderAiAttachments();
}

function renderAiAttachments() {
  if (!dom.aiAttachments) return;
  dom.aiAttachments.replaceChildren();
  if (!state.aiAttachments.length) {
    dom.aiAttachments.hidden = true;
    return;
  }
  dom.aiAttachments.hidden = false;
  for (const attachment of state.aiAttachments) {
    const chip = element("article", `ai-attachment-chip is-${attachment.kind}`);
    const preview = element("span", "ai-attachment-preview");
    if (attachment.kind === "image") {
      const image = document.createElement("img");
      image.src = attachment.url;
      image.alt = "";
      image.decoding = "async";
      preview.append(image);
    } else {
      preview.append(element("span", "", "AUD"));
    }
    const copy = element("span", "ai-attachment-copy");
    copy.append(
      element("b", "", attachment.name),
      element(
        "small",
        "",
        `${aiAttachmentLabel(attachment)} · ${formatAiAttachmentSize(attachment.size)}`,
      ),
    );
    const remove = element("button", "ai-attachment-remove", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", t("aiRemoveAttachment"));
    remove.addEventListener("click", () => removeAiAttachment(attachment.id));
    chip.append(preview, copy, remove);
    dom.aiAttachments.append(chip);
  }
}

function removeAiAttachment(id) {
  const attachment = state.aiAttachments.find((item) => item.id === id);
  if (attachment) revokeAiAttachment(attachment);
  state.aiAttachments = state.aiAttachments.filter((item) => item.id !== id);
  renderAiAttachments();
  updateAiComposer();
}

function addAiAttachmentFromFile(file) {
  const kind = aiAttachmentKind(file);
  if (!kind) {
    showToast(t("aiMediaUnsupported"));
    return;
  }
  if (state.aiAttachments.length >= AI_MAX_ATTACHMENTS) {
    showToast(t("aiMediaLimit", { count: AI_MAX_ATTACHMENTS }));
    return;
  }
  if (Number(file.size || 0) > aiAttachmentLimit(kind)) {
    showToast(t("aiMediaTooLarge"));
    return;
  }
  state.aiAttachments.push({
    id: newAiAttachmentId(),
    kind,
    name: String(file.name || aiAttachmentLabel({ kind })),
    size: Number(file.size || 0),
    type: String(file.type || ""),
    url: URL.createObjectURL(file),
  });
}

function addAiFiles(files) {
  const list = Array.from(files || []);
  for (const file of list) addAiAttachmentFromFile(file);
  renderAiAttachments();
  updateAiComposer();
  if (state.aiAttachments.length) {
    dom.aiFooterStatus.textContent = t("aiMediaAttached", {
      count: state.aiAttachments.length,
    });
  }
}

function appendAiMessageAttachments(parent, attachments = []) {
  if (!attachments.length) return;
  const list = element("div", "ai-message-attachments");
  for (const attachment of attachments) {
    const item = element("div", `ai-message-attachment is-${attachment.kind}`);
    if (attachment.kind === "image" && attachment.url) {
      const image = document.createElement("img");
      image.src = attachment.url;
      image.alt = "";
      image.decoding = "async";
      item.append(image);
    } else {
      item.append(element("span", "ai-message-attachment-icon", "AUD"));
    }
    const copy = element("span", "");
    copy.append(
      element("b", "", attachment.name),
      element(
        "small",
        "",
        `${aiAttachmentLabel(attachment)} · ${formatAiAttachmentSize(attachment.size)}`,
      ),
    );
    item.append(copy);
    list.append(item);
  }
  parent.append(list);
}

function cancelAiRecording() {
  clearTimeout(state.aiRecordingTimer);
  state.aiRecordingTimer = null;
  state.aiRecordDiscard = true;
  if (state.aiRecorder && state.aiRecorder.state !== "inactive") {
    try {
      state.aiRecorder.stop();
    } catch {
      // Recorder may already be closing.
    }
  }
  if (state.aiRecordStream) {
    state.aiRecordStream.getTracks().forEach((track) => track.stop());
  }
  state.aiRecording = false;
  state.aiRecorder = null;
  state.aiRecordStream = null;
  state.aiRecordStartedAt = 0;
  state.aiRecordType = null;
}

function recordedAiAttachmentName(extension) {
  const now = new Date();
  const time = [
    now.getHours(),
    now.getMinutes(),
    now.getSeconds(),
  ]
    .map((value) => String(value).padStart(2, "0"))
    .join("-");
  return `ai-voice-${time}.${extension || "webm"}`;
}

async function startAiRecording() {
  if (!aiIsReady() || state.aiBusy || state.aiRecording) return;
  if (state.aiAttachments.length >= AI_MAX_ATTACHMENTS) {
    showToast(t("aiMediaLimit", { count: AI_MAX_ATTACHMENTS }));
    return;
  }
  const recorderType = supportedAiRecorder();
  if (!recorderType || !navigator.mediaDevices?.getUserMedia) {
    showToast(t("desktop_voice_recorder_unavailable"));
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    const options = recorderType.mime ? { mimeType: recorderType.mime } : {};
    const recorder = new MediaRecorder(stream, options);
    state.aiRecording = true;
    state.aiRecorder = recorder;
    state.aiRecordStream = stream;
    state.aiRecordStartedAt = Date.now();
    state.aiRecordType = recorderType;
    state.aiRecordDiscard = false;
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) chunks.push(event.data);
    });
    recorder.addEventListener("stop", () => {
      clearTimeout(state.aiRecordingTimer);
      state.aiRecordingTimer = null;
      stream.getTracks().forEach((track) => track.stop());
      const duration = Date.now() - state.aiRecordStartedAt;
      const type = recorder.mimeType || recorderType.mime || "audio/mp4";
      const discard = state.aiRecordDiscard;
      state.aiRecording = false;
      state.aiRecorder = null;
      state.aiRecordStream = null;
      state.aiRecordStartedAt = 0;
      state.aiRecordType = null;
      state.aiRecordDiscard = false;
      if (discard) {
        updateAiComposer();
        return;
      }
      if (duration < AI_MIN_RECORDING_MS || !chunks.length) {
        showToast(t("desktop_voice_too_short"));
        updateAiComposer();
        return;
      }
      const blob = new Blob(chunks, { type });
      if (blob.size > AI_MAX_AUDIO_BYTES) {
        showToast(t("desktop_voice_audio_too_large"));
        updateAiComposer();
        return;
      }
      state.aiAttachments.push({
        id: newAiAttachmentId(),
        kind: "audio",
        name: recordedAiAttachmentName(recorderType.extension),
        size: blob.size,
        type,
        url: URL.createObjectURL(blob),
      });
      renderAiAttachments();
      updateAiComposer();
      dom.aiFooterStatus.textContent = t("aiRecordingReady");
    });
    recorder.start();
    state.aiRecordingTimer = setTimeout(() => {
      if (state.aiRecording && state.aiRecorder?.state === "recording") {
        state.aiRecorder.stop();
      }
    }, AI_MAX_RECORDING_MS);
    dom.aiFooterStatus.textContent = t("aiRecording");
    updateAiComposer();
  } catch (error) {
    cancelAiRecording();
    const code =
      error?.name === "NotAllowedError"
        ? "desktop_voice_mic_denied"
        : "desktop_voice_mic_unavailable";
    showToast(t(code));
    updateAiComposer();
  }
}

function stopAiRecording() {
  if (!state.aiRecording || !state.aiRecorder) return;
  if (state.aiRecorder.state === "recording") {
    state.aiRecorder.stop();
  }
}

function handleAiMediaBlockedSend(prompt, attachments) {
  const sentAttachments = attachments.map((attachment) => ({ ...attachment }));
  state.aiAttachments = [];
  state.aiMessages.push(
    {
      role: "user",
      content: prompt || t("aiMediaUserFallback"),
      attachments: sentAttachments,
      excludeHistory: true,
    },
    {
      role: "assistant",
      content: t("aiMediaOnlineRequired"),
      excludeHistory: true,
    },
  );
  dom.aiInput.value = "";
  renderAiAttachments();
  renderAiChat();
  updateAiComposer();
}

function renderAiChat() {
  const wrap = element("div", "ai-chat-shell");
  const screenContext = buildAiScreenContext();
  const ready = element("section", "ai-ready-card");
  ready.append(
    element("span", "ai-ready-dot"),
    element("strong", "", t("aiReadyTitle")),
    element("small", "", t("aiReadyBody")),
  );
  wrap.append(ready, renderAiContextCard(screenContext));

  if (state.aiMessages.length === 0) {
    const intro = element("section", "ai-chat-intro");
    intro.append(
      element("h3", "", t("aiWelcomeTitle")),
      element("p", "", t("aiWelcomeBody")),
    );
    wrap.append(intro);
  }

  const messages = element("div", "ai-message-list");
  messages.setAttribute("aria-live", "polite");
  for (const message of state.aiMessages) {
    const bubble = element("article", `ai-message is-${message.role}`);
    bubble.append(
      element(
        "small",
        "ai-message-author",
        message.role === "user" ? t("aiYou") : t("aiTutor"),
      ),
    );
    appendAiMessageAttachments(bubble, message.attachments);
    bubble.append(
      renderAiFormattedAnswer(message.content, {
        pending: message.pending,
        plain: message.role === "user",
      }),
    );
    messages.append(bubble);
  }
  wrap.append(messages);

  const manage = element("details", "ai-pack-manage");
  manage.append(element("summary", "", t("aiPackManage")));
  const remove = element("button", "text-button danger-text", t("aiRemove"));
  remove.type = "button";
  remove.addEventListener("click", removeAiPack);
  manage.append(
    element("p", "", t("aiPrivacyNote")),
    remove,
  );
  wrap.append(manage);
  wrap.append(renderAiHintStrip(screenContext));
  dom.aiBody.replaceChildren(wrap);
  dom.aiFooterStatus.textContent = state.aiBusy
    ? t("aiGenerating")
    : t("aiOfflineReady");
  requestAnimationFrame(() => {
    dom.aiBody.scrollTop = dom.aiBody.scrollHeight;
  });
}

function updateAiComposer() {
  const ready = aiIsReady();
  const hasText = Boolean(String(dom.aiInput.value || "").trim());
  const hasAttachments = state.aiAttachments.length > 0;
  const hasDraft = hasText || hasAttachments || state.aiRecording;
  dom.aiDrawer.classList.toggle("has-ai-draft", hasDraft);
  const inputLocked = !ready || state.aiBusy || state.aiRecording;
  dom.aiInput.disabled = inputLocked;
  dom.aiInput.placeholder = ready
    ? t("aiInputPlaceholder")
    : t("aiInputDisabledPlaceholder");
  dom.aiAttach.disabled = inputLocked;
  dom.aiEmoji.disabled = inputLocked;
  dom.aiRecord.disabled = !ready || state.aiBusy;
  dom.aiRecord.hidden = !state.aiRecording && (state.aiBusy || hasText || hasAttachments);
  dom.aiRecord.classList.toggle("is-recording", state.aiRecording);
  dom.aiRecord.setAttribute(
    "aria-label",
    state.aiRecording ? t("aiStopRecord") : t("aiRecord"),
  );
  dom.aiSend.hidden = !state.aiBusy && !hasText && !hasAttachments;
  dom.aiSend.setAttribute("aria-label", state.aiBusy ? t("aiStop") : t("aiSend"));
  dom.aiSend.classList.toggle("is-stop", state.aiBusy);
  dom.aiSend.disabled = state.aiBusy
    ? !state.aiRequestId
    : !ready || (!hasText && !hasAttachments);
  if (state.aiRecording) {
    dom.aiFooterStatus.textContent = t("aiRecording");
  } else if (hasAttachments && !state.aiBusy) {
    dom.aiFooterStatus.textContent = t("aiMediaAttached", {
      count: state.aiAttachments.length,
    });
  }
}

function newAiRequestId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `desktop-ai-${globalThis.crypto.randomUUID()}`;
  }
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  return `desktop-ai-${[...bytes].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function localAiPromptWithScreenContext(question) {
  const context = buildAiScreenContext();
  const contextText = boundedAiText(
    context.promptLines.filter(Boolean).join("\n"),
    1300,
  );
  return [
    "Use this verified HSK AI app context when it is relevant.",
    "Do not claim access to anything outside this app window.",
    "Do not reveal lesson, quiz, or practice answer keys before the learner has checked an answer.",
    contextText,
    `Learner interface language: ${getLanguage()}.`,
    "For Chinese examples, include hanzi, pinyin, and a translation.",
    "Do not include hidden reasoning, <think> tags, or chain-of-thought.",
    "Use short headings and bullet lists when comparison or steps make the answer easier to scan.",
    "Learner question:",
    boundedAiText(question, 2200),
  ].join("\n");
}

async function sendAiMessage() {
  if (state.aiBusy) {
    if (state.aiRequestId) {
      try {
        await desktopBridge.localAiChatCancel(state.aiRequestId);
        dom.aiFooterStatus.textContent = t("aiCancelling");
      } catch (error) {
        dom.aiFooterStatus.textContent = t(error?.code || "requestFailed");
      }
    }
    return;
  }
  if (!aiIsReady()) return;
  const prompt = String(dom.aiInput.value || "").trim();
  const attachments = state.aiAttachments.map((attachment) => ({ ...attachment }));
  if (!prompt && !attachments.length) return;
  if (attachments.length) {
    handleAiMediaBlockedSend(prompt, attachments);
    return;
  }
  const history = state.aiMessages
    .filter((message) => !message.pending && !message.excludeHistory)
    .slice(-12)
    .map(({ role, content }) => ({ role, content }));
  const requestId = newAiRequestId();
  state.aiMessages.push(
    { role: "user", content: prompt },
    { role: "assistant", content: "", pending: true, requestId },
  );
  state.aiBusy = true;
  state.aiRequestId = requestId;
  state.aiStreamText = "";
  dom.aiInput.value = "";
  renderAiChat();
  updateAiComposer();
  try {
    const result = await desktopBridge.localAiChat({
      requestId,
      prompt: localAiPromptWithScreenContext(prompt),
      language: getLanguage(),
      history,
      maxTokens: 384,
    });
    const pending = state.aiMessages.find(
      (message) => message.requestId === requestId,
    );
    if (pending) {
      pending.content = String(result?.text || state.aiStreamText || "").trim();
      pending.pending = false;
    }
  } catch (error) {
    const pending = state.aiMessages.find(
      (message) => message.requestId === requestId,
    );
    if (pending) {
      pending.content =
        error?.code === "local_ai_chat_cancelled"
          ? t("aiCancelled")
          : t(error?.code || "local_ai_generation_failed");
      pending.pending = false;
      pending.excludeHistory = true;
    }
  } finally {
    if (state.aiRequestId === requestId) {
      state.aiBusy = false;
      state.aiRequestId = null;
      state.aiStreamText = "";
    }
    renderAiChat();
    updateAiComposer();
    dom.aiInput.focus();
  }
}

async function bindLocalAiEvents() {
  if (state.aiListenersReady) return;
  state.aiListenersReady = true;
  const registrations = [
    ["local-ai://pack-progress", (payload) => {
      if (!payload || typeof payload !== "object") return;
      const current = state.aiStatus || normalizeAiStatus(null);
      state.aiStatus = normalizeAiStatus({ ...current, ...payload });
      state.aiInstallBusy = aiInstallIsActive(state.aiStatus);
      if (payload.state === "ready") {
        void loadAiStatus();
      } else if (state.aiOpen) {
        renderAiInstaller();
        updateAiComposer();
      }
    }],
    ["local-ai://runtime-status", (payload) => {
      if (!state.aiStatus || !payload?.state) return;
      state.aiStatus.runtimeState = String(payload.state);
      if (state.aiOpen && aiIsReady()) renderAiChat();
    }],
    ["local-ai://chat-delta", (payload) => {
      if (!payload || payload.requestId !== state.aiRequestId) return;
      state.aiStreamText += String(payload.delta || "");
      const pending = state.aiMessages.find(
        (message) => message.requestId === payload.requestId,
      );
      if (pending) pending.content = state.aiStreamText;
      if (state.aiOpen) renderAiChat();
    }],
    ["local-ai://error", (payload) => {
      if (!state.aiOpen || !payload?.error) return;
      dom.aiFooterStatus.textContent = t(String(payload.error));
    }],
  ];
  for (const [eventName, handler] of registrations) {
    try {
      state.aiUnlisten.push(await listenLocalAi(eventName, handler));
    } catch {
      // Native commands still return final state/result if event delivery fails.
    }
  }
}

async function bindDesktopUpdateEvents() {
  if (state.updateUnlisten) return;
  try {
    state.updateUnlisten = await listenDesktopUpdate(
      "desktop-update://progress",
      (payload) => {
        const progress = normalizeUpdateProgress(payload);
        if (!progress || state.updateStatus !== "installing") return;
        state.updateProgress = progress;
        renderUpdateBanner();
      },
    );
  } catch {
    // Update install still returns a final success/error when event delivery is unavailable.
  }
}

function bindEvents() {
  dom.startLink.addEventListener("click", startLink);
  dom.retryLink.addEventListener("click", () => {
    if (state.authLinkedPending) {
      resumeLinkedBootstrap();
    } else {
      startLink();
    }
  });
  dom.openTelegram.addEventListener("click", openTelegram);
  dom.copyCode.addEventListener("click", copyAuthCode);
  dom.onboardingLater.addEventListener("click", closeOnboarding);
  dom.onboardingBack.addEventListener("click", onboardingBack);
  dom.onboardingStart.addEventListener("click", () => void confirmOnboarding());
  dom.refreshMap.addEventListener("click", () =>
    loadCourseMap({ keepView: true }),
  );
  dom.updateAction.addEventListener("click", handleUpdateAction);
  dom.showToday.addEventListener("click", () => routeTo("today"));
  dom.showCourse.addEventListener("click", () => routeTo("course"));
  dom.showPractice.addEventListener("click", () => routeTo("practice"));
  dom.showVoice.addEventListener("click", () => routeTo("voice"));
  dom.showVocabulary.addEventListener("click", () => routeTo("vocabulary"));
  dom.showRating.addEventListener("click", () => routeTo("rating"));
  dom.showSubscription.addEventListener("click", () => routeTo("subscription"));
  dom.showProfile.addEventListener("click", () => routeTo("profile"));
  dom.railProfileButton.addEventListener("click", () => routeTo("profile"));
  dom.globalSearch.addEventListener("input", () => {
    state.searchQuery = String(dom.globalSearch.value || "");
    if (state.searchQuery && state.view !== "course") state.view = "course";
    if (state.view === "course") renderActiveView();
  });
  dom.railToggle.addEventListener("click", toggleRail);
  dom.railCollapse.addEventListener("click", () => setRailCollapsed(!state.railCollapsed));
  dom.railResizer.addEventListener("pointerdown", startRailResize);
  dom.notificationsButton.addEventListener("click", toggleNotifications);
  dom.closeNotifications.addEventListener("click", closeNotifications);
  dom.railScrim.addEventListener("click", closeRail);
  dom.aiLauncher.addEventListener("click", toggleAi);
  dom.closeAi.addEventListener("click", closeAi);
  dom.aiAttach.addEventListener("click", () => {
    if (!aiIsReady() || state.aiBusy || state.aiRecording) return;
    dom.aiFileInput.click();
  });
  dom.aiFileInput.addEventListener("change", () => {
    addAiFiles(dom.aiFileInput.files);
    dom.aiFileInput.value = "";
  });
  dom.aiEmoji.addEventListener("click", () => {
    dom.aiInput.focus();
    showToast(t("aiEmojiHint"));
  });
  dom.aiRecord.addEventListener("click", () => {
    if (state.aiRecording) {
      stopAiRecording();
      return;
    }
    void startAiRecording();
  });
  dom.aiInput.addEventListener("input", updateAiComposer);
  dom.aiInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      void sendAiMessage();
    }
  });
  dom.aiSend.addEventListener("click", () => void sendAiMessage());
  void bindLocalAiEvents();
  void bindDesktopUpdateEvents();
  window.addEventListener("online", updateNetworkState);
  window.addEventListener("offline", updateNetworkState);
  window.addEventListener("beforeunload", () => {
    cancelAiRecording();
    clearAiAttachments({ includeMessages: true });
    if (state.updateUnlisten) {
      try {
        state.updateUnlisten();
      } catch {
        // The window is closing; listener cleanup is best effort.
      }
      state.updateUnlisten = null;
    }
    for (const unlisten of state.aiUnlisten.splice(0)) {
      try {
        unlisten();
      } catch {
        // The window is closing; listener cleanup is best effort.
      }
    }
  });
  window.addEventListener("keydown", (event) => {
    const target = event.target;
    const isTyping =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      target?.isContentEditable;
    if (
      (event.metaKey || event.ctrlKey) &&
      !isTyping &&
      /^[1-8]$/.test(event.key) &&
      !dom.workspace.hidden &&
      !lesson.isOpen
    ) {
      const destinations = [
        "today",
        "course",
        "practice",
        "voice",
        "vocabulary",
        "rating",
        "subscription",
        "profile",
      ];
      event.preventDefault();
      routeTo(destinations[Number(event.key) - 1]);
      return;
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f") {
      if (!dom.workspace.hidden && !lesson.isOpen) {
        event.preventDefault();
        dom.globalSearch.focus();
      }
      return;
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      if (!dom.workspace.hidden) {
        event.preventDefault();
        toggleAi();
      }
      return;
    }
    if (event.key === "Tab" && lesson.isOpen) {
      if (state.aiOpen && dom.aiDrawer.contains(document.activeElement)) {
        trapFocusWithin(dom.aiDrawer, event);
        return;
      }
      lesson.trapFocus(event);
      return;
    }
    if (event.key !== "Escape") {
      return;
    }
    // Escape behaves like "Keyinroq": the goal stays unset, so onboarding
    // comes back on the next start instead of being lost silently.
    if (state.referralModalOpen) {
      closeReferralModal();
    } else if (state.onboardingOpen) {
      closeOnboarding();
    } else if (state.aiOpen) {
      closeAi();
    } else if (lesson.isOpen) {
      lesson.close();
    } else if (state.railOpen) {
      closeRail();
    }
  });
}

async function boot() {
  setUiLanguage(readSavedLanguage());
  hydrateStaticMascots();
  applyStaticText();
  bindEvents();
  restoreRailWidth();
  restoreRailCollapsed();
  restoreReduceMotion();
  restoreNotificationState();
  updateNetworkState();
  showOnly("boot");

  try {
    const appInfo = await desktopBridge.appInfo();
    // The version is no longer in the toolbar; the profile screen shows it.
    state.appVersion = String(appInfo?.version || "");
    if (appInfo?.platform) {
      const platform = String(appInfo.platform).toLowerCase();
      document.documentElement.dataset.os = platform;
      dom.aiShortcut.textContent = platform === "windows" ? "Ctrl+K" : "⌘K";
      // The search hint was hard-coded, so Windows showed the macOS glyph.
      dom.searchShortcut.textContent = platform === "windows" ? "Ctrl+F" : "⌘F";
    }
    void checkForUpdates();

    const auth = await desktopBridge.authStatus();
    if (auth?.linked) {
      const bootstrap = auth.bootstrap || (await desktopBridge.bootstrap());
      await enterWorkspace(bootstrap);
    } else {
      showAuth();
    }
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    const retry = element("button", "primary-button", t("retry"));
    retry.type = "button";
    retry.addEventListener("click", () => globalThis.location.reload());
    dom.boot.replaceChildren(
      element("p", "form-error", errorMessage(error)),
      retry,
    );
  }
}

boot();
