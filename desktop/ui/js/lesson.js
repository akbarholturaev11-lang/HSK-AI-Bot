import { getLanguage, pick, t } from "./i18n.js";
import { isSessionError } from "./bridge.js";

const CHOICE_TYPES = new Set([
  "meaning_guess",
  "hanzi_choice",
  "pinyin_choice",
  "quick_quiz",
  "translation_choice",
  "listening_choice",
  "gap_fill",
  "dialog_cloze",
]);

const BUILDER_TYPES = new Set(["sentence_builder", "reverse_builder"]);
export const SUPPORTED_CARD_TYPES = Object.freeze([
  "_grammar",
  "active_word",
  ...CHOICE_TYPES,
  ...BUILDER_TYPES,
  "match_pairs",
  "pronunciation",
]);
const ASSESSED_TYPES = new Set([
  ...CHOICE_TYPES,
  ...BUILDER_TYPES,
  "match_pairs",
]);

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

function localizedList(value) {
  let source = value;
  if (source && !Array.isArray(source) && typeof source === "object") {
    source =
      source[getLanguage()] ?? source.uz ?? source.ru ?? source.tj ?? [];
  }
  if (!Array.isArray(source)) {
    return [];
  }
  return source
    .map((item) => pick(item, typeof item === "string" ? item : ""))
    .filter(Boolean);
}

function safeInteger(value, fallback) {
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : fallback;
}

function briefText(value, limit = 220) {
  return [...String(value ?? "").trim()].slice(0, limit).join("");
}

function completionEventId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `desktop:${globalThis.crypto.randomUUID()}`;
  }
  const suffix = Math.random().toString(36).slice(2, 14);
  return `desktop:${Date.now()}:${suffix}`;
}

function isSameTokens(left, right) {
  return (
    left.length === right.length &&
    left.every((value, index) => value === right[index])
  );
}

export class LessonController {
  constructor({
    bridge,
    onCompleted,
    onSessionExpired,
    onAccessRequired,
    onOpen,
    onClose,
    onContextChanged,
  }) {
    this.bridge = bridge;
    this.onCompleted = onCompleted;
    this.onSessionExpired = onSessionExpired;
    this.onAccessRequired = onAccessRequired;
    this.onOpen = onOpen;
    this.onClose = onClose;
    this.onContextChanged = onContextChanged;

    this.layer = document.querySelector("#lesson-layer");
    this.dialog = this.layer.querySelector(".lesson-shell");
    this.content = document.querySelector("#lesson-content");
    this.feedback = document.querySelector("#lesson-feedback");
    this.nextButton = document.querySelector("#lesson-next");
    this.closeButton = document.querySelector("#close-lesson");
    this.progressBar = document.querySelector("#lesson-progress-bar");
    this.scoreLabel = document.querySelector("#lesson-score");

    this.lessonOrder = null;
    this.level = "hsk1";
    this.lesson = null;
    this.cards = [];
    this.index = 0;
    this.score = 0;
    this.assessmentCount = 0;
    this.mistakes = [];
    this.mistakeRefs = new Set();
    this.interaction = null;
    this.eventId = null;
    this.submitting = false;
    this.completed = false;
    this.previewHalf = false;
    this.previewLimit = 0;
    this.requestEpoch = 0;
    this.previousFocus = null;

    this.closeButton.addEventListener("click", () => this.close());
    this.nextButton.addEventListener("click", () => this.handleNext());
  }

  get isOpen() {
    return !this.layer.hidden;
  }

  aiContext() {
    if (!this.isOpen) return null;
    const entry = this.cards[this.index];
    const card = entry?.card || {};
    const type = String(card.type || "unknown");
    const title =
      briefText(this.content.querySelector(".lesson-title")?.textContent) ||
      pick(card.title) ||
      pick(card.prompt) ||
      t("lessonNumber", { number: this.lessonOrder || "—" });
    const promptLines = [
      `Lesson: ${this.lessonOrder || "—"}`,
      `Level: ${this.level}`,
      `Card: ${this.index + 1}/${this.cards.length || 1}`,
      `Card type: ${type}`,
      `Title: ${title}`,
    ];
    const details = [];
    const add = (label, value, limit = 220) => {
      const text = briefText(value, limit);
      if (text) {
        promptLines.push(`${label}: ${text}`);
        details.push(text);
      }
    };

    if (entry?.sectionTitle) {
      promptLines.push(`Section: ${briefText(entry.sectionTitle, 120)}`);
    }

    if (type === "active_word") {
      const word = card.word || {};
      add("Chinese", word.zh, 80);
      add("Pinyin", word.pinyin, 120);
      add("Translation", pick(word.meaning), 160);
    } else if (type === "_grammar") {
      const grammar = card.g || {};
      add("Grammar", grammar.title_zh || pick(grammar.title), 120);
      add("Rule", pick(grammar.rule), 260);
      const example = Array.isArray(grammar.examples) ? grammar.examples[0] : null;
      if (example) {
        add(
          "Example",
          [
            example.zh,
            example.pinyin,
            pick(example.translation),
          ].filter(Boolean).join(" · "),
          260,
        );
      }
    } else if (CHOICE_TYPES.has(type)) {
      add("Prompt", pick(card.prompt), 220);
      add("Sentence", pick(card.sentence) || card.audio_text, 220);
      add("Pinyin", card.pinyin, 160);
      const options = Array.isArray(card.options)
        ? card.options.map((option, index) =>
            `${String.fromCharCode(65 + index)}. ${pick(option, String(option ?? ""))}`,
          )
        : [];
      if (options.length) {
        promptLines.push(`Visible options: ${briefText(options.join(" | "), 420)}`);
      }
      if (Number.isInteger(this.interaction?.selectedIndex)) {
        const selected = options[this.interaction.selectedIndex] || "";
        if (selected) promptLines.push(`Learner selected: ${briefText(selected, 160)}`);
      }
    } else if (BUILDER_TYPES.has(type)) {
      add("Prompt", pick(card.prompt) || pick(card.sentence) || pick(card.translation), 220);
      add("Chinese", card.zh, 120);
      add("Pinyin", card.pinyin, 160);
      add("Translation", pick(card.translation), 180);
      const tokens = localizedList(card.tokens);
      if (tokens.length) {
        promptLines.push(`Visible tokens: ${briefText(tokens.join(" / "), 360)}`);
      }
      if (Array.isArray(this.interaction?.selectedIndices)) {
        const selected = this.interaction.selectedIndices
          .map((tokenIndex) => tokens[tokenIndex])
          .filter(Boolean);
        if (selected.length) {
          promptLines.push(`Learner selected tokens: ${briefText(selected.join(" / "), 260)}`);
        }
      }
    } else if (type === "match_pairs") {
      add("Task", title, 180);
    } else if (type === "pronunciation") {
      add("Phrase", card.phrase, 120);
      add("Pinyin", card.pinyin, 160);
      add("Translation", pick(card.translation), 180);
    }

    if (this.interaction?.checked) {
      add("Visible feedback", this.feedback.textContent, 260);
    }

    return {
      lessonOrder: this.lessonOrder,
      level: this.level,
      index: this.index + 1,
      total: this.cards.length || 1,
      sectionTitle: entry?.sectionTitle || "",
      title,
      summary: details.slice(0, 3).join(" · "),
      isExercise: ASSESSED_TYPES.has(type),
      promptLines,
    };
  }

  async open(lessonOrder) {
    const wasOpen = this.isOpen;
    if (!wasOpen) {
      this.previousFocus =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
    }
    const requestEpoch = ++this.requestEpoch;
    this.lessonOrder = safeInteger(lessonOrder, 0);
    this.level = "hsk1";
    this.lesson = null;
    this.cards = [];
    this.index = 0;
    this.score = 0;
    this.assessmentCount = 0;
    this.mistakes = [];
    this.mistakeRefs.clear();
    this.interaction = null;
    this.eventId = null;
    this.submitting = false;
    this.completed = false;
    this.previewHalf = false;
    this.previewLimit = 0;

    this.layer.hidden = false;
    if (!wasOpen) {
      this.onOpen?.();
    }
    this.closeButton.focus();
    this.renderLoading();

    try {
      const payload = await this.bridge.lessonData(this.lessonOrder);
      if (requestEpoch !== this.requestEpoch || this.layer.hidden) {
        return;
      }
      if (
        !payload ||
        payload.ok !== true ||
        !payload.lesson ||
        !Array.isArray(payload.lesson.sections)
      ) {
        throw new Error("desktop_lesson_payload_invalid");
      }
      const schemaVersion = safeInteger(payload.lesson.schema_version, 1);
      if (schemaVersion < 1 || schemaVersion > 2) {
        throw new Error("desktop_lesson_schema_unsupported");
      }
      this.lesson = payload.lesson;
      this.level = String(payload.level || payload.lesson.level || "hsk1");
      this.cards = this.flattenCards(payload.lesson);
      this.previewHalf = payload.preview_half === true;
      this.previewLimit = this.previewHalf
        ? Math.max(1, Math.floor(this.cards.length / 2))
        : this.cards.length;
      this.assessmentCount = this.cards.filter((entry) =>
        ASSESSED_TYPES.has(entry.card.type),
      ).length;
      if (this.cards.length === 0) {
        throw new Error("desktop_lesson_payload_invalid");
      }
      this.renderCurrent();
    } catch (error) {
      if (requestEpoch !== this.requestEpoch || this.layer.hidden) {
        return;
      }
      if (isSessionError(error)) {
        this.close();
        this.onSessionExpired?.();
        return;
      }
      if (error?.code === "free_feature_limit_reached") {
        this.close();
        this.onAccessRequired?.();
        return;
      }
      this.renderLoadError();
    }
  }

  close() {
    if (this.submitting) {
      return;
    }
    this.requestEpoch += 1;
    this.layer.hidden = true;
    this.content.replaceChildren();
    this.setFeedback("");
    this.interaction = null;
    this.onClose?.();
    if (this.previousFocus?.isConnected) {
      this.previousFocus.focus();
    } else {
      document.querySelector("#content-title")?.focus();
    }
    this.previousFocus = null;
  }

  flattenCards(lesson) {
    const flattened = [];
    lesson.sections.forEach((section, sectionIndex) => {
      if (!section || typeof section !== "object") {
        return;
      }
      const sectionNo = safeInteger(section.section_no, sectionIndex + 1);
      const cards = Array.isArray(section.cards) ? section.cards : [];
      cards.forEach((card, cardIndex) => {
        if (!card || typeof card !== "object") {
          return;
        }
        flattened.push({
          card,
          sectionNo,
          cardNo: cardIndex + 1,
          sectionTitle: pick(
            section.section_title,
            `${t("exerciseCard")} ${sectionNo}`,
          ),
        });
      });
    });
    return flattened;
  }

  renderLoading() {
    this.setDialogLabel(t("lessonLoading"));
    const wrap = element("div", "loading-card");
    wrap.append(element("div", "spinner"));
    wrap.append(element("p", "", t("lessonLoading")));
    this.content.replaceChildren(wrap);
    this.setProgress(0);
    this.scoreLabel.textContent = "0 / 0";
    this.setFeedback("");
    this.setNext(t("check"), true);
  }

  renderLoadError() {
    this.setDialogLabel(t("lessonLoadFailed"));
    const wrap = element("div", "error-state");
    const title = element("h2", "", t("lessonLoadFailed"));
    const retry = element("button", "primary-button", t("retry"));
    retry.type = "button";
    retry.addEventListener("click", () => this.open(this.lessonOrder));
    wrap.append(title, retry);
    this.content.replaceChildren(wrap);
    this.setFeedback(t("requestFailed"), "error");
    this.setNext(t("check"), true);
  }

  renderCurrent() {
    const entry = this.cards[this.index];
    if (!entry) {
      this.submitCompletion();
      return;
    }

    this.interaction = null;
    this.setFeedback("");
    this.content.replaceChildren();

    const progress = this.index / this.cards.length;
    this.setProgress(progress);
    this.scoreLabel.textContent = `${this.score} / ${this.assessmentCount}`;

    const kicker = element("p", "lesson-kicker", entry.sectionTitle);
    this.content.append(kicker);

    const type = String(entry.card.type || "");
    if (type === "active_word") {
      this.renderActiveWord(entry);
    } else if (type === "_grammar") {
      this.renderGrammar(entry);
    } else if (CHOICE_TYPES.has(type)) {
      this.renderChoice(entry);
    } else if (BUILDER_TYPES.has(type)) {
      this.renderBuilder(entry);
    } else if (type === "match_pairs") {
      this.renderPairs(entry);
    } else if (type === "pronunciation") {
      this.renderPronunciation(entry);
    } else {
      this.renderUnsupported(entry);
    }
    const title = this.content.querySelector(".lesson-title");
    if (title) {
      this.setDialogLabel(title.textContent);
    }
    this.onContextChanged?.();
  }

  renderActiveWord(entry) {
    const word = entry.card.word || {};
    this.content.append(
      element("h1", "lesson-title", t("teachingCard")),
    );
    const hero = element("div", "hanzi-hero");
    hero.append(
      element("strong", "", String(word.zh || "—")),
      element("span", "pinyin", String(word.pinyin || "")),
      element("span", "translation", pick(word.meaning, "—")),
    );
    this.content.append(hero);
    this.interaction = { kind: "teaching" };
    this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
  }

  renderGrammar(entry) {
    const grammar = entry.card.g || {};
    const title =
      pick(grammar.title) || String(grammar.title_zh || "") || t("teachingCard");
    this.content.append(element("h1", "lesson-title", title));

    const grammarCard = element("div", "grammar-card");
    if (grammar.title_zh) {
      grammarCard.append(element("h2", "", String(grammar.title_zh)));
    }
    grammarCard.append(element("p", "", pick(grammar.rule, "—")));

    const examples = Array.isArray(grammar.examples) ? grammar.examples : [];
    if (examples.length > 0) {
      const list = element("div", "example-list");
      examples.forEach((example) => {
        const card = element("article", "example-card");
        card.append(
          element("strong", "", String(example?.zh || "")),
          element("span", "pinyin", String(example?.pinyin || "")),
          element("span", "translation", pick(example?.translation)),
        );
        list.append(card);
      });
      grammarCard.append(list);
    }

    this.content.append(grammarCard);
    this.interaction = { kind: "teaching" };
    this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
  }

  renderChoice(entry) {
    const { card } = entry;
    const options = Array.isArray(card.options) ? card.options : [];
    const correctIndex = safeInteger(card.correct_index, -1);
    if (
      options.length < 2 ||
      correctIndex < 0 ||
      correctIndex >= options.length
    ) {
      this.renderUnsupported(entry);
      return;
    }

    const title =
      pick(card.title) || pick(card.prompt) || t("exerciseCard");
    this.content.append(element("h1", "lesson-title", title));

    const prompt = pick(card.prompt);
    if (prompt && prompt !== title) {
      this.content.append(element("p", "muted", prompt));
    }
    this.renderChoiceContext(card);

    if (card.type === "listening_choice") {
      const listenButton = element("button", "secondary-button", t("listen"));
      listenButton.type = "button";
      listenButton.addEventListener("click", async () => {
        listenButton.disabled = true;
        const spoken = await this.speak(String(card.audio_text || ""));
        listenButton.disabled = false;
        listenButton.textContent = spoken ? t("listenAgain") : t("listen");
        if (!spoken) {
          this.setFeedback(t("aiUnavailableBody"), "error");
        }
      });
      this.content.append(listenButton);
    }

    const list = element("div", "lesson-options");
    const buttons = [];
    options.forEach((option, index) => {
      const button = element("button", "lesson-option");
      button.type = "button";
      button.append(
        element("span", "option-key", String.fromCharCode(65 + index)),
        element("span", "", pick(option, String(option ?? ""))),
      );
      button.addEventListener("click", () => {
        if (this.interaction?.checked) {
          return;
        }
        buttons.forEach((item) => {
          item.classList.remove("is-selected");
          item.setAttribute("aria-pressed", "false");
        });
        button.classList.add("is-selected");
        button.setAttribute("aria-pressed", "true");
        this.interaction.selectedIndex = index;
        this.setNext(t("check"), false);
      });
      button.setAttribute("aria-pressed", "false");
      buttons.push(button);
      list.append(button);
    });
    this.content.append(list);

    this.interaction = {
      kind: "choice",
      entry,
      options,
      correctIndex,
      selectedIndex: null,
      buttons,
      checked: false,
    };
    this.setNext(t("check"), true);
  }

  renderChoiceContext(card) {
    if (card.type === "dialog_cloze" && Array.isArray(card.lines)) {
      const dialog = element("div", "dialog-card");
      card.lines.forEach((line) => {
        const row = element("div", "dialog-line");
        row.append(
          element("span", "dialog-speaker", String(line?.speaker || "•")),
          element(
            "span",
            "",
            line?.blank === true
              ? "＿＿＿＿"
              : String(line?.zh || line?.text || "…"),
          ),
        );
        dialog.append(row);
      });
      this.content.append(dialog);
      return;
    }

    const sentence = pick(card.sentence);
    if (sentence) {
      this.content.append(element("div", "example-card", sentence));
    }
    if (card.pinyin && card.type !== "listening_choice") {
      this.content.append(element("p", "pinyin", String(card.pinyin)));
    }
  }

  renderBuilder(entry) {
    const { card } = entry;
    const tokens = localizedList(card.tokens);
    const answerTokens = localizedList(card.answer_tokens);
    if (tokens.length === 0 || answerTokens.length === 0) {
      this.renderUnsupported(entry);
      return;
    }

    const prompt =
      pick(card.prompt) ||
      pick(card.sentence) ||
      pick(card.translation) ||
      t("buildSentence");
    this.content.append(
      element("h1", "lesson-title", t("buildSentence")),
      element("p", "muted", prompt),
    );
    if (card.zh) {
      const hero = element("div", "hanzi-hero");
      hero.append(
        element("strong", "", String(card.zh)),
        element("span", "pinyin", String(card.pinyin || "")),
        element("span", "translation", pick(card.translation)),
      );
      this.content.append(hero);
    }

    const zone = element("div", "builder-zone");
    const selectedWrap = element("div", "builder-tokens");
    zone.append(selectedWrap);
    const bank = element("div", "token-bank");
    const bankButtons = [];

    tokens.forEach((token, tokenIndex) => {
      const button = element("button", "token-button", token);
      button.type = "button";
      button.addEventListener("click", () => {
        if (this.interaction?.checked) {
          return;
        }
        if (
          this.interaction.selectedIndices.length >=
          this.interaction.answerTokens.length
        ) {
          return;
        }
        this.interaction.selectedIndices.push(tokenIndex);
        button.classList.add("is-used");
        this.renderSelectedBuilderTokens();
        this.setNext(
          t("check"),
          this.interaction.selectedIndices.length !==
            this.interaction.answerTokens.length,
        );
      });
      bankButtons.push(button);
      bank.append(button);
    });

    this.content.append(zone, bank);
    this.interaction = {
      kind: "builder",
      entry,
      tokens,
      answerTokens,
      selectedIndices: [],
      selectedWrap,
      bankButtons,
      checked: false,
    };
    this.setNext(t("check"), true);
  }

  renderSelectedBuilderTokens() {
    const state = this.interaction;
    if (state?.kind !== "builder") {
      return;
    }
    state.selectedWrap.replaceChildren();
    state.selectedIndices.forEach((tokenIndex, selectedIndex) => {
      const token = state.tokens[tokenIndex];
      const button = element("button", "token-button", token);
      button.type = "button";
      button.disabled = state.checked;
      button.addEventListener("click", () => {
        if (state.checked) {
          return;
        }
        state.selectedIndices.splice(selectedIndex, 1);
        state.bankButtons[tokenIndex].classList.remove("is-used");
        this.renderSelectedBuilderTokens();
        this.setNext(
          t("check"),
          state.selectedIndices.length !== state.answerTokens.length,
        );
      });
      state.selectedWrap.append(button);
    });
  }

  renderPairs(entry) {
    const rawPairs = Array.isArray(entry.card.pairs) ? entry.card.pairs : [];
    const pairs = rawPairs
      .map((pair, index) => {
        if (!Array.isArray(pair) || pair.length < 2) {
          return null;
        }
        return {
          id: index,
          left: String(pair[0] ?? ""),
          right: pick(pair[1], String(pair[1] ?? "")),
        };
      })
      .filter((pair) => pair?.left && pair?.right);
    if (pairs.length < 2) {
      this.renderUnsupported(entry);
      return;
    }

    this.content.append(
      element("h1", "lesson-title", t("matchPairs")),
    );
    const grid = element("div", "pair-grid");
    const leftWrap = element("div", "lesson-options");
    const rightWrap = element("div", "lesson-options");
    const leftButtons = new Map();
    const rightButtons = new Map();

    pairs.forEach((pair) => {
      const button = element("button", "pair-button", pair.left);
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => this.selectPair("left", pair.id));
      leftButtons.set(pair.id, button);
      leftWrap.append(button);
    });
    [...pairs].reverse().forEach((pair) => {
      const button = element("button", "pair-button", pair.right);
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => this.selectPair("right", pair.id));
      rightButtons.set(pair.id, button);
      rightWrap.append(button);
    });

    grid.append(leftWrap, rightWrap);
    this.content.append(grid);
    this.interaction = {
      kind: "pairs",
      entry,
      pairs,
      leftButtons,
      rightButtons,
      selectedLeft: null,
      selectedRight: null,
      matched: new Set(),
      hadMistake: false,
      checked: false,
    };
    this.setNext(t("continue"), true);
  }

  selectPair(side, pairId) {
    const state = this.interaction;
    if (
      state?.kind !== "pairs" ||
      state.checked ||
      state.matched.has(pairId)
    ) {
      return;
    }

    const selectedKey = side === "left" ? "selectedLeft" : "selectedRight";
    const buttons = side === "left" ? state.leftButtons : state.rightButtons;
    buttons.forEach((button, id) => {
      if (!state.matched.has(id)) {
        button.classList.toggle("is-selected", id === pairId);
        button.setAttribute("aria-pressed", String(id === pairId));
      }
    });
    state[selectedKey] = pairId;

    if (state.selectedLeft === null || state.selectedRight === null) {
      return;
    }

    if (state.selectedLeft === state.selectedRight) {
      const matchedId = state.selectedLeft;
      state.matched.add(matchedId);
      state.leftButtons.get(matchedId)?.classList.add("is-matched");
      state.rightButtons.get(matchedId)?.classList.add("is-matched");
      state.leftButtons.get(matchedId).disabled = true;
      state.rightButtons.get(matchedId).disabled = true;
      this.setFeedback(t("correct"), "correct");
    } else {
      state.hadMistake = true;
      this.recordPairMistake(
        state,
        state.selectedLeft,
        state.selectedRight,
      );
      this.setFeedback(t("wrong"), "wrong");
    }

    state.leftButtons.forEach((button) => {
      button.classList.remove("is-selected");
      button.setAttribute("aria-pressed", "false");
    });
    state.rightButtons.forEach((button) => {
      button.classList.remove("is-selected");
      button.setAttribute("aria-pressed", "false");
    });
    state.selectedLeft = null;
    state.selectedRight = null;

    if (state.matched.size === state.pairs.length) {
      state.checked = true;
      if (!state.hadMistake) {
        this.score += 1;
      }
      this.scoreLabel.textContent = `${this.score} / ${this.assessmentCount}`;
      this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
    }
  }

  renderPronunciation(entry) {
    const { card } = entry;
    this.content.append(
      element("h1", "lesson-title", t("pronunciationTitle")),
    );
    const panel = element("div", "pronunciation-card");
    const hero = element("div", "hanzi-hero");
    hero.append(
      element("strong", "", String(card.phrase || "—")),
      element("span", "pinyin", String(card.pinyin || "")),
      element("span", "translation", pick(card.translation)),
    );
    panel.append(hero);
    const listenButton = element("button", "secondary-button", t("listen"));
    listenButton.type = "button";
    listenButton.addEventListener("click", async () => {
      listenButton.disabled = true;
      const spoken = await this.speak(String(card.phrase || ""));
      listenButton.disabled = false;
      listenButton.textContent = spoken ? t("listenAgain") : t("listen");
      if (!spoken) {
        this.setFeedback(t("requestFailed"), "error");
      }
    });
    panel.append(listenButton, element("p", "muted", t("pronunciationNote")));
    this.content.append(panel);
    this.interaction = { kind: "pronunciation" };
    this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
  }

  renderUnsupported(entry) {
    const type = String(entry.card.type || "unknown");
    this.content.append(
      element("h1", "lesson-title", t("unsupportedCard")),
    );
    const state = element("div", "error-state");
    state.append(
      element("p", "", t("unsupportedCardType", { type })),
      element("p", "muted", t("requestFailed")),
    );
    const retry = element("button", "secondary-button", t("retry"));
    retry.type = "button";
    retry.addEventListener("click", () => this.open(this.lessonOrder));
    state.append(retry);
    this.content.append(state);
    this.interaction = { kind: "unsupported" };
    this.setFeedback(t("unsupportedCard"), "error");
    this.setNext(t("continue"), true);
  }

  async speak(text) {
    if (!text.trim()) {
      return false;
    }
    try {
      const result = await this.bridge.ttsSpeak(text);
      if (result?.ok === true) {
        return true;
      }
    } catch {
      // The webview's local speech engine is the safe offline fallback.
    }

    const synthesis = globalThis.speechSynthesis;
    const Utterance = globalThis.SpeechSynthesisUtterance;
    if (!synthesis || typeof Utterance !== "function") {
      return false;
    }
    try {
      synthesis.cancel();
      const utterance = new Utterance(text);
      utterance.lang = "zh-CN";
      const voices = synthesis.getVoices();
      const chineseVoice = voices.find((voice) =>
        String(voice.lang || "").toLowerCase().startsWith("zh") &&
        voice.localService === true,
      );
      if (!chineseVoice) {
        return false;
      }
      utterance.voice = chineseVoice;
      synthesis.speak(utterance);
      return true;
    } catch {
      return false;
    }
  }

  handleNext() {
    if (this.submitting) {
      return;
    }
    if (this.completed) {
      this.close();
      return;
    }

    const state = this.interaction;
    if (!state) {
      return;
    }
    if (
      state.kind === "teaching" ||
      state.kind === "pronunciation"
    ) {
      this.advance();
      return;
    }
    if (state.kind === "choice") {
      state.checked ? this.advance() : this.gradeChoice();
      return;
    }
    if (state.kind === "builder") {
      state.checked ? this.advance() : this.gradeBuilder();
      return;
    }
    if (state.kind === "pairs" && state.checked) {
      this.advance();
      return;
    }
    if (state.kind === "completion-retry") {
      this.submitCompletion();
      return;
    }
    if (state.kind === "preview-boundary") {
      this.close();
      this.onAccessRequired?.();
    }
  }

  gradeChoice() {
    const state = this.interaction;
    if (
      state?.kind !== "choice" ||
      !Number.isInteger(state.selectedIndex)
    ) {
      return;
    }
    state.checked = true;
    state.buttons.forEach((button, index) => {
      button.disabled = true;
      if (index === state.correctIndex) {
        button.classList.add("is-correct");
      }
      if (index === state.selectedIndex && index !== state.correctIndex) {
        button.classList.add("is-wrong");
      }
    });

    const correct = state.selectedIndex === state.correctIndex;
    if (correct) {
      this.score += 1;
      this.setFeedback(
        pick(state.entry.card.explanation, t("correct")),
        "correct",
      );
    } else {
      this.recordChoiceMistake(state);
      this.setFeedback(
        pick(state.entry.card.explanation, t("wrong")),
        "wrong",
      );
    }
    this.scoreLabel.textContent = `${this.score} / ${this.assessmentCount}`;
    this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
    this.onContextChanged?.();
  }

  gradeBuilder() {
    const state = this.interaction;
    if (state?.kind !== "builder" || state.selectedIndices.length === 0) {
      return;
    }
    state.checked = true;
    state.bankButtons.forEach((button) => {
      button.disabled = true;
    });
    this.renderSelectedBuilderTokens();

    const selectedTokens = state.selectedIndices.map(
      (tokenIndex) => state.tokens[tokenIndex],
    );
    const correct = isSameTokens(selectedTokens, state.answerTokens);
    if (correct) {
      this.score += 1;
      this.setFeedback(
        pick(state.entry.card.explanation, t("correct")),
        "correct",
      );
    } else {
      this.recordBuilderMistake(state, selectedTokens);
      this.setFeedback(
        pick(state.entry.card.explanation, t("wrong")),
        "wrong",
      );
    }
    this.scoreLabel.textContent = `${this.score} / ${this.assessmentCount}`;
    this.setNext(this.isLastCard() ? t("finish") : t("continue"), false);
    this.onContextChanged?.();
  }

  materialRef(entry) {
    return `lesson:${this.level}:${this.lessonOrder}:section:${entry.sectionNo}:card:${entry.cardNo}`;
  }

  recordChoiceMistake(state) {
    const materialRef = this.materialRef(state.entry);
    if (this.mistakeRefs.has(materialRef) || this.mistakes.length >= 50) {
      return;
    }
    this.mistakeRefs.add(materialRef);
    this.mistakes.push({
      material_ref: materialRef,
      selected_index: state.selectedIndex,
      selected_answer: pick(
        state.options[state.selectedIndex],
        String(state.options[state.selectedIndex] ?? ""),
      ),
    });
  }

  recordBuilderMistake(state, selectedTokens) {
    const materialRef = this.materialRef(state.entry);
    if (this.mistakeRefs.has(materialRef) || this.mistakes.length >= 50) {
      return;
    }
    this.mistakeRefs.add(materialRef);
    this.mistakes.push({
      material_ref: materialRef,
      selected_tokens: selectedTokens.slice(0, 100),
    });
  }

  recordPairMistake(state, selectedLeftIndex, selectedRightIndex) {
    const materialRef = this.materialRef(state.entry);
    if (this.mistakeRefs.has(materialRef) || this.mistakes.length >= 50) {
      return;
    }
    this.mistakeRefs.add(materialRef);
    this.mistakes.push({
      material_ref: materialRef,
      selected_left_index: selectedLeftIndex,
      selected_right_index: selectedRightIndex,
    });
  }

  advance() {
    const nextIndex = this.index + 1;
    if (
      this.previewHalf &&
      nextIndex >= this.previewLimit
    ) {
      this.renderPreviewBoundary();
      return;
    }
    this.index = nextIndex;
    if (this.index >= this.cards.length) {
      this.submitCompletion();
      return;
    }
    this.renderCurrent();
  }

  renderPreviewBoundary() {
    this.setDialogLabel(t("freePlan"));
    this.interaction = { kind: "preview-boundary" };
    this.setProgress(this.previewLimit / Math.max(1, this.cards.length));
    const wrap = element("div", "lesson-finish");
    wrap.append(
      element("div", "finish-mark", "🔒"),
      element("h1", "", t("freePlan")),
      element("p", "muted", t("freeAccessDescription")),
      element("p", "muted", t("manageSubscription")),
    );
    this.content.replaceChildren(wrap);
    this.setFeedback("");
    this.setNext(t("profile"), false);
  }

  async submitCompletion() {
    if (this.submitting) {
      return;
    }
    this.submitting = true;
    this.eventId ||= completionEventId();
    this.setProgress(1);
    this.setNext(t("finish"), true);
    this.setFeedback(t("lessonLoading"));
    this.setDialogLabel(t("lessonLoading"));

    const wrap = element("div", "lesson-finish");
    wrap.append(
      element("div", "spinner"),
      element("h2", "", t("lessonLoading")),
    );
    this.content.replaceChildren(wrap);

    try {
      const result = await this.bridge.lessonComplete(
        this.lessonOrder,
        this.eventId,
        this.mistakes,
      );
      if (!result || result.ok !== true) {
        throw new Error("desktop_course_save_failed");
      }
      this.renderCompletion(result);
      await this.onCompleted?.(result);
    } catch (error) {
      this.submitting = false;
      if (isSessionError(error)) {
        this.close();
        this.onSessionExpired?.();
        return;
      }
      this.renderCompletionError();
    }
  }

  renderCompletion(result) {
    this.submitting = false;
    this.completed = true;
    const accuracy =
      this.assessmentCount > 0
        ? Math.round((this.score / this.assessmentCount) * 100)
        : 100;
    const gamification = result.gamification || {};
    const awardedXp =
      gamification.awarded_xp ?? gamification.xp_awarded ?? 0;
    this.setDialogLabel(t("lessonCompleteTitle"));

    const wrap = element("div", "lesson-finish");
    wrap.append(
      element("div", "finish-mark", "✓"),
      element("h1", "", t("lessonCompleteTitle")),
      element("p", "muted", t("lessonCompleteBody")),
    );
    const stats = element("div", "finish-stats");
    const accuracyItem = element("span");
    accuracyItem.append(
      element("b", "", `${accuracy}%`),
      element("small", "", t("localAccuracy")),
    );
    const correctItem = element("span");
    correctItem.append(
      element("b", "", `${this.score}/${this.assessmentCount}`),
      element("small", "", t("correctAnswers")),
    );
    const rewardItem = element("span");
    rewardItem.append(
      element("b", "", `+${Number(awardedXp) || 0} XP`),
      element("small", "", t("serverReward")),
    );
    stats.append(accuracyItem, correctItem, rewardItem);
    wrap.append(stats);
    this.content.replaceChildren(wrap);
    this.setFeedback("");
    this.setNext(t("continue"), false);
  }

  renderCompletionError() {
    this.setDialogLabel(t("lessonSubmitFailed"));
    const wrap = element("div", "error-state");
    wrap.append(
      element("h2", "", t("lessonSubmitFailed")),
      element("p", "muted", t("noConnection")),
    );
    this.content.replaceChildren(wrap);
    this.setFeedback(t("lessonSubmitFailed"), "error");
    this.setNext(t("retry"), false);
    this.interaction = { kind: "completion-retry" };
  }

  isLastCard() {
    return !this.previewHalf && this.index === this.cards.length - 1;
  }

  setFeedback(message, tone = "") {
    this.feedback.textContent = String(message || "");
    this.feedback.className = "lesson-feedback";
    if (tone) {
      this.feedback.classList.add(`is-${tone}`);
    }
    this.onContextChanged?.();
  }

  setNext(label, disabled) {
    this.nextButton.textContent = label;
    this.nextButton.disabled = Boolean(disabled);
  }

  setProgress(ratio) {
    const normalized = Math.max(0, Math.min(1, Number(ratio) || 0));
    this.progressBar.dataset.progress = String(Math.round(normalized * 20));
    this.progressBar.parentElement?.setAttribute(
      "aria-valuenow",
      String(Math.round(normalized * 100)),
    );
  }

  setDialogLabel(label) {
    this.dialog?.setAttribute(
      "aria-label",
      String(label || t("teachingCard")),
    );
  }

  trapFocus(event) {
    if (!this.isOpen || event.key !== "Tab") {
      return;
    }
    const focusable = [
      ...this.layer.querySelectorAll(
        'button:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
    if (focusable.length === 0) {
      event.preventDefault();
      this.closeButton.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!focusable.includes(document.activeElement)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}
