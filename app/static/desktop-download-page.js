(function () {
  "use strict";

  var STATUS_ENDPOINT = "/api/v3/desktop-download/public-status";
  var params = new URLSearchParams(window.location.search || "");
  var supportedPlatforms = ["macos", "windows"];
  var supportedLanguages = ["uz", "ru", "tj"];

  var COPY = {
    uz: {
      skip: "Yuklashga o‘tish",
      brandNote: "Kompyuter ilovasi",
      eyebrow: "Kurs · progress · AI yordamchi",
      title: "Xitoy tilini katta ekranda davom ettiring.",
      lead: "Telegramdagi hisobingiz, obunangiz va dars natijalaringiz shu ilovada ham ishlaydi.",
      featureCourse: "Bir xil kurs va progress",
      featureAi: "Yon paneldagi AI yordamchi",
      featureUpdate: "Avtomatik yangilanish",
      readyLabel: "Tayyor installer",
      freeDownload: "Bepul yuklash",
      loading: "Tayyorlanmoqda…",
      checking: "Mos versiya tekshirilmoqda.",
      unavailable: "Bu platforma uchun installer hali chiqarilmagan.",
      ready: "Fayl Pomp HSK AI rasmiy download serveridan yuklanadi.",
      opening: "Yuklash ochilmoqda…",
      macTitle: "Mac uchun Pomp HSK AI",
      windowsTitle: "Windows uchun Pomp HSK AI",
      macDownload: "Mac uchun DMG yuklash",
      windowsDownload: "Windows uchun EXE yuklash",
      version: "Versiya {version}",
      guideEyebrow: "O‘rnatish",
      guideTitle: "Uch qadamda tayyor",
      macSteps: [
        ["DMG faylni yuklang", "Yuqoridagi tugma universal Mac installerini kompyuteringizga saqlaydi."],
        ["Applications ichiga tashlang", "DMG’ni oching va Pomp HSK AI ikonkasini Applications ustiga suring."],
        ["Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."]
      ],
      windowsSteps: [
        ["EXE setup’ni yuklang", "Yuqoridagi tugma Windows x64 installerini kompyuteringizga saqlaydi."],
        ["Install tugmasini bosing", "Setup’ni oching. Ilova joriy foydalanuvchi uchun o‘rnatiladi."],
        ["Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."]
      ],
      securityTitle: "Birinchi ochishda ogohlantirish chiqishi mumkin",
      macSecurity: "macOS’da avval ilovani ochishga urining, keyin System Settings → Privacy & Security → Open Anyway’ni bosing.",
      windowsSecurity: "Windows SmartScreen chiqsa, fayl nomi Pomp HSK AI ekanini tekshiring. Smart App Control bloklagan qurilmada himoyani o‘chirmang.",
      mobileEyebrow: "Telefon orqali ochdingiz",
      mobileTitle: "Linkni kompyuteringizga yuboring",
      mobileBody: "Installer faqat Mac yoki Windows’da ishlaydi.",
      copyLink: "Linkni nusxalash",
      copied: "Nusxalandi",
      footer: "Kurs markazda. AI yordamchi sifatida."
    },
    ru: {
      skip: "Перейти к загрузке",
      brandNote: "Приложение для компьютера",
      eyebrow: "Курс · прогресс · AI-помощник",
      title: "Продолжайте китайский на большом экране.",
      lead: "Ваш Telegram-аккаунт, подписка и результаты уроков работают и в приложении.",
      featureCourse: "Единый курс и прогресс",
      featureAi: "AI-помощник в боковой панели",
      featureUpdate: "Автоматические обновления",
      readyLabel: "Установщик готов",
      freeDownload: "Бесплатная загрузка",
      loading: "Подготавливаем…",
      checking: "Проверяем подходящую версию.",
      unavailable: "Установщик для этой платформы ещё не опубликован.",
      ready: "Файл загружается с официального сервера Pomp HSK AI.",
      opening: "Открываем загрузку…",
      macTitle: "Pomp HSK AI для Mac",
      windowsTitle: "Pomp HSK AI для Windows",
      macDownload: "Скачать DMG для Mac",
      windowsDownload: "Скачать EXE для Windows",
      version: "Версия {version}",
      guideEyebrow: "Установка",
      guideTitle: "Готово за три шага",
      macSteps: [
        ["Скачайте DMG", "Кнопка выше сохранит универсальный установщик для Mac."],
        ["Перетащите в Applications", "Откройте DMG и перетащите Pomp HSK AI в папку Applications."],
        ["Подключите Telegram", "Подтвердите код приложения в Telegram. Подписка и прогресс появятся автоматически."]
      ],
      windowsSteps: [
        ["Скачайте EXE", "Кнопка выше сохранит установщик Windows x64."],
        ["Нажмите Install", "Откройте setup. Приложение установится для текущего пользователя."],
        ["Подключите Telegram", "Подтвердите код приложения в Telegram. Подписка и прогресс появятся автоматически."]
      ],
      securityTitle: "При первом запуске может появиться предупреждение",
      macSecurity: "Сначала попробуйте открыть приложение, затем выберите System Settings → Privacy & Security → Open Anyway.",
      windowsSecurity: "Если появился SmartScreen, проверьте имя файла Pomp HSK AI. Не отключайте Smart App Control, если он заблокировал приложение.",
      mobileEyebrow: "Страница открыта на телефоне",
      mobileTitle: "Отправьте ссылку на компьютер",
      mobileBody: "Установщик работает только на Mac или Windows.",
      copyLink: "Скопировать ссылку",
      copied: "Скопировано",
      footer: "Курс — в центре. AI — помощник."
    },
    tj: {
      skip: "Гузаштан ба боргирӣ",
      brandNote: "Барномаи компютерӣ",
      eyebrow: "Курс · пешрафт · ёвари AI",
      title: "Омӯзиши забони чиниро дар экрани калон идома диҳед.",
      lead: "Ҳисоби Telegram, обуна ва натиҷаҳои дарсҳо дар барнома ҳам кор мекунанд.",
      featureCourse: "Курс ва пешрафти умумӣ",
      featureAi: "Ёвари AI дар панели паҳлӯӣ",
      featureUpdate: "Навсозии автоматӣ",
      readyLabel: "Насбкунанда омода",
      freeDownload: "Боргирии ройгон",
      loading: "Омода мешавад…",
      checking: "Версияи мувофиқ санҷида мешавад.",
      unavailable: "Насбкунандаи ин платформа ҳоло нашр нашудааст.",
      ready: "Файл аз сервери расмии Pomp HSK AI бор мешавад.",
      opening: "Боргирӣ кушода мешавад…",
      macTitle: "Pomp HSK AI барои Mac",
      windowsTitle: "Pomp HSK AI барои Windows",
      macDownload: "DMG барои Mac",
      windowsDownload: "EXE барои Windows",
      version: "Версияи {version}",
      guideEyebrow: "Насб",
      guideTitle: "Дар се қадам омода",
      macSteps: [
        ["DMG-ро бор кунед", "Тугмаи боло насбкунандаи универсалии Mac-ро нигоҳ медорад."],
        ["Ба Applications гузаронед", "DMG-ро кушоед ва Pomp HSK AI-ро ба Applications кашед."],
        ["Telegram-ро пайваст кунед", "Рамзи барномаро дар Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."]
      ],
      windowsSteps: [
        ["EXE-ро бор кунед", "Тугмаи боло насбкунандаи Windows x64-ро нигоҳ медорад."],
        ["Install-ро пахш кунед", "Setup-ро кушоед. Барнома барои корбари ҷорӣ насб мешавад."],
        ["Telegram-ро пайваст кунед", "Рамзи барномаро дар Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."]
      ],
      securityTitle: "Ҳангоми кушодани аввал огоҳӣ баромада метавонад",
      macSecurity: "Аввал барномаро кушоед, баъд System Settings → Privacy & Security → Open Anyway-ро пахш кунед.",
      windowsSecurity: "Агар SmartScreen барояд, номи Pomp HSK AI-ро санҷед. Агар Smart App Control барномаро баст, муҳофизатро хомӯш накунед.",
      mobileEyebrow: "Саҳифа дар телефон кушода шуд",
      mobileTitle: "Пайвандро ба компютер фиристед",
      mobileBody: "Насбкунанда танҳо дар Mac ё Windows кор мекунад.",
      copyLink: "Нусхаи пайванд",
      copied: "Нусха шуд",
      footer: "Курс дар марказ. AI ҳамчун ёрдамчӣ."
    }
  };

  var state = {
    language: initialLanguage(),
    platform: initialPlatform(),
    release: null
  };

  function initialLanguage() {
    var requested = String(params.get("lang") || "").toLowerCase();
    if (supportedLanguages.indexOf(requested) >= 0) return requested;
    var browserLanguage = String(navigator.language || "").toLowerCase();
    if (browserLanguage.indexOf("tj") === 0) return "tj";
    if (browserLanguage.indexOf("uz") === 0) return "uz";
    if (browserLanguage.indexOf("ru") === 0) return "ru";
    return "uz";
  }

  function detectedPlatform() {
    var source = String(
      (navigator.userAgentData && navigator.userAgentData.platform) ||
        navigator.platform ||
        navigator.userAgent ||
        ""
    ).toLowerCase();
    if (source.indexOf("win") >= 0) return "windows";
    if (source.indexOf("mac") >= 0) return "macos";
    return "macos";
  }

  function initialPlatform() {
    var requested = String(params.get("platform") || "").toLowerCase();
    return supportedPlatforms.indexOf(requested) >= 0
      ? requested
      : detectedPlatform();
  }

  function copy() {
    return COPY[state.language];
  }

  function isMobile() {
    var userAgent = String(navigator.userAgent || "");
    return (
      /Android|iPhone|iPod/i.test(userAgent) ||
      (/iPad|Macintosh/i.test(userAgent) &&
        Number(navigator.maxTouchPoints || 0) > 1)
    );
  }

  function validRequestToken() {
    var token = String(params.get("request") || "");
    return /^[0-9a-f]{32}$/.test(token) ? token : "";
  }

  function setText(selector, value) {
    var node = document.querySelector(selector);
    if (node) node.textContent = value;
  }

  function applyLanguage() {
    var localized = copy();
    document.documentElement.lang = state.language;
    document.querySelectorAll("[data-i18n]").forEach(function (node) {
      var value = localized[node.dataset.i18n];
      if (typeof value === "string") node.textContent = value;
    });
    document.querySelectorAll("[data-language]").forEach(function (button) {
      button.setAttribute(
        "aria-pressed",
        button.dataset.language === state.language ? "true" : "false"
      );
    });
    renderPlatform();
  }

  function releaseAvailable(platform) {
    return Boolean(
      state.release &&
        state.release.enabled &&
        state.release.platforms &&
        state.release.platforms[platform] &&
        state.release.downloads &&
        state.release.downloads[platform]
    );
  }

  function downloadUrl(platform) {
    if (!releaseAvailable(platform)) return "";
    var base = String(state.release.downloads[platform] || "");
    var token = validRequestToken();
    if (!token) return base;
    var url = new URL(base, window.location.origin);
    url.searchParams.set("request", token);
    return url.toString();
  }

  function renderSteps() {
    var steps =
      state.platform === "macos" ? copy().macSteps : copy().windowsSteps;
    ["one", "two", "three"].forEach(function (key, index) {
      setText('[data-step-title="' + key + '"]', steps[index][0]);
      setText('[data-step-body="' + key + '"]', steps[index][1]);
    });
  }

  function renderInstallerStage() {
    var stage = document.querySelector("[data-installer-stage]");
    if (!stage) return;
    stage.dataset.installerStage = state.platform;
    if (state.platform === "windows") {
      stage.querySelector(".drag-arrow").textContent = "✓";
      stage.querySelector(".applications-folder span").textContent = "⊞";
      stage.querySelector(".applications-folder small").textContent = "Install";
    } else {
      stage.querySelector(".drag-arrow").textContent = "→";
      stage.querySelector(".applications-folder span").textContent = "A";
      stage.querySelector(".applications-folder small").textContent =
        "Applications";
    }
  }

  function renderPlatform() {
    var localized = copy();
    document.querySelectorAll("[data-platform]").forEach(function (button) {
      button.setAttribute(
        "aria-pressed",
        button.dataset.platform === state.platform ? "true" : "false"
      );
    });

    setText(
      "[data-download-title]",
      state.platform === "macos"
        ? localized.macTitle
        : localized.windowsTitle
    );
    setText(
      "[data-download-label]",
      state.platform === "macos"
        ? localized.macDownload
        : localized.windowsDownload
    );
    setText(
      "[data-security-copy]",
      state.platform === "macos"
        ? localized.macSecurity
        : localized.windowsSecurity
    );
    renderSteps();
    renderInstallerStage();
    renderRelease();
  }

  function renderRelease() {
    var localized = copy();
    var button = document.querySelector("[data-download-button]");
    var status = document.querySelector("[data-download-status]");
    var version =
      state.release &&
      state.release.versions &&
      state.release.versions[state.platform];

    setText(
      "[data-version]",
      version
        ? localized.version.replace("{version}", String(version))
        : localized.checking
    );
    if (!button || !status) return;

    var url = downloadUrl(state.platform);
    if (!url) {
      button.href = "#";
      button.setAttribute("aria-disabled", "true");
      status.dataset.state = state.release ? "error" : "checking";
      status.lastElementChild.textContent = state.release
        ? localized.unavailable
        : localized.checking;
      return;
    }

    button.href = url;
    button.removeAttribute("aria-disabled");
    status.dataset.state = "ready";
    status.lastElementChild.textContent = localized.ready;
  }

  function setPlatform(platform) {
    if (supportedPlatforms.indexOf(platform) < 0) return;
    state.platform = platform;
    renderPlatform();
    var nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("platform", platform);
    window.history.replaceState({}, "", nextUrl);
  }

  function setLanguage(language) {
    if (supportedLanguages.indexOf(language) < 0) return;
    state.language = language;
    applyLanguage();
    var nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("lang", language);
    window.history.replaceState({}, "", nextUrl);
  }

  function loadRelease() {
    fetch(STATUS_ENDPOINT, {
      headers: { Accept: "application/json" },
      cache: "no-store"
    })
      .then(function (response) {
        if (!response.ok) throw new Error("release_status_failed");
        return response.json();
      })
      .then(function (payload) {
        state.release = payload && payload.ok === true ? payload : {};
        renderRelease();
      })
      .catch(function () {
        state.release = {};
        renderRelease();
      });
  }

  function bindEvents() {
    document.querySelectorAll("[data-platform]").forEach(function (button) {
      button.addEventListener("click", function () {
        setPlatform(button.dataset.platform);
      });
    });
    document.querySelectorAll("[data-language]").forEach(function (button) {
      button.addEventListener("click", function () {
        setLanguage(button.dataset.language);
      });
    });

    var downloadButton = document.querySelector("[data-download-button]");
    if (downloadButton) {
      downloadButton.addEventListener("click", function (event) {
        if (downloadButton.getAttribute("aria-disabled") === "true") {
          event.preventDefault();
          return;
        }
        setText("[data-download-label]", copy().opening);
      });
    }

    var copyButton = document.querySelector("[data-copy-link]");
    if (copyButton) {
      copyButton.addEventListener("click", function () {
        var cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete("request");
        var operation =
          navigator.clipboard && navigator.clipboard.writeText
            ? navigator.clipboard.writeText(cleanUrl.toString())
            : Promise.reject(new Error("clipboard_unavailable"));
        operation
          .then(function () {
            copyButton.textContent = copy().copied;
          })
          .catch(function () {
            window.prompt("", cleanUrl.toString());
          });
      });
    }
  }

  function init() {
    bindEvents();
    var mobileTransfer = document.querySelector("[data-mobile-transfer]");
    if (mobileTransfer) mobileTransfer.hidden = !isMobile();
    applyLanguage();
    loadRelease();
  }

  init();
})();
