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
  practiceSession: "",
  // Empty on purpose: the preview must reproduce the first run where
  // onboarding opens itself because no goal has been picked yet.
  goalKind: query.get("goal") || "",
  vocabularySaved: [],
  vocabularyReview: [],
  voiceSessionId: "",
  voiceTurns: 0,
  notificationsEnabled: true,
};

const localized = (uz, ru, tj) => ({ uz, ru, tj });
const PREVIEW_QR =
  "data:image/png;base64," +
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk" +
  "+A8AAQUBAScY42YAAAAASUVORK5CYII=";

const PREVIEW_VOICE_MAX_DIALOGS = 7;

// Deterministic replies so the preview and the Chromium flow tests stay
// reproducible. Production never reaches this file: previewInvoke only runs on
// localhost with an explicit ?mock=1.
const PREVIEW_VOICE_REPLIES = [
  {
    transcription: "我今天没时间看电影了",
    chinese_reply: "没关系，那我们明天去吧。",
    pinyin: "Méi guānxi, nà wǒmen míngtiān qù ba.",
    translation: localized(
      "Zarari yo‘q, unda ertaga boramiz.",
      "Ничего страшного, тогда пойдём завтра.",
      "Ҳеҷ гап не, пас фардо меравем.",
    ),
    correction: "我今天没有时间看电影",
  },
  {
    transcription: "好的，明天下午见",
    chinese_reply: "太好了，明天下午三点见！",
    pinyin: "Tài hǎo le, míngtiān xiàwǔ sān diǎn jiàn!",
    translation: localized(
      "Zo‘r, ertaga soat uchda ko‘rishamiz!",
      "Отлично, завтра в три часа!",
      "Хеле хуб, фардо соати се вомехӯрем!",
    ),
    correction: null,
  },
];

/** The server sends one already-translated string, not a language map. */
function previewText(value) {
  if (!value || typeof value !== "object") return String(value || "");
  return String(value[previewState.language] || value.uz || "");
}

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
      app_version: "1.3.4-preview",
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
    notify: {
      enabled: previewState.notificationsEnabled,
    },
    notifications: [
      {
        id: 1,
        key: "lesson_time",
        glyph: "时",
        title: previewText(
          localized("Dars vaqti keldi", "Время урока", "Вақти дарс расид"),
        ),
        body: previewText(
          localized(
            "Bugungi darsni davom ettiring.",
            "Продолжите сегодняшний урок.",
            "Дарси имрӯзаро идома диҳед.",
          ),
        ),
        action: "course",
        level: "hsk1",
        lesson_order: 1,
        created_at: "2026-08-11T10:00:00+00:00",
      },
    ],
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
        version: "1.3.4-preview",
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
    case "desktop_open_external_url":
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
    case "desktop_set_notifications":
      previewState.notificationsEnabled = Boolean(args.enabled);
      return {
        ok: true,
        notifications: previewState.notificationsEnabled,
        notify: { enabled: previewState.notificationsEnabled },
      };
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
    case "desktop_vocabulary_state":
      return {
        saved: [...previewState.vocabularySaved],
        review: [...previewState.vocabularyReview],
      };
    case "desktop_vocabulary_save":
      previewState.vocabularySaved = Array.isArray(args.saved) ? [...args.saved] : [];
      previewState.vocabularyReview = Array.isArray(args.review) ? [...args.review] : [];
      return {
        saved: [...previewState.vocabularySaved],
        review: [...previewState.vocabularyReview],
      };
    case "desktop_referral_overview":
      return {
        code: "AKBAR7",
        link: "https://t.me/darsi_chini_bot?start=ref_AKBAR7",
        invited: 2,
        activated: 1,
        trial_progress: 1,
        trial_required: 5,
        items: [
          {
            name: "Malika",
            status: "active",
            joined_at: "2026-08-02T10:00:00Z",
            activated_at: "2026-08-03T09:00:00Z",
            course_level: "hsk1",
            completed_lessons: 4,
            is_paid: false,
          },
          {
            name: "Aziz",
            status: "pending",
            joined_at: "2026-08-06T18:20:00Z",
            activated_at: "",
            course_level: "",
            completed_lessons: 0,
            is_paid: false,
          },
        ],
      };
    case "desktop_goal_state": {
      const known = ["conversation", "hsk", "study"].includes(
        previewState.goalKind,
      );
      return {
        kind: known ? previewState.goalKind : "",
        configured: known,
      };
    }
    case "desktop_goal_save": {
      const kind = String(args.kind || "");
      if (!["conversation", "hsk", "study"].includes(kind)) {
        throw new Error("desktop_goal_request_invalid");
      }
      previewState.goalKind = kind;
      return { kind, configured: true };
    }
    case "desktop_practice_start": {
      const skill = String(args.skill || "");
      const mode = String(args.mode || "mock");
      previewState.practiceSession =
        `practice:1:course_${mode}:${mode}:${skill || "hsk1"}:v1`;
      return {
        ok: true,
        session: {
          id: previewState.practiceSession,
          mode,
          skill,
          level: "hsk1",
          questions: [
            {
              id: "hsk1:1:0",
              level: "hsk1",
              lesson: 1,
              format: "word_choice",
              category: "word",
              type: "word",
              subtype: skill || "meaning",
              prompt: previewText(
                localized(
                  "«你好» nimani anglatadi?",
                  "Что означает «你好»?",
                  "«你好» чиро ифода мекунад?",
                ),
              ),
              sentence: "你好",
              audio_text: "你好",
              pinyin: "nǐ hǎo",
              options: ["Salom", "Xayr", "Rahmat", "Kechirasiz"],
              answer_index: 0,
              explanation: previewText(
                localized(
                  "你好 — eng keng tarqalgan salomlashish.",
                  "你好 — самое распространённое приветствие.",
                  "你好 — маъмултарин салом додан аст.",
                ),
              ),
            },
            {
              id: "hsk1:1:1",
              level: "hsk1",
              lesson: 1,
              format: "sentence_choice",
              category: "grammar",
              type: "grammar",
              subtype: skill || "order",
              prompt: previewText(
                localized(
                  "To‘g‘ri gapni tanlang.",
                  "Выберите правильное предложение.",
                  "Ҷумлаи дурустро интихоб кунед.",
                ),
              ),
              sentence: "",
              audio_text: "",
              pinyin: "",
              options: ["我是学生。", "我学生是。", "是我学生。", "学生我是。"],
              answer_index: 0,
              explanation: previewText(
                localized(
                  "Xitoy tilida tartib: ega + 是 + kesim.",
                  "Порядок в китайском: подлежащее + 是 + сказуемое.",
                  "Тартиб дар чинӣ: мубтадо + 是 + хабар.",
                ),
              ),
            },
          ],
        },
      };
    }
    case "desktop_practice_complete": {
      if (previewState.practiceSession !== String(args.sessionId || "")) {
        throw new Error("invalid_practice_session");
      }
      const answers = Array.isArray(args.answers) ? args.answers : [];
      const score = answers.filter((item) => Number(item.selected) === 0).length;
      const total = answers.length || 2;
      previewState.practiceSession = "";
      return {
        ok: true,
        score,
        total,
        percent: Math.round((score / total) * 100),
        recommendation: "hsk1",
        wrong_items: answers
          .filter((item) => Number(item.selected) !== 0)
          .map((item) => ({
            question_id: String(item.question_id),
            question: previewText(
              localized("To‘g‘ri gapni tanlang.", "Выберите правильное предложение.", "Ҷумлаи дурустро интихоб кунед."),
            ),
            selected_answer: "我学生是。",
            correct_answer: "我是学生。",
            explanation: previewText(
              localized("Tartib: ega + 是 + kesim.", "Порядок: подлежащее + 是 + сказуемое.", "Тартиб: мубтадо + 是 + хабар."),
            ),
            level: "hsk1",
            type: "grammar",
            subtype: "order",
            format: "sentence_choice",
            sentence: "",
          })),
        reward: { xp_awarded: 15 },
      };
    }
    case "desktop_rating_leaderboard": {
      const board = [
        ["Akbar", "akbar", 420, true],
        ["Li Wei", "liwei", 610, false],
        ["Nодира", "nodira", 505, false],
        ["Ҷамшед", "jamshed", 380, false],
        ["Chen Yu", "chenyu", 260, false],
      ]
        .sort((a, b) => b[2] - a[2])
        .map(([name, username, xp, self], index) => ({
          rank: index + 1,
          name,
          username,
          xp,
          league_points: xp,
          total_xp: xp * 4,
          course_level: "HSK1",
          completed_lessons: previewState.completed,
          is_paid: previewState.subscription === "paid",
          is_current_user: self,
        }));
      return {
        rank: board.find((entry) => entry.is_current_user)?.rank || 1,
        league: "朱雀",
        league_size: board.length,
        xp: 420,
        weekly_xp: 420,
        daily_xp: 40,
        streak: 3,
        longest_streak: 7,
        week_start: "2026-08-03",
        week_activity_dates: ["2026-08-07", "2026-08-08"],
        weekly_reset_day: "monday",
        weekly_reset_seconds: 172800,
        leaderboard: board,
      };
    }
    case "desktop_voice_status":
      return {
        is_paid: previewState.subscription === "paid",
        plan: previewState.subscription === "paid" ? "premium" : "free",
        remaining_voice_limit: previewState.subscription === "paid" ? -1 : 1,
        level: "hsk2",
        language: previewState.language,
        completed_lessons: previewState.completed,
      };
    case "desktop_voice_session_start":
      previewState.voiceSessionId = "preview-voice-0000-0001";
      previewState.voiceTurns = 0;
      return {
        session_id: previewState.voiceSessionId,
        user_status: {
          is_paid: previewState.subscription === "paid",
          plan: previewState.subscription === "paid" ? "premium" : "free",
        },
        remaining_limit: previewState.subscription === "paid" ? -1 : 0,
        character: String(args.role || "lily"),
        course_context: { lesson_order: 5, title: "", words: [], review_words: [] },
        opening_message: {
          chinese_reply: "你好！今天过得怎么样？",
          pinyin: "Nǐ hǎo! Jīntiān guò de zěnmeyàng?",
          translation: previewText(
            localized(
              "Salom! Bugun kuningiz qanday o‘tdi?",
              "Привет! Как прошёл твой день?",
              "Салом! Рӯзи шумо чӣ хел гузашт?",
            ),
          ),
          correction: null,
        },
        max_dialogs: PREVIEW_VOICE_MAX_DIALOGS,
      };
    case "desktop_voice_message": {
      if (previewState.voiceSessionId !== String(args.sessionId || "")) {
        throw new Error("SESSION_NOT_FOUND");
      }
      const reply =
        PREVIEW_VOICE_REPLIES[
          Math.min(previewState.voiceTurns, PREVIEW_VOICE_REPLIES.length - 1)
        ];
      previewState.voiceTurns += 1;
      return {
        transcription: reply.transcription,
        chinese_reply: reply.chinese_reply,
        pinyin: reply.pinyin,
        translation: previewText(reply.translation),
        correction: reply.correction,
        audio_reply_url: null,
        audio_reply_base64: null,
        remaining_limit: previewState.subscription === "paid" ? -1 : 0,
        turn_count: previewState.voiceTurns,
        max_dialogs: PREVIEW_VOICE_MAX_DIALOGS,
        session_should_end: previewState.voiceTurns >= PREVIEW_VOICE_MAX_DIALOGS,
        budget_notice: null,
      };
    }
    case "desktop_voice_pronounce":
      return {
        ok: true,
        score: 88,
        passed: true,
        heard: String(args.target || ""),
        target: String(args.target || ""),
        target_pinyin: String(args.targetPinyin || ""),
        budget_notice: null,
      };
    case "desktop_voice_session_end": {
      if (previewState.voiceSessionId !== String(args.sessionId || "")) {
        throw new Error("SESSION_NOT_FOUND");
      }
      const turns = previewState.voiceTurns;
      previewState.voiceSessionId = "";
      previewState.voiceTurns = 0;
      return {
        ok: true,
        duration_seconds: 96,
        message_count: turns,
        corrections: turns > 0 ? [PREVIEW_VOICE_REPLIES[0].correction] : [],
        transcript: PREVIEW_VOICE_REPLIES.slice(0, turns).map((entry) => ({
          user: entry.transcription,
          assistant: entry.chinese_reply,
          pinyin: entry.pinyin,
          translation: previewText(entry.translation),
          correction: entry.correction,
          good: entry.correction === null,
        })),
        good_count: PREVIEW_VOICE_REPLIES.slice(0, turns).filter(
          (entry) => entry.correction === null,
        ).length,
        mistake_count: PREVIEW_VOICE_REPLIES.slice(0, turns).filter(
          (entry) => entry.correction !== null,
        ).length,
        reward: { xp_awarded: 10 },
      };
    }
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
        currentVersion: "1.3.4-preview",
        version: query.get("update") === "1" ? "1.3.4-preview" : undefined,
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
