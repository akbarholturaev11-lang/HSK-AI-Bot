/**
 * Practice — the real drill engine.
 *
 * Question sets, the free daily-use gate, grading and mistake bookkeeping all
 * live in `CourseMiniAppPracticeService` on the server, exactly as they do for
 * the Telegram Mini App. This module only runs the session: it shows one
 * question at a time, records the chosen option and sends the answers back to
 * be graded. Nothing is invented locally.
 */

const DRILLS = [
  { id: "placement", mode: "placement", skill: "", glyph: "级" },
  { id: "mock", mode: "mock", skill: "", glyph: "考" },
  { id: "characters", mode: "training", skill: "characters", glyph: "字" },
  { id: "listening", mode: "training", skill: "listening", glyph: "听" },
  { id: "pronunciation", mode: "training", skill: "pronunciation", glyph: "音" },
  { id: "pinyin", mode: "training", skill: "pinyin", glyph: "拼" },
  { id: "writing", mode: "training", skill: "writing", glyph: "写" },
];

function node(tag, className = "", text = "") {
  const value = document.createElement(tag);
  if (className) value.className = className;
  if (text !== "") value.textContent = String(text);
  return value;
}

export class DesktopPracticeController {
  constructor({
    host,
    bridge,
    t,
    language,
    level,
    onSessionExpired,
    onToast,
    onOpenSubscription,
    speak,
  }) {
    this.host = host;
    this.bridge = bridge;
    this.t = t;
    this.language = language;
    this.level = String(level || "hsk1");
    this.onSessionExpired = onSessionExpired;
    this.onToast = onToast;
    this.onOpenSubscription = onOpenSubscription;
    this.speak = speak;

    this.phase = "idle";
    this.drill = null;
    this.session = null;
    this.index = 0;
    this.answers = [];
    this.selected = -1;
    this.checked = false;
    this.summary = null;
    this.busy = false;
    this.error = "";
    this.limitReached = false;
  }

  setLanguage(language) {
    this.language = language;
  }

  setLevel(level) {
    this.level = String(level || "hsk1");
  }

  isSessionError(error) {
    return [
      "desktop_unauthorized",
      "desktop_session_not_found",
      "desktop_session_revoked",
      "desktop_refresh_invalid",
      "desktop_access_invalid",
      "desktop_access_expired",
      "desktop_not_linked",
    ].includes(error?.code);
  }

  errorText(error) {
    const code = String(error?.code || error?.message || "");
    const known = this.t(code);
    return known === code ? this.t("practiceGenericError") : known;
  }

  reset() {
    this.phase = "idle";
    this.drill = null;
    this.session = null;
    this.index = 0;
    this.answers = [];
    this.selected = -1;
    this.checked = false;
    this.summary = null;
    this.error = "";
    this.limitReached = false;
  }

  /** Called when the view changes; a half-finished drill is not kept. */
  dispose() {
    this.reset();
  }

  // ---------------------------------------------------------------- rendering

  render() {
    if (!this.host) return;
    this.host.replaceChildren();
    if (this.phase === "summary" && this.summary) {
      this.host.append(this.renderSummary());
      return;
    }
    if (this.phase === "running" && this.session) {
      this.host.append(this.renderQuestion());
      return;
    }
    this.host.append(this.renderIntro());
  }

  renderIntro() {
    const wrap = node("div", "practice-host");

    const intro = node("section", "practice-intro card-panel card cardPad");
    const copy = node("div");
    copy.append(
      node("p", "eyebrow", this.t("realCoursePractice")),
      node("h3", "", this.t("practiceIntroTitle")),
      node("p", "muted", this.t("practiceIntroBody")),
    );
    const panda = document.createElement("img");
    panda.src = "./assets/hsk-ai-avatar.webp";
    panda.alt = "";
    intro.append(copy, panda);
    wrap.append(intro);

    if (this.limitReached) {
      const gate = node("section", "practice-gate card-panel");
      gate.append(
        node("h3", "", this.t("practiceLimitTitle")),
        node("p", "muted", this.t("practiceLimitBody")),
      );
      const cta = node("button", "primary-button", this.t("voiceLimitCta"));
      cta.type = "button";
      cta.addEventListener("click", () => this.onOpenSubscription?.());
      gate.append(cta);
      wrap.append(gate);
    } else if (this.error) {
      wrap.append(node("p", "form-error", this.error));
    }

    const grid = node("section", "practice-grid practiceGrid");
    DRILLS.forEach((drill) => {
      const card = node("article", "practice-card practiceCard card-panel card");
      card.tabIndex = 0;
      card.append(
        node("div", "practice-glyph practiceIcon hanzi", drill.glyph),
        node("h3", "", this.t(`drill_${drill.id}`)),
        node("p", "muted", this.t(`drillBody_${drill.id}`)),
      );
      const foot = node("div", "practice-card-foot practiceFoot");
      foot.append(node("span", "tag", this.t("practiceMinutesShort")));
      const start = node(
        "button",
        "practiceGo secondary-button",
        this.busy && this.drill?.id === drill.id
          ? this.t("practiceStarting")
          : `${this.t("practiceStartShort")} →`,
      );
      start.type = "button";
      start.disabled = this.busy;
      start.addEventListener("click", (event) => {
        event.stopPropagation();
        void this.startDrill(drill);
      });
      foot.append(start);
      card.append(foot);
      card.addEventListener("click", () => {
        if (!this.busy) void this.startDrill(drill);
      });
      card.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        if (!this.busy) void this.startDrill(drill);
      });
      grid.append(card);
    });
    wrap.append(grid);
    return wrap;
  }

  currentQuestion() {
    const questions = this.session?.questions || [];
    return questions[this.index] || null;
  }

  renderQuestion() {
    const question = this.currentQuestion();
    const total = this.session?.questions?.length || 0;
    const wrap = node("div", "practice-run");

    const head = node("header", "practice-run-head");
    const copy = node("div");
    copy.append(
      node("p", "eyebrow", this.t(`drill_${this.drill.id}`)),
      node(
        "strong",
        "",
        this.t("practiceProgress", { current: this.index + 1, total }),
      ),
    );
    const bar = node("div", "practice-progress");
    // Reuses the shared .progress-fill scale: 20 steps of 5% each, driven by a
    // data attribute so no inline styles are needed under the strict CSP.
    const fill = node("span", "progress-fill");
    fill.dataset.progress = String(
      total ? Math.round((this.index / total) * 20) : 0,
    );
    bar.append(fill);
    const quit = node("button", "secondary-button", this.t("practiceQuit"));
    quit.type = "button";
    quit.addEventListener("click", () => {
      this.reset();
      this.render();
    });
    head.append(copy, bar, quit);
    wrap.append(head);

    if (!question) {
      wrap.append(node("p", "muted", this.t("practiceNoQuestions")));
      return wrap;
    }

    const card = node("section", "practice-question card-panel");
    if (question.prompt) {
      card.append(node("p", "practice-prompt", String(question.prompt)));
    }
    const sentence = String(question.sentence || question.audio_text || "");
    if (sentence) {
      card.append(node("strong", "practice-sentence hanzi", sentence));
    }
    if (question.pinyin) {
      card.append(node("span", "pinyin", String(question.pinyin)));
    }
    const audioText = String(question.audio_text || "");
    if (audioText) {
      const listen = node("button", "listen-button", this.t("listen"));
      listen.type = "button";
      listen.addEventListener("click", () => this.speak?.(audioText, listen));
      card.append(listen);
    }

    const options = node("div", "practice-options");
    (question.options || []).forEach((option, optionIndex) => {
      const correct = Number(question.answer_index) === optionIndex;
      let className = "practice-option";
      if (this.checked) {
        if (correct) className += " is-correct";
        else if (optionIndex === this.selected) className += " is-wrong";
      } else if (optionIndex === this.selected) {
        className += " is-selected";
      }
      const button = node("button", className, String(option));
      button.type = "button";
      button.disabled = this.checked;
      button.addEventListener("click", () => {
        this.selected = optionIndex;
        this.render();
      });
      options.append(button);
    });
    card.append(options);

    if (this.checked) {
      const correct = Number(question.answer_index) === this.selected;
      const feedback = node(
        "div",
        `practice-feedback ${correct ? "is-ok" : "is-bad"}`,
      );
      feedback.append(
        node("strong", "", correct ? this.t("answerCorrect") : this.t("answerWrong")),
      );
      if (!correct) {
        feedback.append(
          node(
            "p",
            "",
            `${this.t("correctAnswer")}: ${String(
              (question.options || [])[Number(question.answer_index)] || "",
            )}`,
          ),
        );
      }
      if (question.explanation) {
        feedback.append(node("p", "muted", String(question.explanation)));
      }
      card.append(feedback);
    }

    const action = node(
      "button",
      "primary-button",
      this.checked
        ? this.index + 1 >= total
          ? this.t("practiceFinish")
          : this.t("practiceNext")
        : this.t("practiceCheck"),
    );
    action.type = "button";
    action.disabled = this.busy || (!this.checked && this.selected < 0);
    action.addEventListener("click", () => void this.advance());
    card.append(action);

    if (this.error) card.append(node("p", "form-error", this.error));
    wrap.append(card);
    return wrap;
  }

  renderSummary() {
    const summary = this.summary || {};
    const wrap = node("div", "practice-summary");

    const hero = node("section", "practice-summary-hero card-panel");
    const copy = node("div");
    copy.append(
      node("p", "eyebrow", this.t(`drill_${this.drill?.id || "mock"}`)),
      node("h3", "", this.t("practiceSummaryTitle")),
      node("p", "muted", this.t("practiceSummaryBody")),
    );
    const score = node("div", "practice-score");
    score.append(
      node("strong", "", `${Number(summary.score || 0)} / ${Number(summary.total || 0)}`),
      node("small", "", `${Number(summary.percent || 0)}%`),
    );
    hero.append(copy, score);
    wrap.append(hero);

    const xp = Number(summary?.reward?.xp_awarded ?? summary?.reward?.xp ?? 0);
    if (xp > 0) {
      const reward = node("section", "voice-panel voice-reward");
      reward.append(
        node("strong", "", this.t("voiceXpEarned", { xp })),
        node("small", "muted", this.t("practiceXpBody")),
      );
      wrap.append(reward);
    }

    const wrongItems = Array.isArray(summary.wrong_items) ? summary.wrong_items : [];
    if (wrongItems.length) {
      const list = node("section", "practice-wrong card-panel");
      list.append(node("h3", "voice-section-title", this.t("practiceMistakes")));
      wrongItems.forEach((item) => {
        const row = node("article", "practice-wrong-row");
        row.append(node("strong", "", String(item.question || "")));
        row.append(
          node(
            "p",
            "muted",
            `${this.t("yourAnswer")}: ${String(item.selected_answer || "—")}`,
          ),
        );
        row.append(
          node(
            "p",
            "",
            `${this.t("correctAnswer")}: ${String(item.correct_answer || "")}`,
          ),
        );
        if (item.explanation) {
          row.append(node("small", "muted", String(item.explanation)));
        }
        list.append(row);
      });
      wrap.append(list);
    }

    const actions = node("div", "voice-start-actions");
    const again = node("button", "primary-button", this.t("practiceBackToList"));
    again.type = "button";
    again.addEventListener("click", () => {
      this.reset();
      this.render();
    });
    actions.append(again);
    wrap.append(actions);
    return wrap;
  }

  // ------------------------------------------------------------------ session

  async startDrill(drill) {
    if (this.busy) return;
    this.busy = true;
    this.drill = drill;
    this.error = "";
    this.limitReached = false;
    this.render();
    try {
      const result = await this.bridge.practiceStart({
        mode: drill.mode,
        level: this.level,
        language: this.language,
        skill: drill.skill,
      });
      const session = result?.session;
      if (!session || !Array.isArray(session.questions) || !session.questions.length) {
        throw new Error("practice_questions_not_found");
      }
      this.session = session;
      this.index = 0;
      this.answers = [];
      this.selected = -1;
      this.checked = false;
      this.phase = "running";
    } catch (error) {
      if (this.isSessionError(error)) {
        this.onSessionExpired?.();
        return;
      }
      const code = String(error?.code || error?.message || "");
      if (code === "free_feature_limit_reached") {
        this.limitReached = true;
      } else {
        this.error = this.errorText(error);
      }
      this.drill = null;
    } finally {
      this.busy = false;
      this.render();
    }
  }

  async advance() {
    if (this.busy) return;
    const question = this.currentQuestion();
    if (!question) return;

    if (!this.checked) {
      if (this.selected < 0) return;
      this.checked = true;
      this.answers.push({
        question_id: String(question.id),
        selected: Number(this.selected),
      });
      this.render();
      return;
    }

    const total = this.session?.questions?.length || 0;
    if (this.index + 1 < total) {
      this.index += 1;
      this.selected = -1;
      this.checked = false;
      this.render();
      return;
    }
    await this.finish();
  }

  async finish() {
    this.busy = true;
    this.error = "";
    this.render();
    try {
      const summary = await this.bridge.practiceComplete({
        sessionId: String(this.session?.id || ""),
        mode: this.drill.mode,
        level: this.level,
        language: this.language,
        skill: this.drill.skill,
        answers: this.answers,
      });
      this.summary = summary;
      this.phase = "summary";
      if (Number(summary?.reward?.xp_awarded || 0) > 0) {
        this.onToast?.(this.t("practiceSaved"));
      }
    } catch (error) {
      if (this.isSessionError(error)) {
        this.onSessionExpired?.();
        return;
      }
      this.error = this.errorText(error);
    } finally {
      this.busy = false;
      this.render();
    }
  }
}
