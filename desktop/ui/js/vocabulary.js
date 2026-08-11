/**
 * Vocabulary — the full cross-lesson dictionary.
 *
 * Words, example sentences and stroke data are bundled under ../data, so the
 * dictionary works with no network at all: the strict CSP gives the webview no
 * network transport, and stroke order must never depend on a CDN. Saved words
 * and the review queue are kept by Rust in a local file, not in the shared
 * database — they are a desktop-only convenience and do not sync to the Mini App.
 */

import { EXAMPLES, WORDS } from "../data/vocabulary.js";

const LEVELS = ["HSK1", "HSK2", "HSK3", "HSK4"];
const FILTERS = ["all", "saved", "review"];
const PAGE_SIZE = 60;

let strokesPromise = null;
let writerPromise = null;

/** 2.5 MB of stroke paths — only loaded once a word detail is actually opened. */
function loadStrokes() {
  if (!strokesPromise) {
    strokesPromise = import("../data/strokes.js")
      .then((module) => module.STROKES)
      .catch(() => null);
  }
  return strokesPromise;
}

function loadWriter() {
  if (!writerPromise) {
    writerPromise = import("../vendor/hanzi-writer.js")
      .then((module) => module.default)
      .catch(() => null);
  }
  return writerPromise;
}

function node(tag, className = "", text = "") {
  const value = document.createElement(tag);
  if (className) value.className = className;
  if (text !== "") value.textContent = String(text);
  return value;
}

function soonBlock(content, label) {
  const wrap = node("div", "soon-block");
  content
    .querySelectorAll("button, input, select, textarea, a[href]")
    .forEach((control) => {
      control.disabled = true;
      control.tabIndex = -1;
      control.setAttribute("aria-hidden", "true");
    });
  const veil = node("div", "soon-veil");
  veil.append(node("span", "soon-badge", label));
  wrap.append(content, veil);
  return wrap;
}

function normalized(value) {
  return String(value || "").trim().toLowerCase();
}

export class DesktopVocabularyController {
  constructor({ host, bridge, t, language, onToast, speak, onAskAi }) {
    this.host = host;
    this.bridge = bridge;
    this.t = t;
    this.language = language;
    this.onToast = onToast;
    this.speak = speak;
    this.onAskAi = onAskAi;

    this.query = "";
    this.filter = "all";
    this.level = "";
    this.selected = "";
    this.detailOpen = false;
    this.saved = new Set();
    this.review = new Set();
    this.stateLoaded = false;
    this.limit = PAGE_SIZE;
    this.error = "";
  }

  setLanguage(language) {
    this.language = language;
  }

  dispose() {
    this.detailOpen = false;
  }

  meaning(word) {
    const map = word?.m || {};
    return String(map[this.language] || map.uz || map.ru || map.tj || "");
  }

  example(headword) {
    const entry = EXAMPLES[headword];
    if (!entry) return null;
    const map = entry.m || {};
    return {
      zh: String(entry.zh || ""),
      pos: String(entry.pos || ""),
      // Every sentence now carries all three languages; the fallback only
      // guards against a future entry that is added incompletely.
      translation: String(map[this.language] || map.uz || ""),
    };
  }

  async load() {
    if (!this.stateLoaded) {
      try {
        const state = await this.bridge.vocabularyState();
        this.saved = new Set(state?.saved || []);
        this.review = new Set(state?.review || []);
      } catch {
        // A missing or unreadable file is not an error worth blocking on.
        this.saved = new Set();
        this.review = new Set();
      }
      this.stateLoaded = true;
    }
    this.render();
  }

  async persist() {
    try {
      await this.bridge.vocabularySave({
        saved: [...this.saved],
        review: [...this.review],
      });
      this.error = "";
    } catch (error) {
      this.error = this.t("vocabularySaveFailed");
      void error;
    }
  }

  matches(word) {
    if (this.level && String(word.lv || "") !== this.level) return false;
    if (this.filter === "saved" && !this.saved.has(word.h)) return false;
    if (this.filter === "review" && !this.review.has(word.h)) return false;
    if (!this.query) return true;
    const needle = normalized(this.query);
    return (
      String(word.h || "").includes(this.query.trim()) ||
      normalized(word.p).includes(needle) ||
      normalized(this.meaning(word)).includes(needle)
    );
  }

  results() {
    return WORDS.filter((word) => this.matches(word));
  }

  // ---------------------------------------------------------------- rendering

  render() {
    if (!this.host) return;
    this.host.replaceChildren();
    const rows = this.results();
    if (this.selected && !rows.some((word) => word.h === this.selected)) {
      this.selected = "";
    }
    if (!this.selected && rows.length) {
      this.selected = rows[0].h;
    }
    if (this.detailOpen) {
      this.host.append(this.renderDetailScreen());
      return;
    }
    this.host.append(this.renderControls(rows.length));
    if (this.error) this.host.append(node("p", "form-error", this.error));
    const layout = node("div", "vocabulary-layout vocabLayout");
    layout.append(this.renderList(rows), this.renderSavedBox());
    this.host.append(layout);
  }

  renderControls(count) {
    const bar = node("section", "vocabulary-controls vocabTop");

    const search = node("label", "vocabulary-search vocabSearch");
    search.append(node("span", "", "⌕"));
    const input = document.createElement("input");
    input.type = "search";
    input.autocomplete = "off";
    input.placeholder = this.t("vocabularySearchPlaceholder");
    input.value = this.query;
    input.addEventListener("input", () => {
      this.query = input.value;
      this.limit = PAGE_SIZE;
      this.selected = "";
      this.render();
      const next = this.host?.querySelector(".vocabulary-search input");
      if (next) {
        next.focus();
        next.setSelectionRange(next.value.length, next.value.length);
      }
    });
    search.append(input);
    bar.append(search);

    const filters = node("div", "vocabulary-filters");
    FILTERS.forEach((filter) => {
      const label =
        filter === "all"
          ? this.t("vocabularyFilterAll")
          : filter === "saved"
            ? this.t("vocabularyFilterSaved")
            : this.t("vocabularyFilterReview");
      const count =
        filter === "saved"
          ? this.saved.size
          : filter === "review"
            ? this.review.size
            : 0;
      const button = node(
        "button",
        `filterBtn${this.filter === filter ? " active" : ""}`,
        count ? `${label} · ${count}` : label,
      );
      button.type = "button";
      button.setAttribute("aria-pressed", this.filter === filter ? "true" : "false");
      button.addEventListener("click", () => {
        this.filter = filter;
        this.limit = PAGE_SIZE;
        this.selected = "";
        this.render();
      });
      filters.append(button);
    });
    bar.append(filters);

    const levels = node("div", "vocabulary-filters");
    [["", this.t("vocabularyAllLevels")], ...LEVELS.map((l) => [l, l])].forEach(
      ([value, label]) => {
      const button = node(
        "button",
        `filterBtn${this.level === value ? " active" : ""}`,
        label,
      );
        button.type = "button";
        button.setAttribute("aria-pressed", this.level === value ? "true" : "false");
        button.addEventListener("click", () => {
          this.level = value;
          this.limit = PAGE_SIZE;
          this.selected = "";
          this.render();
        });
        levels.append(button);
      },
    );
    bar.append(levels);
    bar.append(node("span", "word-count", this.t("wordCount", { count })));
    return bar;
  }

  renderList(rows) {
    const list = node("section", "vocabulary-list wordList card-panel card");
    if (!rows.length) {
      list.append(node("p", "muted", this.t("vocabularyNoResults")));
      return list;
    }
    const container = node("div", "vocabulary-rows");
    rows.slice(0, this.limit).forEach((word) => {
      const row = node(
        "button",
        `vocabulary-row wordRow${word.h === this.selected ? " is-active" : ""}`,
      );
      row.type = "button";
      row.append(
        node("strong", "zh hanzi", word.h),
        node("span", "py pinyin", word.p),
        node("small", "translation", this.meaning(word)),
        node("span", "tag vocabulary-level", String(word.lv || "")),
      );
      if (this.saved.has(word.h)) {
        row.append(node("span", "vocabulary-flag", "★"));
      }
      row.addEventListener("click", () => {
        this.selected = word.h;
        this.detailOpen = true;
        this.render();
      });
      container.append(row);
    });
    list.append(container);

    if (rows.length > this.limit) {
      const more = node(
        "button",
        "secondary-button vocabulary-more",
        this.t("vocabularyShowMore"),
      );
      more.type = "button";
      more.addEventListener("click", () => {
        this.limit += PAGE_SIZE;
        this.render();
      });
      list.append(more);
    }
    return list;
  }

  renderSavedBox() {
    const box = node("aside", "savedBox card-panel card");
    const head = node("div", "sectionTitle");
    head.append(
      node("h3", "", this.t("vocabularySavedWords")),
      node("span", "tag", "⌘R"),
    );
    box.append(head);
    const note = node("div", "savedPandaNote");
    const panda = document.createElement("img");
    panda.className = "pandaMini";
    panda.src = "./assets/hsk-ai-avatar.webp";
    panda.alt = "";
    panda.setAttribute("aria-hidden", "true");
    note.append(panda, node("small", "", this.t("vocabularySavedHint")));
    box.append(note);

    const list = node("div", "savedList");
    const savedWords = WORDS.filter((word) => this.saved.has(word.h)).slice(0, 12);
    if (!savedWords.length) {
      list.append(node("p", "muted small", this.t("vocabularyNoSaved")));
    } else {
      savedWords.forEach((word) => {
        const item = node("button", "savedItem");
        item.type = "button";
        const copy = node("div");
        copy.append(
          node("b", "hanzi", word.h),
          node("span", "", ` · ${word.p}`),
        );
        item.append(copy, node("span", "", this.meaning(word)));
        item.addEventListener("click", () => {
          this.selected = word.h;
          this.detailOpen = true;
          this.render();
        });
        list.append(item);
      });
    }
    box.append(list);

    const review = node(
      "button",
      "btn secondary secondary-button vocabulary-review-later",
      this.t("vocabularyReviewLater"),
    );
    review.type = "button";
    review.addEventListener("click", () => {
      this.filter = "review";
      this.detailOpen = false;
      this.limit = PAGE_SIZE;
      this.render();
    });
    box.append(review);
    return box;
  }

  renderDetailScreen() {
    const word = WORDS.find((item) => item.h === this.selected);
    if (!word) {
      this.detailOpen = false;
      return this.renderList(this.results());
    }
    const example = this.example(word.h);
    const fragment = document.createDocumentFragment();

    const head = node("div", "vocabDetailHead");
    const back = node("button", "vocabBack", "‹");
    back.type = "button";
    back.setAttribute("aria-label", this.t("back"));
    back.addEventListener("click", () => {
      this.detailOpen = false;
      this.render();
    });
    const title = node("div", "titleBlock");
    title.append(
      node("h2", "", this.t("vocabularyDetailTitle")),
      node("p", "", this.t("vocabularyDetailSubtitle")),
    );
    head.append(back, title, node("span", "tag", String(word.lv || "")));
    fragment.append(head);

    const grid = node("div", "wordDetailGrid");
    const main = node("main", "wordDetailMain");
    const aside = node("aside", "wordDetailAside");

    const hero = node("article", "card wordHeroDetail card-panel");
    hero.dataset.watermark = word.h;
    const copy = node("div");
    copy.append(
      node("div", "detailPy pinyin", word.p),
      node("div", "detailTranslation translation", this.meaning(word)),
    );
    const meta = node("div", "detailMeta");
    meta.append(
      node("span", "tag", example?.pos || String(word.lv || "")),
      node("span", "tag", String(word.lv || "")),
      this.review.has(word.h)
        ? node("span", "tag red", this.t("vocabularyInReview"))
        : node("span", "tag green", this.t("vocabularySaved")),
    );
    copy.append(meta);
    const audio = node("button", "btn detailSpeak", `▶ ${this.t("listen")}`);
    audio.type = "button";
    audio.addEventListener("click", () => this.speak?.(word.h, audio));
    hero.append(node("div", "detailZh hanzi", word.h), copy, audio);
    main.append(hero);

    const actions = node("div", "vocabulary-actions");
    [
      ["saved", this.saved, this.t("vocabularySave"), this.t("vocabularySaved")],
      ["review", this.review, this.t("vocabularyAddReview"), this.t("vocabularyInReview")],
    ].forEach(([, collection, addLabel, onLabel]) => {
      const active = collection.has(word.h);
      const button = node(
        "button",
        `filterBtn${active ? " active" : ""}`,
        active ? onLabel : addLabel,
      );
      button.type = "button";
      button.setAttribute("aria-pressed", active ? "true" : "false");
      button.addEventListener("click", () => {
        if (collection.has(word.h)) collection.delete(word.h);
        else collection.add(word.h);
        void this.persist().then(() => this.render());
      });
      actions.append(button);
    });
    main.append(actions);

    const strokes = node("article", "card strokeCard card-panel");
    const strokeHead = node("div", "strokeToolbar");
    const strokeCopy = node("div");
    strokeCopy.append(
      node("h3", "", this.t("vocabularyStrokeOrder")),
      node("div", "strokeHint", this.t("vocabularyStrokeHint")),
    );
    strokeHead.append(strokeCopy);
    const stage = node("div", "stroke-stage strokeStage");
    strokes.append(strokeHead, stage);
    main.append(strokes);
    void this.renderStrokes(stage, word.h);

    const examples = node("article", "card examplesCard card-panel");
    examples.append(node("h3", "", this.t("examples")));
    const exampleList = node("div", "exampleList");
    if (example?.zh) {
      const item = node("article", "detailExample vocabulary-example");
      item.append(node("div", "zh hanzi", example.zh));
      if (example.translation) {
        item.append(node("div", "tr translation", example.translation));
      }
      const play = node("button", "listen-button", this.t("listen"));
      play.type = "button";
      play.addEventListener("click", () => this.speak?.(example.zh, play));
      item.append(play);
      exampleList.append(item);
    } else {
      exampleList.append(node("p", "muted", this.t("examplesNotAvailable")));
    }
    examples.append(exampleList);
    main.append(examples);

    const memory = node("article", "card memoryBreakdown card-panel");
    memory.append(
      node("h3", "", this.t("vocabularyMemoryTitle")),
      node("p", "breakdownIntro", this.t("vocabularyMemoryUnavailable")),
    );
    main.append(soonBlock(memory, this.t("comingSoon")));

    const ai = node("article", "card detailAiCard card-panel");
    const aiTop = node("div", "aiTutorTop");
    const aiAvatar = document.createElement("img");
    aiAvatar.className = "detailAiPanda";
    aiAvatar.src = "./assets/hsk-ai-avatar.webp";
    aiAvatar.alt = "";
    aiAvatar.setAttribute("aria-hidden", "true");
    const aiCopy = node("div");
    aiCopy.append(
      node("h3", "", this.t("vocabularyAiTitle")),
      node("span", "muted small", this.t("vocabularyAiSub")),
    );
    aiTop.append(aiAvatar, aiCopy);
    const preview = node("div", "screenPreview");
    preview.append(
      node("div", "screenPreviewBar"),
      node("div", "screenPreviewWord hanzi", word.h),
      node("small", "", this.t("vocabularyAiSees")),
    );
    const chips = node("div", "chips");
    [
      "vocabularyAiChipSimple",
      "vocabularyAiChipExample",
      "vocabularyAiChipCompare",
    ].forEach((key) => {
      const chip = node("button", "promptChip", this.t(key));
      chip.type = "button";
      chip.addEventListener("click", () => {
        this.onAskAi?.(`${this.t(key)}: ${word.h} · ${word.p}`);
      });
      chips.append(chip);
    });
    const composer = node("form", "detailAiComposer");
    const input = document.createElement("input");
    input.placeholder = this.t("vocabularyAskPlaceholder");
    input.maxLength = 1000;
    const send = node("button", "btn", "↑");
    send.type = "submit";
    composer.append(input, send);
    composer.addEventListener("submit", (event) => {
      event.preventDefault();
      const prompt = String(input.value || "").trim();
      this.onAskAi?.(prompt ? `${prompt}: ${word.h}` : `${word.h} · ${word.p}`);
    });
    ai.append(aiTop, preview, chips, composer);
    aside.append(ai);

    grid.append(main, aside);
    fragment.append(grid);
    return fragment;
  }

  renderDetail() {
    const detail = node("aside", "vocabulary-detail card-panel");
    const word = WORDS.find((item) => item.h === this.selected);
    if (!word) {
      detail.append(node("p", "muted", this.t("vocabularyPickWord")));
      return detail;
    }

    const example = this.example(word.h);
    const top = node("div", "vocabulary-detail-top");
    const copy = node("div");
    copy.append(
      node("p", "eyebrow", example?.pos || String(word.lv || "")),
      node("strong", "vocabulary-detail-zh hanzi", word.h),
      node("span", "vocabulary-detail-pinyin pinyin", word.p),
      node("p", "vocabulary-detail-translation translation", this.meaning(word)),
    );
    const listen = node("button", "listen-button", this.t("listen"));
    listen.type = "button";
    listen.addEventListener("click", () => this.speak?.(word.h, listen));
    top.append(copy, listen);
    detail.append(top);

    const actions = node("div", "vocabulary-actions");
    [
      ["saved", this.saved, this.t("vocabularySave"), this.t("vocabularySaved")],
      ["review", this.review, this.t("vocabularyAddReview"), this.t("vocabularyInReview")],
    ].forEach(([, collection, addLabel, onLabel]) => {
      const active = collection.has(word.h);
      const button = node(
        "button",
        `voice-choice${active ? " is-active" : ""}`,
        active ? onLabel : addLabel,
      );
      button.type = "button";
      button.setAttribute("aria-pressed", active ? "true" : "false");
      button.addEventListener("click", () => {
        if (collection.has(word.h)) collection.delete(word.h);
        else collection.add(word.h);
        void this.persist().then(() => this.render());
      });
      actions.append(button);
    });
    detail.append(actions);

    const strokes = node("div", "vocabulary-strokes");
    strokes.append(node("h4", "", this.t("vocabularyStrokeOrder")));
    const stage = node("div", "stroke-stage");
    strokes.append(stage);
    detail.append(strokes);
    void this.renderStrokes(stage, word.h);

    const examples = node("div", "vocabulary-examples");
    examples.append(node("h4", "", this.t("examples")));
    if (example?.zh) {
      const item = node("article", "vocabulary-example");
      item.append(node("strong", "hanzi", example.zh));
      if (example.translation) {
        item.append(node("p", "translation", example.translation));
      }
      const play = node("button", "listen-button", this.t("listen"));
      play.type = "button";
      play.addEventListener("click", () => this.speak?.(example.zh, play));
      item.append(play);
      examples.append(item);
    } else {
      examples.append(node("p", "muted", this.t("examplesNotAvailable")));
    }
    detail.append(examples);
    return detail;
  }

  /** One animated SVG per character, drawn from the bundled stroke paths. */
  async renderStrokes(stage, headword) {
    const characters = [...String(headword || "")].filter((c) =>
      /[一-鿿]/.test(c),
    );
    if (!characters.length) return;
    const [strokes, HanziWriter] = await Promise.all([loadStrokes(), loadWriter()]);
    if (!strokes || !HanziWriter || !stage.isConnected) return;

    const missing = characters.filter((character) => !strokes[character]);
    if (missing.length === characters.length) {
      stage.append(node("p", "muted", this.t("vocabularyStrokesUnavailable")));
      return;
    }

    characters.forEach((character) => {
      const data = strokes[character];
      if (!data) return;
      const box = node("div", "stroke-box");
      stage.append(box);
      const writer = HanziWriter.create(box, character, {
        width: 108,
        height: 108,
        padding: 6,
        showOutline: true,
        strokeAnimationSpeed: 1.1,
        delayBetweenStrokes: 220,
        strokeColor: "#211d17",
        outlineColor: "#e0d6c1",
        radicalColor: "#e04a40",
        // No CDN: the character data is already in memory.
        charDataLoader: (_char, onLoad) => onLoad(data),
      });
      box.addEventListener("click", () => writer.animateCharacter());
      writer.animateCharacter();
    });
  }
}
