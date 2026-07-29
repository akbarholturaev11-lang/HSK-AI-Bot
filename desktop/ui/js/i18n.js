const SUPPORTED_LANGUAGES = new Set(["uz", "ru", "tj"]);

const messages = {
  uz: {
    appPreparing: "Ilova tayyorlanmoqda…",
    authTitle: "Telegram akkauntingizni ulang",
    authDescription: "Obuna, daraja va progress bir xil akkauntdan olinadi.",
    authCodeLabel: "Tasdiqlash kodi",
    authStart: "Telegram bilan ulash",
    authOpen: "Telegramni ochish",
    authRetry: "Yangi kod olish",
    authStep1: "Telegramni oching.",
    authStep2: "Kod va qurilmani tekshiring.",
    authStep3: "Tasdiqlash tugmasini bosing.",
    authExpires: "Kod {time} amal qiladi",
    authExpired: "Kod muddati tugadi. Yangi kod oling.",
    authCancelled: "Ulash bekor qilindi. Yangi kod olishingiz mumkin.",
    authWaiting: "Telegramdagi tasdiqlash kutilmoqda…",
    authStarting: "Xavfsiz ulash kodi olinmoqda…",
    authLinked: "Akkaunt muvaffaqiyatli ulandi.",
    copyCode: "Kodni nusxalash",
    copied: "Kod nusxalandi",
    course: "Kurs",
    profile: "Profil",
    days: "kun",
    lessons: "{done} / {total} dars",
    continueLesson: "Darsni davom ettirish",
    startLesson: "Darsni boshlash",
    currentLesson: "Joriy dars",
    courseProgress: "Kurs progressi",
    courseEmpty: "Bu daraja uchun darslar hali topilmadi.",
    refresh: "Yangilash",
    loadingCourse: "Kurs yuklanmoqda…",
    unit: "{number}-bo‘lim",
    lessonNumber: "{number}-dars",
    lockedLesson: "Oldingi darsni yakunlang",
    profileTitle: "Profil va sozlamalar",
    profileSubtitle: "Til, obuna va akkaunt holati",
    interfaceLanguage: "Interfeys tili",
    accountAccess: "Kursga kirish",
    paidPlan: "Faol obuna",
    freePlan: "Bepul rejim",
    paidAccessDescription: "Obuna va kursga kirish Telegram akkauntingiz bilan sinxron.",
    freeAccessDescription:
      "Obuna Telegram Mini App orqali boshqariladi. Bu oynada soxta xarid oqimi yo‘q.",
    manageSubscription: "Obunani Telegram Mini App orqali boshqaring.",
    logout: "Akkauntdan chiqish",
    languageSaved: "Til saqlandi",
    aiTitle: "AI yordamchi",
    aiSubtitle: "Dars bo‘yicha yordam",
    aiChecking: "AI Pack holati tekshirilmoqda…",
    aiMissingTitle: "AI Pack o‘rnatilmagan",
    aiMissingBody:
      "Lokal, internetsiz AI alohida tasdiqlangan paket sifatida o‘rnatiladi. Hozircha chat faol emas.",
    aiModelFoundTitle: "AI modeli topildi",
    aiModelFoundBody:
      "Model fayli mavjud, ammo lokal inference runtime hali ulanmagan. Chatni soxta javob bilan ochmaymiz.",
    aiUnavailableTitle: "AI holatini tekshirib bo‘lmadi",
    aiUnavailableBody: "Ilovani qayta ochib ko‘ring. Kurs ishlashda davom etadi.",
    aiNotReady: "Hali tayyor emas",
    aiModelReady: "Model bor · runtime kutilmoqda",
    aiInputPlaceholder: "AI Pack tayyor bo‘lgach savol yozasiz",
    lessonLoading: "Dars yuklanmoqda…",
    lessonClose: "Darsni yopish",
    check: "Tekshirish",
    continue: "Davom etish",
    finish: "Darsni yakunlash",
    retry: "Qayta urinish",
    correct: "To‘g‘ri!",
    wrong: "Hali to‘g‘ri emas.",
    teachingCard: "Tushuntirish",
    exerciseCard: "Mashq",
    listen: "Eshitish",
    listenAgain: "Yana eshitish",
    buildSentence: "So‘zlarni to‘g‘ri tartibda joylang",
    matchPairs: "Mos juftliklarni toping",
    pronunciationTitle: "Talaffuzni tinglang va takrorlang",
    pronunciationNote:
      "Bu versiyada ovozni avtomatik baholash yo‘q. Tinglab, o‘zingiz takrorlang.",
    unsupportedCard: "Bu mashq turi desktop ilovada hali qo‘llanmaydi.",
    unsupportedCardType: "Mashq turi: {type}",
    lessonLoadFailed: "Darsni yuklab bo‘lmadi.",
    lessonSubmitFailed:
      "Natija serverga saqlanmadi. Internetni tekshirib, qayta yuboring.",
    lessonCompleteTitle: "Dars saqlandi",
    lessonCompleteBody: "Progress serverdagi akkauntingizga yozildi.",
    localAccuracy: "Aniqlik",
    correctAnswers: "To‘g‘ri",
    serverReward: "Mukofot",
    noReward: "Server javobi",
    bridgeUnavailable:
      "Bu sahifa faqat Pomp HSK AI desktop ilovasi ichida ishlaydi.",
    sessionExpired: "Sessiya tugadi. Telegram orqali qayta ulang.",
    requestFailed: "Amal bajarilmadi. Qayta urinib ko‘ring.",
    noConnection: "Server bilan aloqa yo‘q.",
    unknownUser: "HSK o‘quvchisi",
    levelLabel: "HSK {level}",
    planPaid: "Premium",
    planFree: "Bepul",
    openCourseMenu: "Kurs menyusini ochish",
    closeCourseMenu: "Kurs menyusini yopish",
    openAi: "AI chatni ochish",
    closeAi: "AI chatni yopish",
    offline: "Offline",
    updateAvailableTitle: "Yangi versiya: {version}",
    updateAvailableBody:
      "Pomp HSK AI yangilanishi tayyor. Darsni tugatib, ilovani yangilang.",
    updateInstall: "O‘rnatish va qayta ochish",
    updateCheckingTitle: "Yangilanish tekshirilmoqda",
    updateCheckingBody: "Ilova versiyasi tekshirilmoqda…",
    updateInstallingTitle: "Yangilanish o‘rnatilmoqda",
    updateInstallingBody:
      "Yuklanmoqda. Ilovani yopmang; tayyor bo‘lgach qayta ochiladi.",
    updateReadyTitle: "Yangilanish tayyor",
    updateReadyBody: "Ilova yangi versiyada qayta ochilmoqda…",
    updateCheckFailedTitle: "Yangilanishni tekshirib bo‘lmadi",
    updateInstallFailedTitle: "Yangilanish o‘rnatilmadi",
    updateErrorBody: "Internetni tekshirib, qayta urinib ko‘ring.",
    updateRetry: "Qayta urinish",
    updateLessonActive:
      "Avval darsni yakunlang yoki yoping, keyin ilovani yangilang.",
    updateInstallInProgress:
      "Yangilanish tugaguncha yangi darsni boshlamang.",
  },
  ru: {
    appPreparing: "Приложение загружается…",
    authTitle: "Подключите Telegram-аккаунт",
    authDescription: "Подписка, уровень и прогресс берутся из одного аккаунта.",
    authCodeLabel: "Код подтверждения",
    authStart: "Подключить Telegram",
    authOpen: "Открыть Telegram",
    authRetry: "Получить новый код",
    authStep1: "Откройте Telegram.",
    authStep2: "Проверьте код и устройство.",
    authStep3: "Нажмите кнопку подтверждения.",
    authExpires: "Код действует ещё {time}",
    authExpired: "Срок кода истёк. Получите новый код.",
    authCancelled: "Подключение отменено. Можно получить новый код.",
    authWaiting: "Ожидаем подтверждение в Telegram…",
    authStarting: "Получаем безопасный код…",
    authLinked: "Аккаунт успешно подключён.",
    copyCode: "Скопировать код",
    copied: "Код скопирован",
    course: "Курс",
    profile: "Профиль",
    days: "дн.",
    lessons: "{done} / {total} уроков",
    continueLesson: "Продолжить урок",
    startLesson: "Начать урок",
    currentLesson: "Текущий урок",
    courseProgress: "Прогресс курса",
    courseEmpty: "Для этого уровня уроки пока не найдены.",
    refresh: "Обновить",
    loadingCourse: "Загружаем курс…",
    unit: "Раздел {number}",
    lessonNumber: "Урок {number}",
    lockedLesson: "Сначала завершите предыдущий урок",
    profileTitle: "Профиль и настройки",
    profileSubtitle: "Язык, подписка и состояние аккаунта",
    interfaceLanguage: "Язык интерфейса",
    accountAccess: "Доступ к курсу",
    paidPlan: "Активная подписка",
    freePlan: "Бесплатный режим",
    paidAccessDescription: "Подписка и доступ синхронизированы с Telegram.",
    freeAccessDescription:
      "Подписка управляется в Telegram Mini App. Здесь нет фиктивной оплаты.",
    manageSubscription: "Управляйте подпиской через Telegram Mini App.",
    logout: "Выйти из аккаунта",
    languageSaved: "Язык сохранён",
    aiTitle: "AI-помощник",
    aiSubtitle: "Помощь по уроку",
    aiChecking: "Проверяем AI Pack…",
    aiMissingTitle: "AI Pack не установлен",
    aiMissingBody:
      "Локальный AI без интернета устанавливается отдельным проверенным пакетом. Сейчас чат отключён.",
    aiModelFoundTitle: "AI-модель найдена",
    aiModelFoundBody:
      "Файл модели есть, но локальный inference runtime ещё не подключён. Фиктивных ответов не будет.",
    aiUnavailableTitle: "Не удалось проверить AI",
    aiUnavailableBody: "Перезапустите приложение. Курс продолжит работать.",
    aiNotReady: "Пока недоступно",
    aiModelReady: "Модель есть · ожидается runtime",
    aiInputPlaceholder: "Вопрос можно будет задать после готовности AI Pack",
    lessonLoading: "Загружаем урок…",
    lessonClose: "Закрыть урок",
    check: "Проверить",
    continue: "Продолжить",
    finish: "Завершить урок",
    retry: "Повторить",
    correct: "Верно!",
    wrong: "Пока неверно.",
    teachingCard: "Объяснение",
    exerciseCard: "Упражнение",
    listen: "Слушать",
    listenAgain: "Слушать ещё раз",
    buildSentence: "Расположите слова в правильном порядке",
    matchPairs: "Найдите соответствующие пары",
    pronunciationTitle: "Послушайте и повторите",
    pronunciationNote:
      "В этой версии нет автоматической оценки голоса. Послушайте и повторите сами.",
    unsupportedCard: "Этот тип упражнения пока не поддерживается в desktop-приложении.",
    unsupportedCardType: "Тип: {type}",
    lessonLoadFailed: "Не удалось загрузить урок.",
    lessonSubmitFailed:
      "Результат не сохранён на сервере. Проверьте интернет и повторите.",
    lessonCompleteTitle: "Урок сохранён",
    lessonCompleteBody: "Прогресс записан в ваш серверный аккаунт.",
    localAccuracy: "Точность",
    correctAnswers: "Верно",
    serverReward: "Награда",
    noReward: "Ответ сервера",
    bridgeUnavailable:
      "Эта страница работает только внутри desktop-приложения Pomp HSK AI.",
    sessionExpired: "Сессия истекла. Подключите Telegram снова.",
    requestFailed: "Не удалось выполнить действие. Повторите.",
    noConnection: "Нет связи с сервером.",
    unknownUser: "Ученик HSK",
    levelLabel: "HSK {level}",
    planPaid: "Premium",
    planFree: "Бесплатно",
    openCourseMenu: "Открыть меню курса",
    closeCourseMenu: "Закрыть меню курса",
    openAi: "Открыть AI-чат",
    closeAi: "Закрыть AI-чат",
    offline: "Офлайн",
    updateAvailableTitle: "Доступна версия {version}",
    updateAvailableBody:
      "Обновление Pomp HSK AI готово. Завершите урок и обновите приложение.",
    updateInstall: "Установить и перезапустить",
    updateCheckingTitle: "Проверяем обновление",
    updateCheckingBody: "Проверяем версию приложения…",
    updateInstallingTitle: "Устанавливаем обновление",
    updateInstallingBody:
      "Идёт загрузка. Не закрывайте приложение; после установки оно перезапустится.",
    updateReadyTitle: "Обновление готово",
    updateReadyBody: "Приложение перезапускается с новой версией…",
    updateCheckFailedTitle: "Не удалось проверить обновление",
    updateInstallFailedTitle: "Не удалось установить обновление",
    updateErrorBody: "Проверьте интернет и повторите.",
    updateRetry: "Повторить",
    updateLessonActive:
      "Сначала завершите или закройте урок, затем обновите приложение.",
    updateInstallInProgress:
      "Не начинайте новый урок до завершения обновления.",
  },
  tj: {
    appPreparing: "Барнома омода мешавад…",
    authTitle: "Ҳисоби Telegram-ро пайваст кунед",
    authDescription: "Обуна, сатҳ ва пешрафт аз як ҳисоб гирифта мешаванд.",
    authCodeLabel: "Рамзи тасдиқ",
    authStart: "Пайваст кардани Telegram",
    authOpen: "Кушодани Telegram",
    authRetry: "Рамзи нав гирифтан",
    authStep1: "Telegram-ро кушоед.",
    authStep2: "Рамз ва дастгоҳро санҷед.",
    authStep3: "Тугмаи тасдиқро пахш кунед.",
    authExpires: "Рамз боз {time} амал мекунад",
    authExpired: "Муҳлати рамз гузашт. Рамзи нав гиред.",
    authCancelled: "Пайвасткунӣ бекор шуд. Рамзи нав гирифта метавонед.",
    authWaiting: "Тасдиқ дар Telegram интизор аст…",
    authStarting: "Рамзи бехатар гирифта мешавад…",
    authLinked: "Ҳисоб бо муваффақият пайваст шуд.",
    copyCode: "Нусхабардории рамз",
    copied: "Рамз нусхабардорӣ шуд",
    course: "Курс",
    profile: "Профил",
    days: "рӯз",
    lessons: "{done} / {total} дарс",
    continueLesson: "Идомаи дарс",
    startLesson: "Оғози дарс",
    currentLesson: "Дарси ҷорӣ",
    courseProgress: "Пешрафти курс",
    courseEmpty: "Барои ин сатҳ ҳоло дарс ёфт нашуд.",
    refresh: "Навсозӣ",
    loadingCourse: "Курс бор мешавад…",
    unit: "Бахши {number}",
    lessonNumber: "Дарси {number}",
    lockedLesson: "Аввал дарси пешинаро анҷом диҳед",
    profileTitle: "Профил ва танзимот",
    profileSubtitle: "Забон, обуна ва ҳолати ҳисоб",
    interfaceLanguage: "Забони интерфейс",
    accountAccess: "Дастрасӣ ба курс",
    paidPlan: "Обунаи фаъол",
    freePlan: "Реҷаи ройгон",
    paidAccessDescription: "Обуна ва дастрасӣ бо Telegram ҳамоҳанганд.",
    freeAccessDescription:
      "Обуна дар Telegram Mini App идора мешавад. Дар ин ҷо пардохти сохта нест.",
    manageSubscription: "Обунаро дар Telegram Mini App идора кунед.",
    logout: "Баромадан аз ҳисоб",
    languageSaved: "Забон нигоҳ дошта шуд",
    aiTitle: "Ёвари AI",
    aiSubtitle: "Ёрӣ барои дарс",
    aiChecking: "Ҳолати AI Pack санҷида мешавад…",
    aiMissingTitle: "AI Pack насб нашудааст",
    aiMissingBody:
      "AI-и локалӣ ва бе интернет ҳамчун бастаи алоҳидаи санҷидашуда насб мешавад. Ҳоло чат хомӯш аст.",
    aiModelFoundTitle: "Модели AI ёфт шуд",
    aiModelFoundBody:
      "Файли модел ҳаст, аммо runtime-и локалӣ ҳоло пайваст нест. Ҷавоби сохта намедиҳем.",
    aiUnavailableTitle: "Санҷиши AI номумкин шуд",
    aiUnavailableBody: "Барномаро боз кушоед. Курс корашро идома медиҳад.",
    aiNotReady: "Ҳоло омода нест",
    aiModelReady: "Модел ҳаст · runtime интизор аст",
    aiInputPlaceholder: "Пас аз омода шудани AI Pack савол менависед",
    lessonLoading: "Дарс бор мешавад…",
    lessonClose: "Пӯшидани дарс",
    check: "Санҷидан",
    continue: "Идома",
    finish: "Анҷоми дарс",
    retry: "Такрор",
    correct: "Дуруст!",
    wrong: "Ҳоло дуруст нест.",
    teachingCard: "Шарҳ",
    exerciseCard: "Машқ",
    listen: "Гӯш кардан",
    listenAgain: "Боз гӯш кардан",
    buildSentence: "Калимаҳоро бо тартиби дуруст гузоред",
    matchPairs: "Ҷуфтҳои мувофиқро ёбед",
    pronunciationTitle: "Гӯш кунед ва такрор намоед",
    pronunciationNote:
      "Дар ин версия баҳодиҳии автоматии овоз нест. Гӯш карда, худатон такрор кунед.",
    unsupportedCard: "Ин намуди машқ ҳоло дар барномаи desktop дастгирӣ намешавад.",
    unsupportedCardType: "Намуд: {type}",
    lessonLoadFailed: "Дарс бор нашуд.",
    lessonSubmitFailed:
      "Натиҷа дар сервер нигоҳ дошта нашуд. Интернетро санҷида, такрор кунед.",
    lessonCompleteTitle: "Дарс нигоҳ дошта шуд",
    lessonCompleteBody: "Пешрафт дар ҳисоби серверӣ сабт шуд.",
    localAccuracy: "Дақиқӣ",
    correctAnswers: "Дуруст",
    serverReward: "Мукофот",
    noReward: "Ҷавоби сервер",
    bridgeUnavailable:
      "Ин саҳифа танҳо дар дохили барномаи desktop-и Pomp HSK AI кор мекунад.",
    sessionExpired: "Муҳлати сессия гузашт. Telegram-ро аз нав пайваст кунед.",
    requestFailed: "Амал иҷро нашуд. Боз кӯшиш кунед.",
    noConnection: "Бо сервер алоқа нест.",
    unknownUser: "Донишҷӯи HSK",
    levelLabel: "HSK {level}",
    planPaid: "Premium",
    planFree: "Ройгон",
    openCourseMenu: "Кушодани менюи курс",
    closeCourseMenu: "Пӯшидани менюи курс",
    openAi: "Кушодани AI-чат",
    closeAi: "Пӯшидани AI-чат",
    offline: "Офлайн",
    updateAvailableTitle: "Версияи {version} дастрас аст",
    updateAvailableBody:
      "Навсозии Pomp HSK AI омода аст. Дарсро анҷом дода, барномаро нав кунед.",
    updateInstall: "Насб ва бозкушоӣ",
    updateCheckingTitle: "Навсозӣ санҷида мешавад",
    updateCheckingBody: "Версияи барнома санҷида мешавад…",
    updateInstallingTitle: "Навсозӣ насб мешавад",
    updateInstallingBody:
      "Боргирӣ идома дорад. Барномаро напӯшед; баъди насб он боз кушода мешавад.",
    updateReadyTitle: "Навсозӣ омода аст",
    updateReadyBody: "Барнома бо версияи нав боз кушода мешавад…",
    updateCheckFailedTitle: "Навсозиро санҷидан нашуд",
    updateInstallFailedTitle: "Навсозӣ насб нашуд",
    updateErrorBody: "Интернетро санҷида, боз кӯшиш кунед.",
    updateRetry: "Боз кӯшиш кардан",
    updateLessonActive:
      "Аввал дарсро анҷом диҳед ё пӯшед, баъд барномаро нав кунед.",
    updateInstallInProgress:
      "То анҷоми навсозӣ дарси навро оғоз накунед.",
  },
};

let activeLanguage = "uz";

export function normalizeLanguage(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return SUPPORTED_LANGUAGES.has(normalized) ? normalized : "uz";
}

export function setLanguage(value) {
  activeLanguage = normalizeLanguage(value);
  document.documentElement.lang = activeLanguage;
  return activeLanguage;
}

export function getLanguage() {
  return activeLanguage;
}

export function t(key, variables = {}) {
  const template =
    messages[activeLanguage]?.[key] ?? messages.uz[key] ?? String(key || "");
  return String(template).replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) =>
    Object.prototype.hasOwnProperty.call(variables, name)
      ? String(variables[name])
      : match,
  );
}

export function pick(value, fallback = "") {
  if (value === null || value === undefined) {
    return fallback;
  }
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    return fallback;
  }

  for (const key of [activeLanguage, "uz", "ru", "tj", "en"]) {
    const candidate = value[key];
    if (typeof candidate === "string" || typeof candidate === "number") {
      return String(candidate);
    }
  }
  return fallback;
}

export const languageOptions = Object.freeze([
  { code: "uz", label: "O‘zbekcha" },
  { code: "ru", label: "Русский" },
  { code: "tj", label: "Тоҷикӣ" },
]);
