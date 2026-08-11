(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search || "");
  var isDesktop =
    params.get("desktop") === "1" ||
    Boolean(window.__TAURI__ || window.__TAURI_INTERNALS__);
  var focusProfileDownload = params.get("desktop_download") === "1";
  var promoRoot = document.getElementById("pomp-desktop-promo-root");
  if (!promoRoot && document.body) {
    promoRoot = document.createElement("div");
    promoRoot.id = "pomp-desktop-promo-root";
    promoRoot.hidden = true;
    document.body.appendChild(promoRoot);
  }
  var destinationRoot = document.getElementById(
    "pomp-desktop-destination-root"
  );
  if (!destinationRoot && document.body) {
    destinationRoot = document.createElement("div");
    destinationRoot.id = "pomp-desktop-destination-root";
    destinationRoot.hidden = true;
    document.body.appendChild(destinationRoot);
  }
  var REQUEST_TIMEOUT_MS = 18000;
  var STATUS_ENDPOINT = "/api/v3/desktop-download/status";
  var REQUEST_ENDPOINT = "/api/v3/desktop-download/request";
  var STARTED_ENDPOINT = "/api/v3/desktop-download/started";
  var PROMO_SOURCES = ["home_prompt", "lesson_end_promo", "ad_promo"];
  var ENTRY_SOURCES = ["profile"].concat(PROMO_SOURCES);
  var DEFAULT_PROMO_COOLDOWN_DAYS = 14;

  var COPY = {
    uz: {
      eyebrow: "HSK AI · kompyuter",
      cardTitle: "Kompyuter ilovasi",
      cardBody:
        "Kurs, obuna va progress bir akkauntda. Mac yoki Windows versiyasini tanlang.",
      mobileCardHint:
        "Telefondasiz: eng qulay yo‘l — AirDrop/ulashish yoki linkni kompyuterga yuborish.",
      previewTranslation: "o‘rganmoq",
      preparing:
        "Yuklash fayllari tayyorlanmoqda. Tez orada tugmalar faollashadi.",
      availabilityError:
        "Yuklash holatini tekshirib bo‘lmadi. Internetni tekshirib, qayta urining.",
      retryStatus: "Qayta tekshirish",
      checkingStatus: "Tekshirilmoqda…",
      promoTitle: "Darslarni kompyuterda davom ettiring",
      promoBody:
        "Mac yoki Windows ilovasida kurs katta ekranda, yangilanishlar esa avtomatik keladi.",
      bigScreen: "Katta ekran",
      autoUpdate: "Avtomatik update",
      sharedProgress: "Yagona progress",
      mac: "Mac uchun olish",
      windows: "Windows uchun olish",
      macUnavailable: "Mac — tez orada",
      windowsUnavailable: "Windows — tez orada",
      recommended: "Mos",
      dismiss: "Keyinroq",
      close: "Oynani yopish",
      adEntry: "Kompyuter ilovasini olish",
      adEntrySub: "Mac va Windows · progress saqlanadi",
      sendingShort: "Tayyorlanmoqda…",
      sending: "Yuklash sayti tayyorlanmoqda…",
      telegramRequired: "Mini Appni bot ichidan qayta oching.",
      releaseUnavailable: "Bu platforma uchun yuklash hozircha mavjud emas.",
      rateLimited: "Ko‘p urinish bo‘ldi. Birozdan keyin qayta urinib ko‘ring.",
      messageFailed: "Faylni ochib bo‘lmadi. Qayta urinib ko‘ring.",
      requestTimeout: "Server vaqtida javob bermadi. Qayta urinib ko‘ring.",
      networkError: "Server bilan aloqa bo‘lmadi. Internetni tekshirib, qayta urinib ko‘ring.",
      invalidDownload: "Server xavfsiz yuklash manzilini qaytarmadi.",
      destinationTitle: "{platform} faylini qayerda ochamiz?",
      destinationBody:
        "Installer linkini shu qurilmada oching yoki kompyuteringizga xavfsiz yuboring.",
      destinationMobileIntro:
        "Kompyuterda ochish uchun eng qulay usulni tanlang.",
      destinationMobileBody:
        "DMG/EXE’ni telefonda yuklasangiz, u Downloads yoki Fayllar ichiga tushadi. Kompyuterda ochish uchun ulashish yoki linkni tanlang.",
      directTitle: "Shu qurilmada ochish",
      directBody: "Yuklash sayti hozir ochiladi",
      directMobileTitle: "Telefonda yuklash sahifasini ochish",
      directMobileBody:
        "Saytda yuklasangiz, fayl telefonning Downloads yoki Fayllar papkasiga saqlanadi",
      shareTitle: "AirDrop yoki ulashish",
      shareBody: "Telefonning ulashish oynasini ochadi",
      shareRecommended: "Eng qulay",
      copyTitle: "Linkni nusxalash",
      copyBody: "Kompyuter brauzeriga qo‘yib oching",
      cancel: "Bekor qilish",
      shareCancelled: "Ulashish bekor qilindi. Boshqa usulni tanlashingiz mumkin.",
      copyFailed: "Avtomatik nusxalanmadi. Quyidagi linkni belgilang va nusxalang.",
      manualLinkLabel: "Kompyuterda ochiladigan xavfsiz link",
      successTitle: "Yuklash sayti ochildi",
      successBody:
        "Sayt operatsion tizimingizga mos DMG yoki EXE faylni va o‘rnatish qadamlarini ko‘rsatadi.",
      shareSuccessTitle: "Link ulashildi",
      shareSuccessBody:
        "Kompyuteringizda linkni oching va mos DMG yoki EXE faylni yuklang.",
      copySuccessTitle: "Link nusxalandi",
      copySuccessBody:
        "Linkni kompyuter brauzeriga qo‘ying. Yuklash sahifasi darhol ochiladi.",
      successAction: "Tushunarli"
    },
    ru: {
      eyebrow: "HSK AI · компьютер",
      cardTitle: "Приложение для компьютера",
      cardBody:
        "Курс, подписка и прогресс в одном аккаунте. Выберите версию для Mac или Windows.",
      mobileCardHint:
        "Вы на телефоне: удобнее отправить ссылку через AirDrop или системное меню.",
      previewTranslation: "учиться",
      preparing:
        "Файлы загрузки готовятся. Кнопки станут активны в ближайшее время.",
      availabilityError:
        "Не удалось проверить загрузку. Проверьте интернет и повторите.",
      retryStatus: "Проверить снова",
      checkingStatus: "Проверяем…",
      promoTitle: "Продолжайте уроки на компьютере",
      promoBody:
        "Курс удобнее на большом экране, а новые версии устанавливаются автоматически.",
      bigScreen: "Большой экран",
      autoUpdate: "Автообновление",
      sharedProgress: "Общий прогресс",
      mac: "Скачать для Mac",
      windows: "Скачать для Windows",
      macUnavailable: "Mac — скоро",
      windowsUnavailable: "Windows — скоро",
      recommended: "Подходит",
      dismiss: "Позже",
      close: "Закрыть окно",
      adEntry: "Скачать приложение для компьютера",
      adEntrySub: "Mac и Windows · единый прогресс",
      sendingShort: "Готовим…",
      sending: "Готовим страницу загрузки…",
      telegramRequired: "Откройте Mini App заново из бота.",
      releaseUnavailable: "Загрузка для этой платформы пока недоступна.",
      rateLimited: "Слишком много попыток. Попробуйте немного позже.",
      messageFailed: "Не удалось открыть файл. Попробуйте ещё раз.",
      requestTimeout: "Сервер не ответил вовремя. Попробуйте ещё раз.",
      networkError: "Нет связи с сервером. Проверьте интернет и попробуйте снова.",
      invalidDownload: "Сервер не вернул безопасный адрес загрузки.",
      destinationTitle: "Где открыть файл для {platform}?",
      destinationBody:
        "Откройте установщик на этом устройстве или безопасно отправьте ссылку на компьютер.",
      destinationMobileIntro:
        "Выберите удобный способ открыть установщик на компьютере.",
      destinationMobileBody:
        "Если скачать DMG/EXE на телефоне, файл попадёт в Загрузки или Файлы. Для компьютера выберите отправку или копирование ссылки.",
      directTitle: "Открыть на этом устройстве",
      directBody: "Страница загрузки откроется сейчас",
      directMobileTitle: "Открыть загрузку на телефоне",
      directMobileBody:
        "После загрузки файл сохранится в папке Загрузки или Файлы телефона",
      shareTitle: "AirDrop или поделиться",
      shareBody: "Откроется системное меню отправки",
      shareRecommended: "Удобнее всего",
      copyTitle: "Скопировать ссылку",
      copyBody: "Вставьте её в браузере компьютера",
      cancel: "Отмена",
      shareCancelled: "Отправка отменена. Можно выбрать другой способ.",
      copyFailed: "Не удалось скопировать автоматически. Выделите ссылку ниже и скопируйте.",
      manualLinkLabel: "Безопасная ссылка для компьютера",
      successTitle: "Страница загрузки открыта",
      successBody:
        "На странице показан подходящий DMG или EXE и точные шаги установки.",
      shareSuccessTitle: "Ссылка отправлена",
      shareSuccessBody:
        "Откройте ссылку на компьютере и скачайте подходящий DMG или EXE.",
      copySuccessTitle: "Ссылка скопирована",
      copySuccessBody:
        "Вставьте ссылку в браузер компьютера — страница загрузки откроется сразу.",
      successAction: "Понятно"
    },
    tj: {
      eyebrow: "HSK AI · компютер",
      cardTitle: "Барномаи компютерӣ",
      cardBody:
        "Курс, обуна ва пешрафт дар як ҳисоб. Версияи Mac ё Windows-ро интихоб кунед.",
      mobileCardHint:
        "Шумо дар телефонед: бо AirDrop ё равзанаи фиристодан ба компютер гузарондан қулайтар аст.",
      previewTranslation: "омӯхтан",
      preparing:
        "Файлҳои боргирӣ омода мешаванд. Тугмаҳо ба наздикӣ фаъол мешаванд.",
      availabilityError:
        "Ҳолати боргирӣ санҷида нашуд. Интернетро санҷида, боз кӯшиш кунед.",
      retryStatus: "Боз санҷидан",
      checkingStatus: "Санҷида мешавад…",
      promoTitle: "Дарсҳоро дар компютер идома диҳед",
      promoBody:
        "Курс дар экрани калон қулайтар аст ва версияҳои нав автоматӣ меоянд.",
      bigScreen: "Экрани калон",
      autoUpdate: "Навсозии автоматӣ",
      sharedProgress: "Пешрафти умумӣ",
      mac: "Гирифтан барои Mac",
      windows: "Гирифтан барои Windows",
      macUnavailable: "Mac — ба наздикӣ",
      windowsUnavailable: "Windows — ба наздикӣ",
      recommended: "Мувофиқ",
      dismiss: "Баъдтар",
      close: "Пӯшидани равзана",
      adEntry: "Гирифтани барномаи компютерӣ",
      adEntrySub: "Mac ва Windows · пешрафти умумӣ",
      sendingShort: "Омода мешавад…",
      sending: "Саҳифаи боргирӣ омода мешавад…",
      telegramRequired: "Mini App-ро аз дохили бот аз нав кушоед.",
      releaseUnavailable: "Боргирӣ барои ин платформа ҳоло дастрас нест.",
      rateLimited: "Кӯшишҳо зиёд шуданд. Каме баъд боз санҷед.",
      messageFailed: "Файл кушода нашуд. Боз кӯшиш кунед.",
      requestTimeout: "Сервер сари вақт ҷавоб надод. Боз кӯшиш кунед.",
      networkError: "Бо сервер алоқа нест. Интернетро санҷида, боз кӯшиш кунед.",
      invalidDownload: "Сервер суроғаи бехатари боргириро барнагардонд.",
      destinationTitle: "Файли {platform}-ро дар куҷо мекушоем?",
      destinationBody:
        "Насбкунандаро дар ҳамин дастгоҳ кушоед ё пайвандро бехатар ба компютер фиристед.",
      destinationMobileIntro:
        "Роҳи қулайи кушодан дар компютерро интихоб кунед.",
      destinationMobileBody:
        "Агар DMG/EXE-ро дар телефон бор кунед, файл ба Downloads ё Files меафтад. Барои компютер фиристодан ё нусхаи пайвандро интихоб кунед.",
      directTitle: "Дар ҳамин дастгоҳ кушодан",
      directBody: "Саҳифаи боргирӣ ҳозир кушода мешавад",
      directMobileTitle: "Боргириро дар телефон кушодан",
      directMobileBody:
        "Баъди боргирӣ файл дар Downloads ё Files-и телефон мемонад",
      shareTitle: "AirDrop ё фиристодан",
      shareBody: "Равзанаи системавии фиристодан кушода мешавад",
      shareRecommended: "Қулайтарин",
      copyTitle: "Нусхаи пайванд",
      copyBody: "Дар браузери компютер гузошта кушоед",
      cancel: "Бекор кардан",
      shareCancelled: "Фиристодан бекор шуд. Роҳи дигарро интихоб карда метавонед.",
      copyFailed: "Худкор нусха нашуд. Пайванди поёнро интихоб карда нусха гиред.",
      manualLinkLabel: "Пайванди бехатар барои компютер",
      successTitle: "Саҳифаи боргирӣ кушода шуд",
      successBody:
        "Саҳифа DMG ё EXE-и мувофиқ ва қадамҳои дақиқи насбро нишон медиҳад.",
      shareSuccessTitle: "Пайванд фиристода шуд",
      shareSuccessBody:
        "Пайвандро дар компютер кушоед ва DMG ё EXE-и мувофиқро бор кунед.",
      copySuccessTitle: "Пайванд нусха шуд",
      copySuccessBody:
        "Пайвандро дар браузери компютер гузоред. Саҳифаи боргирӣ кушода мешавад.",
      successAction: "Фаҳмо"
    }
  };

  var state = {
    availabilityLoaded: false,
    availabilityLoading: false,
    availabilityError: false,
    enabled: false,
    platforms: { macos: false, windows: false },
    transferUrls: { macos: "", windows: "" },
    runtimeUnavailable: { macos: false, windows: false },
    promoEligible: false,
    promoReason: "",
    promoCooldownDays: 0,
    promoPlacements: {
      home_prompt: false,
      lesson_end_promo: false,
      ad_promo: false
    },
    pendingPlatform: "",
    pendingEventIds: {},
    errorCode: "",
    promoOpen: false,
    promoSeenInSession: false,
    promoTimer: 0,
    queuedPromo: null,
    queuedPromoTimer: 0,
    activePromoSource: "",
    activePromoMeta: {},
    previousFocus: null,
    profileFocusDone: false,
    lastPlatform: "",
    destinationOpen: false,
    destinationPlatform: "",
    destinationSource: "",
    destinationPreviousFocus: null,
    pendingDestination: "",
    destinationMessage: "",
    destinationMessageKind: "",
    manualTransferUrl: "",
    adPromoMounts: [],
    entrySeen: {}
  };

  function language() {
    var value =
      (typeof window.LANG === "string" && window.LANG) ||
      params.get("lang") ||
      "ru";
    return COPY[value] ? value : "ru";
  }

  function text() {
    return COPY[language()];
  }

  function telegramInitData() {
    if (typeof window.INIT_DATA === "string" && window.INIT_DATA) {
      return window.INIT_DATA;
    }
    var app = telegramWebApp();
    return app && typeof app.initData === "string" ? app.initData : "";
  }

  function telegramWebApp() {
    return (
      window.tg ||
      (window.Telegram && window.Telegram.WebApp) ||
      null
    );
  }

  function element(tag, className, value) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof value === "string") node.textContent = value;
    return node;
  }

  function icon(name) {
    return element("i", "ti ti-" + name);
  }

  function eventId(kind) {
    return (
      "pdd." +
      String(kind || "event").replace(/[^A-Za-z0-9._:-]/g, "-") +
      "." +
      Date.now() +
      "." +
      Math.random().toString(36).slice(2, 10)
    ).slice(0, 80);
  }

  function validEventId(value) {
    return (
      typeof value === "string" &&
      value.length >= 16 &&
      value.length <= 80 &&
      /^[A-Za-z0-9._:-]+$/.test(value)
    );
  }

  function pendingEventStorageKey(platform, source) {
    return "hsk_pdd_pending_v1:" + platform + ":" + source;
  }

  function pendingEventId(platform, source) {
    var key = pendingEventStorageKey(platform, source);
    var value = state.pendingEventIds[key] || "";
    try {
      value = sessionStorage.getItem(key) || value;
    } catch (error) {}
    if (!validEventId(value)) {
      value = eventId("download-request");
      try {
        sessionStorage.setItem(key, value);
      } catch (error) {}
    }
    state.pendingEventIds[key] = value;
    return value;
  }

  function clearPendingEventId(platform, source) {
    var key = pendingEventStorageKey(platform, source);
    delete state.pendingEventIds[key];
    try {
      sessionStorage.removeItem(key);
    } catch (error) {}
  }

  function userStorageSuffix() {
    try {
      var app = telegramWebApp();
      var user = app && app.initDataUnsafe && app.initDataUnsafe.user;
      if (user && user.id) return String(user.id);
    } catch (error) {}
    return "current";
  }

  function storageKey(name) {
    return "hsk_pdd_" + name + "_v1:" + userStorageSuffix();
  }

  function readStoredNumber(name) {
    try {
      return Number(localStorage.getItem(storageKey(name)) || 0);
    } catch (error) {
      return 0;
    }
  }

  function storeNumber(name, value) {
    try {
      localStorage.setItem(storageKey(name), String(value));
    } catch (error) {}
  }

  function track(event, payload) {
    var data = Object.assign({}, payload || {});
    var id = data.event_id || eventId(event);
    data.event_id = id;
    data.dedupe_key = id;
    if (typeof window.trackCourseEvent === "function") {
      window.trackCourseEvent(event, data);
      return;
    }
    if (!telegramInitData()) return;
    data.event = event;
    data.source = data.source || "desktop_promo";
    fetch("/api/miniapp/event", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": telegramInitData()
      },
      body: JSON.stringify(data),
      keepalive: true
    }).catch(function () {});
  }

  function trackEntrySeen(source, meta) {
    if (
      ENTRY_SOURCES.indexOf(source) < 0 ||
      state.entrySeen[source] ||
      !telegramInitData()
    ) {
      return;
    }
    state.entrySeen[source] = true;
    track(
      "desktop_download_entry_seen",
      Object.assign(promoMeta(meta), { source: source })
    );
  }

  function isMobileDevice() {
    var app = telegramWebApp();
    var telegramPlatform = String((app && app.platform) || "").toLowerCase();
    if (telegramPlatform === "android" || telegramPlatform === "ios") {
      return true;
    }
    var userAgent = "";
    try {
      userAgent = String(navigator.userAgent || "");
    } catch (error) {}
    return Boolean(
      /Android|iPhone|iPod/i.test(userAgent) ||
        (/iPad|Macintosh/i.test(userAgent) &&
          Number(navigator.maxTouchPoints || 0) > 1)
    );
  }

  function detectPlatform() {
    if (isMobileDevice()) return "";
    var value = "";
    try {
      value =
        (navigator.userAgentData && navigator.userAgentData.platform) ||
        navigator.platform ||
        navigator.userAgent ||
        "";
    } catch (error) {}
    value = String(value).toLowerCase();
    if (value.indexOf("mac") >= 0) return "macos";
    if (value.indexOf("win") >= 0) return "windows";
    return "";
  }

  function isPlatformAvailable(platform) {
    return Boolean(
      state.enabled &&
        state.platforms[platform] &&
        !state.runtimeUnavailable[platform]
    );
  }

  function hasAvailablePlatform() {
    return (
      isPlatformAvailable("macos") ||
      isPlatformAvailable("windows")
    );
  }

  function errorText(code) {
    var copy = text();
    return {
      invalid_telegram_init_data: copy.telegramRequired,
      desktop_release_unavailable: copy.releaseUnavailable,
      desktop_download_rate_limited: copy.rateLimited,
      desktop_download_delivery_pending: copy.requestTimeout,
      desktop_download_message_failed: copy.messageFailed,
      desktop_download_timeout: copy.requestTimeout,
      invalid_success_response: copy.invalidDownload,
      desktop_download_open_failed: copy.messageFailed,
      network_error: copy.networkError
    }[code] || copy.networkError;
  }

  function buildBenefit(iconName, label) {
    var item = element("span", "pdd-benefit");
    item.appendChild(icon(iconName));
    item.appendChild(document.createTextNode(label));
    return item;
  }

  function buildBenefits(includeProgress) {
    var copy = text();
    var row = element("div", "pdd-benefits");
    row.appendChild(buildBenefit("device-desktop", copy.bigScreen));
    row.appendChild(buildBenefit("refresh", copy.autoUpdate));
    if (includeProgress) {
      row.appendChild(buildBenefit("arrows-exchange", copy.sharedProgress));
    }
    return row;
  }

  function buildProductPreview(mode) {
    var copy = text();
    var preview = element("div", "pdd-product-preview");
    preview.dataset.mode = mode || "card";
    preview.setAttribute("aria-hidden", "true");

    var chrome = element("div", "pdd-preview-chrome");
    var dots = element("span", "pdd-preview-dots");
    dots.appendChild(element("i"));
    dots.appendChild(element("i"));
    dots.appendChild(element("i"));
    chrome.appendChild(dots);
    chrome.appendChild(element("strong", "", "HSK AI"));
    chrome.appendChild(element("small", "", "HSK 2"));
    preview.appendChild(chrome);

    var workspace = element("div", "pdd-preview-workspace");
    var rail = element("div", "pdd-preview-rail");
    var logo = element("img", "pdd-preview-logo");
    logo.src = "/assets/hsk-ai-avatar.webp";
    logo.alt = "";
    rail.appendChild(logo);
    ["layout-dashboard", "book-2", "message-circle"].forEach(function (name) {
      rail.appendChild(icon(name));
    });
    workspace.appendChild(rail);

    var lesson = element("div", "pdd-preview-lesson");
    var toolbar = element("div", "pdd-preview-toolbar");
    toolbar.appendChild(element("span", "", "今日 · Today"));
    toolbar.appendChild(element("b", "", "7 天"));
    lesson.appendChild(toolbar);
    var lessonCard = element("div", "pdd-preview-lesson-card");
    var word = element("div", "pdd-preview-word");
    word.appendChild(element("small", "", "今日课程 · jīnrì kèchéng"));
    word.appendChild(element("strong", "", "学习"));
    word.appendChild(
      element("span", "", "xuéxí · " + copy.previewTranslation)
    );
    lessonCard.appendChild(word);
    var progress = element("span", "pdd-preview-progress");
    progress.appendChild(element("b", "", "68%"));
    progress.appendChild(element("small", "", "HSK"));
    lessonCard.appendChild(progress);
    lesson.appendChild(lessonCard);
    workspace.appendChild(lesson);
    preview.appendChild(workspace);
    return preview;
  }

  function platformButtonLabel(platform) {
    var copy = text();
    if (isPlatformAvailable(platform)) {
      return platform === "macos" ? copy.mac : copy.windows;
    }
    return platform === "macos"
      ? copy.macUnavailable
      : copy.windowsUnavailable;
  }

  function buildOsButton(platform, source) {
    var copy = text();
    var button = element("button", "pdd-os-button");
    var recommended =
      detectPlatform() === platform && isPlatformAvailable(platform);
    button.type = "button";
    button.dataset.pddPlatform = platform;
    button.dataset.pddSource = source;
    button.dataset.recommended = recommended ? "true" : "false";
    button.dataset.recommendedLabel = copy.recommended;
    button.appendChild(
      icon(platform === "macos" ? "brand-apple" : "brand-windows")
    );
    button.appendChild(element("span", "", platformButtonLabel(platform)));
    button.addEventListener("click", function () {
      requestDownload(platform, source);
    });
    return button;
  }

  function buildActions(source) {
    var actions = element("div", "pdd-actions");
    actions.appendChild(buildOsButton("macos", source));
    actions.appendChild(buildOsButton("windows", source));
    return actions;
  }

  function buildInlineStatus() {
    var status = element("div", "pdd-inline-status");
    status.dataset.pddStatus = "true";
    status.dataset.visible = "false";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.appendChild(icon("alert-circle"));
    status.appendChild(element("span", "", ""));
    return status;
  }

  function renderProfile() {
    var host = document.getElementById("pomp-desktop-profile-root");
    if (!host) return;
    host.replaceChildren();
    if (isDesktop || !state.availabilityLoaded) {
      return;
    }

    var copy = text();
    var card = element("section", "pdd-card");
    card.setAttribute("aria-labelledby", "pdd-profile-title");
    var main = element("div", "pdd-card-main");
    var head = element("div", "pdd-card-head");
    var seal = element("img", "pdd-seal");
    seal.src = "/assets/hsk-ai-avatar.webp";
    seal.alt = "";
    seal.setAttribute("aria-hidden", "true");
    seal.width = 43;
    seal.height = 43;
    head.appendChild(seal);
    var content = element("div", "pdd-card-copy");
    content.appendChild(element("span", "pdd-eyebrow", copy.eyebrow));
    var title = element("h3", "", copy.cardTitle);
    title.id = "pdd-profile-title";
    content.appendChild(title);
    content.appendChild(element("p", "", copy.cardBody));
    head.appendChild(content);
    main.appendChild(head);
    main.appendChild(buildProductPreview("card"));
    main.appendChild(buildBenefits(true));
    if (isMobileDevice()) {
      var mobileHint = element("div", "pdd-mobile-hint");
      mobileHint.appendChild(icon("devices-share"));
      mobileHint.appendChild(element("span", "", copy.mobileCardHint));
      main.appendChild(mobileHint);
    }
    main.appendChild(buildActions("profile"));
    if (!hasAvailablePlatform()) {
      var availability = element(
        "div",
        "pdd-availability-note" +
          (state.availabilityError ? " is-error" : "")
      );
      availability.setAttribute("role", "status");
      availability.appendChild(
        icon(state.availabilityError ? "wifi-off" : "clock")
      );
      var availabilityCopy = element(
        "span",
        "",
        state.availabilityError ? copy.availabilityError : copy.preparing
      );
      availability.appendChild(availabilityCopy);
      if (state.availabilityError) {
        var retry = element(
          "button",
          "pdd-availability-retry",
          state.availabilityLoading ? copy.checkingStatus : copy.retryStatus
        );
        retry.type = "button";
        retry.disabled = state.availabilityLoading;
        retry.addEventListener("click", function () {
          loadAvailability();
        });
        availability.appendChild(retry);
      }
      main.appendChild(availability);
    }
    main.appendChild(buildInlineStatus());
    card.appendChild(main);
    host.appendChild(card);
    if (hasAvailablePlatform()) {
      trackEntrySeen("profile", { placement: "profile_card" });
    }
    syncControls();
    if (focusProfileDownload && !state.profileFocusDone) {
      state.profileFocusDone = true;
      card.tabIndex = -1;
      window.setTimeout(function () {
        if (!card.isConnected) return;
        card.classList.add("pdd-card-focus");
        try {
          card.focus({ preventScroll: true });
        } catch (error) {
          card.focus();
        }
        card.scrollIntoView({
          behavior:
            window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches
              ? "auto"
              : "smooth",
          block: "center"
        });
        window.setTimeout(function () {
          card.classList.remove("pdd-card-focus");
        }, 1800);
      }, 260);
    }
  }

  function platformLabel(platform) {
    return platform === "macos" ? "Mac" : "Windows";
  }

  function buildDestinationAction(
    destination,
    iconName,
    title,
    body,
    recommended
  ) {
    var button = element("button", "pdd-destination-action");
    button.type = "button";
    button.dataset.pddDestinationAction = destination;
    button.dataset.recommended = recommended ? "true" : "false";
    if (recommended) {
      button.dataset.recommendedLabel = text().shareRecommended;
    }
    button.appendChild(icon(iconName));
    var copyBox = element("span", "pdd-destination-action-copy");
    copyBox.appendChild(element("strong", "", title));
    copyBox.appendChild(element("small", "", body));
    button.appendChild(copyBox);
    button.appendChild(icon("chevron-right"));
    button.addEventListener("click", function () {
      if (!state.pendingPlatform) {
        track("desktop_download_destination_selected", {
          source: state.destinationSource,
          platform: state.destinationPlatform,
          destination: destination,
          mobile: isMobileDevice()
        });
        performDownloadRequest(
          state.destinationPlatform,
          state.destinationSource,
          destination
        );
      }
    });
    return button;
  }

  function showDestinationChooser(platform, source, trigger) {
    if (!destinationRoot || state.destinationOpen || state.pendingPlatform) return;
    var copy = text();
    var mobile = isMobileDevice();
    state.destinationOpen = true;
    state.destinationPlatform = platform;
    state.destinationSource = source;
    state.destinationPreviousFocus = trigger || document.activeElement;
    state.destinationMessage = "";
    state.destinationMessageKind = "";
    state.manualTransferUrl = "";
    state.errorCode = "";

    destinationRoot.replaceChildren();
    destinationRoot.hidden = false;
    var backdrop = element("button", "pdd-destination-backdrop");
    backdrop.type = "button";
    backdrop.tabIndex = -1;
    backdrop.setAttribute("aria-label", copy.cancel);
    backdrop.addEventListener("click", function () {
      closeDestinationChooser(true);
    });
    destinationRoot.appendChild(backdrop);

    var shell = element("section", "pdd-destination-shell");
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");
    shell.setAttribute("aria-labelledby", "pdd-destination-title");
    shell.setAttribute("aria-describedby", "pdd-destination-description");

    var close = element("button", "pdd-destination-close");
    close.type = "button";
    close.setAttribute("aria-label", copy.cancel);
    close.appendChild(icon("x"));
    close.addEventListener("click", function () {
      closeDestinationChooser(true);
    });
    shell.appendChild(close);

    var heading = element("div", "pdd-destination-heading");
    var platformIcon = element("span", "pdd-destination-platform");
    platformIcon.setAttribute("aria-hidden", "true");
    platformIcon.appendChild(
      icon(platform === "macos" ? "brand-apple" : "brand-windows")
    );
    heading.appendChild(platformIcon);
    var title = element(
      "h2",
      "",
      copy.destinationTitle.replace("{platform}", platformLabel(platform))
    );
    title.id = "pdd-destination-title";
    heading.appendChild(title);
    var description = element(
      "p",
      "",
      mobile ? copy.destinationMobileIntro : copy.destinationBody
    );
    description.id = "pdd-destination-description";
    heading.appendChild(description);
    shell.appendChild(heading);

    if (mobile) {
      var handoff = element("div", "pdd-mobile-handoff");
      var handoffIcons = element("span", "pdd-mobile-handoff-icons");
      handoffIcons.appendChild(icon("device-mobile"));
      handoffIcons.appendChild(icon("arrow-right"));
      handoffIcons.appendChild(icon("device-laptop"));
      handoff.appendChild(handoffIcons);
      handoff.appendChild(element("span", "", copy.destinationMobileBody));
      shell.appendChild(handoff);
    }

    var actions = element("div", "pdd-destination-actions");
    var destinationActions = mobile
      ? [
          ["share", "share-3", copy.shareTitle, copy.shareBody, true],
          ["copy", "copy", copy.copyTitle, copy.copyBody, false],
          [
            "direct",
            "download",
            copy.directMobileTitle,
            copy.directMobileBody,
            false
          ]
        ]
      : [
          ["direct", "external-link", copy.directTitle, copy.directBody, true],
          ["share", "share-3", copy.shareTitle, copy.shareBody, false],
          ["copy", "copy", copy.copyTitle, copy.copyBody, false]
        ];
    destinationActions.forEach(function (definition) {
      actions.appendChild(
        buildDestinationAction(
          definition[0],
          definition[1],
          definition[2],
          definition[3],
          definition[4]
        )
      );
    });
    shell.appendChild(actions);

    var manual = element("label", "pdd-destination-manual");
    manual.hidden = true;
    manual.dataset.pddManualTransfer = "true";
    manual.appendChild(element("span", "", copy.manualLinkLabel));
    var manualInput = element("input", "");
    manualInput.type = "text";
    manualInput.readOnly = true;
    manualInput.dataset.pddManualTransferInput = "true";
    manual.appendChild(manualInput);
    shell.appendChild(manual);

    var status = element("p", "pdd-destination-status");
    status.dataset.pddDestinationStatus = "true";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    shell.appendChild(status);

    var cancel = element("button", "pdd-destination-cancel", copy.cancel);
    cancel.type = "button";
    cancel.addEventListener("click", function () {
      closeDestinationChooser(true);
    });
    shell.appendChild(cancel);
    destinationRoot.appendChild(shell);

    if (promoRoot && state.promoOpen) {
      promoRoot.inert = true;
      promoRoot.setAttribute("aria-hidden", "true");
    }
    track("desktop_download_chooser_opened", {
      source: source,
      platform: platform,
      mobile: mobile
    });
    syncControls();
    var firstAction = shell.querySelector("[data-pdd-destination-action]");
    if (firstAction) firstAction.focus();
  }

  function closeDestinationChooser(restoreFocus) {
    if (!destinationRoot || !state.destinationOpen || state.pendingPlatform) return;
    var previousFocus = state.destinationPreviousFocus;
    state.destinationOpen = false;
    state.destinationPlatform = "";
    state.destinationSource = "";
    state.destinationPreviousFocus = null;
    state.pendingDestination = "";
    state.destinationMessage = "";
    state.destinationMessageKind = "";
    state.manualTransferUrl = "";
    destinationRoot.hidden = true;
    destinationRoot.replaceChildren();
    if (promoRoot) {
      promoRoot.inert = false;
      promoRoot.removeAttribute("aria-hidden");
    }
    syncControls();
    if (
      restoreFocus &&
      previousFocus &&
      previousFocus.isConnected &&
      typeof previousFocus.focus === "function"
    ) {
      try {
        previousFocus.focus();
      } catch (error) {}
    }
  }

  function syncControls() {
    var copy = text();
    document.querySelectorAll("[data-pdd-platform]").forEach(function (button) {
      var platform = button.dataset.pddPlatform;
      var pending = state.pendingPlatform === platform;
      var anyPending = Boolean(state.pendingPlatform);
      button.disabled = anyPending || !isPlatformAvailable(platform);
      button.dataset.pending = pending ? "true" : "false";
      button.dataset.recommended =
        detectPlatform() === platform && isPlatformAvailable(platform)
          ? "true"
          : "false";
      button.setAttribute("aria-busy", pending ? "true" : "false");
      button.dataset.recommendedLabel = copy.recommended;
      var iconNode = button.querySelector("i");
      if (iconNode) {
        iconNode.className =
          "ti ti-" +
          (pending
            ? "loader-2"
            : platform === "macos"
              ? "brand-apple"
              : "brand-windows");
      }
      var label = button.querySelector("span");
      if (label) {
        label.textContent = pending
          ? copy.sendingShort
          : platformButtonLabel(platform);
      }
    });

    document.querySelectorAll("[data-pdd-status]").forEach(function (status) {
      var visible = Boolean(state.pendingPlatform || state.errorCode);
      status.dataset.visible = visible ? "true" : "false";
      status.dataset.pending = state.pendingPlatform ? "true" : "false";
      var iconNode = status.querySelector("i");
      var label = status.querySelector("span");
      if (iconNode) {
        iconNode.className =
          "ti ti-" + (state.pendingPlatform ? "loader-2" : "alert-circle");
      }
      if (label) {
        label.textContent = state.pendingPlatform
          ? copy.sending
          : errorText(state.errorCode);
      }
    });

    if (destinationRoot && state.destinationOpen) {
      destinationRoot
        .querySelectorAll("[data-pdd-destination-action]")
        .forEach(function (button) {
          var pending =
            Boolean(state.pendingPlatform) &&
            button.dataset.pddDestinationAction === state.pendingDestination;
          button.disabled = Boolean(state.pendingPlatform);
          button.dataset.pending = pending ? "true" : "false";
          button.setAttribute("aria-busy", pending ? "true" : "false");
        });
      var closeButton = destinationRoot.querySelector(".pdd-destination-close");
      var cancelButton = destinationRoot.querySelector(".pdd-destination-cancel");
      if (closeButton) closeButton.disabled = Boolean(state.pendingPlatform);
      if (cancelButton) cancelButton.disabled = Boolean(state.pendingPlatform);

      var destinationStatus = destinationRoot.querySelector(
        "[data-pdd-destination-status]"
      );
      if (destinationStatus) {
        destinationStatus.dataset.visible =
          state.pendingPlatform || state.destinationMessage || state.errorCode
            ? "true"
            : "false";
        destinationStatus.dataset.kind = state.pendingPlatform
          ? "pending"
          : state.destinationMessageKind || (state.errorCode ? "error" : "");
        destinationStatus.textContent = state.pendingPlatform
          ? copy.sending
          : state.destinationMessage || errorText(state.errorCode);
      }
      var manual = destinationRoot.querySelector("[data-pdd-manual-transfer]");
      var manualInput = destinationRoot.querySelector(
        "[data-pdd-manual-transfer-input]"
      );
      if (manual) manual.hidden = !state.manualTransferUrl;
      if (manualInput) manualInput.value = state.manualTransferUrl;
    }
  }

  function responseErrorCode(response, data) {
    if (data && typeof data.error === "string") return data.error;
    if (
      data &&
      data.detail &&
      typeof data.detail === "object" &&
      typeof data.detail.error === "string"
    ) {
      return data.detail.error;
    }
    if (response.status === 401) return "invalid_telegram_init_data";
    if (response.status === 429) return "desktop_download_rate_limited";
    if (response.status === 502) return "desktop_download_message_failed";
    if (response.status === 503) return "desktop_release_unavailable";
    return "network_error";
  }

  function requestDownload(platform, source) {
    if (
      state.pendingPlatform ||
      state.destinationOpen ||
      !isPlatformAvailable(platform) ||
      ["profile", "home_prompt", "lesson_end_promo", "ad_promo"].indexOf(
        source
      ) < 0
    ) {
      return;
    }
    if (!telegramInitData()) {
      state.errorCode = "invalid_telegram_init_data";
      syncControls();
      return;
    }
    showDestinationChooser(platform, source, document.activeElement);
  }

  function cleanTransferUrl(value, platform) {
    if (typeof value !== "string") return "";
    try {
      var url = new URL(value, window.location.href);
      if (
        url.protocol !== "https:" ||
        url.username ||
        url.password ||
        url.pathname !== "/downloads/" + platform
      ) {
        return "";
      }
      url.search = "";
      url.hash = "";
      return url.toString();
    } catch (error) {
      return "";
    }
  }

  function validDownloadResponse(data, platform) {
    if (
      !data ||
      data.ok !== true ||
      data.platform !== platform ||
      typeof data.download_url !== "string" ||
      typeof data.transfer_url !== "string" ||
      typeof data.file_name !== "string"
    ) {
      return false;
    }
    try {
      var url = new URL(data.download_url, window.location.href);
      var pageUrl = new URL(
        data.download_page_url || data.download_url,
        window.location.href
      );
      var expectedSuffix = platform === "macos" ? ".dmg" : ".exe";
      return (
        url.protocol === "https:" &&
        !url.username &&
        !url.password &&
        pageUrl.protocol === "https:" &&
        !pageUrl.username &&
        !pageUrl.password &&
        Boolean(cleanTransferUrl(data.transfer_url, platform)) &&
        /^[A-Za-z0-9][A-Za-z0-9._+-]{0,119}$/.test(data.file_name) &&
        data.file_name.toLowerCase().slice(-expectedSuffix.length) ===
          expectedSuffix
      );
    } catch (error) {
      return false;
    }
  }

  function openTrackedLink(url) {
    var app = telegramWebApp();
    try {
      if (app && typeof app.openLink === "function") {
        app.openLink(url);
        return true;
      }
    } catch (error) {}
    try {
      var opened = window.open(url, "_blank", "noopener,noreferrer");
      if (opened) return true;
    } catch (error) {}
    try {
      window.location.assign(url);
      return true;
    } catch (error) {
      return false;
    }
  }

  function launchTrackedDownload(data) {
    return new Promise(function (resolve, reject) {
      var pageUrl = data.download_page_url || data.download_url;
      if (openTrackedLink(pageUrl)) {
        resolve("open_link");
      } else {
        var error = new Error("desktop_download_open_failed");
        error.code = "desktop_download_open_failed";
        reject(error);
      }
    });
  }

  function showManualTransferUrl(url) {
    state.manualTransferUrl = url;
    state.destinationMessage = text().copyFailed;
    state.destinationMessageKind = "error";
    syncControls();
    var input = destinationRoot && destinationRoot.querySelector(
      "[data-pdd-manual-transfer-input]"
    );
    if (input) {
      try {
        input.focus();
        input.select();
      } catch (error) {}
    }
  }

  function legacyCopyText(value) {
    return new Promise(function (resolve, reject) {
      var input = element("textarea", "pdd-copy-helper");
      input.value = value;
      input.readOnly = true;
      input.setAttribute("aria-hidden", "true");
      document.body.appendChild(input);
      input.select();
      var copied = false;
      try {
        copied = Boolean(
          document.execCommand && document.execCommand("copy")
        );
      } catch (error) {}
      input.remove();
      if (copied) {
        resolve();
      } else {
        reject(new Error("clipboard_unavailable"));
      }
    });
  }

  function copyTransferUrl(url) {
    var operation = null;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        operation = navigator.clipboard.writeText(url);
      }
    } catch (error) {}
    var copyOperation = operation
      ? Promise.resolve(operation).catch(function () {
          return legacyCopyText(url);
        })
      : legacyCopyText(url);
    return copyOperation
      .then(function () {
        return "copy_link";
      })
      .catch(function () {
        showManualTransferUrl(url);
        var error = new Error("desktop_download_manual_copy_required");
        error.code = "desktop_download_manual_copy_required";
        throw error;
      });
  }

  function shareTransferUrl(url, platform) {
    if (!navigator.share) return copyTransferUrl(url);
    var payload = {
      title: "HSK AI · " + platformLabel(platform),
      text: text().destinationBody,
      url: url
    };
    try {
      if (navigator.canShare && !navigator.canShare(payload)) {
        return copyTransferUrl(url);
      }
    } catch (error) {}
    var shareOperation = null;
    try {
      shareOperation = navigator.share(payload);
    } catch (error) {
      return copyTransferUrl(url);
    }
    return Promise.resolve(shareOperation)
      .then(function () {
        return "web_share";
      })
      .catch(function (error) {
        if (error && error.name === "AbortError") {
          var cancelled = new Error("desktop_download_share_cancelled");
          cancelled.code = "desktop_download_share_cancelled";
          throw cancelled;
        }
        return copyTransferUrl(url);
      });
  }

  function prepareTransfer(destination, platform, transferUrl) {
    if (destination === "direct") return Promise.resolve("");
    var url = cleanTransferUrl(transferUrl, platform);
    if (!url) {
      var error = new Error("invalid_success_response");
      error.code = "invalid_success_response";
      return Promise.reject(error);
    }
    return destination === "share"
      ? shareTransferUrl(url, platform)
      : copyTransferUrl(url);
  }

  function markDownloadStarted(platform, source, id, transport) {
    if (!telegramInitData()) return;
    fetch(STARTED_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": telegramInitData()
      },
      body: JSON.stringify({
        platform: platform,
        source: source,
        event_id: id,
        transport: transport
      }),
      keepalive: true
    }).catch(function () {});
  }

  function completeDownload(platform, source, id, transport, trackStarted) {
    state.pendingPlatform = "";
    state.pendingDestination = "";
    state.errorCode = "";
    clearPendingEventId(platform, source);
    storeNumber("download_requested", Date.now());
    if (trackStarted) {
      markDownloadStarted(platform, source, id, transport);
    }
    closeDestinationChooser(false);
    syncMountedAdPromos();
    dismissAdPromo();
    showSuccess(platform, transport, source);
    try {
      var app = telegramWebApp();
      if (app && app.HapticFeedback) {
        app.HapticFeedback.notificationOccurred("success");
      }
    } catch (error) {}
  }

  function performDownloadRequest(
    platform,
    source,
    destination,
    retriedExpiredLink
  ) {
    var id = pendingEventId(platform, source);
    state.pendingPlatform = platform;
    state.pendingDestination = destination;
    state.errorCode = "";
    state.destinationMessage = "";
    state.destinationMessageKind = "";
    state.manualTransferUrl = "";
    state.lastPlatform = platform;
    syncControls();

    var controller = null;
    var timeoutId = 0;
    controller =
      typeof window.AbortController === "function"
        ? new window.AbortController()
        : null;
    var requestOptions = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": telegramInitData()
      },
      body: JSON.stringify({
        platform: platform,
        source: source,
        event_id: id,
        language: language()
      })
    };
    if (controller) requestOptions.signal = controller.signal;
    var timeoutPromise = new Promise(function (_, reject) {
      timeoutId = window.setTimeout(function () {
        if (controller) controller.abort();
        var timeoutError = new Error("desktop_download_timeout");
        timeoutError.code = "desktop_download_timeout";
        reject(timeoutError);
      }, REQUEST_TIMEOUT_MS);
    });

    Promise.race([fetch(REQUEST_ENDPOINT, requestOptions), timeoutPromise])
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            if (!response.ok) {
              var requestError = new Error("desktop_download_failed");
              requestError.code = responseErrorCode(response, data);
              throw requestError;
            }
            if (!validDownloadResponse(data, platform)) {
              var invalidError = new Error("invalid_success_response");
              invalidError.code = "invalid_success_response";
              throw invalidError;
            }
            return data;
          });
      })
      .then(function (data) {
        window.clearTimeout(timeoutId);
        return destination === "direct"
          ? launchTrackedDownload(data)
          : prepareTransfer(destination, platform, data.transfer_url);
      })
      .then(function (transport) {
        completeDownload(platform, source, id, transport, true);
      })
      .catch(function (error) {
        window.clearTimeout(timeoutId);
        state.pendingPlatform = "";
        state.pendingDestination = "";
        if (error && error.code === "desktop_download_link_expired") {
          clearPendingEventId(platform, source);
          if (!retriedExpiredLink) {
            performDownloadRequest(platform, source, destination, true);
            return;
          }
        }
        if (error && error.code === "desktop_download_share_cancelled") {
          state.destinationMessage = text().shareCancelled;
          state.destinationMessageKind = "neutral";
          syncControls();
          return;
        }
        if (error && error.code === "desktop_download_manual_copy_required") {
          syncControls();
          return;
        }
        state.errorCode =
          error && (error.code || error.name === "AbortError")
            ? error.code || "desktop_download_timeout"
            : "network_error";
        if (state.errorCode === "desktop_release_unavailable") {
          state.runtimeUnavailable[platform] = true;
        }
        syncControls();
      });
  }

  function showSuccess(platform, transport, source) {
    if (!promoRoot) return;
    var copy = text();
    state.promoOpen = true;
    promoRoot.replaceChildren();
    promoRoot.dataset.source = source || "";
    promoRoot.hidden = false;

    var backdrop = element("button", "pdd-promo-backdrop");
    backdrop.type = "button";
    backdrop.setAttribute("aria-label", copy.close);
    backdrop.addEventListener("click", closePromo);
    promoRoot.appendChild(backdrop);

    var shell = element("section", "pdd-promo-shell");
    shell.dataset.mode = "success";
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");
    shell.setAttribute("aria-labelledby", "pdd-success-title");
    var close = element("button", "pdd-promo-close");
    close.type = "button";
    close.setAttribute("aria-label", copy.close);
    close.appendChild(icon("x"));
    close.addEventListener("click", closePromo);
    shell.appendChild(close);

    var body = element("div", "pdd-promo-body");
    var successVisual = element("span", "pdd-success-visual");
    var successIcon =
      transport === "web_share"
        ? "share-3"
        : transport === "copy_link"
          ? "copy"
          : "download";
    successVisual.appendChild(icon(successIcon));
    body.appendChild(successVisual);
    var successTitle =
      transport === "web_share"
        ? copy.shareSuccessTitle
        : transport === "copy_link"
          ? copy.copySuccessTitle
          : copy.successTitle;
    var successBody =
      transport === "web_share"
        ? copy.shareSuccessBody
        : transport === "copy_link"
          ? copy.copySuccessBody
          : copy.successBody;
    var title = element("h2", "", successTitle);
    title.id = "pdd-success-title";
    body.appendChild(title);
    body.appendChild(element("p", "", successBody));
    var button = element("button", "pdd-return-button");
    button.type = "button";
    button.appendChild(icon("check"));
    button.appendChild(document.createTextNode(" " + copy.successAction));
    button.addEventListener("click", closePromo);
    body.appendChild(button);
    shell.appendChild(body);
    promoRoot.appendChild(shell);
    close.focus();
  }

  function promoMeta(meta) {
    var source = meta && typeof meta === "object" ? meta : {};
    var result = {};
    Object.keys(source).forEach(function (key) {
      var value = source[key];
      if (
        key !== "source" &&
        key !== "event_id" &&
        key !== "dedupe_key" &&
        (typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean")
      ) {
        result[key] = value;
      }
    });
    return result;
  }

  function promoPayload(source, meta) {
    return Object.assign(promoMeta(meta), { source: source });
  }

  function promoCooldownMs() {
    var days = Number(state.promoCooldownDays) || DEFAULT_PROMO_COOLDOWN_DAYS;
    return Math.max(1, Math.min(90, days)) * 24 * 60 * 60 * 1000;
  }

  function hasLocalPromoCooldown() {
    var cutoff = promoCooldownMs();
    var now = Date.now();
    return ["promo_seen", "download_requested"].some(function (name) {
      var timestamp = readStoredNumber(name);
      return timestamp > 0 && now - timestamp < cutoff;
    });
  }

  function hasLocalDownloadCooldown() {
    var timestamp = readStoredNumber("download_requested");
    return timestamp > 0 && Date.now() - timestamp < promoCooldownMs();
  }

  function promoPlacementAllowed(source) {
    return Boolean(
      PROMO_SOURCES.indexOf(source) >= 0 &&
        state.promoEligible &&
        state.promoPlacements[source]
    );
  }

  function shouldShowPromo(source) {
    if (
      isDesktop ||
      !telegramInitData() ||
      !state.availabilityLoaded ||
      !hasAvailablePlatform() ||
      !promoPlacementAllowed(source) ||
      state.promoSeenInSession ||
      state.promoOpen ||
      hasLocalPromoCooldown()
    ) {
      return false;
    }
    return true;
  }

  function shouldShowAdPromoEntry() {
    if (
      isDesktop ||
      !telegramInitData() ||
      !state.availabilityLoaded ||
      !hasAvailablePlatform() ||
      state.promoOpen ||
      state.destinationOpen ||
      state.promoReason === "already_installed" ||
      state.promoReason === "disabled" ||
      state.promoReason === "recent_request" ||
      hasLocalDownloadCooldown()
    ) {
      return false;
    }
    return true;
  }

  function safeForPromo() {
    if (document.visibilityState !== "visible") return false;
    if (
      typeof window.SCREEN === "string" &&
      window.SCREEN !== "course"
    ) {
      return false;
    }
    if (!document.querySelector("#s-course.on")) return false;
    if (
      document.querySelector(
        "#flow.on, #sheet.on, #paywall.on, #adov.on, #writeov.on, #levelup.on, #tour.on, #upov.on, #onboarding.on, .onboarding.on, [data-onboarding].on"
      )
    ) {
      return false;
    }
    if (document.querySelector('#pomp-ai-root[data-open="true"]')) {
      return false;
    }
    return true;
  }

  function schedulePromo() {
    var source = "home_prompt";
    if (state.promoTimer || state.queuedPromo || !shouldShowPromo(source)) return;
    var attempts = 0;
    function tryOpen() {
      state.promoTimer = 0;
      attempts += 1;
      if (state.queuedPromo || !shouldShowPromo(source)) return;
      if (safeForPromo()) {
        showPromo(source, {}, false);
        return;
      }
      if (attempts < 120) {
        state.promoTimer = window.setTimeout(tryOpen, 2500);
      }
    }
    state.promoTimer = window.setTimeout(tryOpen, 6500);
  }

  function drainQueuedPromo() {
    var queued = state.queuedPromo;
    if (!queued || !state.availabilityLoaded) return false;
    if (!shouldShowPromo(queued.source)) {
      state.queuedPromo = null;
      return false;
    }
    if (!safeForPromo()) {
      if (!state.queuedPromoTimer) {
        state.queuedPromoTimer = window.setTimeout(function () {
          state.queuedPromoTimer = 0;
          drainQueuedPromo();
        }, 350);
      }
      return false;
    }
    state.queuedPromo = null;
    return showPromo(queued.source, queued.meta, false);
  }

  function queuePromo(source, meta) {
    if (
      PROMO_SOURCES.indexOf(source) < 0 ||
      isDesktop ||
      !telegramInitData()
    ) {
      return false;
    }
    state.queuedPromo = { source: source, meta: promoMeta(meta) };
    if (state.promoTimer) {
      window.clearTimeout(state.promoTimer);
      state.promoTimer = 0;
    }
    if (!state.availabilityLoaded) return true;
    return drainQueuedPromo();
  }

  function buildPromoVisual() {
    var visual = element("div", "pdd-promo-visual");
    visual.appendChild(buildProductPreview("modal"));
    return visual;
  }

  function showPromo(source, meta, allowUnsafe) {
    if (
      !promoRoot ||
      !shouldShowPromo(source) ||
      (!allowUnsafe && !safeForPromo())
    ) {
      return false;
    }
    var copy = text();
    if (state.promoTimer) window.clearTimeout(state.promoTimer);
    if (state.queuedPromoTimer) window.clearTimeout(state.queuedPromoTimer);
    state.promoTimer = 0;
    state.queuedPromoTimer = 0;
    state.queuedPromo = null;
    state.promoOpen = true;
    state.promoSeenInSession = true;
    state.activePromoSource = source;
    state.activePromoMeta = promoMeta(meta);
    state.previousFocus = document.activeElement;
    storeNumber("promo_seen", Date.now());
    trackEntrySeen(source, state.activePromoMeta);
    track("desktop_promo_seen", promoPayload(source, state.activePromoMeta));

    promoRoot.replaceChildren();
    promoRoot.dataset.source = source;
    promoRoot.hidden = false;
    var backdrop = element("button", "pdd-promo-backdrop");
    backdrop.type = "button";
    backdrop.setAttribute("aria-label", copy.dismiss);
    backdrop.addEventListener("click", dismissPromo);
    promoRoot.appendChild(backdrop);

    var shell = element("section", "pdd-promo-shell");
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");
    shell.setAttribute("aria-labelledby", "pdd-promo-title");
    var close = element("button", "pdd-promo-close");
    close.type = "button";
    close.setAttribute("aria-label", copy.close);
    close.appendChild(icon("x"));
    close.addEventListener("click", dismissPromo);
    shell.appendChild(close);
    shell.appendChild(buildPromoVisual());

    var body = element("div", "pdd-promo-body");
    body.appendChild(element("span", "pdd-eyebrow", copy.eyebrow));
    var title = element("h2", "", copy.promoTitle);
    title.id = "pdd-promo-title";
    body.appendChild(title);
    body.appendChild(element("p", "", copy.promoBody));
    body.appendChild(buildBenefits(true));
    body.appendChild(buildActions(source));
    body.appendChild(buildInlineStatus());
    var later = element("button", "pdd-promo-dismiss", copy.dismiss);
    later.type = "button";
    later.addEventListener("click", dismissPromo);
    body.appendChild(later);
    shell.appendChild(body);
    promoRoot.appendChild(shell);
    syncControls();
    close.focus();
    return true;
  }

  function closePromo() {
    if (!promoRoot) return;
    var previousFocus = state.previousFocus;
    state.promoOpen = false;
    state.errorCode = "";
    state.activePromoSource = "";
    state.activePromoMeta = {};
    promoRoot.hidden = true;
    delete promoRoot.dataset.source;
    promoRoot.replaceChildren();
    syncControls();
    if (!previousFocus || !previousFocus.isConnected || previousFocus.hidden) {
      previousFocus = document.querySelector(
        "#ad-sub-cont:not(:disabled), #nav button.on, #pomp-ai-launcher"
      );
    }
    if (previousFocus && typeof previousFocus.focus === "function") {
      try {
        previousFocus.focus();
      } catch (error) {}
    }
    state.previousFocus = null;
  }

  function dismissPromo() {
    if (!state.promoOpen) return;
    track(
      "desktop_promo_dismissed",
      promoPayload(state.activePromoSource, state.activePromoMeta)
    );
    closePromo();
  }

  function dismissAdPromo() {
    var host = document.getElementById("ad-desktop");
    if (!host) return;
    host.hidden = true;
    host.replaceChildren();
  }

  function buildAdDownloadBlock() {
    var copy = text();
    var block = element("section", "pdd-ad-download");
    block.dataset.pddAdDownload = "true";

    var heading = element("div", "pdd-ad-download-head");
    var badge = element("span", "pdd-ad-download-badge");
    var avatar = element("img", "");
    avatar.src = "/assets/hsk-ai-avatar.webp";
    avatar.alt = "";
    avatar.setAttribute("aria-hidden", "true");
    badge.appendChild(avatar);
    heading.appendChild(badge);
    var labels = element("span", "pdd-ad-download-copy");
    labels.appendChild(element("strong", "", copy.adEntry));
    labels.appendChild(element("small", "", copy.adEntrySub));
    heading.appendChild(labels);
    block.appendChild(heading);

    var actions = buildActions("ad_promo");
    actions.classList.add("pdd-ad-download-actions");
    block.appendChild(actions);
    block.appendChild(buildInlineStatus());
    return block;
  }

  function renderAdActions(host, meta) {
    if (!host) return;
    if (!host.querySelector("[data-pdd-ad-download]")) {
      host.replaceChildren(buildAdDownloadBlock());
    }
    host.classList.add("pdd-ad-actions-host");
    host.hidden = false;
    trackEntrySeen("ad_promo", meta);
    syncControls();
  }

  function hideAdActions(host) {
    if (!host) return;
    host.hidden = true;
    host.replaceChildren();
  }

  function syncAdPromo(visible) {
    var host = document.getElementById("ad-desktop");
    if (!host) return;
    if (!visible || !shouldShowAdPromoEntry()) {
      dismissAdPromo();
      return;
    }
    renderAdActions(host, { placement: "course_ad_end" });
  }

  function syncMountedAdPromos() {
    state.adPromoMounts = state.adPromoMounts.filter(function (mount) {
      if (!mount.host || !mount.host.isConnected) return false;
      var visible = shouldShowAdPromoEntry();
      if (visible) {
        renderAdActions(mount.host, mount.meta);
      } else {
        hideAdActions(mount.host);
      }
      return true;
    });
  }

  function mountAdPromoTrigger(host, meta) {
    if (!host) return;
    var mount = null;
    state.adPromoMounts.forEach(function (candidate) {
      if (candidate.host === host) mount = candidate;
    });
    if (!mount) {
      mount = { host: host, meta: {} };
      state.adPromoMounts.push(mount);
    }
    mount.meta = promoMeta(meta);
    if (shouldShowAdPromoEntry()) {
      renderAdActions(host, mount.meta);
    } else {
      hideAdActions(host);
    }
  }

  function loadAvailability() {
    if (state.availabilityLoading) return;
    if (isDesktop || !telegramInitData()) {
      state.availabilityLoaded = true;
      renderProfile();
      return;
    }
    state.availabilityLoading = true;
    renderProfile();
    fetch(STATUS_ENDPOINT, {
      headers: { "X-Telegram-Init-Data": telegramInitData() }
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            if (!response.ok || !data || data.ok !== true) {
              throw new Error("desktop_status_failed");
            }
            state.availabilityLoaded = true;
            state.availabilityError = false;
            state.enabled = data.enabled === true;
            state.platforms.macos = Boolean(
              data.platforms && data.platforms.macos
            );
            state.platforms.windows = Boolean(
              data.platforms && data.platforms.windows
            );
            state.transferUrls.macos = cleanTransferUrl(
              data.downloads && data.downloads.macos,
              "macos"
            );
            state.transferUrls.windows = cleanTransferUrl(
              data.downloads && data.downloads.windows,
              "windows"
            );
            var promo =
              data.promo && typeof data.promo === "object" ? data.promo : {};
            var placements =
              promo.placements && typeof promo.placements === "object"
                ? promo.placements
                : {};
            state.promoEligible = promo.eligible === true;
            state.promoReason =
              typeof promo.reason === "string" ? promo.reason : "";
            state.promoCooldownDays = Math.max(
              1,
              Math.min(
                90,
                Number(promo.cooldown_days) || DEFAULT_PROMO_COOLDOWN_DAYS
              )
            );
            PROMO_SOURCES.forEach(function (source) {
              state.promoPlacements[source] = placements[source] === true;
            });
          });
      })
      .catch(function () {
        state.availabilityLoaded = true;
        state.availabilityError = true;
        state.enabled = false;
        state.platforms.macos = false;
        state.platforms.windows = false;
        state.transferUrls.macos = "";
        state.transferUrls.windows = "";
        state.promoEligible = false;
        state.promoReason = "";
        PROMO_SOURCES.forEach(function (source) {
          state.promoPlacements[source] = false;
        });
      })
      .then(function () {
        state.availabilityLoading = false;
        renderProfile();
        syncMountedAdPromos();
        var adSubscribe = document.getElementById("ad-sub");
        syncAdPromo(
          Boolean(
            adSubscribe &&
              !adSubscribe.hidden &&
              adSubscribe.style.display !== "none"
          )
        );
        if (!drainQueuedPromo()) schedulePromo();
      });
  }

  function trapDialogFocus(event, root) {
    if (event.key !== "Tab" || !root) return;
    var focusable = Array.prototype.slice.call(
      root.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), [href], [tabindex]:not([tabindex="-1"])'
      )
    ).filter(function (node) {
      return !node.hidden && node.getClientRects().length > 0;
    });
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  document.addEventListener("keydown", function (event) {
    if (state.destinationOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDestinationChooser(true);
      } else {
        trapDialogFocus(event, destinationRoot);
      }
      return;
    }
    if (event.key === "Escape" && state.promoOpen) {
      event.preventDefault();
      if (promoRoot && promoRoot.querySelector('[data-mode="success"]')) {
        closePromo();
      } else {
        dismissPromo();
      }
    }
  });

  window.PompDesktopDownload = {
    dismissAdPromo: dismissAdPromo,
    queuePromo: queuePromo,
    renderProfile: renderProfile,
    refreshAvailability: loadAvailability,
    mountAdPromoTrigger: mountAdPromoTrigger,
    syncAdPromo: syncAdPromo
  };

  renderProfile();
  loadAvailability();
})();
