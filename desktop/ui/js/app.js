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
  showSubscription: $("#show-subscription"),
  showProfile: $("#show-profile"),
  todayLabel: $("#today-label"),
  courseLabel: $("#course-label"),
  subscriptionLabel: $("#subscription-label"),
  subscriptionBadge: $("#subscription-badge"),
  profileLabel: $("#profile-label"),
  contentTitle: $("#content-title"),
  contentSubtitle: $("#content-subtitle"),
  content: $("#content-inner"),
  globalSearch: $("#global-search"),
  headerStreak: $("#header-streak"),
  headerXp: $("#header-xp"),
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
  dom.subscriptionLabel.textContent = t("subscription");
  dom.profileLabel.textContent = t("profile");
  dom.railDaysLabel.textContent = t("days");
  dom.refreshMap.setAttribute("aria-label", t("refresh"));
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
    element("span", "lesson-subtitle", pick(item.tr, String(item.py || ""))),
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
    subscription: dom.showSubscription,
    profile: dom.showProfile,
  };
  Object.entries(views).forEach(([name, button]) => {
    button.setAttribute("aria-current", state.view === name ? "page" : "false");
  });
  dom.content.dataset.view = state.view;

  if (state.view === "today") renderToday();
  else if (state.view === "course") renderCourseHome();
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
  renderActiveView();
  closeRail();
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
  dom.contentSubtitle.textContent = t("todaySubtitle");
  dom.content.replaceChildren(
    viewHeading(t("todayTitle"), t("todaySubtitle"), level),
  );

  const grid = element("div", "today-grid");
  const main = element("div", "today-main");
  const side = element("aside", "today-side");

  if (current) {
    const glyph =
      Array.from(String(current.zh || "课").replace(/[·\s]+/g, ""))[0] || "课";
    const resume = element("section", "resume-card");
    resume.dataset.watermark = glyph;
    const copy = element("div", "resume-copy");
    copy.append(
      element("p", "eyebrow", t("currentLesson")),
      element("h3", "", t("lessonNumber", { number: current.n })),
      element("p", "resume-chinese", String(current.zh || glyph)),
      element(
        "p",
        "",
        [String(current.py || ""), pick(current.tr)].filter(Boolean).join(" · "),
      ),
    );
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
    const action = element(
      "button",
      "primary-button",
      current.status === "done" ? t("startLesson") : t("continueLesson"),
    );
    action.type = "button";
    action.addEventListener("click", () => openLesson(Number(current.n)));
    resume.append(copy, action);
    main.append(resume);
  } else {
    const empty = element("section", "empty-state card-panel");
    empty.append(element("p", "", t("courseEmpty")));
    main.append(empty);
  }

  const stats = element("section", "dashboard-stats");
  [
    [t("xpTotal"), Number(progress.xp || 0)],
    [t("streakDays"), Number(progress.streak || 0)],
    [t("completedLessons"), completed],
  ].forEach(([label, value]) => {
    const card = element("article", "dashboard-stat");
    card.append(element("small", "", label), element("strong", "", value));
    stats.append(card);
  });
  main.append(stats);

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
  side.append(progressCard, planCard);
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
    const unitLessons = (Array.isArray(unit.lessons) ? unit.lessons : []).filter(
      (item) => lessonMatches(item, query),
    );
    if (!unitLessons.length) return;
    renderedLessons += unitLessons.length;
    const unitNumber = Number(unit.no ?? unit.n ?? unitIndex + 1);
    const card = element("section", "course-unit-card");
    const head = element("header", "course-unit-head");
    const copy = element("div");
    copy.append(
      element("h3", "", pick(unit.title, t("unit", { number: unitNumber }))),
      element("p", "", t("unitLessonCount", { count: unitLessons.length })),
    );
    head.append(element("span", "course-unit-number", unitNumber), copy);
    const trail = element("div", "lesson-trail");
    unitLessons.forEach((item) => trail.append(renderLessonNode(item)));
    card.append(head, trail);
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
  );
  [
    [t("xpTotal"), Number(progress.xp || 0)],
    [t("streakDays"), Number(progress.streak || 0)],
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
  const button = element("button", `lesson-node is-${status}`);
  button.type = "button";
  button.append(
    element(
      "span",
      "lesson-node-mark",
      status === "done" ? "✓" : accessible ? "▶" : "⌁",
    ),
    element("strong", "", t("lessonNumber", { number: item.n })),
    element("span", "lesson-node-zh", String(item.zh || "课")),
    element(
      "small",
      "",
      [String(item.py || ""), pick(item.tr)].filter(Boolean).join(" · "),
    ),
  );
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
      `${String(map.label || levelLabel(map.level))} · ${user.is_paid ? t("paidPlan") : t("freePlan")}`,
    ),
  );
  identity.append(avatar, identityCopy);
  const stats = element("div", "profile-stats");
  [
    [Number(progress.xp || 0), t("xpTotal")],
    [Number(progress.streak || 0), t("streakDays")],
    [completed, t("completedLessons")],
  ].forEach(([value, label]) => {
    const card = element("div");
    card.append(element("strong", "", value), element("small", "", label));
    stats.append(card);
  });
  hero.append(identity, stats);

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
  layout.append(hero, profileSide);
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
  dom.showSubscription.addEventListener("click", () => routeTo("subscription"));
  dom.showProfile.addEventListener("click", () => routeTo("profile"));
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
