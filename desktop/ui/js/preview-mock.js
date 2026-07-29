const query =
  typeof globalThis.location?.search === "string"
    ? new URLSearchParams(globalThis.location.search)
    : new URLSearchParams();

const previewState = {
  linked: query.get("unlinked") !== "1",
  pollCount: 0,
  language: "uz",
  completed: 1,
};

const localized = (uz, ru, tj) => ({ uz, ru, tj });

function bootstrap() {
  return {
    ok: true,
    authenticated: true,
    first_open: false,
    device: {
      id: "preview-device",
      platform: "preview",
      app_version: "0.1.0-preview",
    },
    user: {
      name: "Akbar",
      language: previewState.language,
      level: "hsk1",
      access_state: "active",
      is_paid: true,
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
        productName: "Pomp HSK AI",
        version: "0.1.0-preview",
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
        displayCode: "HSK4821X",
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
    case "desktop_tts_speak":
      return { ok: false, available: false, error: "desktop_tts_unavailable" };
    case "local_ai_model_status":
      return {
        modelId: "qwen3-4b-q4-k-m",
        installed: false,
        sizeBytes: null,
        state: "missing",
      };
    case "desktop_update_check":
      return {
        available: query.get("update") === "1",
        currentVersion: "0.1.0-preview",
        version: query.get("update") === "1" ? "0.2.0-preview" : undefined,
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
