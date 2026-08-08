import { desktopBridge, isSessionError } from "./bridge.js";
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
  appVersion: $("#app-version"),
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
  headerProfile: $("#header-profile"),
  railProfileButton: $("#rail-profile-button"),
  refreshMap: $("#refresh-map"),
  updateBanner: $("#update-banner"),
  updateStatus: $("#update-status"),
  updateTitle: $("#update-title"),
  updateMessage: $("#update-message"),
  updateNotes: $("#update-notes"),
  updateAction: $("#update-action"),
  aiLauncher: $("#ai-launcher"),
  aiDrawer: $("#ai-drawer"),
  closeAi: $("#close-ai"),
  aiTitle: $("#ai-title"),
  aiSubtitle: $("#ai-subtitle"),
  aiBody: $("#ai-body"),
  aiInput: $("#ai-input"),
  aiSend: $("#ai-send"),
  aiShortcut: $("#ai-shortcut"),
  toast: $("#toast"),
  closeLesson: $("#close-lesson"),
};

const state = {
  bootstrap: null,
  map: null,
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
  vocabularyRequest: 0,
  vocabularyCache: new Map(),
  vocabularySelected: null,
  updateStatus: "idle",
  updateInfo: null,
  updateErrorStage: "check",
  updateShowChecking: false,
  toastTimer: null,
};

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
  dom.headerProfile.setAttribute("aria-label", t("openProfile"));
  dom.aiTitle.textContent = t("aiTitle");
  dom.aiSubtitle.textContent = t("aiSubtitle");
  dom.aiLauncher.setAttribute("aria-label", t("openAi"));
  dom.closeAi.setAttribute("aria-label", t("closeAi"));
  dom.closeLesson.setAttribute("aria-label", t("lessonClose"));
  dom.aiInput.placeholder = t("aiInputPlaceholder");
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

async function installUpdate() {
  if (state.updateStatus !== "available" && !(
    state.updateStatus === "error" &&
    state.updateErrorStage === "install"
  )) {
    return;
  }
  if (lesson.isOpen) {
    showToast(t("updateLessonActive"));
    return;
  }

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
  installUpdate();
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

function showAuth({ expired = false } = {}) {
  if (lesson.isOpen) {
    lesson.close();
  }
  closeAi();
  closeRail();
  state.bootstrap = null;
  state.map = null;
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
}

async function loadCourseMap({ keepView = false } = {}) {
  if (!keepView) {
    state.view = "today";
  }
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

  if (state.view === "today") renderToday();
  else if (state.view === "course") renderCourseHome();
  else if (state.view === "practice") renderPractice();
  else if (state.view === "voice") renderVoice();
  else if (state.view === "vocabulary") void renderVocabulary();
  else if (state.view === "rating") renderRating();
  else if (state.view === "subscription") renderSubscription();
  else renderProfile();
}

function viewHeading(title, subtitle, tag = "") {
  const heading = element("header", "view-heading");
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

function routeTo(view) {
  state.view = view;
  if (view !== "vocabulary") {
    state.vocabularySelected = null;
  }
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

function renderToday() {
  const map = state.map;
  if (!map) return;
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);
  const current = currentLesson();
  const percent = progressPercent(completed, lessons.length);
  const level = String(map.label || levelLabel(map.level));

  dom.contentTitle.textContent = t("today");
  dom.contentSubtitle.textContent = formattedToday(progress);
  dom.content.replaceChildren(
    viewHeading(t("todayTitle"), formattedToday(progress), level),
  );

  const grid = element("div", "today-grid");
  const main = element("div", "today-main");
  const side = element("aside", "today-side");

  if (current) {
    const glyph =
      Array.from(String(current.zh || "课").replace(/[·\s]+/g, ""))[0] || "课";
    const resume = element("section", "resume-card today-lesson-hero");
    resume.dataset.watermark = glyph;
    const copy = element("div", "resume-copy");
    copy.append(
      element("p", "eyebrow", t("nextStep")),
      element("h3", "", t("lessonNumber", { number: current.n })),
      element("p", "resume-chinese", String(current.zh || glyph)),
      element("p", "resume-pinyin", String(current.py || "")),
      element("p", "resume-translation", pick(current.tr)),
    );
    const lessonMeta = element("div", "lesson-meta-list");
    lessonMeta.append(
      element("span", "lesson-meta-chip", level),
      element(
        "span",
        "lesson-meta-chip",
        current.checkpoint ? t("checkpoint") : t("learningPart"),
      ),
    );
    if (Number(current.part_count || 0) > 1) {
      lessonMeta.append(
        element(
          "span",
          "lesson-meta-chip",
          t("partProgress", {
            part: Number(current.part || 1),
            total: Number(current.part_count),
          }),
        ),
      );
    }
    copy.append(lessonMeta);

    const progressRow = element("div", "resume-progress");
    progressRow.append(
      element("span", "", t("courseProgress")),
      element("strong", "", `${percent}%`),
    );
    const track = element("div", "summary-progress");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    const fill = element("span", "progress-fill");
    track.append(fill);
    setProgress(fill, completed, lessons.length);
    progressRow.append(track);
    copy.append(progressRow);

    const actions = element("div", "hero-actions");
    const action = element(
      "button",
      "primary-button",
      current.status === "done" ? t("startLesson") : t("continueLesson"),
    );
    action.type = "button";
    action.addEventListener("click", () => openLesson(Number(current.n)));
    const practice = element("button", "secondary-button", t("openPractice"));
    practice.type = "button";
    practice.addEventListener("click", () => routeTo("practice"));
    actions.append(action, practice);
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
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("courseEmpty")));
    main.append(empty);
  }

  const stats = element("section", "dashboard-stats");
  [
    ["星", t("xpTotal"), Number(progress.xp || 0)],
    ["火", t("streakDays"), Number(progress.streak || 0)],
    ["周", t("weeklyXp"), Number(progress.weekly_xp || 0)],
    ["课", t("completedLessons"), completed],
  ].forEach(([glyph, label, value]) => {
    const card = element("article", "dashboard-stat");
    card.append(
      element("span", "stat-glyph", glyph),
      element("small", "", label),
      element("strong", "", value),
    );
    stats.append(card);
  });
  main.append(stats);

  const activityCard = element("section", "activity-card card-panel");
  const activityHead = element("div", "card-heading-row");
  activityHead.append(
    element("div", "", ""),
    element(
      "strong",
      "activity-count",
      t("activeDays", {
        count: weekSnapshot(progress).filter((day) => day.active).length,
      }),
    ),
  );
  activityHead.firstElementChild.append(
    element("p", "eyebrow", t("weeklyActivity")),
    element("h3", "", t("keepRhythm")),
  );
  activityCard.append(activityHead, weekActivity(progress));
  main.append(activityCard);

  const progressCard = element("section", "today-progress-card card-panel");
  progressCard.append(
    element("p", "eyebrow", t("courseProgress")),
    element("h3", "", level),
  );
  const ring = element("div", "progress-ring");
  ring.dataset.progress = String(Math.round(percent / 5));
  ring.setAttribute("role", "progressbar");
  ring.setAttribute("aria-valuemin", "0");
  ring.setAttribute("aria-valuemax", "100");
  ring.setAttribute("aria-valuenow", String(percent));
  const ringCopy = element("div");
  ringCopy.append(
    element("strong", "", `${percent}%`),
    element("small", "", t("completed")),
  );
  ring.append(ringCopy);
  progressCard.append(
    ring,
    element("p", "muted", t("lessons", { done: completed, total: lessons.length })),
  );

  const todayXpCard = element("section", "today-xp-card card-panel");
  todayXpCard.append(
    element("p", "eyebrow", t("todayResult")),
    element("strong", "today-xp-value", `+${Number(progress.daily_xp || 0)} XP`),
    element("p", "muted", t("todayXpDescription")),
  );

  const planCard = element("section", "today-plan-card card-panel");
  planCard.append(
    element("p", "eyebrow", t("accountAccess")),
    element("h3", "", map.user?.is_paid ? t("paidPlan") : t("freePlan")),
    element(
      "p",
      "muted",
      map.user?.is_paid ? t("paidAccessDescription") : t("freeAccessDescription"),
    ),
  );
  const planAction = element("button", "secondary-button", t("manageSubscription"));
  planAction.type = "button";
  planAction.addEventListener("click", () => routeTo("subscription"));
  planCard.append(planAction);
  side.append(progressCard, todayXpCard, planCard);
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
  const layout = element("div", "course-layout");
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
      `course-unit-card${hasCurrent ? " is-current-unit" : ""}`,
    );
    const head = element("header", "course-unit-head");
    const copy = element("div");
    copy.append(
      element("h3", "", pick(unit.title, t("unit", { number: unitNumber }))),
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
      element("small", "", hasCurrent ? t("currentUnit") : t("unit" , { number: unitNumber })),
    );
    head.append(element("span", "course-unit-number", unitNumber), copy, unitProgress);
    const unitTrack = element("div", "summary-progress unit-progress-track");
    unitTrack.setAttribute("role", "progressbar");
    unitTrack.setAttribute("aria-valuemin", "0");
    unitTrack.setAttribute("aria-valuemax", "100");
    const unitFill = element("span", "progress-fill");
    unitTrack.append(unitFill);
    setProgress(unitFill, unitDone, allUnitLessons.length);
    const trail = element("div", "lesson-trail");
    unitLessons.forEach((item) => trail.append(renderLessonNode(item)));
    card.append(head, unitTrack, trail);
    units.append(card);
  });

  if (!renderedLessons) {
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("searchEmpty")));
    units.append(empty);
  }

  const aside = element("aside", "course-aside card-panel");
  aside.append(
    element("p", "eyebrow", t("courseProgress")),
    element("h3", "", level),
    element("div", "course-percent", `${percent}%`),
    element("p", "muted", t("lessons", { done: completed, total: lessons.length })),
    weekActivity(progress, true),
  );
  [
    [t("xpTotal"), Number(progress.xp || 0)],
    [t("streakDays"), Number(progress.streak || 0)],
    [t("league"), String(progress.league || t("notAvailable"))],
    [t("accountAccess"), map.user?.is_paid ? t("paidPlan") : t("freePlan")],
  ].forEach(([label, value]) => {
    const row = element("div", "course-aside-stat");
    row.append(element("span", "", label), element("b", "", value));
    aside.append(row);
  });
  if (!map.user?.is_paid) {
    const action = element("button", "primary-button", t("unlockCourse"));
    action.type = "button";
    action.addEventListener("click", () => routeTo("subscription"));
    aside.append(action);
  }
  layout.append(units, aside);
  dom.content.append(layout);
}

function renderLessonNode(item) {
  const status = String(item?.status || "locked");
  const accessible = lessonAccessible(item);
  const button = element(
    "button",
    `lesson-node is-${status}${item?.checkpoint ? " is-checkpoint" : ""}`,
  );
  button.type = "button";
  button.dataset.status = status;
  const marker = element("span", "lesson-node-orb");
  marker.append(
    element(
      "span",
      "lesson-node-mark",
      status === "done" ? "✓" : accessible ? "▶" : "—",
    ),
  );
  const copy = element("span", "lesson-node-copy");
  const heading = element("span", "lesson-node-heading");
  heading.append(
    element("strong", "", t("lessonNumber", { number: item.n })),
    item?.checkpoint
      ? element("em", "checkpoint-badge", t("checkpoint"))
      : element("span"),
  );
  copy.append(
    heading,
    element("span", "lesson-node-zh", String(item.zh || "课")),
    element("span", "lesson-node-pinyin", String(item.py || "")),
    element("small", "lesson-node-translation", pick(item.tr)),
  );
  if (status === "current") {
    copy.append(element("span", "current-location", t("youAreHere")));
  }
  button.append(marker, copy);
  if (accessible) {
    button.addEventListener("click", () => openLesson(Number(item.n)));
  } else if (item.preview_half || item.locked_premium) {
    button.classList.add("is-locked");
    button.addEventListener("click", () => routeTo("subscription"));
  } else {
    button.classList.add("is-locked");
    button.disabled = true;
  }
  return button;
}

function practiceCard({ glyph, title, description, lessonItem, actionLabel, onAction }) {
  const card = element("article", "practice-card card-panel");
  card.append(
    element("span", "practice-glyph", glyph),
    element("h3", "", title),
    element("p", "muted", description),
  );
  if (lessonItem) {
    const sample = element("div", "practice-sample");
    sample.append(
      element("strong", "hanzi", String(lessonItem.zh || "课")),
      element("span", "pinyin", String(lessonItem.py || "")),
      element("small", "translation", pick(lessonItem.tr)),
    );
    card.append(sample);
  }
  const action = element("button", "secondary-button", actionLabel);
  action.type = "button";
  action.disabled = typeof onAction !== "function";
  if (typeof onAction === "function") {
    action.addEventListener("click", onAction);
  }
  card.append(action);
  return card;
}

function renderPractice() {
  const map = state.map;
  if (!map) return;
  const current = currentLesson();
  const completed = [...allLessons()]
    .reverse()
    .find((item) => item.status === "done" && lessonAccessible(item));

  dom.contentTitle.textContent = t("practice");
  dom.contentSubtitle.textContent = t("practiceSubtitle");
  dom.content.replaceChildren(
    viewHeading(
      t("practiceTitle"),
      t("practiceSubtitle"),
      String(map.label || levelLabel(map.level)),
    ),
  );

  const intro = element("section", "practice-intro card-panel");
  const introCopy = element("div");
  introCopy.append(
    element("p", "eyebrow", t("realCoursePractice")),
    element("h3", "", t("practiceIntroTitle")),
    element("p", "muted", t("practiceIntroBody")),
  );
  const panda = element("img");
  panda.src = "./assets/hsk-ai-avatar.webp";
  panda.alt = "";
  intro.append(introCopy, panda);

  const cards = element("section", "practice-grid");
  cards.append(
    practiceCard({
      glyph: "练",
      title: t("continueCurrentPractice"),
      description: t("continueCurrentPracticeBody"),
      lessonItem: current,
      actionLabel: current ? t("continueLesson") : t("notAvailable"),
      onAction: current ? () => openLesson(Number(current.n)) : null,
    }),
    practiceCard({
      glyph: "复",
      title: t("repeatCompleted"),
      description: t("repeatCompletedBody"),
      lessonItem: completed,
      actionLabel: completed ? t("repeatLesson") : t("notAvailable"),
      onAction: completed ? () => openLesson(Number(completed.n)) : null,
    }),
    practiceCard({
      glyph: "听",
      title: t("pronunciationPractice"),
      description: t("pronunciationPracticeBody"),
      lessonItem: current,
      actionLabel: current ? t("openLesson") : t("notAvailable"),
      onAction: current ? () => openLesson(Number(current.n)) : null,
    }),
    practiceCard({
      glyph: "路",
      title: t("chooseAnotherLesson"),
      description: t("chooseAnotherLessonBody"),
      lessonItem: null,
      actionLabel: t("openCourseMap"),
      onAction: () => routeTo("course"),
    }),
  );
  dom.content.append(intro, cards);
}

function renderVoice() {
  const map = state.map;
  if (!map) return;
  const current = currentLesson();
  dom.contentTitle.textContent = t("voice");
  dom.contentSubtitle.textContent = t("voiceSubtitle");
  dom.content.replaceChildren(
    viewHeading(
      t("voiceTitle"),
      t("voiceSubtitle"),
      t("localAi"),
    ),
  );

  const shell = element("section", "voice-shell card-panel");
  const stage = element("div", "voice-stage");
  const avatarWrap = element("div", "voice-avatar-wrap");
  const avatar = element("img");
  avatar.src = "./assets/hsk-ai-avatar.webp";
  avatar.alt = "";
  avatarWrap.append(avatar, element("span", "voice-status-dot"));
  const stageCopy = element("div", "voice-stage-copy");
  stageCopy.append(
    element("p", "eyebrow", t("textRoleplay")),
    element("h3", "", t("voiceReadyTitle")),
    element("p", "muted", t("voiceReadyBody")),
  );
  if (current) {
    const context = element("div", "voice-context");
    context.append(
      element("small", "", t("lessonContext")),
      element("strong", "hanzi", String(current.zh || "课")),
      element("span", "pinyin", String(current.py || "")),
      element("p", "translation", pick(current.tr)),
    );
    stageCopy.append(context);
  }
  const actions = element("div", "voice-actions");
  const textAction = element("button", "primary-button", t("openTextRoleplay"));
  textAction.type = "button";
  textAction.addEventListener("click", openAi);
  const lessonAction = element("button", "secondary-button", t("practiceInLesson"));
  lessonAction.type = "button";
  lessonAction.disabled = !current;
  if (current) {
    lessonAction.addEventListener("click", () => openLesson(Number(current.n)));
  }
  actions.append(textAction, lessonAction);
  stageCopy.append(actions);
  stage.append(avatarWrap, stageCopy);

  const microphone = element("aside", "voice-microphone-state");
  const micButton = element("button", "voice-mic-button", "声");
  micButton.type = "button";
  micButton.disabled = true;
  micButton.setAttribute("aria-describedby", "voice-mic-note");
  const micCopy = element("div");
  micCopy.append(
    element("h3", "", t("microphoneComingTitle")),
    element("p", "muted", t("microphoneComingBody")),
  );
  micCopy.lastElementChild.id = "voice-mic-note";
  microphone.append(micButton, micCopy);
  shell.append(stage, microphone);
  dom.content.append(shell);
}

function vocabularyExamples(lessonPayload) {
  const examples = [];
  const add = (entry, translationKey = "translation") => {
    if (!entry || typeof entry !== "object") return;
    const zh = String(entry.zh || entry.phrase || "").trim();
    const pinyin = String(entry.pinyin || "").trim();
    const translation = pick(entry[translationKey] || entry.text);
    if (zh && pinyin && translation) {
      examples.push({ zh, pinyin, translation });
    }
  };

  (Array.isArray(lessonPayload?.grammar) ? lessonPayload.grammar : []).forEach(
    (grammar) =>
      (Array.isArray(grammar?.examples) ? grammar.examples : []).forEach((entry) =>
        add(entry),
      ),
  );
  (Array.isArray(lessonPayload?.dialogues) ? lessonPayload.dialogues : []).forEach(
    (dialogue) =>
      (Array.isArray(dialogue?.dialogue) ? dialogue.dialogue : []).forEach((line) =>
        add(line, "text"),
      ),
  );
  (Array.isArray(lessonPayload?.sections) ? lessonPayload.sections : []).forEach(
    (section) =>
      (Array.isArray(section?.cards) ? section.cards : []).forEach((card) => {
        if (card?.type === "pronunciation") add(card);
        if (card?.g && Array.isArray(card.g.examples)) {
          card.g.examples.forEach((entry) => add(entry));
        }
      }),
  );
  return examples;
}

function extractVocabulary(payload) {
  const lessonPayload = payload?.lesson || {};
  const source = Array.isArray(lessonPayload.active_words)
    ? lessonPayload.active_words
    : (Array.isArray(lessonPayload.sections) ? lessonPayload.sections : [])
        .flatMap((section) => (Array.isArray(section?.cards) ? section.cards : []))
        .filter((card) => card?.type === "active_word" && card.word)
        .map((card) => card.word);
  const examples = vocabularyExamples(lessonPayload);
  const seen = new Set();
  return source
    .map((word, index) => {
      const zh = String(word?.zh || "").trim();
      const pinyin = String(word?.pinyin || word?.py || "").trim();
      const translation = pick(word?.meaning || word?.translation);
      const key = `${zh}\u0000${pinyin}`;
      if (!zh || !pinyin || !translation || seen.has(key)) return null;
      seen.add(key);
      return {
        id: `${Number(payload?.lesson_order || 0)}-${index}-${zh}`,
        zh,
        pinyin,
        translation,
        pos: String(word?.pos || ""),
        examples: examples.filter((example) => example.zh.includes(zh)).slice(0, 3),
      };
    })
    .filter(Boolean);
}

async function speakVocabulary(text, button) {
  button.disabled = true;
  try {
    const result = await desktopBridge.ttsSpeak(text);
    if (result?.ok !== true) showToast(t("audioUnavailable"));
  } catch (error) {
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    showToast(t("audioUnavailable"));
  } finally {
    button.disabled = false;
  }
}

function renderVocabularyContent(words, lessonItem) {
  if (state.view !== "vocabulary") return;
  const heading = viewHeading(
    t("vocabularyTitle"),
    t("vocabularySubtitle"),
    t("lessonNumber", { number: lessonItem.n }),
  );
  dom.content.replaceChildren(heading);

  if (!words.length) {
    const empty = element("section", "empty-state card-panel");
    empty.append(
      element("h3", "", t("vocabularyEmptyTitle")),
      element("p", "muted", t("vocabularyEmptyBody")),
    );
    const action = element("button", "primary-button", t("openLesson"));
    action.type = "button";
    action.addEventListener("click", () => openLesson(Number(lessonItem.n)));
    empty.append(action);
    dom.content.append(empty);
    return;
  }

  if (!words.some((word) => word.id === state.vocabularySelected)) {
    state.vocabularySelected = words[0].id;
  }
  const selected = words.find((word) => word.id === state.vocabularySelected) || words[0];
  const layout = element("div", "vocabulary-layout");
  const list = element("section", "vocabulary-list card-panel");
  const listHead = element("header", "vocabulary-list-head");
  listHead.append(
    element("div", "", ""),
    element("span", "word-count", t("wordCount", { count: words.length })),
  );
  listHead.firstElementChild.append(
    element("p", "eyebrow", t("currentLesson")),
    element("h3", "", String(lessonItem.zh || t("vocabulary"))),
  );
  list.append(listHead);
  const rows = element("div", "vocabulary-rows");
  words.forEach((word) => {
    const row = element(
      "button",
      `vocabulary-row${word.id === selected.id ? " is-active" : ""}`,
    );
    row.type = "button";
    row.append(
      element("strong", "hanzi", word.zh),
      element("span", "pinyin", word.pinyin),
      element("small", "translation", word.translation),
      element("span", "word-arrow", "→"),
    );
    row.addEventListener("click", () => {
      state.vocabularySelected = word.id;
      renderVocabularyContent(words, lessonItem);
    });
    rows.append(row);
  });
  list.append(rows);

  const detail = element("aside", "vocabulary-detail card-panel");
  const detailTop = element("div", "vocabulary-detail-top");
  const wordCopy = element("div");
  wordCopy.append(
    element("p", "eyebrow", selected.pos || t("newWord")),
    element("strong", "vocabulary-detail-zh hanzi", selected.zh),
    element("span", "vocabulary-detail-pinyin pinyin", selected.pinyin),
    element("p", "vocabulary-detail-translation translation", selected.translation),
  );
  const listen = element("button", "listen-button", t("listen"));
  listen.type = "button";
  listen.addEventListener("click", () => speakVocabulary(selected.zh, listen));
  detailTop.append(wordCopy, listen);
  detail.append(detailTop);

  const examples = element("div", "vocabulary-examples");
  examples.append(element("h4", "", t("examples")));
  if (selected.examples.length) {
    selected.examples.forEach((example) => {
      const item = element("article", "vocabulary-example");
      item.append(
        element("strong", "hanzi", example.zh),
        element("span", "pinyin", example.pinyin),
        element("p", "translation", example.translation),
      );
      examples.append(item);
    });
  } else {
    examples.append(element("p", "muted", t("examplesNotAvailable")));
  }
  detail.append(examples);
  layout.append(list, detail);
  dom.content.append(layout);
}

async function renderVocabulary() {
  const current = currentLesson();
  dom.contentTitle.textContent = t("vocabulary");
  dom.contentSubtitle.textContent = t("vocabularySubtitle");
  dom.content.replaceChildren(
    viewHeading(t("vocabularyTitle"), t("vocabularySubtitle"), "词"),
  );
  if (!current) {
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("courseEmpty")));
    dom.content.append(empty);
    return;
  }

  const lessonOrder = Number(current.n);
  const cached = state.vocabularyCache.get(lessonOrder);
  if (cached) {
    renderVocabularyContent(cached, current);
    return;
  }

  const loading = element("section", "loading-card vocabulary-loading");
  loading.append(element("div", "spinner"), element("p", "", t("vocabularyLoading")));
  dom.content.append(loading);
  const request = ++state.vocabularyRequest;
  try {
    const payload = await desktopBridge.lessonData(lessonOrder);
    if (request !== state.vocabularyRequest || state.view !== "vocabulary") return;
    const words = extractVocabulary(payload);
    state.vocabularyCache.set(lessonOrder, words);
    renderVocabularyContent(words, current);
  } catch (error) {
    if (request !== state.vocabularyRequest || state.view !== "vocabulary") return;
    if (isSessionError(error)) {
      showAuth({ expired: true });
      return;
    }
    const failed = element("section", "empty-state card-panel");
    failed.append(
      element("h3", "", t("vocabularyLoadFailed")),
      element("p", "muted", errorMessage(error)),
    );
    const retry = element("button", "primary-button", t("retry"));
    retry.type = "button";
    retry.addEventListener("click", () => {
      state.vocabularyCache.delete(lessonOrder);
      void renderVocabulary();
    });
    failed.append(retry);
    dom.content.replaceChildren(
      viewHeading(t("vocabularyTitle"), t("vocabularySubtitle"), "词"),
      failed,
    );
  }
}

function renderRating() {
  const map = state.map;
  if (!map) return;
  const progress = map.progress || {};
  const lessons = allLessons();
  const completed = Number(progress.completed || 0);
  const league = String(progress.league || t("notAvailable"));
  const percent = progressPercent(completed, lessons.length);
  dom.contentTitle.textContent = t("rating");
  dom.contentSubtitle.textContent = t("ratingSubtitle");
  dom.content.replaceChildren(
    viewHeading(t("ratingTitle"), t("ratingSubtitle"), league),
  );

  const hero = element("section", "rating-hero card-panel");
  const emblem = element("div", "league-emblem", "级");
  const copy = element("div", "rating-hero-copy");
  copy.append(
    element("p", "eyebrow", t("yourLeague")),
    element("h3", "", league),
    element("p", "muted", t("ratingTruthfulBody")),
  );
  const weekly = element("div", "rating-weekly-xp");
  weekly.append(
    element("strong", "", Number(progress.weekly_xp || 0)),
    element("small", "", t("weeklyXp")),
  );
  hero.append(emblem, copy, weekly);

  const layout = element("div", "rating-layout");
  const personal = element("section", "personal-ranking card-panel");
  personal.append(element("p", "eyebrow", t("personalResult")));
  const userRow = element("div", "personal-ranking-row");
  const avatar = element("img");
  avatar.src = "./assets/hsk-ai-avatar.webp";
  avatar.alt = "";
  const identity = element("div");
  identity.append(
    element("strong", "", String(map.user?.name || t("unknownUser"))),
    element("small", "", `${String(map.label || levelLabel(map.level))} · ${league}`),
  );
  userRow.append(
    avatar,
    identity,
    element("strong", "personal-xp", `${Number(progress.xp || 0)} XP`),
  );
  personal.append(userRow);

  const realStats = element("div", "rating-stats");
  [
    [t("dailyXp"), Number(progress.daily_xp || 0)],
    [t("streakDays"), Number(progress.streak || 0)],
    [t("longestStreak"), Number(progress.longest_streak || 0)],
    [t("courseProgress"), `${percent}%`],
  ].forEach(([label, value]) => {
    const card = element("article");
    card.append(element("small", "", label), element("strong", "", value));
    realStats.append(card);
  });
  personal.append(realStats);

  const activity = element("aside", "rating-activity card-panel");
  activity.append(
    element("p", "eyebrow", t("weeklyActivity")),
    element("h3", "", t("realServerActivity")),
    element("p", "muted", t("realServerActivityBody")),
    weekActivity(progress),
  );
  layout.append(personal, activity);
  dom.content.append(hero, layout);
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

function renderProfile() {
  const map = state.map;
  if (!map) return;
  const user = map.user || {};
  const progress = map.progress || {};
  const completed = Number(progress.completed || 0);
  const lessons = allLessons();
  const percent = progressPercent(completed, lessons.length);
  const league = String(progress.league || t("notAvailable"));
  dom.contentTitle.textContent = t("profileTitle");
  dom.contentSubtitle.textContent = t("profileSubtitle");
  dom.content.replaceChildren(
    viewHeading(
      t("profileTitle"),
      t("profileSubtitle"),
      String(map.label || levelLabel(map.level)),
    ),
  );

  const layout = element("div", "profile-layout");
  const profileMain = element("div", "profile-main");
  const hero = element("section", "profile-hero card-panel");
  const identity = element("div", "profile-identity");
  const avatar = element("img");
  avatar.src = "./assets/hsk-ai-avatar.webp";
  avatar.alt = "";
  const identityCopy = element("div");
  identityCopy.append(
    element("p", "eyebrow", t("singleAccount")),
    element("h3", "", String(user.name || t("unknownUser"))),
    element(
      "p",
      "",
      `${String(map.label || levelLabel(map.level))} · ${league}`,
    ),
  );
  identity.append(avatar, identityCopy);
  const accessPill = element(
    "span",
    `profile-plan-pill${user.is_paid ? " is-paid" : ""}`,
    user.is_paid ? t("paidPlan") : t("freePlan"),
  );
  const heroHead = element("div", "profile-hero-head");
  heroHead.append(identity, accessPill);
  const stats = element("div", "profile-stats");
  [
    [Number(progress.xp || 0), t("xpTotal")],
    [Number(progress.streak || 0), t("streakDays")],
    [Number(progress.longest_streak || 0), t("longestStreak")],
    [Number(progress.weekly_xp || 0), t("weeklyXp")],
    [Number(progress.daily_xp || 0), t("dailyXp")],
    [completed, t("completedLessons")],
  ].forEach(([value, label]) => {
    const card = element("div");
    card.append(element("strong", "", value), element("small", "", label));
    stats.append(card);
  });
  hero.append(heroHead, stats);

  const progressPanel = element("section", "profile-progress-panel card-panel");
  const progressHead = element("div", "card-heading-row");
  const progressCopy = element("div");
  progressCopy.append(
    element("p", "eyebrow", t("learningProgress")),
    element("h3", "", String(map.label || levelLabel(map.level))),
  );
  progressHead.append(progressCopy, element("strong", "profile-percent", `${percent}%`));
  const track = element("div", "summary-progress profile-progress-track");
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  const fill = element("span", "progress-fill");
  track.append(fill);
  setProgress(fill, completed, lessons.length);
  const progressMeta = element("div", "profile-progress-meta");
  progressMeta.append(
    element("span", "", t("lessons", { done: completed, total: lessons.length })),
    element("span", "", t("leagueValue", { league })),
  );
  progressPanel.append(
    progressHead,
    track,
    progressMeta,
    element("h4", "profile-week-title", t("weeklyActivity")),
    weekActivity(progress),
  );
  profileMain.append(hero, progressPanel);

  const profileSide = element("div", "profile-side");
  const settings = element("section", "profile-settings card-panel");
  settings.append(
    element("p", "eyebrow", t("settings")),
    element("h3", "", t("interfaceLanguage")),
  );
  const languages = element("div", "language-list");
  languageOptions.forEach((option) => {
    const button = element("button", "language-button", option.label);
    button.type = "button";
    button.classList.toggle("is-active", option.code === getLanguage());
    button.addEventListener("click", () => changeLanguage(option.code));
    languages.append(button);
  });
  settings.append(languages);

  const access = element("section", "profile-access card-panel");
  access.append(
    element("p", "eyebrow", t("accountAccess")),
    element("h3", "", user.is_paid ? t("paidPlan") : t("freePlan")),
    element(
      "p",
      "muted",
      user.is_paid ? t("paidAccessDescription") : t("freeAccessDescription"),
    ),
  );
  const accessAction = element("button", "primary-button", t("manageSubscription"));
  accessAction.type = "button";
  accessAction.addEventListener("click", () => routeTo("subscription"));
  access.append(accessAction);

  const logout = element("button", "secondary-button", t("logout"));
  logout.type = "button";
  logout.addEventListener("click", () => logoutDesktop(logout));
  profileSide.append(settings, access, logout);
  layout.append(profileMain, profileSide);
  dom.content.append(layout);
}

async function changeLanguage(language) {
  if (language === getLanguage()) {
    return;
  }
  const buttons = dom.content.querySelectorAll(".language-button");
  buttons.forEach((button) => {
    button.disabled = true;
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
    buttons.forEach((button) => {
      button.disabled = false;
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
  const panel = element("section", "ai-pack-state");
  panel.append(element("p", "", t("aiChecking")));
  dom.aiBody.replaceChildren(panel);
  try {
    const result = await desktopBridge.localAiModelStatus();
    panel.replaceChildren();
    if (result?.installed === true) {
      panel.append(
        element("h3", "", t("aiModelFoundTitle")),
        element("p", "", t("aiModelFoundBody")),
        element("span", "pack-status", t("aiModelReady")),
      );
    } else if (result?.state === "missing") {
      panel.append(
        element("h3", "", t("aiMissingTitle")),
        element("p", "", t("aiMissingBody")),
        element("span", "pack-status", t("aiNotReady")),
      );
    } else {
      state.aiLoaded = false;
      panel.append(
        element("h3", "", t("aiUnavailableTitle")),
        element("p", "", t("aiUnavailableBody")),
        element("span", "pack-status", t("aiNotReady")),
      );
    }
  } catch {
    state.aiLoaded = false;
    panel.replaceChildren(
      element("h3", "", t("aiUnavailableTitle")),
      element("p", "", t("aiUnavailableBody")),
      element("span", "pack-status", t("aiNotReady")),
    );
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
  dom.headerProfile.addEventListener("click", () => routeTo("profile"));
  dom.railProfileButton.addEventListener("click", () => routeTo("profile"));
  dom.globalSearch.addEventListener("input", () => {
    state.searchQuery = String(dom.globalSearch.value || "");
    if (state.searchQuery && state.view !== "course") state.view = "course";
    if (state.view === "course") renderActiveView();
  });
  dom.railToggle.addEventListener("click", toggleRail);
  dom.railScrim.addEventListener("click", closeRail);
  dom.aiLauncher.addEventListener("click", toggleAi);
  dom.closeAi.addEventListener("click", closeAi);
  window.addEventListener("online", updateNetworkState);
  window.addEventListener("offline", updateNetworkState);
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
    if (lesson.isOpen) {
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
  updateNetworkState();
  showOnly("boot");

  try {
    const appInfo = await desktopBridge.appInfo();
    dom.appVersion.textContent = appInfo?.version
      ? `v${String(appInfo.version)}`
      : "";
    if (appInfo?.platform) {
      const platform = String(appInfo.platform).toLowerCase();
      document.documentElement.dataset.os = platform;
      dom.aiShortcut.textContent = platform === "windows" ? "Ctrl+K" : "⌘K";
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
