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
  railXp: $("#rail-xp"),
  railStreak: $("#rail-streak"),
  railDaysLabel: $("#rail-days-label"),
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
  aiInput: $("#ai-input"),
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
  aiBusy: false,
  aiInstallBusy: false,
  aiRequestId: null,
  aiStreamText: "",
  aiListenersReady: false,
  aiUnlisten: [],
  reduceMotion: false,
  referral: null,
  referralError: "",
  goal: null,
  onboardingOpen: false,
  onboardingStep: 0,
  onboardingChoice: "",
  onboardingPreviousFocus: null,
  railCollapsed: false,
  railWidth: 0,
  notificationsOpen: false,
  ratingRequest: 0,
  ratingBoard: null,
  ratingError: "",
  updateStatus: "idle",
  updateInfo: null,
  updateErrorStage: "check",
  updateShowChecking: false,
  updateProgress: null,
  updateAutoTimer: null,
  updateUnlisten: null,
  toastTimer: null,
};

const AUTO_UPDATE_DELAY_MS = 6_000;
const AUTO_UPDATE_RETRY_MS = 15_000;

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
});

const vocabulary = new DesktopVocabularyController({
  host: null,
  bridge: desktopBridge,
  t,
  language: getLanguage(),
  onToast: showToast,
  speak: (text, button) => void speakChinese(text, button),
  onAskAi: (prompt) => openAiWithPrompt(prompt),
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
  dom.railDaysLabel.textContent = t("days");
  dom.refreshMap.setAttribute("aria-label", t("refresh"));
  dom.aiTitle.textContent = t("aiTitle");
  dom.aiSubtitle.textContent = t("aiSubtitle");
  dom.aiLauncher.setAttribute("aria-label", t("openAi"));
  dom.closeAi.setAttribute("aria-label", t("closeAi"));
  dom.closeLesson.setAttribute("aria-label", t("lessonClose"));
  updateAiComposer();
  dom.globalSearch.placeholder = t("searchLessons");
  dom.offlinePill.textContent = t("offline");
  subscription.setLanguage(getLanguage());
  updateRailToggleLabel();
  renderUpdateBanner();
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
    if (state.updateStatus === "available") scheduleAutomaticUpdate();
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

function scheduleAutomaticUpdate(delay = AUTO_UPDATE_DELAY_MS) {
  clearTimeout(state.updateAutoTimer);
  if (state.updateStatus !== "available") return;
  state.updateAutoTimer = setTimeout(() => {
    state.updateAutoTimer = null;
    void installUpdate({ automatic: true });
  }, delay);
}

async function installUpdate({ automatic = false } = {}) {
  if (state.updateStatus !== "available" && !(
    state.updateStatus === "error" &&
    state.updateErrorStage === "install"
  )) {
    return;
  }
  if (updateActivityInProgress()) {
    if (automatic) scheduleAutomaticUpdate(AUTO_UPDATE_RETRY_MS);
    else showToast(t("updateLessonActive"));
    return;
  }

  clearTimeout(state.updateAutoTimer);
  state.updateAutoTimer = null;
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
  state.aiMessages = [];
  state.aiBusy = false;
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
  closeAi();
  resetAiSession();
  voice.dispose();
  practice.dispose();
  vocabulary.dispose();
  closeRail();
  state.bootstrap = null;
  state.map = null;
  state.ratingBoard = null;
  state.ratingError = "";
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
  dom.subscriptionBadge.textContent = user.is_paid ? t("active") : "PLUS";
  dom.railXp.textContent = String(Number(progress.xp || 0));
  dom.railStreak.textContent = String(Number(progress.streak || 0));
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

/**
 * Only real, already-known items appear here. There is no notification feed on
 * the server, and inventing one would put fake data in front of the learner.
 */
function notificationItems() {
  const items = [];
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
  if (streak > 0 && !activeToday) {
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
    const mascotImage = element("img");
    mascotImage.src = "./assets/hsk-ai-avatar.webp";
    mascotImage.alt = "";
    mascot.append(
      element("figcaption", "mascot-note", t("mascotReady")),
      mascotImage,
    );
    resume.append(copy, mascot);
    main.append(resume);
  } else {
    const empty = element("section", "empty-state card-panel card cardPad");
    empty.append(element("p", "", t("courseEmpty")));
    main.append(empty);
  }

  const quickGrid = element("section", "twoCols today-quick-grid");
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

  const aiCard = element("article", "card cardPad today-quick-card today-ai-quick");
  const aiHead = element("div", "sectionTitle");
  aiHead.append(
    element("h3", "", t("todayAiTitle")),
    element("span", "tag", level),
  );
  aiCard.append(
    aiHead,
    element("p", "muted", t("todayAiBody")),
  );
  const aiForm = element("form", "quickInput today-ai-form");
  const aiInput = element("input");
  aiInput.type = "text";
  aiInput.maxLength = 1000;
  aiInput.placeholder = t("todayAiPlaceholder");
  aiInput.setAttribute("aria-label", t("todayAiPlaceholder"));
  const aiAction = element("button", "btn primary-button", "↑");
  aiAction.type = "submit";
  aiAction.setAttribute("aria-label", t("openAi"));
  aiForm.append(aiInput, aiAction);
  aiForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = String(aiInput.value || "").trim();
    if (prompt) dom.aiInput.value = prompt;
    openAi();
    updateAiComposer();
    requestAnimationFrame(() => dom.aiInput.focus());
  });
  const chips = element("div", "chips");
  [
    ["todayAiChipGrammar", "先…再…"],
    ["todayAiChipExamples", String(current?.zh || "")],
    ["todayAiChipMistakes", ""],
  ].forEach(([labelKey, seed]) => {
    const chip = element("button", "promptChip", t(labelKey));
    chip.type = "button";
    chip.addEventListener("click", () => {
      aiInput.value = [t(labelKey), seed].filter(Boolean).join(": ");
      aiInput.focus();
    });
    chips.append(chip);
  });
  aiCard.append(aiForm, chips);

  quickGrid.append(reviewCard, aiCard);
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
    unitLessons.forEach((item) => trail.append(renderLessonNode(item)));
    card.append(head, trail);
    units.append(card);
  });

  if (!renderedLessons) {
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("searchEmpty")));
    units.append(empty);
  }

  const aside = element("aside", "courseAside course-aside");
  const summary = element("article", "card courseSummary card-panel");
  const pandaWrap = element("div", "coursePandaWrap");
  const panda = document.createElement("img");
  panda.className = "coursePanda";
  panda.src = "./assets/hsk-ai-avatar.webp";
  panda.alt = "";
  panda.setAttribute("aria-hidden", "true");
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
}

function renderLessonNode(item) {
  const status = String(item?.status || "locked");
  const accessible = lessonAccessible(item);
  const row = element(
    "div",
    `pathNodeRow${item?.checkpoint ? " milestone" : ""} lesson-node-row`,
  );
  const button = element(
    "button",
    `pathNode lesson-node ${status} is-${status}${item?.checkpoint ? " is-checkpoint" : ""}`,
  );
  button.type = "button";
  button.dataset.status = status;
  button.append(
    element("span", "nodeNo", String(item.n || "")),
    element("span", "nodeIcon", status === "done" ? "✓" : accessible ? "▶" : "⌁"),
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
  const panda = document.createElement("img");
  panda.className = "pandaMini";
  panda.src = "./assets/hsk-ai-avatar.webp";
  panda.alt = "";
  panda.setAttribute("aria-hidden", "true");
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
    state.ratingError = t("leaderboardUnavailable");
    renderRatingContent(null);
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

/**
 * The demo's notification card. The server stores a single `notify.enabled`
 * flag and exposes no desktop command for it, so every row here would be
 * invented — the card is rendered in full and veiled as one.
 */
function renderNotificationsCard() {
  const card = element("article", "profile-settings card-panel");
  card.append(element("h3", "", t("notificationsTitle")));
  card.append(
    settingRow(
      t("notifyReminderTime"),
      t("notifyReminderTimeBody"),
      timeControl("09:00"),
    ),
    settingRow(
      t("notifyQuietHours"),
      "22:00 — 08:00",
      toggleButton(true, () => {}),
    ),
    settingRow(
      t("notifyFrequency"),
      t("notifyFrequencyBody"),
      selectControl(
        [
          { value: "normal", label: t("notifyFrequencyNormal") },
          { value: "low", label: t("notifyFrequencyLow") },
        ],
        "normal",
      ),
    ),
    settingRow(
      t("notifyTone"),
      t("notifyToneBody"),
      selectControl(
        [
          { value: "calm", label: t("notifyToneCalm") },
          { value: "direct", label: t("notifyToneDirect") },
        ],
        "calm",
      ),
    ),
    settingRow(
      t("notifyStreakReminder"),
      t("notifyStreakReminderBody"),
      toggleButton(true, () => {}),
    ),
  );
  return soonBlock(card);
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

/**
 * The demo's morphing invite button: one pill that opens a four-slot tray.
 * Copy is wired to the real referral link. Telegram, WhatsApp and QR have no
 * capability behind them yet, so each keeps its slot behind a "coming soon"
 * veil rather than being dropped or faked.
 */
function inviteMorph(link) {
  const morph = element("div", "invite-morph");
  const main = element("button", "invite-main", t("inviteAddFriend"));
  main.type = "button";
  main.addEventListener("click", () => {
    morph.classList.add("is-open");
    morph.querySelector(".invite-action")?.focus();
  });

  const tray = element("div", "invite-tray");
  const copy = element("button", "invite-action", "⌘C");
  copy.type = "button";
  copy.setAttribute("aria-label", t("copy"));
  copy.disabled = !link;
  copy.addEventListener("click", () => {
    void navigator.clipboard
      ?.writeText(String(link || ""))
      .then(() => {
        copy.classList.add("is-sent");
        showToast(t("inviteCopied"));
      })
      .catch(() => showToast(t("inviteCopyFailed")));
  });
  const share = (label, aria) => {
    const button = element("button", "invite-action", label);
    button.type = "button";
    button.setAttribute("aria-label", aria);
    return soonBlock(button);
  };
  tray.append(
    share("TG", t("inviteShareTelegram")),
    share("WA", t("inviteShareWhatsapp")),
    copy,
    share("QR", t("inviteShareQr")),
  );

  morph.append(main, tray);
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

  const referral = state.referral;
  if (!referral) {
    card.append(
      element("p", "muted small", state.referralError || t("inviteLoading")),
    );
    return card;
  }

  card.append(inviteMorph(referral.link));

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
  const avatar = element("div", "profile-initials", userInitials(user.name));
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
  const panda = document.createElement("img");
  panda.className = "profile-panda";
  panda.src = "./assets/hsk-ai-avatar.webp";
  panda.alt = "";
  panda.setAttribute("aria-hidden", "true");
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

function openAi() {
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
  dom.closeAi.focus();
}

function openAiWithPrompt(prompt = "") {
  const value = String(prompt || "").trim();
  if (value) dom.aiInput.value = value;
  openAi();
  updateAiComposer();
}

function closeAi() {
  const shouldRestoreFocus = state.aiOpen;
  state.aiOpen = false;
  dom.aiDrawer.classList.remove("is-open");
  dom.aiDrawer.setAttribute("aria-hidden", "true");
  dom.aiLauncher.setAttribute("aria-expanded", "false");
  if (shouldRestoreFocus) {
    const target = state.aiPreviousFocus?.isConnected
      ? state.aiPreviousFocus
      : dom.aiLauncher;
    target.focus();
  }
  state.aiPreviousFocus = null;
}

function toggleAi() {
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

function renderAiChat() {
  const wrap = element("div", "ai-chat-shell");
  const ready = element("section", "ai-ready-card");
  ready.append(
    element("span", "ai-ready-dot"),
    element("strong", "", t("aiReadyTitle")),
    element("small", "", t("aiReadyBody")),
  );
  wrap.append(ready);

  if (state.aiMessages.length === 0) {
    const intro = element("section", "ai-chat-intro");
    intro.append(
      element("h3", "", t("aiWelcomeTitle")),
      element("p", "", t("aiWelcomeBody")),
    );
    const suggestions = element("div", "ai-suggestions");
    ["aiSuggestionExplain", "aiSuggestionExamples", "aiSuggestionQuiz"].forEach(
      (key) => {
        const button = element("button", "ai-suggestion", t(key));
        button.type = "button";
        button.addEventListener("click", () => {
          dom.aiInput.value = t(`${key}Prompt`);
          updateAiComposer();
          dom.aiInput.focus();
        });
        suggestions.append(button);
      },
    );
    intro.append(suggestions);
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
      element(
        "p",
        message.pending ? "ai-message-text is-thinking" : "ai-message-text",
        message.content || t("aiThinking"),
      ),
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
  dom.aiInput.disabled = !ready || state.aiBusy;
  dom.aiInput.placeholder = ready
    ? t("aiInputPlaceholder")
    : t("aiInputDisabledPlaceholder");
  dom.aiSend.textContent = state.aiBusy ? t("aiStop") : t("aiSend");
  dom.aiSend.classList.toggle("is-stop", state.aiBusy);
  dom.aiSend.disabled = state.aiBusy
    ? !state.aiRequestId
    : !ready || !String(dom.aiInput.value || "").trim();
}

function newAiRequestId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `desktop-ai-${globalThis.crypto.randomUUID()}`;
  }
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  return `desktop-ai-${[...bytes].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function localAiPromptWithLessonContext(question) {
  const bounded = (value, limit = 240) =>
    [...String(value || "").trim()].slice(0, limit).join("");
  const current = currentLesson();
  const level = bounded(state.map?.label || levelLabel(state.map?.level), 64);
  const context = current
    ? [
        `Current course: ${level}`,
        `Current lesson: ${Number(current.n)}.`,
        `Chinese: ${bounded(current.zh)}`,
        `Pinyin: ${bounded(current.py)}`,
        `Translation: ${bounded(pick(current.tr))}`,
      ].join("\n")
    : `Current course: ${level}`;
  return [
    "Use this verified lesson context when it is relevant.",
    context,
    `Learner interface language: ${getLanguage()}.`,
    "For Chinese examples, include hanzi, pinyin, and a translation.",
    "Learner question:",
    bounded(question, 2800),
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
  if (!prompt) return;
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
      prompt: localAiPromptWithLessonContext(prompt),
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
    clearTimeout(state.updateAutoTimer);
    state.updateAutoTimer = null;
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
      if (!dom.workspace.hidden && !lesson.isOpen) {
        event.preventDefault();
        toggleAi();
      }
      return;
    }
    if (event.key === "Tab" && lesson.isOpen) {
      lesson.trapFocus(event);
      return;
    }
    if (event.key !== "Escape") {
      return;
    }
    // Escape behaves like "Keyinroq": the goal stays unset, so onboarding
    // comes back on the next start instead of being lost silently.
    if (state.onboardingOpen) {
      closeOnboarding();
    } else if (lesson.isOpen) {
      lesson.close();
    } else if (state.aiOpen) {
      closeAi();
    } else if (state.railOpen) {
      closeRail();
    }
  });
}

async function boot() {
  setUiLanguage(readSavedLanguage());
  applyStaticText();
  bindEvents();
  restoreRailWidth();
  restoreRailCollapsed();
  restoreReduceMotion();
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
