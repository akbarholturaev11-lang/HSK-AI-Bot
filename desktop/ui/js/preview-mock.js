const query =
  typeof globalThis.location?.search === "string"
    ? new URLSearchParams(globalThis.location.search)
    : new URLSearchParams();

const previewState = {
  linked: query.get("unlinked") !== "1",
  pollCount: 0,
  language: "uz",
  completed: 1,
  subscription:
    query.get("subscription") === "paid"
      ? "paid"
      : query.get("subscription") === "pending"
        ? "pending"
        : "free",
};

const localized = (uz, ru, tj) => ({ uz, ru, tj });
const PREVIEW_QR =
  "data:image/png;base64," +
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk" +
  "+A8AAQUBAScY42YAAAAASUVORK5CYII=";

function subscriptionAccess() {
  const paid = previewState.subscription === "paid";
  return {
    state: paid ? "paid" : "free",
    is_paid: paid,
    expires_at: paid ? "2026-12-31T23:59:59Z" : null,
  };
}

function previewPrices() {
  const plans = (currency, values) => ({
    "10_days": {
      final_amount: values[0],
      currency,
      discount_applied: false,
      discount_percent: 0,
    },
    "1_month": {
      final_amount: values[1],
      currency,
      discount_applied: false,
      discount_percent: 0,
    },
    "3_months": {
      final_amount: values[2],
      currency,
      discount_applied: true,
      discount_percent: 10,
    },
  });
  return {
    visa: plans("TJS", [49, 129, 329]),
    alipay: plans("¥", [28, 66, 168]),
    wechat: plans("¥", [28, 66, 168]),
  };
}

function subscriptionOverview() {
  const access = subscriptionAccess();
  const pending = previewState.subscription === "pending";
  return {
    ok: true,
    source: "desktop_subscription",
    mode: "subscription",
    language: previewState.language,
    access,
    checkout_allowed: !access.is_paid && !pending,
    read_only_reason: access.is_paid
      ? "desktop_subscription_active"
      : pending
        ? "desktop_subscription_pending"
        : null,
    attempt_id: !access.is_paid && !pending ? "desktop-preview-checkout-0001" : null,
    pending_payment: pending
      ? {
          id: 1001,
          plan_type: "1_month",
          payment_method: "alipay",
          amount: 66,
          currency: "¥",
          submitted_at: "2026-08-02T08:00:00Z",
        }
      : null,
    prices: access.is_paid || pending ? {} : previewPrices(),
    payment_details: access.is_paid || pending ? "" : "HSK AI · 0000 0000 0000 0000",
    payment_details_configured: !access.is_paid && !pending,
    card_countries: ["tj", "uz", "ru", "other"],
  };
}

function subscriptionQuote(args) {
  const prices = previewPrices();
  const plan = String(args.plan || "");
  const method = String(args.method || "");
  const price = prices[method]?.[plan];
  if (!price || previewState.subscription !== "free") {
    throw new Error("desktop_subscription_request_invalid");
  }
  const quote = {
    plan_type: plan,
    payment_method: method,
    card_country: method === "visa" ? String(args.country || "tj") : null,
    base_amount: price.final_amount,
    base_currency: price.currency,
    final_amount: price.final_amount,
    final_currency: price.currency,
    pay_amount: String(price.final_amount),
    pay_currency: price.currency,
    pay_base_amount: String(price.final_amount),
    pay_base_currency: price.currency,
    exchange_rate: "",
    discount_applied: price.discount_applied,
    discount_percent: price.discount_percent,
    payment_details:
      method === "visa" ? "HSK AI · 0000 0000 0000 0000" : "",
  };
  if (method !== "visa") {
    quote.qr = { available: true, image_data_url: PREVIEW_QR };
  }
  return {
    ok: true,
    source: "desktop_subscription",
    mode: "subscription",
    access: subscriptionAccess(),
    quote,
  };
}

function bootstrap() {
  const access = subscriptionAccess();
  return {
    ok: true,
    authenticated: true,
    first_open: false,
    device: {
      id: "preview-device",
      platform: "preview",
      app_version: "1.3.2-preview",
    },
    user: {
      name: "Akbar",
      language: previewState.language,
      level: "hsk1",
      access_state: access.state,
      is_paid: access.is_paid,
    },
  };
}

function courseMap() {
  return {
    ok: true,
    authenticated: true,
    level: "hsk1",
    label: "HSK 1",
    user: bootstrap().user,
    progress: {
      completed: previewState.completed,
      total: 4,
      xp: 240,
      streak: 5,
    },
    units: [
      {
        no: 1,
        title: localized("Tanishuv", "Знакомство", "Шиносоӣ"),
        status: "current",
        lessons: [
          {
            n: 1,
            status: previewState.completed >= 1 ? "done" : "current",
            zh: "你好",
            py: "nǐ hǎo",
            tr: localized("Salom", "Привет", "Салом"),
          },
          {
            n: 2,
            status: previewState.completed >= 1 ? "current" : "locked",
            zh: "你叫什么名字",
            py: "nǐ jiào shénme míngzi",
            tr: localized("Ismingiz nima?", "Как вас зовут?", "Номи шумо чист?"),
          },
        ],
      },
      {
        no: 2,
        title: localized("Oila", "Семья", "Оила"),
        status: "locked",
        lessons: [
          {
            n: 3,
            status: "locked",
            zh: "我的家",
            py: "wǒ de jiā",
            tr: localized("Mening oilam", "Моя семья", "Оилаи ман"),
          },
          {
            n: 4,
            status: "locked",
            zh: "他是我爸爸",
            py: "tā shì wǒ bàba",
            tr: localized("U mening otam", "Он мой папа", "Ӯ падари ман аст"),
          },
        ],
      },
    ],
  };
}

function lessonData(lessonOrder) {
  return {
    ok: true,
    level: "hsk1",
    lesson_order: lessonOrder,
    preview_half: false,
    lesson: {
      schema_version: 2,
      level: "hsk1",
      lesson_id: lessonOrder,
      title: "你叫什么名字",
      subtitle: localized(
        "Ism so‘rash va o‘zingizni tanishtirish",
        "Как спросить имя и представиться",
        "Пурсидани ном ва шинос кардани худ",
      ),
      sections: [
        {
          section_no: 1,
          section_title: localized("Yangi so‘z", "Новое слово", "Калимаи нав"),
          cards: [
            {
              type: "active_word",
              word: {
                zh: "名字",
                pinyin: "míngzi",
                meaning: localized("ism", "имя", "ном"),
              },
            },
            {
              type: "meaning_guess",
              title: localized("Ma’nosi nima?", "Что означает?", "Маъно чист?"),
              prompt: localized(
                "名字 so‘zining ma’nosini tanlang",
                "Выберите значение 名字",
                "Маънои 名字-ро интихоб кунед",
              ),
              options: [
                localized("familiya", "фамилия", "насаб"),
                localized("ism", "имя", "ном"),
                localized("davlat", "страна", "давлат"),
              ],
              correct_index: 1,
              explanation: localized(
                "名字 = ism (míngzi)",
                "名字 = имя (míngzi)",
                "名字 = ном (míngzi)",
              ),
            },
            {
              type: "pronunciation",
              phrase: "你叫什么名字？",
              pinyin: "Nǐ jiào shénme míngzi?",
              translation: localized(
                "Ismingiz nima?",
                "Как вас зовут?",
                "Номи шумо чист?",
              ),
            },
          ],
        },
        {
          section_no: 2,
          section_title: localized("Grammatika", "Грамматика", "Грамматика"),
          cards: [
            {
              type: "_grammar",
              g: {
                title: localized(
                  "Ismni so‘rash",
                  "Как спросить имя",
                  "Пурсидани ном",
                ),
                title_zh: "问名字",
                rule: localized(
                  "你叫什么名字？ — suhbatdoshning ismini so‘rash uchun ishlatiladi.",
                  "你叫什么名字？ используется, чтобы спросить имя собеседника.",
                  "你叫什么名字？ барои пурсидани номи ҳамсуҳбат истифода мешавад.",
                ),
                examples: [
                  {
                    zh: "我叫安娜。",
                    pinyin: "Wǒ jiào Ānnà.",
                    translation: localized(
                      "Mening ismim Anna.",
                      "Меня зовут Анна.",
                      "Номи ман Анна аст.",
                    ),
                  },
                ],
              },
            },
            {
              type: "sentence_builder",
              sentence: localized(
                "Ismingiz nima?",
                "Как вас зовут?",
                "Номи шумо чист?",
              ),
              tokens: ["什么", "你", "名字", "叫"],
              answer_tokens: ["你", "叫", "什么", "名字"],
              explanation: localized(
                "你叫什么名字？",
                "你叫什么名字？",
                "你叫什么名字？",
              ),
            },
          ],
        },
        {
          section_no: 3,
          section_title: localized("Takrorlash", "Повторение", "Такрор"),
          cards: [
            {
              type: "match_pairs",
              pairs: [
                ["你好", localized("salom", "привет", "салом")],
                ["名字", localized("ism", "имя", "ном")],
              ],
              explanation: localized(
                "Barcha juftliklar topildi.",
                "Все пары найдены.",
                "Ҳамаи ҷуфтҳо ёфт шуданд.",
              ),
            },
          ],
        },
      ],
    },
  };
}

export async function previewInvoke(command, args = {}) {
  switch (command) {
    case "desktop_app_info":
      return {
        productName: "HSK AI",
        version: "1.3.2-preview",
        platform: "preview",
      };
    case "desktop_auth_status":
      return {
        linked: previewState.linked,
        bootstrap: previewState.linked ? bootstrap() : null,
      };
    case "desktop_link_start":
      previewState.pollCount = 0;
      return {
        status: "pending",
        displayCode: "HSK4827X",
        expiresIn: 300,
      };
    case "desktop_link_open_telegram":
      return { ok: true };
    case "desktop_link_poll":
      previewState.pollCount += 1;
      if (previewState.pollCount < 2) {
        return { status: "pending", bootstrap: null };
      }
      previewState.linked = true;
      return { status: "linked", bootstrap: bootstrap() };
    case "desktop_bootstrap":
      return bootstrap();
    case "desktop_logout":
      previewState.linked = false;
      return { ok: true };
    case "desktop_course_map":
      return courseMap();
    case "desktop_lesson_data":
      return lessonData(Number(args.lessonOrder || 1));
    case "desktop_lesson_complete":
      previewState.completed = Math.max(
        previewState.completed,
        Number(args.lessonOrder || 1),
      );
      return {
        ok: true,
        completed_lesson: Number(args.lessonOrder || 1),
        next_lesson: Number(args.lessonOrder || 1) + 1,
        completed_lessons_count: previewState.completed,
        gamification: {
          awarded_xp: 20,
          xp: 260,
          streak: 5,
        },
      };
    case "desktop_set_language":
      previewState.language = String(args.language || "uz");
      return { ok: true, language: previewState.language };
    case "desktop_subscription_overview":
      return subscriptionOverview();
    case "desktop_subscription_quote":
      return subscriptionQuote(args);
    case "desktop_subscription_submit":
      if (previewState.subscription !== "free") {
        throw new Error("desktop_subscription_pending");
      }
      previewState.subscription = "pending";
      return {
        ok: true,
        status: "pending",
        payment_id: 1001,
        already_pending: false,
        source: "desktop_subscription",
        mode: "subscription",
        access: subscriptionAccess(),
      };
    case "desktop_tts_speak":
      return { ok: false, available: false, error: "desktop_tts_unavailable" };
    case "local_ai_model_status":
      return {
        modelId: "qwen3-4b-q4-k-m",
        installed: false,
        sizeBytes: null,
        expectedSizeBytes: 2_497_280_256,
        downloadedBytes: 0,
        state: "missing",
        runtimeAvailable: false,
        runtimeState: "stopped",
      };
    case "local_ai_install_start":
      return {
        modelId: "qwen3-4b-q4-k-m",
        installed: false,
        sizeBytes: null,
        expectedSizeBytes: 2_497_280_256,
        downloadedBytes: 0,
        state: "starting",
        runtimeAvailable: false,
        runtimeState: "stopped",
      };
    case "local_ai_install_cancel":
      return {
        modelId: "qwen3-4b-q4-k-m",
        installed: false,
        sizeBytes: null,
        expectedSizeBytes: 2_497_280_256,
        downloadedBytes: 0,
        state: "paused",
        runtimeAvailable: false,
        runtimeState: "stopped",
      };
    case "local_ai_pack_remove":
      return {
        modelId: "qwen3-4b-q4-k-m",
        installed: false,
        sizeBytes: null,
        expectedSizeBytes: 2_497_280_256,
        downloadedBytes: 0,
        state: "missing",
        runtimeAvailable: false,
        runtimeState: "stopped",
      };
    case "local_ai_chat":
    case "local_ai_chat_cancel":
      throw new Error("local_ai_runtime_missing");
    case "desktop_update_check":
      return {
        available: query.get("update") === "1",
        currentVersion: "1.3.2-preview",
        version: query.get("update") === "1" ? "1.3.3-preview" : undefined,
        notes:
          query.get("update") === "1"
            ? "Desktop kurs oqimi va barqarorlik yangilandi."
            : undefined,
      };
    case "desktop_update_install":
      return null;
    default:
      throw new Error("desktop_operation_not_allowed");
  }
}
