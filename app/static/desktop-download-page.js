(function () {
  "use strict";

  var STATUS_ENDPOINT = "/api/v3/apps/public-status";
  var params = new URLSearchParams(window.location.search || "");
  var supportedPlatforms = ["ios", "macos", "android", "windows"];
  // iOS has no build of its own. It is offered because an iPhone owner
  // deserves an answer, and the answer is the Mini App inside Telegram.
  var BOT_URL = "https://t.me/darsi_chini_bot";
  // The copy keys are prefixed per platform; `macos` is historically "mac".
  var COPY_KEY = { ios: "ios", macos: "mac", android: "android", windows: "windows" };
  // The quick guide keeps one step list per platform in the DOM; the prefix
  // says which slots to fill, the badge says whose instructions these are.
  var QUICK_PREFIX = { macos: "m", windows: "w", android: "a" };
  var QUICK_BADGE = { macos: "macOS", windows: "Windows", android: "Android" };

  function forPlatform(localized, suffix) {
    return localized[COPY_KEY[state.platform] + suffix];
  }
  var supportedLanguages = ["uz", "ru", "tj"];

  var COPY = {
    uz: {
      iosSecurityTitle: "Hech narsa o‘rnatilmaydi",
      androidSecurityTitle: "O‘rnatishda ogohlantirish chiqishi mumkin",
      macSecurityTitle: "Birinchi ochishda ogohlantirish chiqishi mumkin",
      windowsSecurityTitle: "Birinchi ochishda ogohlantirish chiqishi mumkin",
      iosTitle: "iPhone va iPad uchun",
      iosDownload: "Telegramda ochish",
      iosStatus: "iOS uchun alohida ilova hozircha yo‘q — Telegram ichidagi Mini App to‘liq ishlaydi.",
      iosSecurity: "Mini App Telegram ichida ochiladi. Hech narsa o‘rnatilmaydi, hisobingiz va progressingiz o‘sha yerda qoladi.",
      iosSteps: [
        ["Telegramni oching", "Yuqoridagi tugma botni ochadi."],
        ["Kursni boshlang", "Mini App darslar, mashq va AI yordamchini to‘liq beradi."],
        ["Alohida ilova kutmang", "iOS uchun ilova tayyor bo‘lganda shu sahifada paydo bo‘ladi."],
      ],
      androidTitle: "Android uchun HSK AI",
      androidDownload: "APK yuklab olish",
      androidSecurity: "Android «noma’lum manbalar» haqida ogohlantirishi mumkin: ruxsat bering va davom eting. Bu — bizning rasmiy faylimiz.",
      androidSteps: [
        ["APK faylni yuklang", "Yuqoridagi tugma faylni telefoningizga saqlaydi."],
        ["Faylni oching va o‘rnating", "Yuklangan faylni bosing → «O‘rnatish»."],
        ["Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."],
      ],
      allTitle: "Barcha yuklamalar",
      allLead: "Har bir qurilma uchun oxirgi versiya.",
      allUnavailable: "hali chiqarilmagan",
      skip: "Yuklashga o‘tish",
      brandNote: "Ilovalar",
      eyebrow: "Kurs · progress · AI yordamchi",
      title: "Yuklab olish",
      lead: "Qurilmangizni tanlang",
      featureCourse: "Bir xil kurs va progress",
      featureAi: "Yon paneldagi AI yordamchi",
      featureUpdate: "Avtomatik yangilanish",
      readyLabel: "Tayyor installer",
      freeDownload: "Bepul yuklash",
      selectTitle: "Qurilmangizni tanlang",
      selectBody: "Qurilmangizni tanlang — mos fayl yoki havola ko‘rsatiladi.",
      selectDownload: "Avval qurilmangizni tanlang",
      loading: "Tayyorlanmoqda…",
      checking: "Mos versiya tekshirilmoqda.",
      unavailable: "Bu platforma uchun installer hali chiqarilmagan.",
      ready: "Fayl HSK AI rasmiy download serveridan yuklanadi.",
      opening: "Yuklash ochilmoqda…",
      downloadAgain: "Qayta yuklash",
      macTitle: "Mac uchun HSK AI",
      windowsTitle: "Windows uchun HSK AI",
      macDownload: "Mac uchun DMG yuklash",
      windowsDownload: "Windows uchun EXE yuklash",
      version: "Versiya {version}",
      guideEyebrow: "O‘rnatish",
      guideTitle: "Uch qadamda tayyor",
      macSteps: [
        ["DMG faylni yuklang", "Yuqoridagi tugma universal Mac installerini kompyuteringizga saqlaydi."],
        ["Applications ichiga tashlang", "DMG’ni oching va HSK AI ikonkasini Applications ustiga suring."],
        ["Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."]
      ],
      windowsSteps: [
        ["EXE setup’ni yuklang", "Yuqoridagi tugma Windows x64 installerini kompyuteringizga saqlaydi."],
        ["Install tugmasini bosing", "Setup’ni oching. Ilova joriy foydalanuvchi uchun o‘rnatiladi."],
        ["Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."]
      ],
      securityTitle: "Birinchi ochishda ogohlantirish chiqishi mumkin",
      macSecurity: "macOS bloklasa: Applications ichida HSK AI ustida o‘ng tugma → Open → Open. Hali ham bloklansa, System Settings → Privacy & Security → Open Anyway’ni bosing.",
      windowsSecurity: "Windows SmartScreen chiqsa: More info → Run anyway → Yes’ni bosing. Fayl nomi HSK AI ekanini tekshiring.",
      quickGuideEyebrow: "Yuklash boshlandi",
      quickGuideTitle: "Yuklab bo‘lgach, shunday oching",
      quickGuideLead: "Brauzerning yuqori o‘ngidagi yuklash belgisi tugashini kuting. Bu oynani hozircha yopmang.",
      quickGuideProgress: "Fayl yuklanmoqda",
      quickGuideClose: "Tushundim",
      quickGuideCloseAria: "Qo‘llanmani yopish",
      quickGuideFooter: "Ilova ochilgach, undagi kodni Telegram orqali tasdiqlang.",
      visualRightClick: "O‘ng tugma",
      visualMacOpen: "Open",
      visualOr: "yoki",
      visualSettings: "Privacy & Security",
      visualOpenAnyway: "Open Anyway",
      visualWindowsBlocked: "Windows kompyuteringizni himoya qildi",
      visualMoreInfo: "More info",
      visualRunAnyway: "Run anyway",
      visualInstall: "Install",
      visualOpenApp: "Ilovani ochish",
      macQuickSteps: [
        ["DMG’ni oching", "Downloads (↓) ichidan yuklangan .dmg faylini bosing."],
        ["Applications’ga torting", "Ochilgan oynada HSK AI ikonkasini Applications papkasiga suring."],
        ["Birinchi ochishda ogohlantirish chiqadi", "«Файл «HSK AI» не был открыт» oynasida «Готово» ni bosing. «Переместить в Корзину» ni bosmang."],
        ["System Settings’dan ruxsat bering", "Konfidensiallik va xavfsizlik bo‘limini oching, pastga tushing va «Все равно открыть» ni bosing."],
        ["Tasdiqlang", "Chiqqan oynada yana «Все равно открыть», so‘ng Touch ID yoki admin parolini kiriting."],
        ["Keychain’ga «Разрешать всегда» deng", "Ilova ochilganda parol so‘raladi. «Разрешать всегда» ni tanlang — shunda keyingi safar so‘ramaydi."]
      ],
      quickShotAlts: {
        m2: "DMG oynasi: HSK AI ikonkasi va Applications papkasi",
        m3: "macOS ogohlantirishi: «Файл «HSK AI» не был открыт»",
        m4: "System Settings, xavfsizlik bo‘limi: «Все равно открыть» tugmasi",
        m5: "Tasdiqlash oynasi: «Все равно открыть»",
        m5b: "Touch ID yoki admin paroli so‘rovi",
        m6: "Keychain so‘rovi, «Разрешать всегда» tugmasi ajratilgan"
      },
      windowsQuickSteps: [
        ["EXE’ni oching", "Downloads (↓) ichidan yuklangan .exe faylini bosing."],
        ["SmartScreen bloklasa", "Rasmdagi More info, keyin Run anyway va Yes’ni bosing."],
        ["O‘rnating va oching", "Install tugmasini bosing, so‘ng Start menyusidan ilovani oching."]
      ],
      androidQuickLead:
        "Yuklab olish tugashini kuting. Fayl bildirishnomada yoki «Yuklamalar» papkasida paydo bo‘ladi.",
      androidQuickSteps: [
        ["Yuklangan APK’ni oching", "Bildirishnomadagi faylni bosing yoki «Yuklamalar» papkasidan HSK AI faylini toping."],
        ["Shu manbadan o‘rnatishga ruxsat bering", "Android so‘rasa: «Sozlamalar» → «Shu manbadan o‘rnatishga ruxsat berish» ni yoqing va orqaga qayting."],
        ["«O‘rnatish» ni bosing", "Play Protect tekshiruvi chiqsa «Baribir o‘rnatish» ni tanlang. Bu — HSK AI rasmiy fayli."],
        ["Ilovani oching va Telegram hisobingizni ulang", "Ilovadagi kodni Telegram orqali tasdiqlang. Obuna va progress avtomatik keladi."]
      ],
      mobileEyebrow: "Telefon orqali ochdingiz",
      mobileTitle: "Linkni kompyuteringizga yuboring",
      mobileBody:
        "Avval kompyuteringiz turini tanlang. Telefonda yuklangan DMG/EXE Downloads yoki Fayllarga tushadi, lekin faqat Mac yoki Windows’da ochiladi.",
      shareLink: "AirDrop yoki ulashish",
      copyLink: "Linkni nusxalash",
      copied: "Nusxalandi",
      shared: "Ulashish oynasi ochildi",
      copyFailed: "Avtomatik nusxalanmadi. Quyidagi linkni qo‘lda nusxalang.",
      manualLinkLabel: "Kompyuterda ochiladigan xavfsiz link",
      footer: "Kurs markazda. AI yordamchi sifatida."
    },
    ru: {
      iosSecurityTitle: "Ничего устанавливать не нужно",
      androidSecurityTitle: "При установке может появиться предупреждение",
      macSecurityTitle: "При первом запуске может появиться предупреждение",
      windowsSecurityTitle: "При первом запуске может появиться предупреждение",
      iosTitle: "Для iPhone и iPad",
      iosDownload: "Открыть в Telegram",
      iosStatus: "Отдельного приложения для iOS пока нет — Mini App в Telegram работает полностью.",
      iosSecurity: "Mini App открывается внутри Telegram. Ничего устанавливать не нужно, аккаунт и прогресс остаются там же.",
      iosSteps: [
        ["Откройте Telegram", "Кнопка выше открывает бота."],
        ["Начните курс", "Mini App даёт уроки, практику и AI-помощника полностью."],
        ["Отдельного приложения ждать не нужно", "Когда приложение для iOS будет готово, оно появится на этой странице."],
      ],
      androidTitle: "HSK AI для Android",
      androidDownload: "Скачать APK",
      androidSecurity: "Android может предупредить о «неизвестных источниках»: разрешите и продолжите. Это наш официальный файл.",
      androidSteps: [
        ["Скачайте APK", "Кнопка выше сохранит файл на телефон."],
        ["Откройте файл и установите", "Нажмите на скачанный файл → «Установить»."],
        ["Подключите аккаунт Telegram", "Подтвердите код из приложения через Telegram. Подписка и прогресс придут автоматически."],
      ],
      allTitle: "Все загрузки",
      allLead: "Последняя версия для каждого устройства.",
      allUnavailable: "ещё не выпущено",
      skip: "Перейти к загрузке",
      brandNote: "Приложения",
      eyebrow: "Курс · прогресс · AI-помощник",
      title: "Загрузка",
      lead: "Выберите устройство",
      featureCourse: "Единый курс и прогресс",
      featureAi: "AI-помощник в боковой панели",
      featureUpdate: "Автоматические обновления",
      readyLabel: "Установщик готов",
      freeDownload: "Бесплатная загрузка",
      selectTitle: "Выберите устройство",
      selectBody: "Выберите устройство — покажем подходящий файл или ссылку.",
      selectDownload: "Сначала выберите устройство",
      loading: "Подготавливаем…",
      checking: "Проверяем подходящую версию.",
      unavailable: "Установщик для этой платформы ещё не опубликован.",
      ready: "Файл загружается с официального сервера HSK AI.",
      opening: "Открываем загрузку…",
      downloadAgain: "Скачать ещё раз",
      macTitle: "HSK AI для Mac",
      windowsTitle: "HSK AI для Windows",
      macDownload: "Скачать DMG для Mac",
      windowsDownload: "Скачать EXE для Windows",
      version: "Версия {version}",
      guideEyebrow: "Установка",
      guideTitle: "Готово за три шага",
      macSteps: [
        ["Скачайте DMG", "Кнопка выше сохранит универсальный установщик для Mac."],
        ["Перетащите в Applications", "Откройте DMG и перетащите HSK AI в папку Applications."],
        ["Подключите Telegram", "Подтвердите код приложения в Telegram. Подписка и прогресс появятся автоматически."]
      ],
      windowsSteps: [
        ["Скачайте EXE", "Кнопка выше сохранит установщик Windows x64."],
        ["Нажмите Install", "Откройте setup. Приложение установится для текущего пользователя."],
        ["Подключите Telegram", "Подтвердите код приложения в Telegram. Подписка и прогресс появятся автоматически."]
      ],
      securityTitle: "При первом запуске может появиться предупреждение",
      macSecurity: "Если macOS блокирует запуск: в Applications нажмите правой кнопкой на HSK AI → Open → Open. Если не помогло: System Settings → Privacy & Security → Open Anyway.",
      windowsSecurity: "Если появился SmartScreen: нажмите Подробнее → Выполнить в любом случае → Да. Проверьте, что файл называется HSK AI.",
      quickGuideEyebrow: "Загрузка началась",
      quickGuideTitle: "После загрузки откройте так",
      quickGuideLead: "Дождитесь завершения загрузки у значка в правом верхнем углу браузера. Пока не закрывайте это окно.",
      quickGuideProgress: "Файл загружается",
      quickGuideClose: "Понятно",
      quickGuideCloseAria: "Закрыть инструкцию",
      quickGuideFooter: "Когда приложение откроется, подтвердите показанный код через Telegram.",
      visualRightClick: "Правый клик",
      visualMacOpen: "Открыть",
      visualOr: "или",
      visualSettings: "Конфиденциальность и безопасность",
      visualOpenAnyway: "Всё равно открыть",
      visualWindowsBlocked: "Windows защитила ваш компьютер",
      visualMoreInfo: "Подробнее",
      visualRunAnyway: "Выполнить в любом случае",
      visualInstall: "Установить",
      visualOpenApp: "Открыть приложение",
      macQuickSteps: [
        ["Откройте DMG", "Нажмите загруженный файл .dmg в Downloads (↓)."],
        ["Перетащите в Applications", "В открывшемся окне перетащите иконку HSK AI в папку Applications."],
        ["При первом запуске появится предупреждение", "В окне «Файл «HSK AI» не был открыт» нажмите «Готово». Не нажимайте «Переместить в Корзину»."],
        ["Разрешите в System Settings", "Откройте «Конфиденциальность и безопасность», прокрутите вниз и нажмите «Все равно открыть»."],
        ["Подтвердите", "В следующем окне снова нажмите «Все равно открыть», затем подтвердите через Touch ID или пароль администратора."],
        ["В Keychain выберите «Разрешать всегда»", "При запуске приложение попросит пароль связки ключей. Нажмите «Разрешать всегда» — тогда больше спрашивать не будет."]
      ],
      quickShotAlts: {
        m2: "Окно DMG: иконка HSK AI и папка Applications",
        m3: "Предупреждение macOS: «Файл «HSK AI» не был открыт»",
        m4: "System Settings, раздел безопасности: кнопка «Все равно открыть»",
        m5: "Окно подтверждения: «Все равно открыть»",
        m5b: "Запрос Touch ID или пароля администратора",
        m6: "Запрос Keychain, кнопка «Разрешать всегда» выделена"
      },
      windowsQuickSteps: [
        ["Откройте EXE", "Нажмите загруженный файл .exe в Downloads (↓)."],
        ["Если появился SmartScreen", "Нажмите показанные ниже кнопки: «Подробнее», затем «Выполнить в любом случае»."],
        ["Установите и откройте", "Нажмите «Установить», затем откройте HSK AI через меню Пуск."]
      ],
      androidQuickLead:
        "Дождитесь окончания загрузки. Файл появится в уведомлении или в папке «Загрузки».",
      androidQuickSteps: [
        ["Откройте скачанный APK", "Нажмите файл в уведомлении или найдите HSK AI в папке «Загрузки»."],
        ["Разрешите установку из этого источника", "Если Android спросит: «Настройки» → «Разрешить установку из этого источника», затем вернитесь назад."],
        ["Нажмите «Установить»", "Если появится проверка Play Protect, выберите «Всё равно установить». Это наш официальный файл."],
        ["Откройте приложение и подключите Telegram", "Подтвердите код из приложения через Telegram. Подписка и прогресс придут автоматически."]
      ],
      mobileEyebrow: "Страница открыта на телефоне",
      mobileTitle: "Отправьте ссылку на компьютер",
      mobileBody:
        "Сначала выберите систему компьютера. Скачанный на телефон DMG/EXE попадёт в Загрузки или Файлы, но откроется только на Mac или Windows.",
      shareLink: "AirDrop или поделиться",
      copyLink: "Скопировать ссылку",
      copied: "Скопировано",
      shared: "Меню отправки открыто",
      copyFailed: "Не удалось скопировать автоматически. Скопируйте ссылку ниже вручную.",
      manualLinkLabel: "Безопасная ссылка для компьютера",
      footer: "Курс — в центре. AI — помощник."
    },
    tj: {
      iosSecurityTitle: "Ҳеҷ чиз насб намешавад",
      androidSecurityTitle: "Ҳангоми насб огоҳӣ пайдо шуда метавонад",
      macSecurityTitle: "Ҳангоми кушодани аввал огоҳӣ пайдо шуда метавонад",
      windowsSecurityTitle: "Ҳангоми кушодани аввал огоҳӣ пайдо шуда метавонад",
      iosTitle: "Барои iPhone ва iPad",
      iosDownload: "Дар Telegram кушодан",
      iosStatus: "Барномаи алоҳида барои iOS ҳанӯз нест — Mini App дар Telegram пурра кор мекунад.",
      iosSecurity: "Mini App дар дохили Telegram кушода мешавад. Ҳеҷ чиз насб намешавад, ҳисоб ва пешрафти шумо ҳамон ҷо мемонад.",
      iosSteps: [
        ["Telegram-ро кушоед", "Тугмаи боло ботро мекушояд."],
        ["Курсро оғоз кунед", "Mini App дарсҳо, машқ ва ёрдамчии AI-ро пурра медиҳад."],
        ["Барномаи алоҳидаро интизор нашавед", "Вақте барнома барои iOS тайёр шавад, дар ҳамин саҳифа пайдо мешавад."],
      ],
      androidTitle: "HSK AI барои Android",
      androidDownload: "APK-ро боргирӣ кунед",
      androidSecurity: "Android метавонад дар бораи «манбаъҳои номаълум» огоҳӣ диҳад: иҷозат диҳед ва идома диҳед. Ин файли расмии мост.",
      androidSteps: [
        ["APK-ро боргирӣ кунед", "Тугмаи боло файлро ба телефони шумо мегузорад."],
        ["Файлро кушоед ва насб кунед", "Файли боргиришударо пахш кунед → «Насб кардан»."],
        ["Ҳисоби Telegram-ро пайваст кунед", "Рамзи барномаро тавассути Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."],
      ],
      allTitle: "Ҳамаи боргириҳо",
      allLead: "Версияи охирин барои ҳар дастгоҳ.",
      allUnavailable: "ҳанӯз нашр нашудааст",
      skip: "Гузаштан ба боргирӣ",
      brandNote: "Барномаҳо",
      eyebrow: "Курс · пешрафт · ёвари AI",
      title: "Боргирӣ",
      lead: "Дастгоҳи худро интихоб кунед",
      featureCourse: "Курс ва пешрафти умумӣ",
      featureAi: "Ёвари AI дар панели паҳлӯӣ",
      featureUpdate: "Навсозии автоматӣ",
      readyLabel: "Насбкунанда омода",
      freeDownload: "Боргирии ройгон",
      selectTitle: "Дастгоҳи худро интихоб кунед",
      selectBody: "Дастгоҳи худро интихоб кунед — файл ё пайванди мувофиқ нишон дода мешавад.",
      selectDownload: "Аввал дастгоҳро интихоб кунед",
      loading: "Омода мешавад…",
      checking: "Версияи мувофиқ санҷида мешавад.",
      unavailable: "Насбкунандаи ин платформа ҳоло нашр нашудааст.",
      ready: "Файл аз сервери расмии HSK AI бор мешавад.",
      opening: "Боргирӣ кушода мешавад…",
      downloadAgain: "Аз нав бор кардан",
      macTitle: "HSK AI барои Mac",
      windowsTitle: "HSK AI барои Windows",
      macDownload: "DMG барои Mac",
      windowsDownload: "EXE барои Windows",
      version: "Версияи {version}",
      guideEyebrow: "Насб",
      guideTitle: "Дар се қадам омода",
      macSteps: [
        ["DMG-ро бор кунед", "Тугмаи боло насбкунандаи универсалии Mac-ро нигоҳ медорад."],
        ["Ба Applications гузаронед", "DMG-ро кушоед ва HSK AI-ро ба Applications кашед."],
        ["Telegram-ро пайваст кунед", "Рамзи барномаро дар Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."]
      ],
      windowsSteps: [
        ["EXE-ро бор кунед", "Тугмаи боло насбкунандаи Windows x64-ро нигоҳ медорад."],
        ["Install-ро пахш кунед", "Setup-ро кушоед. Барнома барои корбари ҷорӣ насб мешавад."],
        ["Telegram-ро пайваст кунед", "Рамзи барномаро дар Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."]
      ],
      securityTitle: "Ҳангоми кушодани аввал огоҳӣ баромада метавонад",
      macSecurity: "Агар macOS роҳ надиҳад: дар Applications рӯи HSK AI тугмаи рост → Open → Open. Агар ҳанӯз баста бошад: System Settings → Privacy & Security → Open Anyway.",
      windowsSecurity: "Агар SmartScreen барояд: More info → Run anyway → Yes-ро пахш кунед. Номи файли HSK AI-ро санҷед.",
      quickGuideEyebrow: "Боргирӣ оғоз шуд",
      quickGuideTitle: "Пас аз боргирӣ ҳамин тавр кушоед",
      quickGuideLead: "То анҷоми боргирӣ дар нишонаи болои рости браузер интизор шавед. Ҳоло ин равзанаро напӯшед.",
      quickGuideProgress: "Файл бор шуда истодааст",
      quickGuideClose: "Фаҳмо",
      quickGuideCloseAria: "Пӯшидани дастур",
      quickGuideFooter: "Пас аз кушодани барнома, рамзи онро тавассути Telegram тасдиқ кунед.",
      visualRightClick: "Тугмаи рост",
      visualMacOpen: "Кушодан",
      visualOr: "ё",
      visualSettings: "Махфият ва амният",
      visualOpenAnyway: "Ба ҳар ҳол кушодан",
      visualWindowsBlocked: "Windows компютери шуморо ҳифз кард",
      visualMoreInfo: "Маълумоти бештар",
      visualRunAnyway: "Ба ҳар ҳол иҷро кардан",
      visualInstall: "Насб кардан",
      visualOpenApp: "Кушодани барнома",
      macQuickSteps: [
        ["DMG-ро кушоед", "Дар Downloads (↓) файли .dmg-и боршударо пахш кунед."],
        ["Ба Applications кашед", "Дар тирезаи кушодашуда нишонаи HSK AI-ро ба папкаи Applications кашед."],
        ["Ҳангоми кушодани аввал огоҳӣ мебарояд", "Дар тирезаи «Файл «HSK AI» не был открыт» «Готово»-ро пахш кунед. «Переместить в Корзину»-ро пахш накунед."],
        ["Дар System Settings иҷозат диҳед", "«Конфиденциальность и безопасность»-ро кушоед, поён равед ва «Все равно открыть»-ро пахш кунед."],
        ["Тасдиқ кунед", "Дар тирезаи навбатӣ боз «Все равно открыть», сипас Touch ID ё пароли администраторро ворид кунед."],
        ["Дар Keychain «Разрешать всегда»-ро интихоб кунед", "Ҳангоми оғоз барнома пароли Keychain мепурсад. «Разрешать всегда»-ро пахш кунед — дигар намепурсад."]
      ],
      quickShotAlts: {
        m2: "Тирезаи DMG: нишонаи HSK AI ва папкаи Applications",
        m3: "Огоҳии macOS: «Файл «HSK AI» не был открыт»",
        m4: "System Settings, бахши амният: тугмаи «Все равно открыть»",
        m5: "Тирезаи тасдиқ: «Все равно открыть»",
        m5b: "Дархости Touch ID ё пароли администратор",
        m6: "Дархости Keychain, тугмаи «Разрешать всегда» ҷудо шудааст"
      },
      windowsQuickSteps: [
        ["EXE-ро кушоед", "Дар Downloads (↓) файли .exe-и боршударо пахш кунед."],
        ["Агар SmartScreen роҳ надиҳад", "Тугмаҳои расмро пахш кунед: «Маълумоти бештар», баъд «Ба ҳар ҳол иҷро кардан»."],
        ["Насб ва кушоед", "«Насб кардан»-ро пахш кунед ва баъд HSK AI-ро аз Start кушоед."]
      ],
      androidQuickLead:
        "То анҷоми боргирӣ интизор шавед. Файл дар огоҳинома ё дар ҷузвдони «Боргириҳо» пайдо мешавад.",
      androidQuickSteps: [
        ["APK-и боршударо кушоед", "Файлро дар огоҳинома пахш кунед ё дар ҷузвдони «Боргириҳо» HSK AI-ро ёбед."],
        ["Ба насб аз ин манбаъ иҷозат диҳед", "Агар Android пурсад: «Танзимот» → «Иҷозати насб аз ин манбаъ»-ро фаъол кунед ва баргардед."],
        ["«Насб кардан»-ро пахш кунед", "Агар санҷиши Play Protect барояд, «Ба ҳар ҳол насб кардан»-ро интихоб кунед. Ин файли расмии мост."],
        ["Барномаро кушоед ва Telegram-ро пайваст кунед", "Рамзи барномаро тавассути Telegram тасдиқ кунед. Обуна ва пешрафт худкор меоянд."]
      ],
      mobileEyebrow: "Саҳифа дар телефон кушода шуд",
      mobileTitle: "Пайвандро ба компютер фиристед",
      mobileBody:
        "Аввал системаи компютерро интихоб кунед. DMG/EXE-и дар телефон боршуда ба Downloads ё Files меафтад, вале танҳо дар Mac ё Windows кушода мешавад.",
      shareLink: "AirDrop ё фиристодан",
      copyLink: "Нусхаи пайванд",
      copied: "Нусха шуд",
      shared: "Равзанаи фиристодан кушода шуд",
      copyFailed: "Худкор нусха нашуд. Пайванди поёнро дастӣ нусха гиред.",
      manualLinkLabel: "Пайванди бехатар барои компютер",
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
    var agent = String(navigator.userAgent || "");
    // A phone is no longer a dead end: it gets the platform it is.
    if (/Android/i.test(agent)) return "android";
    if (/iPhone|iPod/i.test(agent)) return "ios";
    if (/iPad/i.test(agent)) return "ios";
    if (isMobile()) return "";
    var source = String(
      (navigator.userAgentData && navigator.userAgentData.platform) ||
        navigator.platform ||
        navigator.userAgent ||
        ""
    ).toLowerCase();
    if (source.indexOf("win") >= 0) return "windows";
    if (source.indexOf("mac") >= 0) return "macos";
    return "";
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

  function platformEntry(platform) {
    return (
      (state.release && state.release.platforms && state.release.platforms[platform]) || null
    );
  }

  function releaseAvailable(platform) {
    var entry = platformEntry(platform);
    return Boolean(entry && entry.available && entry.download);
  }

  function transferUrl(platform) {
    if (!releaseAvailable(platform)) return "";
    var entry = platformEntry(platform);
    try {
      return new URL(String(entry.download), window.location.origin).toString();
    } catch (error) {
      return "";
    }
  }

  function downloadUrl(platform) {
    var base = transferUrl(platform);
    // A learner who arrived from the Mini App carries a request token, and
    // the download is attributed by it. Losing it does not break the
    // download — it silently empties the funnel it feeds.
    var token = validRequestToken();
    if (!base || !token) return base;
    try {
      var url = new URL(base, window.location.origin);
      url.searchParams.set("request", token);
      return url.toString();
    } catch (error) {
      return base;
    }
  }

  function renderSteps() {
    if (supportedPlatforms.indexOf(state.platform) < 0) return;
    var steps = forPlatform(copy(), "Steps");
    if (!steps) return;
    ["one", "two", "three"].forEach(function (key, index) {
      var step = steps[index] || ["", ""];
      setText('[data-step-title="' + key + '"]', step[0]);
      setText('[data-step-body="' + key + '"]', step[1]);
    });
  }

  function renderQuickGuide() {
    var localized = copy();
    var steps = forPlatform(localized, "QuickSteps");
    if (!steps) {
      // iOS installs nothing, so there is nothing to open "like this". The
      // guide is closed rather than left holding another platform's steps.
      closeQuickGuide();
      return;
    }
    var guide = document.querySelector("[data-quick-guide]");
    var platform = document.querySelector("[data-quick-guide-platform]");
    var progress = document.querySelector("[data-quick-guide-progress]");
    var lead = document.querySelector("#quick-guide-lead");
    if (guide) guide.dataset.platform = state.platform;
    if (platform) platform.textContent = QUICK_BADGE[state.platform] || "";
    if (progress) progress.setAttribute("aria-label", localized.quickGuideProgress);
    // A phone has no download icon in a browser toolbar, so Android gets its
    // own opening line instead of the desktop one.
    if (lead) {
      lead.textContent =
        forPlatform(localized, "QuickLead") || localized.quickGuideLead;
    }
    document.querySelectorAll("[data-quick-guide-close-aria]").forEach(function (button) {
      button.setAttribute("aria-label", localized.quickGuideCloseAria);
    });
    var prefix = QUICK_PREFIX[state.platform];
    steps.forEach(function (step, index) {
      var key = prefix + (index + 1);
      setText('[data-quick-step-title="' + key + '"]', step[0]);
      setText('[data-quick-step-body="' + key + '"]', step[1]);
    });
    var alts = localized.quickShotAlts || {};
    document.querySelectorAll("[data-quick-shot-alt]").forEach(function (image) {
      image.setAttribute("alt", alts[image.dataset.quickShotAlt] || "");
    });
  }

  function openQuickGuide() {
    var guide = document.querySelector("[data-quick-guide]");
    if (!guide) return;
    // Without steps there is no guide to open — iOS just opens Telegram.
    if (!forPlatform(copy(), "QuickSteps")) return;
    renderQuickGuide();
    document.body.classList.add("quick-guide-open");
    if (typeof guide.showModal === "function") {
      if (!guide.open) guide.showModal();
    } else {
      guide.setAttribute("open", "");
    }
    try {
      guide.focus();
    } catch (error) {}
  }

  function closeQuickGuide() {
    var guide = document.querySelector("[data-quick-guide]");
    if (!guide) return;
    if (typeof guide.close === "function" && guide.open) guide.close();
    else guide.removeAttribute("open");
    document.body.classList.remove("quick-guide-open");
  }

  function renderInstallerStage() {
    var stage = document.querySelector("[data-installer-stage]");
    if (!stage) return;
    if (supportedPlatforms.indexOf(state.platform) < 0) {
      stage.hidden = true;
      stage.dataset.installerStage = "unselected";
      return;
    }
    stage.hidden = false;
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
    var selected = supportedPlatforms.indexOf(state.platform) >= 0;
    document.documentElement.dataset.platformSelected = selected
      ? "true"
      : "false";
    document.querySelectorAll("[data-platform]").forEach(function (button) {
      button.setAttribute(
        "aria-pressed",
        button.dataset.platform === state.platform ? "true" : "false"
      );
    });

    var prompt = document.querySelector("[data-platform-prompt]");
    var guide = document.querySelector("[data-platform-guide]");
    var security = document.querySelector("[data-platform-security]");
    if (prompt) prompt.hidden = selected;
    if (guide) guide.hidden = !selected;
    if (security) security.hidden = !selected;

    if (!selected) {
      setText("[data-download-title]", localized.selectTitle);
      setText("[data-download-label]", localized.selectDownload);
      renderInstallerStage();
      renderRelease();
      return;
    }

    setText("[data-download-title]", forPlatform(localized, "Title"));
    setText("[data-download-label]", forPlatform(localized, "Download"));
    setText("[data-security-copy]", forPlatform(localized, "Security"));
    // The heading is per platform too: on iOS nothing is installed, so
    // "a warning may appear on first open" would simply be untrue.
    setText("#security-title", forPlatform(localized, "SecurityTitle"));
    renderSteps();
    renderInstallerStage();
    renderQuickGuide();
    renderRelease();
  }

  function renderTransfer() {
    // Only the desktop installers are unusable on the phone that opened this
    // page. An APK is not, and iOS has nothing to transfer at all.
    var block = document.querySelector("[data-mobile-transfer]");
    if (block) {
      var desktopChoice =
        state.platform === "macos" || state.platform === "windows";
      block.hidden = !(isMobile() && desktopChoice);
    }
    var url = transferUrl(state.platform);
    var shareButton = document.querySelector("[data-share-link]");
    var copyButton = document.querySelector("[data-copy-link]");
    var input = document.querySelector("[data-transfer-link]");
    [shareButton, copyButton].forEach(function (button) {
      if (button) button.disabled = !url;
    });
    if (input) {
      input.value = url;
      input.setAttribute("aria-label", copy().manualLinkLabel);
    }
  }

  function renderRelease() {
    var localized = copy();
    var button = document.querySelector("[data-download-button]");
    var status = document.querySelector("[data-download-status]");
    var selected = supportedPlatforms.indexOf(state.platform) >= 0;
    var entry = selected ? platformEntry(state.platform) : null;

    renderTransfer();

    // iOS has nothing to download and never will until there is a build. It
    // gets the truth and a working way in, not a disabled button.
    if (state.platform === "ios") {
      setText("[data-version]", "");
      setText("[data-published]", "");
      if (!button || !status) return;
      button.href = BOT_URL;
      button.removeAttribute("aria-disabled");
      button.dataset.action = "open";
      status.dataset.state = "ready";
      status.lastElementChild.textContent = localized.iosStatus;
      return;
    }

    setText(
      "[data-version]",
      !selected
        ? ""
        : entry && entry.version
        ? localized.version.replace("{version}", String(entry.version))
        : localized.checking
    );
    setText("[data-published]", (selected && entry && entry.published) || "");
    if (!button || !status) return;

    if (!selected) {
      button.href = "#";
      button.setAttribute("aria-disabled", "true");
      status.dataset.state = "choose";
      status.lastElementChild.textContent = localized.selectBody;
      return;
    }

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
    button.dataset.action = "download";
    status.dataset.state = "ready";
    status.lastElementChild.textContent = localized.ready;
  }

  function setPlatform(platform) {
    if (supportedPlatforms.indexOf(platform) < 0) return;
    state.platform = platform;
    resetTransferFeedback();
    renderPlatform();
    var nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("platform", platform);
    window.history.replaceState({}, "", nextUrl);
  }

  function setLanguage(language) {
    if (supportedLanguages.indexOf(language) < 0) return;
    state.language = language;
    resetTransferFeedback();
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

  function setTransferStatus(message, kind) {
    var status = document.querySelector("[data-transfer-status]");
    if (!status) return;
    status.textContent = message || "";
    status.dataset.state = kind || "";
  }

  function resetTransferFeedback() {
    var manual = document.querySelector("[data-transfer-manual]");
    if (manual) manual.hidden = true;
    setTransferStatus("", "");
  }

  function showManualTransfer(url) {
    var manual = document.querySelector("[data-transfer-manual]");
    var input = document.querySelector("[data-transfer-link]");
    if (input) input.value = url;
    if (manual) manual.hidden = false;
    setTransferStatus(copy().copyFailed, "error");
    if (input) {
      try {
        input.focus();
        input.select();
      } catch (error) {}
    }
  }

  function legacyCopy(value) {
    return new Promise(function (resolve, reject) {
      var helper = document.createElement("textarea");
      helper.className = "transfer-copy-helper";
      helper.value = value;
      helper.readOnly = true;
      helper.setAttribute("aria-hidden", "true");
      document.body.appendChild(helper);
      helper.select();
      var copied = false;
      try {
        copied = Boolean(
          document.execCommand && document.execCommand("copy")
        );
      } catch (error) {}
      helper.remove();
      if (copied) resolve();
      else reject(new Error("clipboard_unavailable"));
    });
  }

  function copyPublicTransfer(url) {
    var operation = null;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        operation = navigator.clipboard.writeText(url);
      }
    } catch (error) {}
    var copyOperation = operation
      ? Promise.resolve(operation).catch(function () {
          return legacyCopy(url);
        })
      : legacyCopy(url);
    return copyOperation
      .then(function () {
        setTransferStatus(copy().copied, "success");
      })
      .catch(function () {
        showManualTransfer(url);
        throw new Error("clipboard_unavailable");
      });
  }

  function sharePublicTransfer(url) {
    if (!navigator.share) return copyPublicTransfer(url);
    var payload = {
      title: "HSK AI",
      text: copy().mobileBody,
      url: url
    };
    try {
      if (navigator.canShare && !navigator.canShare(payload)) {
        return copyPublicTransfer(url);
      }
    } catch (error) {}
    var shareOperation = null;
    try {
      shareOperation = navigator.share(payload);
    } catch (error) {
      return copyPublicTransfer(url);
    }
    return Promise.resolve(shareOperation)
      .then(function () {
        setTransferStatus(copy().shared, "success");
      })
      .catch(function (error) {
        if (error && error.name === "AbortError") return;
        return copyPublicTransfer(url);
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
        var startedPlatform = state.platform;
        setText("[data-download-label]", copy().opening);
        openQuickGuide();
        window.setTimeout(function () {
          if (state.platform === startedPlatform) {
            setText("[data-download-label]", copy().downloadAgain);
          }
        }, 1200);
      });
    }

    document.querySelectorAll("[data-quick-guide-close]").forEach(function (button) {
      button.addEventListener("click", closeQuickGuide);
    });
    var quickGuide = document.querySelector("[data-quick-guide]");
    if (quickGuide) {
      quickGuide.addEventListener("close", function () {
        document.body.classList.remove("quick-guide-open");
      });
    }

    var copyButton = document.querySelector("[data-copy-link]");
    if (copyButton) {
      copyButton.addEventListener("click", function () {
        var url = transferUrl(state.platform);
        if (url) copyPublicTransfer(url).catch(function () {});
      });
    }

    var shareButton = document.querySelector("[data-share-link]");
    if (shareButton) {
      shareButton.addEventListener("click", function () {
        var url = transferUrl(state.platform);
        if (url) sharePublicTransfer(url).catch(function () {});
      });
    }
  }

  function init() {
    bindEvents();
    var mobileTransfer = document.querySelector("[data-mobile-transfer]");
    // Hidden until a platform is chosen; renderTransfer decides from there.
    if (mobileTransfer) mobileTransfer.hidden = true;
    applyLanguage();
    loadRelease();
  }

  init();
})();
