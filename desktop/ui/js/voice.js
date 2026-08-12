/**
 * AI Voice — real speaking practice.
 *
 * The webview records the learner, hands the audio to Rust over IPC, and Rust
 * forwards it to the shared voice-practice backend. Transcription, the reply,
 * corrections, limits and XP all come from the server: nothing here is
 * simulated. The waveform is drawn from a live AnalyserNode rather than from
 * random numbers, so what is on screen is the actual microphone signal.
 *
 * Platform note: Windows WebView2 records `audio/webm;codecs=opus` while macOS
 * WKWebView records `audio/mp4`. Both are negotiated below and both are
 * accepted by the Rust validator and the Python adapter.
 */

const ROLES = [
  { id: "lily", glyph: "友" },
  { id: "chen", glyph: "旅" },
  { id: "xiao_mei", glyph: "学" },
  { id: "teacher_li", glyph: "师" },
  { id: "manager_wang", glyph: "商" },
  { id: "friend", glyph: "伴" },
  { id: "roommate", glyph: "家" },
  { id: "seller", glyph: "买" },
  { id: "classmate", glyph: "同" },
  { id: "social", glyph: "话" },
];

const RECORDER_TYPES = [
  { mime: "audio/webm;codecs=opus", prefix: "data:audio/webm;base64" },
  { mime: "audio/webm", prefix: "data:audio/webm;base64" },
  { mime: "audio/mp4", prefix: "data:audio/mp4;base64" },
  { mime: "audio/ogg;codecs=opus", prefix: "data:audio/ogg;base64" },
  { mime: "audio/ogg", prefix: "data:audio/ogg;base64" },
];

const MAX_AUDIO_BYTES = 5 * 1024 * 1024;
const MAX_RECORDING_MS = 30_000;
const MIN_RECORDING_MS = 700;
const WAVE_BARS = 56;

function node(tag, className = "", text = "") {
  const value = document.createElement(tag);
  if (className) value.className = className;
  if (text !== "") value.textContent = String(text);
  return value;
}

function briefText(value, limit = 220) {
  return [...String(value ?? "").trim()].slice(0, limit).join("");
}

function formatClock(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function supportedRecorder() {
  if (typeof MediaRecorder !== "function") return null;
  for (const candidate of RECORDER_TYPES) {
    try {
      if (MediaRecorder.isTypeSupported(candidate.mime)) return candidate;
    } catch {
      // isTypeSupported can throw on older engines; keep probing.
    }
  }
  // Safari historically reported nothing while still recording audio/mp4.
  return { mime: "", prefix: "data:audio/mp4;base64" };
}

/**
 * Rebuild a strict data URL. A recorder blob type carries codec parameters
 * (`audio/webm;codecs=opus`) that the Rust and Python allowlists reject, so the
 * base64 payload is re-prefixed with the plain container type.
 */
function blobToDataUrl(blob, prefix) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      const separator = raw.indexOf(",");
      const encoded = separator < 0 ? "" : raw.slice(separator + 1);
      if (!encoded) {
        reject(new Error("desktop_voice_audio_invalid"));
        return;
      }
      resolve(`${prefix},${encoded}`);
    };
    reader.onerror = () => reject(new Error("desktop_voice_audio_invalid"));
    reader.readAsDataURL(blob);
  });
}

export class DesktopVoiceController {
  constructor({
    host,
    bridge,
    t,
    language,
    onSessionExpired,
    onToast,
    onOpenSubscription,
    speak,
    onContextChanged,
  }) {
    this.host = host;
    this.bridge = bridge;
    this.t = t;
    this.language = language;
    this.onSessionExpired = onSessionExpired;
    this.onToast = onToast;
    this.onOpenSubscription = onOpenSubscription;
    this.speak = speak;
    this.onContextChanged = onContextChanged;

    this.status = null;
    this.statusError = "";
    this.phase = "idle";
    this.role = "lily";
    this.voice = "female";
    this.level = "hsk1";
    this.sessionId = "";
    this.turns = [];
    this.turnCount = 0;
    this.maxDialogs = 0;
    this.summary = null;
    this.busy = false;
    this.error = "";
    this.showPinyin = true;
    this.showTranslation = true;
    this.seconds = 0;

    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.recorderType = null;
    this.audioContext = null;
    this.analyser = null;
    this.frequencies = null;
    this.bars = new Array(WAVE_BARS).fill(0.04);
    this.canvas = null;
    this.frame = null;
    this.timer = null;
    this.recordingStartedAt = 0;
    this.recordingLimit = null;
    this.launchIssue = "";
  }

  setLanguage(language) {
    this.language = language;
  }

  /** `launchIssue` from `desktop_app_info`: macOS blocks the mic before we ask. */
  setLaunchIssue(issue) {
    this.launchIssue = String(issue || "");
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
    return known === code ? this.t("voiceGenericError") : known;
  }

  async open({ refresh = false } = {}) {
    if (refresh || !this.status) {
      this.statusError = "";
      try {
        this.status = await this.bridge.voiceStatus();
        const level = String(this.status?.level || "").toLowerCase();
        if (level) this.setLevel(level.startsWith("hsk4") ? "hsk4" : level);
      } catch (error) {
        if (this.isSessionError(error)) {
          this.onSessionExpired?.();
          return;
        }
        this.status = null;
        this.statusError = this.errorText(error);
      }
    }
    this.render();
  }

  /** Release the microphone and every timer. Called when the view changes. */
  dispose() {
    this.stopWave();
    this.stopTimer();
    if (this.recordingLimit) {
      clearTimeout(this.recordingLimit);
      this.recordingLimit = null;
    }
    if (this.recorder && this.recorder.state !== "inactive") {
      try {
        this.recorder.stop();
      } catch {
        // Already stopping.
      }
    }
    this.recorder = null;
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.audioContext) {
      void this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    this.analyser = null;
  }

  // ---------------------------------------------------------------- rendering

  render() {
    if (!this.host) return;
    this.host.replaceChildren();
    if (this.phase === "summary" && this.summary) {
      this.host.append(this.renderSummary());
      this.onContextChanged?.();
      return;
    }
    if (this.sessionId) {
      this.host.append(this.renderCall());
      this.attachCanvas();
      this.onContextChanged?.();
      return;
    }
    this.host.append(this.renderIntro());
    this.onContextChanged?.();
  }

  aiContext() {
    const role = this.t(`voiceRole_${this.role}`);
    const phase = this.sessionId ? this.phaseLabel() : this.t("voiceIntroTitle");
    const latest = this.turns.length ? this.turns[this.turns.length - 1] : null;
    const promptLines = [
      `Voice role: ${briefText(role, 80)}`,
      `Voice level: ${briefText(this.level, 40)}`,
      `Voice phase: ${briefText(phase, 80)}`,
      `Voice turns: ${Number(this.turnCount || 0)}/${Number(this.maxDialogs || 0)}`,
    ];
    let latestTurn = "";
    if (latest) {
      const speaker =
        latest.speaker === "user" ? this.t("voiceYou") : this.t(`voiceRole_${this.role}`);
      latestTurn = `${speaker}: ${briefText(latest.text, 140)}`;
      promptLines.push(`Latest visible turn: ${latestTurn}`);
      if (latest.pinyin) promptLines.push(`Latest pinyin: ${briefText(latest.pinyin, 180)}`);
      if (latest.translation) {
        promptLines.push(`Latest translation: ${briefText(latest.translation, 180)}`);
      }
      if (latest.correction) {
        promptLines.push(`Latest correction: ${briefText(latest.correction, 220)}`);
      }
    }
    return {
      title: role,
      summary: `${String(this.level || "hsk1").toUpperCase()} · ${phase}`,
      latestTurn,
      promptLines,
    };
  }

  renderIntro() {
    const wrap = node("div", "voice-intro voice-v3");

    if (this.statusError) {
      const failed = node("section", "voice-panel voice-error-panel");
      failed.append(
        node("h3", "", this.t("voiceStatusFailedTitle")),
        node("p", "muted", this.statusError),
      );
      const retry = node("button", "primary-button", this.t("retry"));
      retry.type = "button";
      retry.addEventListener("click", () => void this.open({ refresh: true }));
      failed.append(retry);
      wrap.append(failed);
      return wrap;
    }

    const remaining = Number(this.status?.remaining_voice_limit ?? 0);
    const isPaid = this.status?.is_paid === true;
    const blocked = !isPaid && remaining <= 0;

    const lead = node("section", "voice-panel voice-lead voice-v3-lead");
    const leadCopy = node("div");
    leadCopy.append(
      node("p", "eyebrow", this.t("voiceEyebrow")),
      node("h3", "", this.t("voiceIntroTitle")),
      node("p", "muted", this.t("voiceIntroBody")),
    );
    const quota = node("div", "voice-quota");
    quota.append(
      node("strong", "", isPaid ? this.t("voiceUnlimited") : String(Math.max(0, remaining))),
      node("small", "", isPaid ? this.t("voicePlanPremium") : this.t("voiceSessionsLeft")),
    );
    lead.append(leadCopy, quota);
    wrap.append(lead);

    if (blocked) {
      const gate = node("section", "voice-panel voice-gate");
      gate.append(
        node("h3", "", this.t("voiceLimitTitle")),
        node("p", "muted", this.t("voiceLimitBody")),
      );
      const cta = node("button", "primary-button", this.t("voiceLimitCta"));
      cta.type = "button";
      cta.addEventListener("click", () => this.onOpenSubscription?.());
      gate.append(cta);
      wrap.append(gate);
      return wrap;
    }

    const picker = node("section", "voice-panel");
    picker.append(node("h3", "voice-section-title", this.t("voiceChooseRole")));
    const grid = node("div", "voice-role-grid");
    ROLES.forEach((role) => {
      const card = node(
        "button",
        `voice-role-card${role.id === this.role ? " is-active" : ""}`,
      );
      card.type = "button";
      card.setAttribute("aria-pressed", role.id === this.role ? "true" : "false");
      card.append(
        node("span", "voice-role-glyph hanzi", role.glyph),
        node("strong", "", this.t(`voiceRole_${role.id}`)),
        node("small", "", this.t(`voiceRoleBody_${role.id}`)),
      );
      card.addEventListener("click", () => {
        this.role = role.id;
        this.render();
      });
      grid.append(card);
    });
    picker.append(grid);
    wrap.append(picker);

    const options = node("section", "voice-panel voice-options");
    const voiceRow = node("div", "voice-option-row");
    voiceRow.append(node("span", "", this.t("voiceVoiceLabel")));
    const voiceGroup = node("div", "voice-choice-group");
    [
      ["female", this.t("voiceFemale")],
      ["male", this.t("voiceMale")],
    ].forEach(([value, label]) => {
      const button = node(
        "button",
        `voice-choice${this.voice === value ? " is-active" : ""}`,
        label,
      );
      button.type = "button";
      button.setAttribute("aria-pressed", this.voice === value ? "true" : "false");
      button.addEventListener("click", () => {
        this.voice = value;
        this.render();
      });
      voiceGroup.append(button);
    });
    voiceRow.append(voiceGroup);
    options.append(voiceRow);
    wrap.append(options);

    const actions = node("div", "voice-start-actions");
    const start = node(
      "button",
      "primary-button",
      this.busy ? this.t("voiceStarting") : this.t("voiceStart"),
    );
    start.type = "button";
    start.disabled = this.busy;
    start.addEventListener("click", () => void this.startSession());
    actions.append(start);
    if (this.error) {
      actions.append(node("p", "form-error", this.error));
    }
    actions.append(node("p", "voice-hint muted", this.t("voiceMicHint")));
    wrap.append(actions);
    return wrap;
  }

  renderCall() {
    const wrap = node("div", "voice-call voice-v3-call");

    const head = node("header", "voice-call-head");
    const identity = node("div", "voice-call-identity");
    identity.append(
      node("span", "voice-role-glyph hanzi", ROLES.find((r) => r.id === this.role)?.glyph || "话"),
      node("div"),
    );
    identity.lastElementChild.append(
      node("strong", "", this.t(`voiceRole_${this.role}`)),
      node("small", "muted", this.phaseLabel()),
    );
    const meters = node("div", "voice-call-meters");
    meters.append(
      node("span", "voice-clock", formatClock(this.seconds)),
      node(
        "span",
        "voice-turns",
        this.t("voiceTurnCounter", {
          current: this.turnCount,
          total: this.maxDialogs || 0,
        }),
      ),
    );
    const hangup = node("button", "secondary-button", this.t("voiceFinish"));
    hangup.type = "button";
    hangup.disabled = this.busy && this.phase === "processing";
    hangup.addEventListener("click", () => void this.endSession());
    head.append(identity, meters, hangup);
    wrap.append(head);

    const stage = node("section", "voice-panel voice-stage-live voice-v3-stage");
    this.canvas = document.createElement("canvas");
    this.canvas.className = "voice-wave";
    this.canvas.width = 960;
    this.canvas.height = 132;
    this.canvas.setAttribute("aria-hidden", "true");
    stage.append(this.canvas);

    const micRow = node("div", "voice-mic-row");
    const mic = node(
      "button",
      `voice-mic${this.phase === "recording" ? " is-recording" : ""}`,
    );
    mic.type = "button";
    mic.disabled = this.busy || this.phase === "processing";
    mic.setAttribute(
      "aria-label",
      this.phase === "recording" ? this.t("voiceStopRecording") : this.t("voiceStartRecording"),
    );
    mic.append(node("span", "voice-mic-dot", ""));
    mic.addEventListener("click", () => void this.toggleRecording());
    const micCopy = node("div", "voice-mic-copy");
    micCopy.append(
      node("strong", "", this.micTitle()),
      node("small", "muted", this.micBody()),
    );
    micRow.append(mic, micCopy);
    stage.append(micRow);
    if (this.error) {
      stage.append(node("p", "form-error", this.error));
    }
    wrap.append(stage);

    const toggles = node("div", "voice-toggles");
    [
      ["showPinyin", this.t("voicePinyin")],
      ["showTranslation", this.t("voiceTranslation")],
    ].forEach(([field, label]) => {
      const button = node(
        "button",
        `voice-choice${this[field] ? " is-active" : ""}`,
        label,
      );
      button.type = "button";
      button.setAttribute("aria-pressed", this[field] ? "true" : "false");
      button.addEventListener("click", () => {
        this[field] = !this[field];
        this.render();
      });
      toggles.append(button);
    });
    wrap.append(toggles);

    wrap.append(this.renderTranscript());
    return wrap;
  }

  renderTranscript() {
    const list = node("section", "voice-panel voice-transcript");
    list.append(node("h3", "voice-section-title", this.t("voiceTranscript")));
    if (!this.turns.length) {
      list.append(node("p", "muted", this.t("voiceTranscriptEmpty")));
      return list;
    }
    this.turns.forEach((turn) => {
      const row = node("article", `voice-turn voice-turn-${turn.speaker}`);
      if (turn.speaker === "user") {
        row.append(node("small", "voice-turn-label", this.t("voiceYou")));
        row.append(node("strong", "hanzi", turn.text));
        if (turn.correction) {
          const fix = node("div", "voice-correction");
          fix.append(
            node("small", "", this.t("voiceCorrection")),
            node("p", "", turn.correction),
          );
          row.append(fix);
        } else {
          row.append(node("small", "voice-good", this.t("voiceNoMistake")));
        }
      } else {
        row.append(
          node("small", "voice-turn-label", this.t(`voiceRole_${this.role}`)),
        );
        row.append(node("strong", "hanzi", turn.text));
        if (this.showPinyin && turn.pinyin) {
          row.append(node("span", "pinyin", turn.pinyin));
        }
        if (this.showTranslation && turn.translation) {
          row.append(node("p", "translation", turn.translation));
        }
        const listen = node("button", "listen-button", this.t("listen"));
        listen.type = "button";
        listen.addEventListener("click", () => this.speak?.(turn.text, listen));
        row.append(listen);
      }
      list.append(row);
    });
    return list;
  }

  renderSummary() {
    const summary = this.summary || {};
    const wrap = node("div", "voice-summary");

    const hero = node("section", "voice-panel voice-summary-hero");
    const copy = node("div");
    copy.append(
      node("p", "eyebrow", this.t("voiceEyebrow")),
      node("h3", "", this.t("voiceSummaryTitle")),
      node("p", "muted", this.t("voiceSummaryBody")),
    );
    const xp = Number(summary?.reward?.xp_awarded ?? summary?.reward?.xp ?? 0);
    const stats = node("div", "voice-summary-stats");
    [
      [this.t("voiceStatTurns"), Number(summary.message_count || 0)],
      [this.t("voiceStatDuration"), formatClock(Number(summary.duration_seconds || 0))],
      [this.t("voiceStatGood"), Number(summary.good_count || 0)],
      [this.t("voiceStatMistakes"), Number(summary.mistake_count || 0)],
    ].forEach(([label, value]) => {
      const card = node("article");
      card.append(node("small", "", label), node("strong", "", value));
      stats.append(card);
    });
    hero.append(copy, stats);
    wrap.append(hero);

    if (xp > 0) {
      const reward = node("section", "voice-panel voice-reward");
      reward.append(
        node("strong", "", this.t("voiceXpEarned", { xp })),
        node("small", "muted", this.t("voiceXpBody")),
      );
      wrap.append(reward);
    }

    const transcript = Array.isArray(summary.transcript) ? summary.transcript : [];
    if (transcript.length) {
      const list = node("section", "voice-panel voice-transcript");
      list.append(node("h3", "voice-section-title", this.t("voiceTranscript")));
      transcript.forEach((entry) => {
        const row = node(
          "article",
          `voice-turn voice-turn-user${entry.good ? " is-good" : " is-mistake"}`,
        );
        row.append(node("small", "voice-turn-label", this.t("voiceYou")));
        row.append(node("strong", "hanzi", String(entry.user || "")));
        if (entry.correction) {
          const fix = node("div", "voice-correction");
          fix.append(
            node("small", "", this.t("voiceCorrection")),
            node("p", "", String(entry.correction)),
          );
          row.append(fix);
        } else {
          row.append(node("small", "voice-good", this.t("voiceNoMistake")));
        }
        list.append(row);
      });
      wrap.append(list);
    }

    const actions = node("div", "voice-start-actions");
    const again = node("button", "primary-button", this.t("voiceStartAnother"));
    again.type = "button";
    again.addEventListener("click", () => {
      this.summary = null;
      this.phase = "idle";
      this.turns = [];
      this.turnCount = 0;
      this.seconds = 0;
      this.error = "";
      void this.open({ refresh: true });
    });
    actions.append(again);
    wrap.append(actions);
    return wrap;
  }

  phaseLabel() {
    if (this.phase === "recording") return this.t("voicePhaseRecording");
    if (this.phase === "processing") return this.t("voicePhaseProcessing");
    return this.t("voicePhaseReady");
  }

  micTitle() {
    if (this.phase === "recording") return this.t("voiceStopRecording");
    if (this.phase === "processing") return this.t("voicePhaseProcessing");
    return this.t("voiceStartRecording");
  }

  micBody() {
    if (this.phase === "recording") return this.t("voiceRecordingBody");
    if (this.phase === "processing") return this.t("voiceProcessingBody");
    return this.t("voiceReadyBody2");
  }

  // ------------------------------------------------------------------- session

  async startSession() {
    if (this.busy) return;
    this.busy = true;
    this.error = "";
    this.render();
    try {
      const result = await this.bridge.voiceSessionStart({
        role: this.role,
        level: this.level,
        language: this.language,
        voice: this.voice,
      });
      this.sessionId = String(result?.session_id || "");
      this.maxDialogs = Number(result?.max_dialogs || 0);
      this.turnCount = 0;
      this.turns = [];
      this.seconds = 0;
      const opening = result?.opening_message;
      if (opening?.chinese_reply) {
        this.turns.push({
          speaker: "ai",
          text: String(opening.chinese_reply),
          pinyin: String(opening.pinyin || ""),
          translation: String(opening.translation || ""),
        });
      }
      this.phase = "listening";
      this.startTimer();
      this.render();
      if (opening?.chinese_reply) {
        this.speak?.(String(opening.chinese_reply));
      }
    } catch (error) {
      if (this.isSessionError(error)) {
        this.onSessionExpired?.();
        return;
      }
      this.error = this.errorText(error);
      this.render();
    } finally {
      this.busy = false;
      if (this.sessionId) this.render();
    }
  }

  async toggleRecording() {
    if (this.phase === "recording") {
      this.stopRecording();
      return;
    }
    await this.startRecording();
  }

  async startRecording() {
    if (this.busy || this.phase === "processing") return;
    this.error = "";
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("desktop_voice_mic_unavailable");
      }
      if (!this.stream) {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      this.recorderType = this.recorderType || supportedRecorder();
      if (!this.recorderType) throw new Error("desktop_voice_recorder_unavailable");

      this.chunks = [];
      this.recorder = this.recorderType.mime
        ? new MediaRecorder(this.stream, { mimeType: this.recorderType.mime })
        : new MediaRecorder(this.stream);
      this.recorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) this.chunks.push(event.data);
      });
      this.recorder.addEventListener("stop", () => void this.submitRecording());
      this.recorder.start();
      this.recordingStartedAt = Date.now();
      this.phase = "recording";
      this.startWave();
      this.recordingLimit = setTimeout(() => this.stopRecording(), MAX_RECORDING_MS);
      this.render();
      this.attachCanvas();
    } catch (error) {
      // A denied microphone prompt reaches here on both macOS and Windows.
      // On macOS the same rejection also arrives when the OS never asked at
      // all, because a translocated bundle cannot hold a TCC permission. That
      // learner must move the app, not open Privacy & Security, so the two
      // cases need different instructions.
      const denied =
        error?.name === "NotAllowedError" || error?.name === "SecurityError";
      const blockedByLaunch =
        this.launchIssue === "translocated" ||
        this.launchIssue === "read_only_volume";
      const code = denied
        ? blockedByLaunch
          ? "desktop_voice_mic_translocated"
          : "desktop_voice_mic_denied"
        : error?.name === "NotFoundError"
          ? "desktop_voice_mic_unavailable"
          : String(error?.message || "desktop_voice_mic_unavailable");
      this.error = this.errorText({ code });
      this.phase = "listening";
      this.stopWave();
      this.render();
    }
  }

  stopRecording() {
    if (this.recordingLimit) {
      clearTimeout(this.recordingLimit);
      this.recordingLimit = null;
    }
    if (!this.recorder || this.recorder.state === "inactive") return;
    try {
      this.recorder.stop();
    } catch {
      this.phase = "listening";
      this.stopWave();
      this.render();
    }
  }

  async submitRecording() {
    this.stopWave();
    const elapsed = Date.now() - this.recordingStartedAt;
    const blob = new Blob(this.chunks, {
      type: this.recorderType?.mime || "audio/mp4",
    });
    this.chunks = [];

    if (elapsed < MIN_RECORDING_MS || blob.size <= 0) {
      this.phase = "listening";
      this.error = this.errorText({ code: "desktop_voice_too_short" });
      this.render();
      return;
    }
    if (blob.size > MAX_AUDIO_BYTES) {
      this.phase = "listening";
      this.error = this.errorText({ code: "desktop_voice_audio_too_large" });
      this.render();
      return;
    }

    this.phase = "processing";
    this.busy = true;
    this.render();
    try {
      const audioDataUrl = await blobToDataUrl(blob, this.recorderType.prefix);
      const result = await this.bridge.voiceMessage({
        sessionId: this.sessionId,
        audioDataUrl,
      });
      this.turns.push({
        speaker: "user",
        text: String(result?.transcription || ""),
        correction: result?.correction ? String(result.correction) : "",
      });
      this.turns.push({
        speaker: "ai",
        text: String(result?.chinese_reply || ""),
        pinyin: String(result?.pinyin || ""),
        translation: String(result?.translation || ""),
      });
      this.turnCount = Number(result?.turn_count || this.turnCount + 1);
      this.maxDialogs = Number(result?.max_dialogs || this.maxDialogs);
      if (result?.budget_notice) {
        this.onToast?.(this.t("voiceBudgetNotice"));
      }
      this.phase = "listening";
      this.busy = false;
      this.render();
      if (result?.chinese_reply) {
        this.speak?.(String(result.chinese_reply));
      }
      if (result?.session_should_end === true) {
        await this.endSession();
      }
    } catch (error) {
      this.busy = false;
      if (this.isSessionError(error)) {
        this.onSessionExpired?.();
        return;
      }
      this.phase = "listening";
      this.error = this.errorText(error);
      this.render();
    }
  }

  async endSession() {
    if (!this.sessionId) return;
    const sessionId = this.sessionId;
    this.busy = true;
    this.render();
    try {
      const result = await this.bridge.voiceSessionEnd(sessionId);
      this.summary = result;
      this.phase = "summary";
    } catch (error) {
      if (this.isSessionError(error)) {
        this.onSessionExpired?.();
        return;
      }
      this.error = this.errorText(error);
      this.phase = "idle";
    } finally {
      this.busy = false;
      this.sessionId = "";
      this.stopTimer();
      this.dispose();
      this.render();
    }
  }

  // --------------------------------------------------------------------- timer

  startTimer() {
    this.stopTimer();
    this.timer = setInterval(() => {
      this.seconds += 1;
      const clock = this.host?.querySelector(".voice-clock");
      if (clock) clock.textContent = formatClock(this.seconds);
    }, 1000);
  }

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  // ------------------------------------------------------------------ waveform

  attachCanvas() {
    this.canvas = this.host?.querySelector(".voice-wave") || this.canvas;
    this.drawWave();
  }

  startWave() {
    try {
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextCtor || !this.stream) return;
      if (!this.audioContext) {
        this.audioContext = new AudioContextCtor();
      }
      if (this.audioContext.state === "suspended") {
        void this.audioContext.resume().catch(() => {});
      }
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      this.analyser.smoothingTimeConstant = 0.75;
      source.connect(this.analyser);
      this.frequencies = new Uint8Array(this.analyser.frequencyBinCount);
      this.loopWave();
    } catch {
      // Without an analyser the bars simply stay flat; recording still works.
      this.analyser = null;
    }
  }

  stopWave() {
    if (this.frame) {
      cancelAnimationFrame(this.frame);
      this.frame = null;
    }
    this.analyser = null;
    this.bars = new Array(WAVE_BARS).fill(0.04);
    this.drawWave();
  }

  loopWave() {
    if (this.frame) cancelAnimationFrame(this.frame);
    const step = () => {
      if (!this.analyser || !this.frequencies) return;
      this.analyser.getByteFrequencyData(this.frequencies);
      let sum = 0;
      for (let i = 0; i < this.frequencies.length; i += 1) {
        sum += this.frequencies[i];
      }
      const level = Math.min(1, sum / this.frequencies.length / 140);
      for (let i = this.bars.length - 1; i > 0; i -= 1) {
        this.bars[i] = this.bars[i - 1];
      }
      this.bars[0] = Math.max(0.04, level);
      this.drawWave();
      this.frame = requestAnimationFrame(step);
    };
    this.frame = requestAnimationFrame(step);
  }

  drawWave() {
    const canvas = this.canvas;
    if (!canvas || typeof canvas.getContext !== "function") return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const width = canvas.width;
    const height = canvas.height;
    const middle = height / 2;
    context.clearRect(0, 0, width, height);
    const recording = this.phase === "recording";
    const styles = getComputedStyle(document.documentElement);
    const accent = (styles.getPropertyValue("--red") || "#E04A40").trim();
    const idle = (styles.getPropertyValue("--line2") || "#D8C9AC").trim();
    context.fillStyle = recording ? accent : idle;
    const barWidth = width / this.bars.length;
    for (let i = 0; i < this.bars.length; i += 1) {
      const value = this.bars[i];
      const barHeight = Math.max(3, value * (height - 12));
      const x = i * barWidth;
      context.fillRect(
        x + barWidth * 0.25,
        middle - barHeight / 2,
        Math.max(2, barWidth * 0.5),
        barHeight,
      );
    }
  }
}
