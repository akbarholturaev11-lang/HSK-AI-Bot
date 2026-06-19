(function () {
  const LABELS = {
    uz: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Mustahkamlash",
      check: "Tekshirish",
      continue: "Davom etish",
      return: "Botga qaytish",
      correct: "To'g'ri!",
      wrong: "Yana bir marta ko'ring",
      correctAnswer: "To'g'ri javob",
      yourAnswer: "Sizning javobingiz",
      listen: "Eshitish",
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
      type_word_order: "So'z tartibi",
      type_build_chinese_sentence: "Xitoycha gap",
      type_match_pairs: "Moslashtirish",
      type_stroke_preview: "Iyeroglif",
    },
    ru: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Закрепление",
      check: "Проверить",
      continue: "Продолжить",
      return: "Вернуться в бот",
      correct: "Правильно!",
      wrong: "Посмотрите ещё раз",
      correctAnswer: "Правильный ответ",
      yourAnswer: "Ваш ответ",
      listen: "Слушать",
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
      type_word_order: "Порядок слов",
      type_build_chinese_sentence: "Китайское предложение",
      type_match_pairs: "Пары",
      type_stroke_preview: "Иероглиф",
    },
    tj: {
      brand: "HSK AI",
      quiz: "Quiz",
      reinforce: "Мустаҳкамкунӣ",
      check: "Санҷидан",
      continue: "Давом додан",
      return: "Бозгашт ба бот",
      correct: "Дуруст!",
      wrong: "Боз як бор бинед",
      correctAnswer: "Ҷавоби дуруст",
      yourAnswer: "Ҷавоби шумо",
      listen: "Гӯш кардан",
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
      type_word_order: "Тартиби калимаҳо",
      type_build_chinese_sentence: "Ҷумлаи чинӣ",
      type_match_pairs: "Ҷуфтҳо",
      type_stroke_preview: "Иероглиф",
    },
  };

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

  function speak(text) {
    const value = compact(text);
    if (!value || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(value);
      utterance.lang = "zh-CN";
      utterance.rate = 0.82;
      window.speechSynthesis.speak(utterance);
    } catch (e) {}
  }

  function taskLabel(state, type, fallback) {
    return l(state, `type_${type}`) || fallback || type;
  }

  function formatAnswer(task) {
    if (Array.isArray(task.answer)) {
      return task.type === "build_chinese_sentence" ? task.answer.join("") : task.answer.join(" ");
    }
    if (task.type === "match_pairs") {
      return (task.pairs || []).map((pair) => `${pair[0]} = ${pair[1]}`).join(" · ");
    }
    if (task.type === "stroke_preview") {
      return [task.word, task.pinyin, task.meaning].filter(Boolean).join(" · ");
    }
    return compact(task.answer);
  }

  function normalizeChoiceTask(raw, index) {
    const options = raw.opts || raw.options || [];
    const answerIndex = Number.isInteger(raw.ans) ? raw.ans : Number(raw.ans);
    const answer = compact(raw.answer || options[answerIndex]);
    let type = raw.type || "multiple_choice";
    if (!["multiple_choice", "listening_choice", "fill_blank"].includes(type)) type = "multiple_choice";
    return {
      id: compact(raw.id || raw.question_id || `quiz:${index}`),
      type,
      subtype: raw.subtype || raw.type || "",
      label: raw.cat || raw.category || "",
      prompt: raw.q || raw.prompt || "",
      hint: raw.hint || "",
      sentence: raw.sentence || "",
      source: raw.source || "",
      audioText: raw.audioText || raw.audio_text || "",
      options,
      answer,
      answerIndex: Number.isInteger(answerIndex) ? answerIndex : options.indexOf(answer),
      explanation: raw.expl || raw.explanation || "",
    };
  }

  function normalizePracticeTask(raw, index) {
    const type = raw.type || "multiple_choice";
    const task = {
      id: compact(raw.id || `practice:${index}`),
      type,
      label: raw.label || "",
      prompt: raw.prompt || "",
      source: raw.source || "",
      sentence: raw.sentence || "",
      audioText: raw.audioText || raw.audio_text || raw.word || "",
      tokens: raw.tokens || [],
      answer: raw.answer,
      options: raw.options || raw.opts || [],
      answerIndex: Number.isInteger(raw.ans) ? raw.ans : Number(raw.ans),
      pairs: raw.pairs || [],
      chars: raw.chars || [],
      word: raw.word || "",
      pinyin: raw.pinyin || "",
      meaning: raw.meaning || "",
      explanation: raw.explanation || "",
    };
    if (!task.answer && ["multiple_choice", "listening_choice", "fill_blank"].includes(type)) {
      task.answer = task.options[task.answerIndex];
    }
    return task;
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
          <div class="cmv2-row">
            <button class="cmv2-close" id="cmv2-close" type="button" aria-label="close">×</button>
            <div class="cmv2-brand">${esc(l(state, "brand"))}</div>
            <div class="cmv2-xp" id="cmv2-xp">${esc(l(state, "xp", { xp: 0 }))}</div>
          </div>
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
    document.getElementById("cmv2-close").onclick = () => closeToBot(state);
  }

  function lessonLine(state) {
    const base = `${l(state, "lesson")} ${state.lessonId}`;
    return state.blockNo ? `${base} · ${l(state, "part")} ${state.blockNo}` : base;
  }

  function updateTop(state) {
    const progress = state.tasks.length ? Math.round((state.index / state.tasks.length) * 100) : 0;
    const bar = document.getElementById("cmv2-progress");
    const xp = document.getElementById("cmv2-xp");
    if (bar) bar.style.width = `${Math.min(progress, 100)}%`;
    if (xp) xp.textContent = l(state, "xp", { xp: state.xp });
  }

  function renderTask(state) {
    state.checked = false;
    state.answer = null;
    const task = state.tasks[state.index];
    if (!task) return renderResult(state);

    updateTop(state);
    const main = document.getElementById("cmv2-main");
    const primary = document.getElementById("cmv2-primary");
    const feedback = document.getElementById("cmv2-feedback");
    feedback.className = "cmv2-feedback";
    feedback.innerHTML = "";
    primary.disabled = true;
    primary.textContent = l(state, "check");
    primary.onclick = () => checkTask(state);

    main.innerHTML = `
      <div class="cmv2-meta">
        <span class="cmv2-pill">${esc(state.mode === "quiz" ? l(state, "quiz") : l(state, "reinforce"))}</span>
        <span class="cmv2-count">${esc(lessonLine(state))} · ${state.index + 1}/${state.tasks.length}</span>
      </div>
      <div class="cmv2-pill" style="margin-bottom:12px;">${esc(taskLabel(state, task.type, task.label))}</div>
      <h1 class="cmv2-prompt">${esc(task.prompt || task.label || "")}</h1>
      <div id="cmv2-task"></div>
    `;

    const target = document.getElementById("cmv2-task");
    if (task.type === "word_order" || task.type === "build_chinese_sentence") renderOrderTask(state, target, task);
    else if (task.type === "match_pairs") renderMatchTask(state, target, task);
    else if (task.type === "stroke_preview") renderStrokeTask(state, target, task);
    else renderChoiceTask(state, target, task);
  }

  function renderChoiceTask(state, target, task) {
    const hasAudio = task.type === "listening_choice" || task.audioText;
    const sentence = task.type === "fill_blank" && task.sentence
      ? `<div class="cmv2-blank">${esc(task.sentence).replace("____", "<u>____</u>")}</div>`
      : "";
    const source = task.source
      ? `<div class="cmv2-source"><div class="cmv2-source-main">${esc(task.source)}</div>${task.hint ? `<div class="cmv2-source-sub">${esc(task.hint)}</div>` : ""}</div>`
      : "";
    target.innerHTML = `
      ${source}
      ${sentence}
      ${hasAudio ? `<button class="cmv2-audio" id="cmv2-audio" type="button">▶ ${esc(l(state, "listen"))}</button>` : ""}
      <div class="cmv2-options">
        ${(task.options || []).map((option, index) => `
          <button class="cmv2-option" type="button" data-index="${index}" data-value="${attr(option)}">${esc(option)}</button>
        `).join("")}
      </div>
    `;
    const audio = document.getElementById("cmv2-audio");
    if (audio) audio.onclick = () => speak(task.audioText || task.answer);
    target.querySelectorAll(".cmv2-option").forEach((button) => {
      button.onclick = () => {
        target.querySelectorAll(".cmv2-option").forEach((item) => item.classList.remove("selected"));
        button.classList.add("selected");
        state.answer = {
          selected_index: Number(button.dataset.index),
          selected_answer: button.dataset.value,
        };
        document.getElementById("cmv2-primary").disabled = false;
        haptic("tap");
      };
    });
  }

  function renderOrderTask(state, target, task) {
    const tokens = (task.tokens || []).map((token, index) => ({ id: `${index}:${token}`, text: token }));
    state.orderTokens = [];
    target.innerHTML = `
      ${task.source ? `<div class="cmv2-source"><div class="cmv2-source-main">${esc(task.source)}</div></div>` : ""}
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
    const rightItems = shuffle(pairs.map((pair) => pair[1]), task.id || "pairs");
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

    if (["multiple_choice", "listening_choice", "fill_blank"].includes(task.type)) {
      correct = compact(answer.selected_answer) === compact(task.answer);
    } else if (task.type === "word_order" || task.type === "build_chinese_sentence") {
      correct = arraysEqual(answer.answer_tokens, task.answer);
    } else if (task.type === "match_pairs") {
      correct = samePairs(answer.pairs, task.pairs);
    } else if (task.type === "stroke_preview") {
      correct = Boolean(answer.completed || answer.seen);
    }

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
      prompt: task.prompt,
      correct_answer: formatAnswer(task),
      explanation: task.explanation || "",
    };
    state.results.push(result);
    paintAnswerState(task, correct, answer);
    showFeedback(state, task, correct);
    updateTop(state);
    document.getElementById("cmv2-primary").disabled = false;
    document.getElementById("cmv2-primary").textContent = l(state, "continue");
    document.getElementById("cmv2-primary").onclick = () => continueTask(state);
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

  function showFeedback(state, task, correct) {
    const feedback = document.getElementById("cmv2-feedback");
    const answer = formatAnswer(task);
    const text = correct
      ? (task.explanation || l(state, "xp", { xp: 5 }))
      : `${l(state, "correctAnswer")}: ${answer}${task.explanation ? ` · ${task.explanation}` : ""}`;
    feedback.innerHTML = `
      <div class="cmv2-sheet ${correct ? "ok" : "no"}">
        <div class="cmv2-sheet-title">${esc(correct ? l(state, "correct") : l(state, "wrong"))}</div>
        <div class="cmv2-sheet-text">${esc(text)}</div>
      </div>
    `;
    feedback.className = "cmv2-feedback show";
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
        selected_index: item.selected_index,
        selected_answer: item.selected_answer,
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
    };
    setShell(state);
    try {
      await loadLesson(state);
      if (state.mode === "quiz") {
        state.tasks = (state.lesson.quiz_questions || []).map(normalizeChoiceTask).slice(0, 5);
      } else {
        const rawTasks = state.lesson.reinforcement_tasks || state.lesson.practice_tasks || [];
        state.tasks = (rawTasks.length ? rawTasks : fallbackPracticeTasks(state.lesson, state)).map(normalizePracticeTask).slice(0, 4);
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
