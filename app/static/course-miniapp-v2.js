(function () {
  const LABELS = {
    uz: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Mustahkamlash",
      check: "Tekshirish",
      continue: "Davom etish",
      understood: "Tushunarli",
      return: "Botga qaytish",
      correct: "To'g'ri!",
      wrong: "Yana bir marta ko'ring",
      correctAnswer: "To'g'ri javob",
      yourAnswer: "Sizning javobingiz",
      explainError: "Xatoni tushuntirish",
      explanationTitle: "Xato sababi",
      answerLine: "Javob",
      noExplanation: "Javobni solishtiring: ma'no, so'z tartibi yoki tanlangan chip mos kelmagan.",
      listen: "Eshitish",
      listenSlow: "Sekin",
      speak: "Gapirish",
      recording: "Eshitilyapti...",
      voiceUnsupported: "Bu qurilmada ovoz tanish ishlamadi",
      skipVoice: "O'tkazib yuborish",
      seen: "Ko'rdim",
      tapPairs: "Juftliklarni tanlang",
      orderPlaceholder: "So'zlarni shu yerga yig'ing",
      quizDone: "Quiz tugadi",
      reinforceDone: "Ajoyib! Dars mustahkamlandi.",
      unlocked: "Keyingi dars ochildi",
      score: "{score}/{total} to'g'ri",
      xp: "+{xp} XP",
      loading: "Dars yuklanmoqda...",
      noTasks: "Topshiriqlar topilmadi. Kursdan qayta oching.",
      networkSaved: "Natija botga yuborildi.",
      networkPending: "Natija saqlandi. Botga qaytganda qayta yuboriladi.",
      lesson: "Dars",
      part: "qism",
      type_multiple_choice: "Tanlash",
      type_listening_choice: "Eshitib tanlash",
      type_fill_blank: "Bo'sh joy",
      type_fill_blank_choice: "Bo'sh joy",
      type_tap_missing_word: "Yetishmayotgan so'z",
      type_word_order: "So'z tartibi",
      type_build_sentence_chips: "Gap tuzish",
      type_choose_meaning_in_context: "Context ma'no",
      type_grammar_in_context: "Grammatika",
      type_listen_and_fill: "Eshitib to'ldirish",
      type_odd_one_out: "Ortiqchasini topish",
      type_build_chinese_sentence: "Xitoycha gap",
      type_match_pairs: "Moslashtirish",
      type_quick_match: "Tez moslashtirish",
      type_stroke_preview: "Iyeroglif",
      type_speak_repeat: "Ovoz bilan takrorlash",
    },
    ru: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Закрепление",
      check: "Проверить",
      continue: "Продолжить",
      understood: "Понятно",
      return: "Вернуться в бот",
      correct: "Правильно!",
      wrong: "Посмотрите ещё раз",
      correctAnswer: "Правильный ответ",
      yourAnswer: "Ваш ответ",
      explainError: "Объяснение ошибки",
      explanationTitle: "Почему ошибка",
      answerLine: "Ответ",
      noExplanation: "Сравните ответ: значение, порядок слов или выбранный чип не совпал.",
      listen: "Слушать",
      listenSlow: "Медленно",
      speak: "Говорить",
      recording: "Слушаю...",
      voiceUnsupported: "Распознавание голоса недоступно на этом устройстве",
      skipVoice: "Пропустить",
      seen: "Посмотрел",
      tapPairs: "Выберите пары",
      orderPlaceholder: "Соберите слова здесь",
      quizDone: "Quiz завершён",
      reinforceDone: "Отлично! Урок закреплён.",
      unlocked: "Следующий урок открыт",
      score: "{score}/{total} правильно",
      xp: "+{xp} XP",
      loading: "Загружаю урок...",
      noTasks: "Задания не найдены. Откройте заново из курса.",
      networkSaved: "Результат отправлен в бот.",
      networkPending: "Результат сохранён. Повторим отправку при возврате в бот.",
      lesson: "Урок",
      part: "часть",
      type_multiple_choice: "Выбор",
      type_listening_choice: "Аудирование",
      type_fill_blank: "Пропуск",
      type_fill_blank_choice: "Пропуск",
      type_tap_missing_word: "Пропущенное слово",
      type_word_order: "Порядок слов",
      type_build_sentence_chips: "Собрать фразу",
      type_choose_meaning_in_context: "Слово в контексте",
      type_grammar_in_context: "Грамматика",
      type_listen_and_fill: "Слушать и заполнить",
      type_odd_one_out: "Лишнее слово",
      type_build_chinese_sentence: "Китайское предложение",
      type_match_pairs: "Пары",
      type_quick_match: "Быстрые пары",
      type_stroke_preview: "Иероглиф",
      type_speak_repeat: "Повторить голосом",
    },
    tj: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Мустаҳкамкунӣ",
      check: "Санҷидан",
      continue: "Давом додан",
      understood: "Фаҳмо",
      return: "Бозгашт ба бот",
      correct: "Дуруст!",
      wrong: "Боз як бор бинед",
      correctAnswer: "Ҷавоби дуруст",
      yourAnswer: "Ҷавоби шумо",
      explainError: "Шарҳи хато",
      explanationTitle: "Сабаби хато",
      answerLine: "Ҷавоб",
      noExplanation: "Ҷавобро муқоиса кунед: маъно, тартиби калимаҳо ё чипи интихобшуда мувофиқ нашуд.",
      listen: "Гӯш кардан",
      listenSlow: "Оҳиста",
      speak: "Гап задан",
      recording: "Гӯш карда истодаам...",
      voiceUnsupported: "Шинохти овоз дар ин дастгоҳ дастрас нест",
      skipVoice: "Гузарондан",
      seen: "Дидам",
      tapPairs: "Ҷуфтҳоро интихоб кунед",
      orderPlaceholder: "Калимаҳоро ин ҷо ҷамъ кунед",
      quizDone: "Quiz анҷом шуд",
      reinforceDone: "Офарин! Дарс мустаҳкам шуд.",
      unlocked: "Дарси навбатӣ кушода шуд",
      score: "{score}/{total} дуруст",
      xp: "+{xp} XP",
      loading: "Дарс бор мешавад...",
      noTasks: "Супоришҳо ёфт нашуданд. Аз курс дубора кушоед.",
      networkSaved: "Натиҷа ба бот фиристода шуд.",
      networkPending: "Натиҷа нигоҳ дошта шуд. Ҳангоми бозгашт дубора мефиристем.",
      lesson: "Дарс",
      part: "қисм",
      type_multiple_choice: "Интихоб",
      type_listening_choice: "Гӯш карда интихоб",
      type_fill_blank: "Ҷои холӣ",
      type_fill_blank_choice: "Ҷои холӣ",
      type_tap_missing_word: "Калимаи намерасида",
      type_word_order: "Тартиби калимаҳо",
      type_build_sentence_chips: "Сохтани ҷумла",
      type_choose_meaning_in_context: "Маъно дар context",
      type_grammar_in_context: "Грамматика",
      type_listen_and_fill: "Гӯш карда пур кардан",
      type_odd_one_out: "Калимаи номувофиқ",
      type_build_chinese_sentence: "Ҷумлаи чинӣ",
      type_match_pairs: "Ҷуфтҳо",
      type_quick_match: "Ҷуфтҳои тез",
      type_stroke_preview: "Иероглиф",
      type_speak_repeat: "Бо овоз такрор кардан",
    },
  };

  const CHARACTERS = [
    { id: "lumo", name: "Lumo", accent: "#7ce66b", face: "#d9fff2", shell: "#2dd4bf", mood: "curious", trait: "fast-feedback coach" },
    { id: "byte", name: "Byte", accent: "#67b7ff", face: "#eaf6ff", shell: "#3b82f6", mood: "sharp", trait: "grammar scanner" },
    { id: "nuri", name: "Nuri", accent: "#c084fc", face: "#f4e8ff", shell: "#8b5cf6", mood: "calm", trait: "pronunciation listener" },
    { id: "orbit", name: "Orbit", accent: "#f9a8d4", face: "#fff0f7", shell: "#ec4899", mood: "playful", trait: "memory booster" },
  ];

  function l(state, key, vars = {}) {
    let text = (LABELS[state.lang] || LABELS.uz)[key] || LABELS.uz[key] || key;
    Object.keys(vars).forEach((name) => {
      text = text.replaceAll(`{${name}}`, vars[name]);
    });
    return text;
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function attr(value) {
    return esc(value).replaceAll("`", "&#096;");
  }

  function normalizeLang(value) {
    const raw = String(value || "").toLowerCase();
    if (raw === "tg" || raw === "tg-cyrl") return "tj";
    return ["uz", "ru", "tj"].includes(raw) ? raw : "uz";
  }

  function compact(value) {
    return String(value || "").trim();
  }

  function normalizeVoiceText(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[\s。，、！？!?.,;:：；"'“”‘’()（）\[\]{}<>《》-]/g, "")
      .trim();
  }

  function voiceMatches(actual, expected) {
    const heard = normalizeVoiceText(actual);
    const target = normalizeVoiceText(expected);
    if (!heard || !target) return false;
    return heard === target || heard.includes(target) || (target.includes(heard) && heard.length >= 2);
  }

  function speechRecognitionFactory() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  function getCharacter(state, task) {
    if (task.type === "speak_repeat") return CHARACTERS.find((item) => item.id === "nuri") || CHARACTERS[0];
    if (String(task.type || "").includes("grammar")) return CHARACTERS.find((item) => item.id === "byte") || CHARACTERS[0];
    if (isMatchType(task.type)) return CHARACTERS.find((item) => item.id === "orbit") || CHARACTERS[0];
    const seed = `${state.lessonId}:${state.blockNo || 0}:${task.id || state.index}:${task.type || ""}`;
    let value = 0;
    for (let i = 0; i < seed.length; i += 1) value = (value + seed.charCodeAt(i) * (i + 1)) % 997;
    return CHARACTERS[value % CHARACTERS.length];
  }

  function robotSvg(character, mood = "idle") {
    const happy = mood === "happy";
    const sad = mood === "sad";
    const listening = mood === "listening";
    const eyeY = happy ? 61 : 58;
    const eyeShape = listening ? "M52 58 q6 -7 12 0" : `M52 ${eyeY} h14`;
    const rightEyeShape = listening ? "M86 58 q6 -7 12 0" : `M86 ${eyeY} h14`;
    const mouth = happy ? "M63 84 q13 14 28 0" : sad ? "M64 91 q13 -12 28 0" : "M66 86 h24";
    const wave = listening
      ? `<path d="M118 48 q13 12 0 24" fill="none" stroke="${attr(character.accent)}" stroke-width="5" stroke-linecap="round"/><path d="M128 41 q24 20 0 40" fill="none" stroke="${attr(character.accent)}" stroke-width="4" stroke-linecap="round" opacity=".7"/>`
      : "";
    return `
      <svg viewBox="0 0 160 160" role="img" aria-label="${attr(character.name)}" class="cmv2-robot-svg">
        <ellipse cx="80" cy="139" rx="48" ry="10" fill="#091216" opacity=".35"/>
        <path d="M80 27 v-13" stroke="${attr(character.accent)}" stroke-width="7" stroke-linecap="round"/>
        <circle cx="80" cy="10" r="8" fill="${attr(character.accent)}"/>
        <rect x="24" y="36" width="112" height="92" rx="30" fill="${attr(character.shell)}"/>
        <rect x="35" y="47" width="90" height="68" rx="24" fill="${attr(character.face)}"/>
        <rect x="14" y="65" width="18" height="36" rx="9" fill="#263842"/>
        <rect x="128" y="65" width="18" height="36" rx="9" fill="#263842"/>
        <path d="${eyeShape}" fill="none" stroke="#132129" stroke-width="8" stroke-linecap="round"/>
        <path d="${rightEyeShape}" fill="none" stroke="#132129" stroke-width="8" stroke-linecap="round"/>
        <path d="${mouth}" fill="none" stroke="#132129" stroke-width="7" stroke-linecap="round"/>
        <circle cx="47" cy="76" r="5" fill="${attr(character.accent)}" opacity=".55"/>
        <circle cx="111" cy="76" r="5" fill="${attr(character.accent)}" opacity=".55"/>
        <path d="M50 128 v12M110 128 v12" stroke="#263842" stroke-width="10" stroke-linecap="round"/>
        ${wave}
      </svg>
    `;
  }

  function bubbleHtml(state, task) {
    const fillLike = FILL_TYPES.has(task.type);
    const contextLike = CONTEXT_TYPES.has(task.type);
    let main = "";
    let sub = task.hint || "";
    if (task.type === "stroke_preview") {
      main = esc(task.word || (task.chars || []).join(""));
      sub = [task.pinyin, task.meaning].filter(Boolean).join(" · ");
    } else if (isMatchType(task.type)) {
      main = esc(task.prompt || l(state, "tapPairs"));
      sub = task.explanation || "";
    } else if (isOrderType(task.type)) {
      main = esc(task.translation || task.source || task.prompt || "");
      sub = l(state, "orderPlaceholder");
    } else if (task.type === "speak_repeat") {
      main = esc(task.audioText || task.answer || "");
      sub = task.translation || task.source || l(state, "type_speak_repeat");
    } else if (task.sentence) {
      main = fillLike ? renderBlankText(task.sentence, "") : renderHighlightedText(task.sentence);
      sub = task.source || task.translation || task.hint || "";
    } else if (task.source) {
      main = contextLike ? renderHighlightedText(task.source) : esc(task.source);
      sub = task.translation || task.hint || "";
    } else {
      main = esc(task.hint || task.label || taskLabel(state, task.type, task.type));
      sub = task.label && task.hint ? task.label : "";
    }
    const audioText = task.audioText || (task.type === "speak_repeat" ? task.answer : "");
    const audioButton = audioText
      ? `<button class="cmv2-audio cmv2-bubble-audio" id="cmv2-bubble-audio" type="button" data-audio="${attr(audioText)}">▶ ${esc(l(state, "listen"))}</button>`
      : "";
    return `
      <div class="cmv2-bubble-main">${main}</div>
      ${sub ? `<div class="cmv2-bubble-sub">${esc(sub)}</div>` : ""}
      ${audioButton}
    `;
  }

  function arraysEqual(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
    return a.every((item, index) => compact(item) === compact(b[index]));
  }

  function pairKey(pair) {
    if (Array.isArray(pair)) return `${compact(pair[0])}|||${compact(pair[1])}`;
    return `${compact(pair?.left)}|||${compact(pair?.right)}`;
  }

  function samePairs(a, b) {
    const left = new Set((a || []).map(pairKey));
    const right = new Set((b || []).map(pairKey));
    if (left.size !== right.size) return false;
    for (const item of left) {
      if (!right.has(item)) return false;
    }
    return true;
  }

  function shuffle(list, seed) {
    const items = [...list];
    let value = 0;
    for (let i = 0; i < seed.length; i += 1) value = (value * 31 + seed.charCodeAt(i)) >>> 0;
    for (let i = items.length - 1; i > 0; i -= 1) {
      const j = value % (i + 1);
      [items[i], items[j]] = [items[j], items[i]];
      value = (value * 31 + i) >>> 0;
    }
    return items;
  }

  function injectStyles() {
    if (document.getElementById("course-miniapp-v2-style")) return;
    const style = document.createElement("style");
    style.id = "course-miniapp-v2-style";
    style.textContent = `
body.course-miniapp-v2{margin:0;min-height:100vh;overflow:hidden;background:#fbfcff;color:#202938;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
body.course-miniapp-v2 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent;letter-spacing:0;}
.cmv2{height:100vh;height:100dvh;display:flex;flex-direction:column;background:linear-gradient(180deg,#ffffff 0%,#f7f9fd 100%);}
.cmv2-top{padding:calc(14px + env(safe-area-inset-top,0px)) 18px 10px;border-bottom:1px solid #edf0f6;background:rgba(255,255,255,.96);backdrop-filter:blur(18px);}
.cmv2-row{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.cmv2-close{width:38px;height:38px;border:0;background:#f2f5fa;border-radius:12px;color:#5b6474;font-size:22px;line-height:1;display:grid;place-items:center;}
.cmv2-brand{font-weight:800;color:#2f7cf6;font-size:18px;}
.cmv2-xp{min-width:58px;text-align:right;color:#ec7d35;font-weight:800;font-size:14px;}
.cmv2-progress{height:10px;background:#e8edf5;border-radius:999px;overflow:hidden;margin-top:12px;}
.cmv2-progress span{display:block;height:100%;width:0;background:linear-gradient(90deg,#23c7a7,#2f7cf6);border-radius:999px;transition:width .28s ease;}
.cmv2-main{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:18px 18px 150px;}
.cmv2-meta{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:18px;}
.cmv2-pill{display:inline-flex;align-items:center;min-height:30px;padding:6px 11px;border-radius:999px;background:#eef4ff;color:#2f63c5;font-size:12px;font-weight:800;}
.cmv2-count{font-size:13px;color:#7a8494;font-weight:700;}
.cmv2-prompt{font-size:25px;line-height:1.18;font-weight:850;color:#252b36;margin:0 0 14px;white-space:pre-line;}
.cmv2-source{background:#ffffff;border:1px solid #e5eaf2;border-radius:18px;padding:16px;margin:0 0 16px;box-shadow:0 10px 28px rgba(25,36,59,.07);}
.cmv2-source-main{font-size:28px;line-height:1.3;font-weight:800;color:#242b36;word-break:break-word;}
.cmv2-source-sub{margin-top:6px;color:#738093;font-size:14px;line-height:1.45;}
.cmv2-audio{border:0;background:#eaf4ff;color:#2473da;border-radius:16px;padding:12px 14px;font-weight:850;display:inline-flex;align-items:center;gap:8px;margin-bottom:14px;}
.cmv2-options{display:flex;flex-direction:column;gap:10px;}
.cmv2-option{width:100%;min-height:58px;border:2px solid #dfe5ee;background:#fff;border-radius:16px;padding:14px 16px;text-align:left;font-size:18px;font-weight:750;color:#303847;box-shadow:0 4px 0 #dfe5ee;transition:transform .12s ease,border-color .12s ease,box-shadow .12s ease,background .12s ease;}
.cmv2-option:active{transform:translateY(2px);box-shadow:0 2px 0 #dfe5ee;}
.cmv2-option.selected{border-color:#2f7cf6;box-shadow:0 4px 0 #98c2ff;background:#f4f9ff;}
.cmv2-option.correct{border-color:#17b978;box-shadow:0 4px 0 #9ee8c9;background:#effcf6;}
.cmv2-option.wrong{border-color:#ee7c67;box-shadow:0 4px 0 #ffc0b5;background:#fff4f1;}
.cmv2-blank{font-size:22px;font-weight:850;color:#252b36;line-height:1.35;margin-bottom:14px;padding-bottom:10px;border-bottom:3px solid #e5eaf2;}
.cmv2-sentence{background:#fff;border:1px solid #e5eaf2;border-radius:20px;padding:18px 16px;margin:0 0 16px;box-shadow:0 10px 28px rgba(25,36,59,.07);}
.cmv2-sentence-main{font-size:28px;line-height:1.35;font-weight:850;color:#242b36;word-break:break-word;}
.cmv2-slot{display:inline-flex;align-items:center;justify-content:center;min-width:74px;min-height:42px;margin:0 3px;padding:2px 12px;border:2px solid #8bb9ff;border-radius:14px;background:#f4f9ff;color:#2f7cf6;vertical-align:middle;box-shadow:0 3px 0 #c4dcff;transition:transform .15s ease,background .15s ease;}
.cmv2-slot.empty{color:#a7b1c0;background:#f8fbff;border-style:dashed;box-shadow:none;}
.cmv2-slot.filled{transform:translateY(-1px);background:#eaf4ff;}
.cmv2-highlight{display:inline-block;padding:0 7px;border-radius:10px;background:#eaf4ff;color:#1f65c8;border-bottom:3px solid #8bb9ff;}
.cmv2-order-box{min-height:86px;border:2px dashed #d9e0ea;border-radius:18px;background:#fff;padding:12px;display:flex;gap:8px;flex-wrap:wrap;align-content:flex-start;margin-bottom:16px;}
.cmv2-placeholder{color:#9aa3b2;font-size:15px;font-weight:700;align-self:center;}
.cmv2-bank{display:flex;gap:9px;flex-wrap:wrap;}
.cmv2-chip{border:2px solid #dfe5ee;background:#fff;border-radius:14px;padding:10px 13px;font-size:17px;font-weight:800;color:#313847;box-shadow:0 3px 0 #dfe5ee;}
.cmv2-chip:disabled{opacity:.28;box-shadow:none;}
.cmv2-chip.selected{border-color:#2f7cf6;background:#f4f9ff;box-shadow:0 3px 0 #98c2ff;}
.cmv2-match{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.cmv2-match-col{display:flex;flex-direction:column;gap:9px;}
.cmv2-match-btn{min-height:48px;border:2px solid #dfe5ee;background:#fff;border-radius:14px;padding:10px;font-size:16px;font-weight:800;color:#303847;box-shadow:0 3px 0 #dfe5ee;}
.cmv2-match-btn.active{border-color:#7c5cff;background:#f6f3ff;box-shadow:0 3px 0 #c9bbff;}
.cmv2-match-btn.done{border-color:#17b978;background:#effcf6;color:#167d56;}
.cmv2-pairs{margin-top:12px;display:flex;flex-direction:column;gap:7px;}
.cmv2-pair{border:1px solid #dfe5ee;background:#fff;border-radius:12px;padding:9px 10px;color:#5a6575;font-weight:700;}
.cmv2-stroke{background:#fff;border:1px solid #e5eaf2;border-radius:22px;padding:22px 16px;text-align:center;box-shadow:0 10px 28px rgba(25,36,59,.07);}
.cmv2-hanzi{font-size:70px;font-weight:900;line-height:1;color:#202938;}
.cmv2-pinyin{margin-top:12px;color:#2f7cf6;font-weight:850;font-size:18px;}
.cmv2-meaning{margin-top:4px;color:#6a7485;font-weight:700;}
.cmv2-feedback{position:fixed;left:0;right:0;bottom:calc(86px + env(safe-area-inset-bottom,0px));padding:0 18px;transform:translateY(18px);opacity:0;pointer-events:none;transition:transform .18s ease,opacity .18s ease;z-index:30;}
.cmv2-feedback.show{transform:translateY(0);opacity:1;pointer-events:auto;}
.cmv2-sheet{border-radius:20px;padding:15px 16px;border:1px solid #dfe5ee;background:#fff;box-shadow:0 18px 44px rgba(27,38,62,.14);}
.cmv2-sheet.ok{background:#effcf6;border-color:#bdeed8;color:#12734e;}
.cmv2-sheet.no{background:#fff4f1;border-color:#ffd0c6;color:#a84531;}
.cmv2-sheet-title{font-size:18px;font-weight:900;margin-bottom:4px;}
.cmv2-sheet-text{font-size:14px;line-height:1.45;font-weight:650;}
.cmv2-footer{position:fixed;left:0;right:0;bottom:0;padding:12px 18px calc(14px + env(safe-area-inset-bottom,0px));background:rgba(255,255,255,.96);border-top:1px solid #edf0f6;backdrop-filter:blur(18px);z-index:40;}
.cmv2-primary{width:100%;min-height:58px;border:0;border-radius:17px;background:#2f7cf6;color:#fff;font-size:16px;font-weight:900;box-shadow:0 5px 0 #1f5dbb;transition:transform .12s ease,opacity .12s ease,box-shadow .12s ease;}
.cmv2-primary:active{transform:translateY(2px);box-shadow:0 3px 0 #1f5dbb;}
.cmv2-primary:disabled{opacity:.42;background:#cfd6e0;box-shadow:0 5px 0 #b8c1cc;color:#fff;}
.cmv2-result{text-align:center;padding:22px 0;}
.cmv2-result-icon{width:82px;height:82px;margin:0 auto 16px;border-radius:26px;background:linear-gradient(135deg,#23c7a7,#2f7cf6);display:grid;place-items:center;color:#fff;font-size:40px;font-weight:900;box-shadow:0 18px 40px rgba(47,124,246,.22);}
.cmv2-result h1{font-size:28px;line-height:1.16;margin:0 0 8px;color:#202938;}
.cmv2-result p{font-size:15px;line-height:1.45;color:#697386;margin:0 0 12px;}
.cmv2-status{margin-top:14px;border-radius:16px;padding:12px 13px;background:#f2f6fb;color:#637083;font-weight:750;font-size:13px;line-height:1.4;}
.cmv2-error{padding:22px;background:#fff;border:1px solid #e5eaf2;border-radius:20px;box-shadow:0 10px 28px rgba(25,36,59,.07);}
@media (min-width:640px){.cmv2{max-width:520px;margin:0 auto;border-left:1px solid #edf0f6;border-right:1px solid #edf0f6;}.cmv2-feedback,.cmv2-footer{left:50%;right:auto;width:520px;transform:translateX(-50%);} .cmv2-feedback{transform:translate(-50%,18px);} .cmv2-feedback.show{transform:translate(-50%,0);}}
body.course-miniapp-v2{background:#131f24;color:#f2f7fb;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
.cmv2{background:#131f24;color:#f2f7fb;}
.cmv2-top{background:#131f24;border-bottom:0;padding:calc(14px + env(safe-area-inset-top,0px)) 20px 8px;backdrop-filter:none;}
.cmv2-row{gap:14px;}.cmv2-close{background:transparent;color:#6f838f;border-radius:10px;font-size:34px;font-weight:800;width:42px;height:42px;}.cmv2-brand{color:#7ce66b;font-size:24px;font-weight:950;letter-spacing:0;}.cmv2-xp{color:#f28acb;font-size:20px;min-width:68px;}.cmv2-xp::before{content:"⚡";display:inline-grid;place-items:center;width:29px;height:29px;margin-right:8px;border-radius:8px;background:#f28acb;color:#fff;font-size:19px;vertical-align:middle;box-shadow:inset -6px 0 rgba(0,0,0,.12);}
.cmv2-progress{height:20px;background:#3a4853;border-radius:999px;margin-top:16px;box-shadow:inset 0 1px 0 rgba(255,255,255,.06);}.cmv2-progress span{background:linear-gradient(90deg,#68f7e5 0%,#55b4ff 46%,#7ee35f 100%);box-shadow:inset 0 -4px rgba(0,0,0,.08);}.cmv2-main{padding:20px 20px 196px;background:#131f24;}.cmv2-meta{margin-bottom:16px;}.cmv2-pill{background:transparent;color:#c18cff;font-size:19px;text-transform:uppercase;letter-spacing:0;font-weight:950;padding:0;min-height:0;border-radius:0;}.cmv2-count{color:#7f929d;font-size:13px;font-weight:850;}.cmv2-prompt{color:#f5f7fb;font-size:27px;line-height:1.15;margin:0 0 20px;font-weight:950;}
.cmv2-scene{display:grid;grid-template-columns:minmax(104px,34%) 1fr;gap:14px;align-items:end;margin:0 0 22px;}.cmv2-character{position:relative;min-height:160px;display:flex;align-items:flex-end;justify-content:center;}.cmv2-robot-svg{width:min(172px,100%);height:auto;display:block;filter:drop-shadow(0 12px 0 rgba(0,0,0,.18));}.cmv2-character-tag{position:absolute;left:50%;bottom:-3px;transform:translateX(-50%);display:flex;align-items:center;gap:5px;min-height:24px;padding:3px 9px;border-radius:999px;background:#22313a;color:#dbe8ef;border:1px solid #40515d;font-size:11px;font-weight:900;white-space:nowrap;}
.cmv2-bubble{position:relative;min-height:132px;border:3px solid #40515d;border-radius:18px;padding:20px 20px 16px;background:#131f24;color:#f7fbff;align-self:center;}.cmv2-bubble::before{content:"";position:absolute;left:-26px;bottom:35px;width:26px;height:24px;background:#131f24;border-left:3px solid #40515d;border-bottom:3px solid #40515d;transform:skewX(-34deg);border-bottom-left-radius:5px;}.cmv2-bubble-main{font-size:32px;line-height:1.25;font-weight:650;color:#f7fbff;word-break:break-word;}.cmv2-bubble-sub{margin-top:10px;color:#7f929d;font-size:15px;line-height:1.35;font-weight:800;}.cmv2-bubble-audio{margin:14px 0 0;}.cmv2-audio{background:transparent;color:#61bfff;border:0;padding:8px 0;font-size:17px;font-weight:950;}
.cmv2-source,.cmv2-sentence{background:transparent;border:0;border-radius:0;padding:0;margin:0 0 14px;box-shadow:none;color:#f2f7fb;}.cmv2-source-main,.cmv2-sentence-main{color:#f2f7fb;font-size:29px;}.cmv2-source-sub{color:#7f929d;font-weight:800;}.cmv2-highlight{background:transparent;color:#f7fbff;border-bottom:4px dotted #738692;border-radius:0;padding:0 2px;}.cmv2-blank{color:#f2f7fb;border-bottom:4px solid #40515d;}.cmv2-slot{border-color:#4d6370;background:#192830;color:#f7fbff;box-shadow:0 4px 0 #2d3d47;min-width:78px;}.cmv2-slot.empty{background:#192830;color:#697d88;border-style:solid;box-shadow:0 4px 0 #2d3d47;}.cmv2-slot.filled{background:#20313b;color:#f7fbff;border-color:#8b5cf6;box-shadow:0 4px 0 #5b3ca1;}
.cmv2-answer-lines{display:flex;flex-direction:column;gap:28px;margin:18px 0 42px;}.cmv2-answer-line{height:2px;background:#40515d;border-radius:999px;}.cmv2-options{display:flex;flex-direction:row;flex-wrap:wrap;gap:12px;align-items:center;justify-content:center;margin-top:28px;}.cmv2-option,.cmv2-chip,.cmv2-match-btn{background:#131f24;color:#f5f7fb;border:3px solid #40515d;box-shadow:0 5px 0 #2b3942;border-radius:16px;font-size:22px;font-weight:650;min-height:58px;}.cmv2-option{width:auto;min-width:92px;text-align:center;padding:12px 18px;}.cmv2-option.selected,.cmv2-chip.selected,.cmv2-match-btn.active{border-color:#67b7ff;background:#172933;box-shadow:0 5px 0 #315d75;}.cmv2-option.correct{border-color:#58cc02;background:#193220;box-shadow:0 5px 0 #3a8f0f;color:#dfffce;}.cmv2-option.wrong{border-color:#e75f5a;background:#321d22;box-shadow:0 5px 0 #a84b4a;color:#ffd9d7;}
.cmv2-order-box{min-height:116px;border:0;border-top:2px solid #40515d;border-bottom:2px solid #40515d;border-radius:0;background:transparent;padding:20px 0;margin:0 0 28px;}.cmv2-placeholder{color:#647984;font-size:16px;font-weight:900;}.cmv2-bank{justify-content:center;gap:12px;}.cmv2-chip{font-size:25px;padding:11px 18px;}.cmv2-chip:disabled{opacity:.25;background:#131f24;box-shadow:none;}.cmv2-match{gap:12px;margin-top:10px;}.cmv2-match-col{gap:12px;}.cmv2-match-btn{font-size:18px;}.cmv2-match-btn.done{border-color:#58cc02;background:#193220;color:#dfffce;box-shadow:0 5px 0 #3a8f0f;}.cmv2-pair{border:2px solid #40515d;background:#17252c;color:#f2f7fb;border-radius:14px;font-weight:850;}
.cmv2-stroke{background:#17252c;border:3px solid #40515d;border-radius:20px;box-shadow:0 6px 0 #2b3942;color:#f2f7fb;}.cmv2-hanzi{color:#f7fbff;}.cmv2-pinyin{color:#67b7ff;}.cmv2-meaning{color:#9cadb6;}.cmv2-voice-card{display:flex;flex-direction:column;gap:14px;align-items:center;margin-top:10px;}.cmv2-mic{width:108px;height:108px;border-radius:999px;border:4px solid #67b7ff;background:#172933;color:#f7fbff;font-size:38px;font-weight:950;box-shadow:0 8px 0 #315d75;}.cmv2-mic.recording{border-color:#f28acb;background:#332331;box-shadow:0 8px 0 #9f4d7b;animation:cmv2-pulse 1s infinite;}.cmv2-transcript{min-height:52px;width:100%;border:2px solid #40515d;border-radius:16px;padding:13px 14px;color:#dbe8ef;background:#17252c;font-size:18px;font-weight:800;text-align:center;}.cmv2-voice-skip{border:0;background:transparent;color:#9cadb6;font-size:15px;font-weight:900;text-decoration:underline;}
.cmv2-feedback{bottom:calc(78px + env(safe-area-inset-bottom,0px));padding:0;z-index:35;}.cmv2-sheet{border-radius:0;padding:22px 20px 20px;background:#22313a;border:0;box-shadow:none;}.cmv2-sheet.ok{background:#193320;color:#58cc02;border:0;}.cmv2-sheet.no{background:#22313a;color:#e75f5a;border:0;}.cmv2-sheet-title{font-size:28px;font-weight:950;margin-bottom:10px;}.cmv2-sheet-text{font-size:19px;line-height:1.35;font-weight:650;color:inherit;}.cmv2-explain-btn{width:100%;min-height:58px;margin-top:18px;border:3px solid #a85b5d;border-radius:18px;background:transparent;color:#e75f5a;font-size:17px;font-weight:950;text-transform:uppercase;}.cmv2-footer{background:#22313a;border-top:0;padding:12px 20px calc(14px + env(safe-area-inset-bottom,0px));}.cmv2-primary{min-height:62px;border-radius:18px;background:#58cc02;color:#10210b;font-size:18px;font-weight:950;box-shadow:0 7px 0 #46a302;text-transform:uppercase;}.cmv2-primary:active{box-shadow:0 4px 0 #46a302;}.cmv2-primary.danger{background:#e75f5a;color:#111b20;box-shadow:0 7px 0 #c64a45;}.cmv2-primary:disabled{background:#3b4953;box-shadow:none;color:#6d7e88;opacity:1;}
.cmv2-result h1{color:#f7fbff;}.cmv2-result p{color:#9cadb6;}.cmv2-result-icon{background:linear-gradient(135deg,#58cc02,#67b7ff);color:#101a1e;}.cmv2-status,.cmv2-error{background:#17252c;color:#dbe8ef;border:2px solid #40515d;box-shadow:none;}.cmv2-modal{position:fixed;inset:0;background:rgba(7,13,16,.72);display:grid;place-items:end center;padding:20px;z-index:60;}.cmv2-modal-card{width:min(100%,520px);max-height:82vh;overflow:auto;background:#22313a;border:3px solid #40515d;border-radius:24px;padding:20px;color:#f7fbff;box-shadow:0 24px 60px rgba(0,0,0,.36);}.cmv2-modal-head{display:grid;grid-template-columns:88px 1fr;gap:14px;align-items:center;margin-bottom:14px;}.cmv2-modal-title{font-size:24px;font-weight:950;color:#f7fbff;}.cmv2-modal-text{font-size:17px;line-height:1.45;color:#dbe8ef;font-weight:700;margin:0 0 16px;}.cmv2-modal-answer{border:2px solid #40515d;background:#17252c;border-radius:18px;padding:14px;margin:0 0 14px;color:#f7fbff;font-size:18px;font-weight:850;}
@keyframes cmv2-pulse{0%{transform:scale(1)}50%{transform:scale(1.04)}100%{transform:scale(1)}}
@media (max-width:390px){.cmv2-main{padding-left:16px;padding-right:16px}.cmv2-scene{grid-template-columns:100px 1fr;gap:10px}.cmv2-bubble{padding:16px 14px}.cmv2-bubble-main{font-size:27px}.cmv2-prompt{font-size:25px}.cmv2-option,.cmv2-chip{font-size:20px}}
@media (min-width:640px){.cmv2{max-width:520px;border-left:1px solid #22313a;border-right:1px solid #22313a}.cmv2-feedback{left:50%;right:auto;width:520px;transform:translate(-50%,18px)}.cmv2-feedback.show{transform:translate(-50%,0)}.cmv2-footer{left:50%;right:auto;width:520px;transform:translateX(-50%)}}
.cmv2-top{padding:calc(8px + env(safe-area-inset-top,0px)) 20px 8px;}
.cmv2-progress{height:14px;margin-top:0;}
.cmv2-main{padding:16px 20px 156px;}
.cmv2-meta{margin-bottom:12px;}
.cmv2-pill{font-size:16px;font-weight:950;}
.cmv2-count{display:none;}
.cmv2-prompt{font-size:23px;line-height:1.2;margin:0 0 16px;font-weight:900;}
.cmv2-scene{grid-template-columns:92px 1fr;gap:10px;align-items:end;margin:0 0 16px;}
.cmv2-character{min-height:118px;}
.cmv2-robot-svg{width:min(112px,100%);filter:drop-shadow(0 8px 0 rgba(0,0,0,.16));}
.cmv2-character-tag{display:none;}
.cmv2-bubble{min-height:110px;border-width:3px;border-radius:18px;padding:16px 16px 14px;}
.cmv2-bubble::before{left:-21px;width:22px;height:22px;bottom:30px;}
.cmv2-bubble-main{font-size:24px;line-height:1.25;font-weight:750;}
.cmv2-bubble-sub{font-size:14px;line-height:1.35;margin-top:8px;}
.cmv2-bubble-audio{margin-top:10px;}
.cmv2-answer-lines{gap:24px;margin:12px 0 34px;}
.cmv2-options{gap:10px;margin-top:22px;}
.cmv2-option,.cmv2-chip,.cmv2-match-btn{font-size:19px;min-height:50px;border-radius:15px;}
.cmv2-option{min-width:82px;padding:10px 15px;}
.cmv2-order-box{min-height:92px;padding:16px 0;margin-bottom:22px;}
.cmv2-bank{gap:10px;}
.cmv2-chip{font-size:21px;padding:10px 15px;}
.cmv2-voice-card{gap:12px;margin-top:8px;}
.cmv2-mic{width:88px;height:88px;font-size:32px;box-shadow:0 6px 0 #315d75;}
.cmv2-transcript{font-size:16px;min-height:46px;padding:11px 12px;}
.cmv2-footer{padding:10px 20px calc(12px + env(safe-area-inset-bottom,0px));}
.cmv2-primary{min-height:56px;font-size:16px;border-radius:17px;}
@media (max-width:390px){.cmv2-main{padding-left:18px;padding-right:18px}.cmv2-scene{grid-template-columns:82px 1fr;gap:8px}.cmv2-character{min-height:108px}.cmv2-robot-svg{width:min(98px,100%)}.cmv2-bubble{padding:14px 13px}.cmv2-bubble-main{font-size:22px}.cmv2-prompt{font-size:22px}.cmv2-option,.cmv2-chip{font-size:18px}.cmv2-chip{font-size:20px}}
`;
    document.head.appendChild(style);
  }

  function tg() {
    return window.Telegram?.WebApp;
  }

  function haptic(kind) {
    try {
      if (kind === "success" || kind === "error") tg()?.HapticFeedback?.notificationOccurred(kind);
      else tg()?.HapticFeedback?.impactOccurred("light");
    } catch (e) {}
  }

  function speak(text, rate = 0.82) {
    const value = compact(text);
    if (!value || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(value);
      utterance.lang = "zh-CN";
      utterance.rate = rate;
      utterance.pitch = 1.02;
      window.speechSynthesis.speak(utterance);
    } catch (e) {}
  }

  function taskLabel(state, type, fallback) {
    return l(state, `type_${type}`) || fallback || type;
  }

  function formatAnswer(task) {
    if (Array.isArray(task.answer)) {
      return ["build_chinese_sentence", "build_sentence_chips"].includes(task.type) ? task.answer.join("") : task.answer.join(" ");
    }
    if (isMatchType(task.type)) {
      return (task.pairs || []).map((pair) => `${pair[0]} = ${pair[1]}`).join(" · ");
    }
    if (task.type === "stroke_preview") {
      return [task.word, task.pinyin, task.meaning].filter(Boolean).join(" · ");
    }
    if (task.type === "speak_repeat") {
      return compact(task.answer || task.audioText);
    }
    return compact(task.answer);
  }

  const CHOICE_TYPES = new Set([
    "multiple_choice",
    "listening_choice",
    "fill_blank",
    "fill_blank_choice",
    "tap_missing_word",
    "choose_meaning_in_context",
    "grammar_in_context",
    "listen_and_fill",
    "odd_one_out",
    "grammar_example_to_pattern",
    "grammar_pattern_to_example",
  ]);
  const ORDER_TYPES = new Set(["word_order", "build_chinese_sentence", "build_sentence_chips"]);
  const MATCH_TYPES = new Set(["match_pairs", "quick_match"]);
  const STROKE_TYPES = new Set(["stroke_preview"]);
  const SPEAK_TYPES = new Set(["speak_repeat"]);
  const FILL_TYPES = new Set(["fill_blank", "fill_blank_choice", "tap_missing_word", "listen_and_fill"]);
  const CONTEXT_TYPES = new Set(["choose_meaning_in_context", "grammar_in_context"]);

  function isChoiceType(type) {
    return CHOICE_TYPES.has(type);
  }

  function isOrderType(type) {
    return ORDER_TYPES.has(type);
  }

  function isMatchType(type) {
    return MATCH_TYPES.has(type);
  }

  function isSpeakType(type) {
    return SPEAK_TYPES.has(type);
  }

  function renderHighlightedText(value) {
    const text = compact(value);
    if (!text.includes("【") || !text.includes("】")) return esc(text);
    const before = text.split("【")[0] || "";
    const rest = text.slice(before.length + 1);
    const target = rest.split("】")[0] || "";
    const after = rest.slice(target.length + 1);
    return `${esc(before)}<span class="cmv2-highlight">${esc(target)}</span>${esc(after)}`;
  }

  function renderBlankText(sentence, selected) {
    const value = compact(sentence);
    const slotClass = selected ? "cmv2-slot filled" : "cmv2-slot empty";
    const slotText = selected || "...";
    if (!value.includes("____")) {
      return `${esc(value)} <span class="${slotClass}" id="cmv2-blank-slot">${esc(slotText)}</span>`;
    }
    const parts = value.split("____");
    return `${esc(parts[0])}<span class="${slotClass}" id="cmv2-blank-slot">${esc(slotText)}</span>${esc(parts.slice(1).join("____"))}`;
  }

  function normalizeTask(raw, index, prefix = "task") {
    const options = raw.opts || raw.options || [];
    let type = raw.type || (options.length ? "multiple_choice" : "multiple_choice");
    if (!CHOICE_TYPES.has(type) && !ORDER_TYPES.has(type) && !MATCH_TYPES.has(type) && !STROKE_TYPES.has(type) && !SPEAK_TYPES.has(type)) {
      type = options.length ? "multiple_choice" : type;
    }
    const answerIndex = Number.isInteger(raw.ans) ? raw.ans : Number(raw.ans);
    let answer = raw.answer;
    if ((answer === undefined || answer === null || answer === "") && options.length && Number.isInteger(answerIndex)) {
      answer = options[answerIndex];
    }
    return {
      id: compact(raw.id || raw.question_id || `${prefix}:${index}`),
      type,
      subtype: raw.subtype || raw.type || "",
      label: raw.cat || raw.category || raw.label || "",
      prompt: raw.q || raw.prompt || "",
      hint: raw.hint || "",
      sentence: raw.sentence || "",
      source: raw.source || "",
      translation: raw.translation || "",
      target: raw.target || raw.word || "",
      audioText: raw.audioText || raw.audio_text || "",
      tokens: Array.isArray(raw.tokens) ? raw.tokens : [],
      options,
      answer,
      answerIndex: Number.isInteger(answerIndex) ? answerIndex : options.indexOf(answer),
      pairs: raw.pairs || [],
      chars: raw.chars || [],
      word: raw.word || "",
      pinyin: raw.pinyin || "",
      meaning: raw.meaning || "",
      explanation: raw.expl || raw.explanation || "",
    };
  }

  function normalizeChoiceTask(raw, index) {
    return normalizeTask(raw, index, "quiz");
  }

  function normalizePracticeTask(raw, index) {
    return normalizeTask(raw, index, "practice");
  }

  function fallbackPracticeTasks(lesson, state) {
    const vocab = Array.isArray(lesson.vocabulary) ? lesson.vocabulary : [];
    const tasks = [];
    const words = vocab.filter((item) => item.zh && item.meaning).slice(0, 3);
    if (words.length >= 2) {
      tasks.push({
        id: "fallback:match",
        type: "match_pairs",
        prompt: l(state, "tapPairs"),
        pairs: words.map((item) => [item.zh, item.meaning]),
        explanation: words.map((item) => `${item.zh} = ${item.meaning}`).join(" · "),
      });
    }
    if (words[0]) {
      tasks.push({
        id: "fallback:listen",
        type: "listening_choice",
        prompt: l(state, "type_listening_choice"),
        audioText: words[0].zh,
        options: words.map((item) => item.zh),
        answer: words[0].zh,
        explanation: `${words[0].zh} = ${words[0].meaning}`,
      });
      tasks.push({
        id: "fallback:speak",
        type: "speak_repeat",
        prompt: l(state, "type_speak_repeat"),
        audioText: words[0].zh,
        answer: words[0].zh,
        translation: words[0].meaning,
        explanation: `${words[0].zh} = ${words[0].meaning}`,
      });
      tasks.push({
        id: "fallback:stroke",
        type: "stroke_preview",
        prompt: l(state, "type_stroke_preview"),
        chars: [...words[0].zh],
        word: words[0].zh,
        pinyin: words[0].pinyin,
        meaning: words[0].meaning,
        answer: "seen",
        explanation: `${words[0].zh} · ${words[0].pinyin} · ${words[0].meaning}`,
      });
    }
    return tasks;
  }

  async function loadLesson(state) {
    const blockParam = state.blockNo ? `&block=${encodeURIComponent(state.blockNo)}` : "";
    const response = await fetch(
      `/api/miniapp/lesson?level=${encodeURIComponent(state.level)}&lesson=${encodeURIComponent(state.lessonId)}&lang=${encodeURIComponent(state.lang)}${blockParam}`,
      { headers: { "X-Telegram-Init-Data": tg()?.initData || "" } }
    );
    const data = await response.json();
    if (!data?.ok || !data.lesson) throw new Error(data?.error || "lesson_not_found");
    state.lesson = data.lesson;
    state.lang = normalizeLang(data.lesson.lang || state.lang);
  }

  function setShell(state) {
    document.documentElement.lang = state.lang;
    document.body.className = "course-miniapp-v2";
    document.body.innerHTML = `
      <div class="cmv2">
        <header class="cmv2-top">
          <div class="cmv2-progress"><span id="cmv2-progress"></span></div>
        </header>
        <main class="cmv2-main" id="cmv2-main">
          <div class="cmv2-error">${esc(l(state, "loading"))}</div>
        </main>
        <div class="cmv2-feedback" id="cmv2-feedback"></div>
        <footer class="cmv2-footer">
          <button class="cmv2-primary" id="cmv2-primary" type="button" disabled>${esc(l(state, "check"))}</button>
        </footer>
      </div>
    `;
  }

  function lessonLine(state) {
    const base = `${l(state, "lesson")} ${state.lessonId}`;
    return state.blockNo ? `${base} · ${l(state, "part")} ${state.blockNo}` : base;
  }

  function updateTop(state) {
    const progress = state.tasks.length ? Math.round((state.index / state.tasks.length) * 100) : 0;
    const bar = document.getElementById("cmv2-progress");
    if (bar) bar.style.width = `${Math.min(progress, 100)}%`;
  }

  function renderTask(state) {
    state.checked = false;
    state.answer = null;
    state.lastResult = null;
    const task = state.tasks[state.index];
    if (!task) return renderResult(state);

    updateTop(state);
    const main = document.getElementById("cmv2-main");
    const primary = document.getElementById("cmv2-primary");
    const feedback = document.getElementById("cmv2-feedback");
    const character = getCharacter(state, task);
    feedback.className = "cmv2-feedback";
    feedback.innerHTML = "";
    primary.disabled = true;
    primary.classList.remove("danger");
    primary.textContent = l(state, "check");
    primary.onclick = () => checkTask(state);

    main.innerHTML = `
      <div class="cmv2-meta">
        <span class="cmv2-pill">${esc(state.mode === "quiz" ? l(state, "quiz") : l(state, "reinforce"))}</span>
        <span class="cmv2-count">${esc(lessonLine(state))} · ${state.index + 1}/${state.tasks.length}</span>
      </div>
      <h1 class="cmv2-prompt">${esc(task.prompt || task.label || "")}</h1>
      <section class="cmv2-scene">
        <div class="cmv2-character">
          ${robotSvg(character, task.type === "speak_repeat" ? "listening" : "idle")}
          <div class="cmv2-character-tag">${esc(character.name)} · ${esc(character.mood)}</div>
        </div>
        <div class="cmv2-bubble">${bubbleHtml(state, task)}</div>
      </section>
      <div id="cmv2-task"></div>
    `;

    const bubbleAudio = document.getElementById("cmv2-bubble-audio");
    if (bubbleAudio) bubbleAudio.onclick = () => speak(bubbleAudio.dataset.audio || task.audioText || task.answer);

    const target = document.getElementById("cmv2-task");
    if (isOrderType(task.type)) renderOrderTask(state, target, task);
    else if (isMatchType(task.type)) renderMatchTask(state, target, task);
    else if (isSpeakType(task.type)) renderSpeakTask(state, target, task);
    else if (task.type === "stroke_preview") renderStrokeTask(state, target, task);
    else renderChoiceTask(state, target, task);
  }

  function renderChoiceTask(state, target, task) {
    const fillLike = FILL_TYPES.has(task.type);
    target.innerHTML = `
      <div class="cmv2-answer-lines" aria-hidden="true">
        <div class="cmv2-answer-line"></div>
        <div class="cmv2-answer-line"></div>
      </div>
      <div class="cmv2-options">
        ${(task.options || []).map((option, index) => `
          <button class="cmv2-option" type="button" data-index="${index}" data-value="${attr(option)}">${esc(option)}</button>
        `).join("")}
      </div>
    `;
    target.querySelectorAll(".cmv2-option").forEach((button) => {
      button.onclick = () => {
        target.querySelectorAll(".cmv2-option").forEach((item) => item.classList.remove("selected"));
        button.classList.add("selected");
        state.answer = { selected_index: Number(button.dataset.index), selected_answer: button.dataset.value };
        if (fillLike) {
          const slot = document.getElementById("cmv2-blank-slot");
          if (slot) {
            slot.textContent = button.dataset.value;
            slot.className = "cmv2-slot filled";
          }
        }
        document.getElementById("cmv2-primary").disabled = false;
        haptic("tap");
      };
    });
  }

  function renderOrderTask(state, target, task) {
    const tokens = shuffle(task.tokens || [], `${task.id}:${state.attemptSeed || ""}`).map((token, index) => ({ id: `${index}:${token}`, text: token }));
    state.orderTokens = [];
    target.innerHTML = `
      <div class="cmv2-order-box" id="cmv2-order-box"><span class="cmv2-placeholder">${esc(l(state, "orderPlaceholder"))}</span></div>
      <div class="cmv2-bank" id="cmv2-bank">
        ${tokens.map((token) => `<button class="cmv2-chip" type="button" data-id="${attr(token.id)}">${esc(token.text)}</button>`).join("")}
      </div>
    `;
    const box = document.getElementById("cmv2-order-box");
    const bank = document.getElementById("cmv2-bank");
    function sync() {
      box.innerHTML = state.orderTokens.length
        ? state.orderTokens.map((token) => `<button class="cmv2-chip selected" type="button" data-id="${attr(token.id)}">${esc(token.text)}</button>`).join("")
        : `<span class="cmv2-placeholder">${esc(l(state, "orderPlaceholder"))}</span>`;
      bank.querySelectorAll(".cmv2-chip").forEach((button) => {
        button.disabled = state.orderTokens.some((token) => token.id === button.dataset.id);
      });
      box.querySelectorAll(".cmv2-chip").forEach((button) => {
        button.onclick = () => {
          state.orderTokens = state.orderTokens.filter((token) => token.id !== button.dataset.id);
          state.answer = { answer_tokens: state.orderTokens.map((token) => token.text) };
          document.getElementById("cmv2-primary").disabled = state.orderTokens.length === 0;
          sync();
        };
      });
    }
    bank.querySelectorAll(".cmv2-chip").forEach((button) => {
      button.onclick = () => {
        const token = tokens.find((item) => item.id === button.dataset.id);
        if (!token) return;
        state.orderTokens.push(token);
        state.answer = { answer_tokens: state.orderTokens.map((item) => item.text) };
        document.getElementById("cmv2-primary").disabled = false;
        sync();
        haptic("tap");
      };
    });
    sync();
  }

  function renderMatchTask(state, target, task) {
    const pairs = task.pairs || [];
    const rightItems = shuffle(pairs.map((pair) => pair[1]), `${task.id || "pairs"}:${state.attemptSeed || ""}`);
    state.matchLeft = "";
    state.matchPairs = [];
    target.innerHTML = `
      <div class="cmv2-source"><div class="cmv2-source-sub">${esc(l(state, "tapPairs"))}</div></div>
      <div class="cmv2-match">
        <div class="cmv2-match-col" id="cmv2-left">${pairs.map((pair) => `<button class="cmv2-match-btn" type="button" data-left="${attr(pair[0])}">${esc(pair[0])}</button>`).join("")}</div>
        <div class="cmv2-match-col" id="cmv2-right">${rightItems.map((item) => `<button class="cmv2-match-btn" type="button" data-right="${attr(item)}">${esc(item)}</button>`).join("")}</div>
      </div>
      <div class="cmv2-pairs" id="cmv2-pairs"></div>
    `;
    function syncPairs() {
      const usedLeft = new Set(state.matchPairs.map((pair) => pair[0]));
      const usedRight = new Set(state.matchPairs.map((pair) => pair[1]));
      target.querySelectorAll("[data-left]").forEach((button) => {
        button.classList.toggle("active", state.matchLeft === button.dataset.left);
        button.classList.toggle("done", usedLeft.has(button.dataset.left));
      });
      target.querySelectorAll("[data-right]").forEach((button) => {
        button.classList.toggle("done", usedRight.has(button.dataset.right));
      });
      document.getElementById("cmv2-pairs").innerHTML = state.matchPairs.map((pair) => `
        <button class="cmv2-pair" type="button" data-left="${attr(pair[0])}" data-right="${attr(pair[1])}">${esc(pair[0])} = ${esc(pair[1])}</button>
      `).join("");
      document.getElementById("cmv2-pairs").querySelectorAll(".cmv2-pair").forEach((button) => {
        button.onclick = () => {
          state.matchPairs = state.matchPairs.filter((pair) => pair[0] !== button.dataset.left || pair[1] !== button.dataset.right);
          state.answer = { pairs: state.matchPairs.map((pair) => [pair[0], pair[1]]) };
          document.getElementById("cmv2-primary").disabled = state.matchPairs.length !== pairs.length;
          syncPairs();
        };
      });
      document.getElementById("cmv2-primary").disabled = state.matchPairs.length !== pairs.length;
    }
    target.querySelectorAll("[data-left]").forEach((button) => {
      button.onclick = () => {
        if (state.matchPairs.some((pair) => pair[0] === button.dataset.left)) return;
        state.matchLeft = state.matchLeft === button.dataset.left ? "" : button.dataset.left;
        syncPairs();
        haptic("tap");
      };
    });
    target.querySelectorAll("[data-right]").forEach((button) => {
      button.onclick = () => {
        if (!state.matchLeft || state.matchPairs.some((pair) => pair[1] === button.dataset.right)) return;
        state.matchPairs.push([state.matchLeft, button.dataset.right]);
        state.matchLeft = "";
        state.answer = { pairs: state.matchPairs.map((pair) => [pair[0], pair[1]]) };
        syncPairs();
        haptic("tap");
      };
    });
    syncPairs();
  }

  function renderSpeakTask(state, target, task) {
    const Recognition = speechRecognitionFactory();
    const supported = Boolean(Recognition);
    state.answer = { transcript: "", skipped: false, voice_unsupported: !supported };
    target.innerHTML = `
      <div class="cmv2-voice-card">
        <button class="cmv2-mic" id="cmv2-mic" type="button" ${supported ? "" : "disabled"}>🎙</button>
        <div class="cmv2-transcript" id="cmv2-transcript">${esc(supported ? l(state, "speak") : l(state, "voiceUnsupported"))}</div>
        ${supported ? "" : `<button class="cmv2-voice-skip" id="cmv2-voice-skip" type="button">${esc(l(state, "skipVoice"))}</button>`}
      </div>
    `;
    const primary = document.getElementById("cmv2-primary");
    const transcriptBox = document.getElementById("cmv2-transcript");
    const mic = document.getElementById("cmv2-mic");
    const skip = document.getElementById("cmv2-voice-skip");
    if (skip) {
      skip.onclick = () => {
        state.answer = { transcript: "", skipped: true, voice_unsupported: true };
        primary.disabled = false;
        transcriptBox.textContent = l(state, "voiceUnsupported");
        haptic("tap");
      };
    }
    if (!supported || !mic) return;
    mic.onclick = () => {
      const recognition = new Recognition();
      recognition.lang = "zh-CN";
      recognition.interimResults = false;
      recognition.maxAlternatives = 3;
      mic.classList.add("recording");
      mic.disabled = true;
      transcriptBox.textContent = l(state, "recording");
      try { recognition.start(); } catch (e) {
        mic.classList.remove("recording");
        mic.disabled = false;
        transcriptBox.textContent = l(state, "voiceUnsupported");
        state.answer = { transcript: "", skipped: true, voice_unsupported: true };
        primary.disabled = false;
        return;
      }
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || "";
        state.answer = { transcript, skipped: false, voice_unsupported: false };
        transcriptBox.textContent = transcript || l(state, "speak");
        primary.disabled = !compact(transcript);
      };
      recognition.onerror = () => {
        state.answer = { transcript: "", skipped: true, voice_unsupported: false };
        transcriptBox.textContent = l(state, "skipVoice");
        primary.disabled = false;
      };
      recognition.onend = () => {
        mic.classList.remove("recording");
        mic.disabled = false;
      };
      haptic("tap");
    };
  }

  function renderStrokeTask(state, target, task) {
    target.innerHTML = `
      <div class="cmv2-stroke">
        <div class="cmv2-hanzi">${esc(task.word || (task.chars || []).join(""))}</div>
        <div class="cmv2-pinyin">${esc(task.pinyin || "")}</div>
        <div class="cmv2-meaning">${esc(task.meaning || "")}</div>
      </div>
    `;
    state.answer = { completed: true, seen: true };
    document.getElementById("cmv2-primary").disabled = false;
    document.getElementById("cmv2-primary").textContent = l(state, "seen");
  }

  function checkTask(state) {
    if (state.checked) return continueTask(state);
    const task = state.tasks[state.index];
    let correct = false;
    const answer = state.answer || {};

    if (isChoiceType(task.type)) correct = compact(answer.selected_answer) === compact(task.answer);
    else if (isOrderType(task.type)) correct = arraysEqual(answer.answer_tokens, task.answer);
    else if (isMatchType(task.type)) correct = samePairs(answer.pairs, task.pairs);
    else if (task.type === "stroke_preview") correct = Boolean(answer.completed || answer.seen);
    else if (isSpeakType(task.type)) correct = voiceMatches(answer.transcript, task.answer || task.audioText);

    state.checked = true;
    if (correct) state.score += 1;
    state.xp += correct ? 5 : 1;
    const result = {
      task_id: task.id,
      question_id: task.id,
      type: task.type,
      correct,
      selected_index: Number.isInteger(answer.selected_index) ? answer.selected_index : null,
      selected_answer: answer.selected_answer || "",
      answer_tokens: answer.answer_tokens || [],
      pairs: answer.pairs || [],
      completed: Boolean(answer.completed || answer.seen),
      transcript: answer.transcript || "",
      skipped: Boolean(answer.skipped),
      voice_unsupported: Boolean(answer.voice_unsupported),
      prompt: task.prompt,
      correct_answer: formatAnswer(task),
      explanation: task.explanation || "",
    };
    state.lastResult = result;
    state.results.push(result);
    paintAnswerState(task, correct, answer);
    showFeedback(state, task, correct, result);
    updateTop(state);
    const primary = document.getElementById("cmv2-primary");
    primary.disabled = false;
    primary.classList.toggle("danger", !correct);
    primary.textContent = l(state, "continue");
    primary.onclick = () => continueTask(state);
    haptic(correct ? "success" : "error");
  }

  function paintAnswerState(task, correct, answer) {
    document.querySelectorAll(".cmv2-option").forEach((button) => {
      const value = button.dataset.value;
      if (compact(value) === compact(task.answer)) button.classList.add("correct");
      if (!correct && compact(value) === compact(answer.selected_answer)) button.classList.add("wrong");
      button.disabled = true;
    });
    document.querySelectorAll(".cmv2-chip,.cmv2-match-btn,.cmv2-pair").forEach((button) => {
      button.disabled = true;
    });
  }

  function showFeedback(state, task, correct, result) {
    const feedback = document.getElementById("cmv2-feedback");
    const answer = formatAnswer(task);
    const text = correct ? (task.explanation || l(state, "xp", { xp: 5 })) : `${l(state, "correctAnswer")}: ${answer}`;
    feedback.innerHTML = `
      <div class="cmv2-sheet ${correct ? "ok" : "no"}">
        <div class="cmv2-sheet-title">${esc(correct ? l(state, "correct") : l(state, "wrong"))}</div>
        <div class="cmv2-sheet-text">${esc(text)}</div>
        ${correct ? "" : `<button class="cmv2-explain-btn" id="cmv2-explain" type="button">${esc(l(state, "explainError"))}</button>`}
      </div>
    `;
    feedback.className = "cmv2-feedback show";
    const explain = document.getElementById("cmv2-explain");
    if (explain) explain.onclick = () => openExplanation(state, task, result);
  }

  function openExplanation(state, task, result) {
    const existing = document.getElementById("cmv2-modal");
    if (existing) existing.remove();
    const character = getCharacter(state, task);
    const correctAnswer = result?.correct_answer || formatAnswer(task);
    const userAnswer = result?.transcript || result?.selected_answer || (result?.answer_tokens || []).join(" ") || "";
    const explanation = task.explanation || result?.explanation || l(state, "noExplanation");
    const modal = document.createElement("div");
    modal.id = "cmv2-modal";
    modal.className = "cmv2-modal";
    modal.innerHTML = `
      <div class="cmv2-modal-card" role="dialog" aria-modal="true">
        <div class="cmv2-modal-head">
          <div>${robotSvg(character, "sad")}</div>
          <div><div class="cmv2-modal-title">${esc(l(state, "explanationTitle"))}</div><div class="cmv2-bubble-sub">${esc(character.name)} · ${esc(character.trait)}</div></div>
        </div>
        ${userAnswer ? `<div class="cmv2-modal-answer">${esc(l(state, "yourAnswer"))}: ${esc(userAnswer)}</div>` : ""}
        <div class="cmv2-modal-answer">${esc(l(state, "answerLine"))}: ${esc(correctAnswer)}</div>
        <p class="cmv2-modal-text">${esc(explanation)}</p>
        <button class="cmv2-primary danger" id="cmv2-modal-ok" type="button">${esc(l(state, "understood"))}</button>
      </div>
    `;
    document.body.appendChild(modal);
    document.getElementById("cmv2-modal-ok").onclick = () => modal.remove();
  }

  function continueTask(state) {
    state.index += 1;
    if (state.index >= state.tasks.length) renderResult(state);
    else renderTask(state);
  }

  async function renderResult(state) {
    const progress = document.getElementById("cmv2-progress");
    if (progress) progress.style.width = "100%";
    const main = document.getElementById("cmv2-main");
    const feedback = document.getElementById("cmv2-feedback");
    const primary = document.getElementById("cmv2-primary");
    feedback.className = "cmv2-feedback";
    feedback.innerHTML = "";
    primary.classList.remove("danger");
    const total = state.tasks.length;
    const percent = total ? Math.round((state.score / total) * 100) : 0;
    const title = state.mode === "quiz" ? l(state, "quizDone") : l(state, "reinforceDone");
    main.innerHTML = `
      <div class="cmv2-result">
        <div class="cmv2-result-icon">✓</div>
        <h1>${esc(title)}</h1>
        <p>${esc(l(state, "score", { score: state.score, total }))} · ${percent}%</p>
        ${state.mode === "homework" ? `<p>${esc(l(state, "unlocked"))}</p>` : ""}
        <div class="cmv2-status" id="cmv2-status">${esc(l(state, "loading"))}</div>
      </div>
    `;
    primary.disabled = false;
    primary.classList.remove("danger");
    primary.textContent = l(state, "return");
    primary.onclick = () => closeToBot(state);

    const delivered = state.mode === "quiz" ? await reportQuiz(state, percent) : await reportHomework(state, percent);
    const status = document.getElementById("cmv2-status");
    if (status) status.textContent = delivered ? l(state, "networkSaved") : l(state, "networkPending");
  }

  async function reportQuiz(state, percent) {
    const wrongItems = state.results.filter((item) => !item.correct).map((item) => ({
      lesson_id: state.lessonId,
      block_no: state.blockNo || null,
      type: item.type,
      question: item.prompt,
      selected_answer: item.selected_answer,
      selected_index: item.selected_index,
      correct_answer: item.correct_answer,
      explanation: item.explanation,
    }));
    return reportEvent(state, "quiz_completed", {
      lesson_id: state.lessonId,
      block_no: state.blockNo || null,
      score: state.score,
      total: state.tasks.length,
      percent,
      answers: state.results.map((item) => ({
        question_id: item.question_id,
        type: item.type,
        selected_index: item.selected_index,
        selected_answer: item.selected_answer,
        answer_tokens: item.answer_tokens,
        pairs: item.pairs,
        completed: item.completed,
        transcript: item.transcript,
        skipped: item.skipped,
        voice_unsupported: item.voice_unsupported,
      })),
      wrong_items: wrongItems,
    });
  }

  async function reportHomework(state, percent) {
    const results = state.results.map((item) => ({
      task_id: item.task_id,
      type: item.type,
      selected_index: item.selected_index,
      selected_answer: item.selected_answer,
      answer_tokens: item.answer_tokens,
      pairs: item.pairs,
      completed: item.completed,
      transcript: item.transcript,
      skipped: item.skipped,
      voice_unsupported: item.voice_unsupported,
      correct: item.correct,
    }));
    return reportEvent(state, "homework_submitted", {
      lesson_id: state.lessonId,
      block_no: state.blockNo || null,
      answers: {
        reinforcement_completed: true,
        reinforcement_score: state.score,
        reinforcement_total: state.tasks.length,
        reinforcement_percent: percent,
        reinforcement_results: results,
        vocab_sentences: "interactive_reinforcement_completed",
        grammar_sentences: "interactive_reinforcement_completed",
        translations: "interactive_reinforcement_completed",
      },
      submitted_at: new Date().toISOString(),
    });
  }

  async function reportEvent(state, eventName, payload = {}) {
    const eventPayload = {
      level: state.level,
      event: eventName,
      ...payload,
      created_at: new Date().toISOString(),
    };
    try {
      const response = await fetch(state.eventEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Init-Data": tg()?.initData || "",
        },
        body: JSON.stringify(eventPayload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.ok === false) throw new Error(data?.error || `event_${response.status}`);
      return true;
    } catch (error) {
      if ((eventName === "quiz_completed" || eventName === "homework_submitted") && tg()?.sendData) {
        try { tg().sendData(JSON.stringify(eventPayload)); } catch (e) {}
      }
      try {
        const pending = JSON.parse(localStorage.getItem(state.pendingKey) || "[]");
        pending.push(eventPayload);
        localStorage.setItem(state.pendingKey, JSON.stringify(pending));
      } catch (e) {}
      return false;
    }
  }

  function closeToBot(state) {
    reportEvent(state, "bot_return_clicked", {
      lesson_id: state.lessonId,
      block_no: state.blockNo || null,
      mode: state.mode,
    }).finally(() => {
      try { tg()?.close?.(); } catch (e) {}
    });
  }

  function renderError(state, message) {
    const main = document.getElementById("cmv2-main");
    const primary = document.getElementById("cmv2-primary");
    main.innerHTML = `<div class="cmv2-error">${esc(message || l(state, "noTasks"))}</div>`;
    primary.disabled = false;
    primary.textContent = l(state, "return");
    primary.onclick = () => closeToBot(state);
  }

  function nextAttemptSeed(state) {
    const key = "hskai_attempt_history";
    const attemptKey = `${state.level}:${state.lessonId}:${state.blockNo || "all"}:${state.mode}`;
    try {
      const history = JSON.parse(localStorage.getItem(key) || "{}");
      const count = Number(history[attemptKey] || 0) + 1;
      history[attemptKey] = count;
      localStorage.setItem(key, JSON.stringify(history));
      return `${attemptKey}:${count}`;
    } catch (e) {
      return `${attemptKey}:${Date.now()}`;
    }
  }

  function prepareTasksForAttempt(state, tasks, limit) {
    const selected = tasks.slice(0, limit);
    if (selected.length <= 1) return selected;
    return shuffle(selected, state.attemptSeed || `${state.level}:${state.lessonId}:${state.mode}`);
  }


  async function start(config) {
    injectStyles();
    try { tg()?.ready?.(); tg()?.expand?.(); } catch (e) {}
    const state = {
      level: config.level,
      lessonId: Number(config.lessonId),
      blockNo: config.blockNo ? Number(config.blockNo) : null,
      mode: config.mode === "homework" ? "homework" : "quiz",
      lang: normalizeLang(config.lang),
      eventEndpoint: config.eventEndpoint || "/api/miniapp/event",
      pendingKey: config.pendingKey || `${config.level}_pending_events`,
      lesson: null,
      tasks: [],
      index: 0,
      score: 0,
      xp: 0,
      checked: false,
      answer: null,
      results: [],
      attemptSeed: "",
    };
    setShell(state);
    try {
      await loadLesson(state);
      state.attemptSeed = nextAttemptSeed(state);
      if (state.mode === "quiz") {
        const quizTasks = (state.lesson.quiz_questions || []).map(normalizeChoiceTask);
        state.tasks = prepareTasksForAttempt(state, quizTasks, 5);
      } else {
        const rawTasks = state.lesson.reinforcement_tasks || state.lesson.practice_tasks || [];
        const practiceTasks = (rawTasks.length ? rawTasks : fallbackPracticeTasks(state.lesson, state)).map(normalizePracticeTask);
        state.tasks = prepareTasksForAttempt(state, practiceTasks, 4);
      }
      if (!state.tasks.length) {
        renderError(state, l(state, "noTasks"));
        return true;
      }
      renderTask(state);
      return true;
    } catch (error) {
      renderError(state, l(state, "noTasks"));
      return true;
    }
  }

  window.CourseMiniAppV2 = { start };
})();
