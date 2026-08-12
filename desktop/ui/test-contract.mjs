import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { previewInvoke } from "./js/preview-mock.js";
import { SUPPORTED_CARD_TYPES } from "./js/lesson.js";

const uiRoot = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.dirname(uiRoot);
const projectRoot = path.dirname(desktopRoot);
const lessonRoot = path.join(
  projectRoot,
  "app",
  "static",
  "course_v3_data",
);

const expectedCommands = [
  "desktop_app_info",
  "desktop_auth_status",
  "desktop_link_start",
  "desktop_link_poll",
  "desktop_link_open_telegram",
  "desktop_open_external_url",
  "desktop_bootstrap",
  "desktop_logout",
  "desktop_course_map",
  "desktop_lesson_data",
  "desktop_lesson_complete",
  "desktop_set_language",
  "desktop_subscription_overview",
  "desktop_subscription_quote",
  "desktop_subscription_submit",
  "desktop_vocabulary_state",
  "desktop_vocabulary_save",
  "desktop_referral_overview",
  "desktop_goal_state",
  "desktop_goal_save",
  "desktop_practice_start",
  "desktop_practice_complete",
  "desktop_rating_leaderboard",
  "desktop_voice_status",
  "desktop_voice_session_start",
  "desktop_voice_message",
  "desktop_voice_pronounce",
  "desktop_voice_session_end",
  "desktop_tts_speak",
  "local_ai_model_status",
  "local_ai_install_start",
  "local_ai_install_cancel",
  "local_ai_pack_remove",
  "local_ai_chat",
  "local_ai_chat_cancel",
  "desktop_update_check",
  "desktop_update_install",
];

const supportedCardTypes = new Set(SUPPORTED_CARD_TYPES);

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), "utf8");
}

test("desktop entry is strict-CSP compatible", async () => {
  const html = await source("desktop/ui/index.html");
  const appCss = await source("desktop/ui/css/app.css");
  const workspaceCss = await source("desktop/ui/css/workspace.css");
  const javascript = await Promise.all(
    [
      "app.js",
      "bridge.js",
      "i18n.js",
      "lesson.js",
      "mascot.js",
      "preview-mock.js",
      "subscription.js",
      "practice.js",
      "vocabulary.js",
      "voice.js",
    ].map((file) => source(`desktop/ui/js/${file}`)),
  );
  assert.match(html, /<script type="module" src="\.\/js\/app\.js"><\/script>/);
  assert.doesNotMatch(html, /\son[a-z]+\s*=/i);
  assert.doesNotMatch(html, /\sstyle\s*=/i);
  assert.doesNotMatch(html, /<script(?![^>]*\ssrc=)[^>]*>/i);
  assert.match(html, /src="\.\/assets\/hsk-ai-avatar\.webp"/);
  assert.match(html, />老师 AI</);
  assert.doesNotMatch(html, /panda-real\.webp/);
  assert.match(appCss, /\.panda-mascot \{/);
  assert.doesNotMatch(html, /class="(?:brand-mark|panda-badge|panda-mini)"[^>]*>[汉阿]</);
  assert.match(workspaceCss, /\.rail-action \.rail-icon[\s\S]*fill: none;[\s\S]*stroke: currentColor;/);
  for (const content of javascript) {
    assert.doesNotMatch(content, /\.style\./);
    assert.doesNotMatch(content, /\b(fetch|XMLHttpRequest|WebSocket)\b/);
    assert.doesNotMatch(content, /panda-real\.webp/);
  }
});

test("Tauri loads the dedicated UI with IPC-only network CSP", async () => {
  const config = JSON.parse(
    await source("desktop/src-tauri/tauri.conf.json"),
  );
  assert.equal(config.productName, "HSK AI");
  assert.equal(config.identifier, "com.pomp.hskai");
  assert.equal(config.build.frontendDist, "../ui");
  assert.ok(config.bundle.icon.includes("icons/icon.icns"));
  assert.ok(config.bundle.icon.includes("icons/icon.ico"));
  assert.match(
    config.app.security.csp,
    /img-src 'self' data: https:\/\/telegram-chinese-bot-production\.up\.railway\.app/,
  );
  assert.match(config.app.security.csp, /connect-src ipc: http:\/\/ipc\.localhost/);
  assert.doesNotMatch(config.app.security.csp, /unsafe-inline/);
});

test("frontend bridge and Rust expose the same named commands", async () => {
  const bridge = await source("desktop/ui/js/bridge.js");
  const rust = await source("desktop/src-tauri/src/lib.rs");
  for (const command of expectedCommands) {
    assert.match(bridge, new RegExp(`"${command}"`));
    assert.match(rust, new RegExp(`\\b${command}\\b`));
  }
});

test("preview responses follow production response casing", async () => {
  const bootstrap = await previewInvoke("desktop_bootstrap");
  assert.equal(bootstrap.user.level, "hsk1");
  assert.equal(typeof bootstrap.user.is_paid, "boolean");
  assert.equal(typeof bootstrap.user.access_state, "string");

  const map = await previewInvoke("desktop_course_map");
  assert.equal(map.level, "hsk1");
  assert.equal(typeof map.units[0].no, "number");
  assert.equal(typeof map.progress.completed, "number");
  assert.equal(typeof map.notify.enabled, "boolean");
  assert.ok(Array.isArray(map.notifications));
  assert.equal(typeof map.notifications[0].title, "string");

  const lesson = await previewInvoke("desktop_lesson_data", {
    lessonOrder: 2,
  });
  assert.equal(lesson.lesson_order, 2);
  assert.equal(typeof lesson.preview_half, "boolean");
  assert.ok(Array.isArray(lesson.lesson.sections));

  const completion = await previewInvoke("desktop_lesson_complete", {
    lessonOrder: 2,
  });
  assert.equal(completion.completed_lesson, 2);
  assert.equal(typeof completion.gamification.awarded_xp, "number");

  const update = await previewInvoke("desktop_update_check");
  assert.equal(typeof update.available, "boolean");
  assert.equal(typeof update.currentVersion, "string");

  const overview = await previewInvoke("desktop_subscription_overview");
  assert.equal(overview.source, "desktop_subscription");
  assert.equal(overview.mode, "subscription");
  assert.equal(overview.access.state, "free");
  assert.equal(typeof overview.prices.visa["1_month"].final_amount, "number");

  const quote = await previewInvoke("desktop_subscription_quote", {
    plan: "1_month",
    method: "alipay",
    country: null,
  });
  assert.equal(quote.quote.plan_type, "1_month");
  assert.equal(quote.quote.payment_method, "alipay");
  assert.match(quote.quote.qr.image_data_url, /^data:image\/png;base64,/);

  const submitted = await previewInvoke("desktop_subscription_submit", {
    plan: "1_month",
    method: "alipay",
    country: null,
    screenshotDataUrl: quote.quote.qr.image_data_url,
    attemptId: overview.attempt_id,
  });
  assert.equal(submitted.status, "pending");
  const pending = await previewInvoke("desktop_subscription_overview");
  assert.equal(pending.pending_payment.plan_type, "1_month");
});

test("updater checks automatically but installs only after a user action", async () => {
  const app = await source("desktop/ui/js/app.js");
  const bridge = await source("desktop/ui/js/bridge.js");
  const rust = await source("desktop/src-tauri/src/lib.rs");
  assert.match(app, /void checkForUpdates\(\)/);
  assert.match(app, /lesson\.isOpen[\s\S]*state\.aiBusy[\s\S]*state\.aiInstallBusy/);
  assert.match(app, /dom\.updateAction\.addEventListener\("click", handleUpdateAction\)/);
  assert.match(app, /desktopBridge\.updateInstall\(\)/);
  assert.match(app, /desktop-update:\/\/progress/);
  assert.match(bridge, /listenDesktopUpdate/);
  assert.match(rust, /download_and_install[\s\S]*emit_update_progress/);
  assert.doesNotMatch(app, /scheduleAutomaticUpdate/);
  assert.doesNotMatch(app, /installUpdate\(\{ automatic: true \}\)/);
  assert.doesNotMatch(app, /setInterval\([^)]*installUpdate/);
});

test("local AI is explicit, bounded and never replaced with preview answers", async () => {
  const bridge = await source("desktop/ui/js/bridge.js");
  const app = await source("desktop/ui/js/app.js");
  const lesson = await source("desktop/ui/js/lesson.js");
  const practice = await source("desktop/ui/js/practice.js");
  const vocabulary = await source("desktop/ui/js/vocabulary.js");
  const voice = await source("desktop/ui/js/voice.js");
  const preview = await source("desktop/ui/js/preview-mock.js");
  assert.match(bridge, /MAX_LOCAL_AI_PROMPT_CHARS = 4_000/);
  assert.match(bridge, /MAX_LOCAL_AI_HISTORY_MESSAGES = 12/);
  assert.match(app, /desktopBridge\.localAiInstallStart\(\)/);
  assert.match(app, /desktopBridge\.localAiChat\(/);
  assert.match(app, /function buildAiScreenContext\(\)/);
  assert.match(app, /function renderAiContextCard\(context\)/);
  assert.match(app, /function renderAiHintStrip\(context\)/);
  assert.match(app, /localAiPromptWithScreenContext\(prompt\)/);
  assert.match(app, /Do not claim access to anything outside this app window/);
  assert.match(app, /Do not reveal lesson, quiz, or practice answer keys/);
  assert.match(lesson, /aiContext\(\)/);
  assert.doesNotMatch(lesson, /promptLines\.push\(`Correct/);
  assert.match(practice, /aiContext\(\)/);
  assert.doesNotMatch(practice, /promptLines\.push\([\s\S]{0,180}correct_answer/);
  assert.match(vocabulary, /aiContext\(\)/);
  assert.match(voice, /aiContext\(\)/);
  assert.match(app, /local-ai:\/\/chat-delta/);
  assert.match(app, /function resetAiSession\(\)/);
  assert.match(app, /state\.aiMessages = \[\];/);
  assert.match(app, /function showAuth[\s\S]{0,350}resetAiSession\(\)/);
  assert.match(preview, /case "local_ai_chat":/);
  assert.match(preview, /throw new Error\("local_ai_runtime_missing"\)/);
  assert.doesNotMatch(preview, /case "local_ai_chat":[\s\S]{0,300}text:/);
});

test("local AI drawer renders polished answers without leaking reasoning", async () => {
  const app = await source("desktop/ui/js/app.js");
  const css = await source("desktop/ui/css/workspace.css");

  assert.match(app, /function cleanAiContent\(/);
  assert.match(app, /<think>\[\\s\\S\]\*\?\(\?:<\\\/think>\|\$\)/);
  assert.match(app, /function renderAiFormattedAnswer\(/);
  assert.match(app, /function appendInlineAiText\(/);
  assert.match(app, /function appendAiTable\(/);
  assert.match(app, /renderAiFormattedAnswer\(message\.content/);
  assert.match(app, /Do not include hidden reasoning, <think> tags/);
  assert.doesNotMatch(app, /innerHTML|insertAdjacentHTML|outerHTML/);

  assert.match(css, /\.ai-answer-section \{/);
  assert.match(css, /\.ai-ready-card \{[\s\S]*background: transparent;/);
  assert.match(css, /\.ai-chat-intro \{[\s\S]*background: transparent;/);
  assert.match(css, /\.ai-message\.is-assistant \.ai-message-text \{[\s\S]*background: transparent;/);
  assert.match(css, /\.ai-answer-section \{[\s\S]*border: 0;/);
  assert.match(css, /\.ai-answer-list \{/);
  assert.match(css, /\.ai-table-wrap \{/);
  assert.match(css, /\.ai-code-block \{/);
  assert.match(css, /\.ai-pack-manage summary::after/);
  assert.match(css, /--drawer-width: 500px;/);
});

test("local AI composer supports media controls without hidden network egress", async () => {
  const html = await source("desktop/ui/index.html");
  const app = await source("desktop/ui/js/app.js");
  const css = await source("desktop/ui/css/workspace.css");

  assert.match(html, /id="ai-file-input"[\s\S]*accept="image\/\*,audio\/\*"/);
  assert.match(html, /id="ai-attach"/);
  assert.match(html, /id="ai-record"/);
  assert.match(html, /id="ai-emoji"/);
  assert.match(app, /const AI_MAX_ATTACHMENTS = 4/);
  assert.match(app, /function addAiFiles\(/);
  assert.match(app, /function startAiRecording\(/);
  assert.match(app, /new MediaRecorder/);
  assert.match(app, /function handleAiMediaBlockedSend\(/);
  assert.doesNotMatch(app, /desktopBridge\.desktopAiMedia|desktop_ai_media/);
  assert.match(css, /\.ai-compose-field \{/);
  assert.match(css, /\.ai-compose-button \{/);
  assert.match(css, /\.ai-attachment-chip \{/);
  assert.match(css, /\.ai-send-button \{/);
});

test("renderer covers every checked-in Course v3 card type", async () => {
  const levels = (await readdir(lessonRoot, { withFileTypes: true })).filter(
    (entry) => entry.isDirectory() && /^hsk[1-4]$/.test(entry.name),
  );
  const discovered = new Set();

  for (const level of levels) {
    const files = (await readdir(path.join(lessonRoot, level.name))).filter(
      (name) => /^lesson_\d+\.json$/.test(name),
    );
    for (const file of files) {
      const payload = JSON.parse(
        await readFile(path.join(lessonRoot, level.name, file), "utf8"),
      );
      for (const section of payload.sections || []) {
        for (const card of section.cards || []) {
          if (card?.type) {
            discovered.add(String(card.type));
          }
        }
      }
    }
  }

  assert.deepEqual(
    [...discovered].sort(),
    [...supportedCardTypes].sort(),
    "A new Course v3 card type needs an explicit desktop renderer",
  );
});

test("AI Voice speaks to the shared voice-practice backend", async () => {
  const status = await previewInvoke("desktop_voice_status");
  assert.equal(typeof status.is_paid, "boolean");
  assert.equal(typeof status.remaining_voice_limit, "number");
  assert.equal(typeof status.level, "string");

  const started = await previewInvoke("desktop_voice_session_start", {
    role: "lily",
    level: "hsk2",
    language: "uz",
    voice: "female",
  });
  assert.equal(typeof started.session_id, "string");
  assert.ok(started.session_id.length >= 8);
  assert.equal(typeof started.max_dialogs, "number");
  assert.equal(typeof started.opening_message.chinese_reply, "string");
  // The server sends one already-translated string, never a language map.
  assert.equal(typeof started.opening_message.translation, "string");

  const turn = await previewInvoke("desktop_voice_message", {
    sessionId: started.session_id,
    audioDataUrl: "data:audio/webm;base64,GkXfow==",
  });
  assert.equal(typeof turn.transcription, "string");
  assert.equal(typeof turn.chinese_reply, "string");
  assert.equal(typeof turn.translation, "string");
  assert.equal(typeof turn.turn_count, "number");
  assert.equal(typeof turn.session_should_end, "boolean");
  // A correction is either a string or null; the UI branches on exactly that.
  assert.ok(turn.correction === null || typeof turn.correction === "string");

  const ended = await previewInvoke("desktop_voice_session_end", {
    sessionId: started.session_id,
  });
  assert.equal(ended.ok, true);
  assert.equal(typeof ended.duration_seconds, "number");
  assert.equal(typeof ended.good_count, "number");
  assert.equal(typeof ended.mistake_count, "number");
  assert.ok(Array.isArray(ended.transcript));
  assert.equal(typeof ended.transcript[0].good, "boolean");

  await assert.rejects(
    () => previewInvoke("desktop_voice_message", { sessionId: "preview-gone-0001" }),
    /SESSION_NOT_FOUND/,
  );
});

test("AI Voice records on both macOS and Windows webviews", async () => {
  const voice = await source("desktop/ui/js/voice.js");
  const bridge = await source("desktop/ui/js/bridge.js");
  const rust = await source("desktop/src-tauri/src/lib.rs");
  const adapter = await source("app/api/desktop_voice.py");

  // WKWebView records audio/mp4, WebView2 records audio/webm. Losing either
  // container silently breaks AI Voice on one of the two desktop builds.
  for (const container of ["audio/webm", "audio/mp4"]) {
    assert.match(voice, new RegExp(container.replace("/", "\\/")));
    assert.match(bridge, new RegExp(`data:${container.replace("/", "\\/")};base64`));
    assert.match(rust, new RegExp(`data:${container.replace("/", "\\/")};base64`));
    assert.match(adapter, new RegExp(`data:${container.replace("/", "\\/")};base64`));
  }

  // Audio travels over IPC as a data URL; the webview never opens a socket.
  assert.doesNotMatch(voice, /\b(fetch|XMLHttpRequest|WebSocket)\b/);
  assert.match(voice, /getUserMedia/);
  assert.match(voice, /MediaRecorder/);
  // Leaving the screen must release the capture on both platforms.
  assert.match(voice, /dispose\(\)/);
  assert.match(voice, /getTracks\(\)\.forEach\(\(track\) => track\.stop\(\)\)/);
});

test("macOS declares a microphone purpose string", async () => {
  const plist = await source("desktop/src-tauri/Info.plist");
  // Without this key macOS terminates the app on the first getUserMedia call.
  assert.match(plist, /<key>NSMicrophoneUsageDescription<\/key>/);
  assert.match(plist, /<string>[^<]{10,}<\/string>/);
});

test("every AI Voice string exists in Uzbek, Russian and Tajik", async () => {
  const i18n = await source("desktop/ui/js/i18n.js");
  const blocks = {};
  for (const language of ["uz", "ru", "tj"]) {
    const opener = `\n  ${language}: {\n`;
    const start = i18n.indexOf(opener) + opener.length;
    const end = i18n.indexOf("\n  },", start);
    blocks[language] = new Set(
      [...i18n.slice(start, end).matchAll(/^ {4}([A-Za-z_][A-Za-z0-9_]*):/gm)].map(
        (match) => match[1],
      ),
    );
  }
  for (const language of ["ru", "tj"]) {
    assert.deepEqual(
      [...blocks.uz].filter((key) => !blocks[language].has(key)),
      [],
      `Keys missing from ${language}`,
    );
    assert.deepEqual(
      [...blocks[language]].filter((key) => !blocks.uz.has(key)),
      [],
      `Keys missing from uz that ${language} defines`,
    );
  }

  // Every key AI Voice asks for must resolve, including the role templates.
  const voice = await source("desktop/ui/js/voice.js");
  const referenced = new Set(
    [...voice.matchAll(/this\.t\("([A-Za-z_][A-Za-z0-9_]*)"/g)].map((m) => m[1]),
  );
  for (const role of [...voice.matchAll(/\{ id: "([a-z_]+)", glyph:/g)].map(
    (m) => m[1],
  )) {
    referenced.add(`voiceRole_${role}`);
    referenced.add(`voiceRoleBody_${role}`);
  }
  assert.deepEqual(
    [...referenced].filter((key) => !blocks.uz.has(key)),
    [],
    "AI Voice references an undefined translation key",
  );
});

test("the weekly league comes from the shared gamification service", async () => {
  const board = await previewInvoke("desktop_rating_leaderboard", {
    timezoneOffset: 300,
  });
  assert.equal(typeof board.rank, "number");
  assert.equal(typeof board.league, "string");
  assert.equal(typeof board.league_size, "number");
  assert.ok(Array.isArray(board.leaderboard));
  const current = board.leaderboard.filter((entry) => entry.is_current_user);
  assert.equal(current.length, 1, "exactly one row is the signed-in learner");
  assert.equal(current[0].rank, board.rank);

  const adapter = await source("app/api/desktop_rating.py");
  // The league must not be reimplemented for desktop.
  assert.match(adapter, /CourseGamificationService/);
  assert.match(adapter, /\.leaderboard\(/);
  // Telegram IDs are personal data the desktop UI never renders.
  assert.doesNotMatch(adapter, /"telegram_id"/);
  for (const entry of board.leaderboard) {
    assert.equal(entry.telegram_id, undefined);
  }
});

test("practice drills are graded by the shared course service", async () => {
  const started = await previewInvoke("desktop_practice_start", {
    mode: "training",
    level: "hsk1",
    language: "uz",
    skill: "characters",
  });
  assert.equal(started.ok, true);
  assert.ok(started.session.id.length >= 8);
  assert.ok(started.session.questions.length > 0);
  const [question] = started.session.questions;
  assert.equal(typeof question.id, "string");
  assert.ok(Array.isArray(question.options));
  assert.equal(typeof question.answer_index, "number");

  const summary = await previewInvoke("desktop_practice_complete", {
    sessionId: started.session.id,
    mode: "training",
    level: "hsk1",
    language: "uz",
    skill: "characters",
    answers: started.session.questions.map((item) => ({
      question_id: item.id,
      selected: 0,
    })),
  });
  assert.equal(summary.ok, true);
  assert.equal(typeof summary.score, "number");
  assert.equal(typeof summary.percent, "number");
  assert.ok(Array.isArray(summary.wrong_items));

  await assert.rejects(
    () =>
      previewInvoke("desktop_practice_complete", {
        sessionId: "practice:gone:0000:mock:hsk1:v1",
        mode: "mock",
        level: "hsk1",
        language: "uz",
        skill: "",
        answers: [],
      }),
    /invalid_practice_session/,
  );

  const adapter = await source("app/api/desktop_practice.py");
  // The question bank and the free daily gate must not be reimplemented.
  assert.match(adapter, /CourseMiniAppPracticeService/);
  assert.match(adapter, /PRACTICE_MODES/);
  assert.match(adapter, /TRAINING_SKILLS/);
  // A used-up free slot is a normal 403, not a crash.
  assert.match(adapter, /free_feature_limit_reached/);
});

test("desktop bridge preserves practice error codes", async () => {
  const previousLocation = globalThis.location;
  globalThis.location = new URL("http://localhost/?mock=1");
  try {
    const moduleUrl = pathToFileURL(path.join(uiRoot, "js", "bridge.js"));
    moduleUrl.search = `?practice-errors=${Date.now()}`;
    const { desktopBridge } = await import(moduleUrl.href);
    await assert.rejects(
      () =>
        desktopBridge.practiceComplete({
          sessionId: "practice:gone:0000:mock:hsk1:v1",
          mode: "mock",
          level: "hsk1",
          language: "uz",
          skill: "",
          answers: [],
        }),
      (error) => {
        assert.equal(error.code, "invalid_practice_session");
        return true;
      },
    );
  } finally {
    if (previousLocation === undefined) {
      delete globalThis.location;
    } else {
      globalThis.location = previousLocation;
    }
  }
});

test("the dictionary is a full offline word bank", async () => {
  const vocabulary = await source("desktop/ui/js/vocabulary.js");
  const dataModule = await source("desktop/ui/data/vocabulary.js");
  const strokeModule = await source("desktop/ui/data/strokes.js");
  const writer = await source("desktop/ui/vendor/hanzi-writer.js");

  // Words, sentences and stroke paths ship with the app; the strict CSP allows
  // no network from the webview and stroke order must not hit a CDN.
  assert.match(dataModule, /export const WORDS = \[/);
  assert.match(dataModule, /export const EXAMPLES = \{/);
  assert.match(strokeModule, /export const STROKES = \{/);
  assert.match(vocabulary, /charDataLoader: \(_char, onLoad\) => onLoad\(data\)/);
  assert.doesNotMatch(vocabulary, /cdn\./);

  // The vendored copy must not fall back to the jsdelivr loader at runtime.
  assert.match(writer, /MIT License/);
  assert.match(writer, /export default HanziWriter;/);

  // Saved words are device-local and bounded on both sides of the IPC.
  const bridge = await source("desktop/ui/js/bridge.js");
  const rust = await source("desktop/src-tauri/src/lib.rs");
  assert.match(bridge, /CJK_WORD_PATTERN/);
  assert.match(rust, /fn sanitize_vocabulary_list/);
  assert.match(rust, /MAX_VOCABULARY_ENTRIES/);
  // A crash mid-write must not truncate the saved list.
  assert.match(rust, /json\.tmp/);

  const state = await previewInvoke("desktop_vocabulary_state");
  assert.ok(Array.isArray(state.saved));
  const saved = await previewInvoke("desktop_vocabulary_save", {
    saved: ["计划"],
    review: ["周末"],
  });
  assert.deepEqual(saved.saved, ["计划"]);
  const reread = await previewInvoke("desktop_vocabulary_state");
  assert.deepEqual(reread.review, ["周末"]);
});

test("every bundled example sentence exists in all three languages", async () => {
  const { EXAMPLES } = await import("../ui/data/vocabulary.js");
  const entries = Object.entries(EXAMPLES);
  assert.ok(entries.length > 500, "the example bank should not shrink silently");
  const incomplete = entries.filter(
    ([, entry]) =>
      !String(entry?.m?.uz || "").trim() ||
      !String(entry?.m?.ru || "").trim() ||
      !String(entry?.m?.tj || "").trim(),
  );
  assert.deepEqual(
    incomplete.map(([key]) => key),
    [],
    "an example sentence is missing a translation",
  );
});

test("keyboard hints follow the host platform on both builds", async () => {
  const html = await source("desktop/ui/index.html");
  const app = await source("desktop/ui/js/app.js");
  // Both hints must be addressable so Windows never shows a macOS glyph.
  assert.match(html, /<kbd id="search-shortcut">/);
  assert.match(html, /<kbd id="ai-shortcut">/);
  assert.match(app, /searchShortcut\.textContent = platform === "windows" \? "Ctrl\+F" : "⌘F"/);
  assert.match(app, /aiShortcut\.textContent = platform === "windows" \? "Ctrl\+K" : "⌘K"/);
});

test("the shell follows the demo chrome", async () => {
  const html = await source("desktop/ui/index.html");
  const app = await source("desktop/ui/js/app.js");
  const css = await source("desktop/ui/css/workspace.css");

  // The demo has no separate title row: the brand sits inside the sidebar and
  // the toolbar carries the metrics, the bell and the avatar.
  assert.doesNotMatch(html, /class="titlebar"/);
  assert.match(html, /class="rail-brand"/);
  assert.match(html, /id="notifications-button"/);
  assert.match(html, /id="rail-collapse"/);
  assert.match(html, /id="rail-resizer"/);
  // Offline state stays in the toolbar; the version moved into the profile.
  assert.match(html, /id="offline-pill"/);
  assert.doesNotMatch(html, /id="app-version"/);
  assert.match(app, /"profile-version"/);

  // Sidebar width and collapse are driven by data attributes because the strict
  // CSP forbids the inline styles a drag handle would normally write.
  assert.doesNotMatch(app, /\.style\./);
  assert.match(app, /dataset\.railWidth/);
  assert.match(app, /dataset\.railCollapsed/);
  assert.match(css, /:root\[data-rail-collapsed="1"\]/);
  assert.match(css, /:root\[data-rail-width="230"\]/);

  // Notifications must never be invented: server-saved Telegram reminders plus
  // update, plan and streak facts the client already holds are listed.
  assert.match(app, /function notificationItems\(\)/);
  assert.match(app, /function serverNotificationItems\(\)/);
  assert.match(app, /state\.map\?\.notifications/);
  assert.match(app, /state\.updateStatus === "available"/);
  assert.doesNotMatch(app, /notificationItems[\s\S]{0,800}Math\.random/);
});

test("every id app.js resolves exists in the markup", async () => {
  const html = await source("desktop/ui/index.html");
  const app = await source("desktop/ui/js/app.js");
  const ids = new Set([...html.matchAll(/id="([A-Za-z0-9_-]+)"/g)].map((m) => m[1]));
  const missing = [...app.matchAll(/\$\("#([A-Za-z0-9_-]+)"\)/g)]
    .map((m) => m[1])
    .filter((id) => !ids.has(id));
  assert.deepEqual(missing, [], "app.js queries an element the shell does not render");
});

test("invites are real and the study goal stays on the device", async () => {
  const app = await source("desktop/ui/js/app.js");
  const css = await source("desktop/ui/css/workspace.css");
  const adapter = await source("app/api/desktop_referral.py");
  const rust = await source("desktop/src-tauri/src/lib.rs");

  // The invite card reads the same referral programme the bot uses.
  assert.match(adapter, /ReferralService/);
  assert.match(adapter, /list_miniapp_referrals/);
  assert.match(adapter, /get_trial_activation_progress/);
  // Deep links must match the bot's own attribution format.
  assert.match(adapter, /\?start=ref_/);
  // No identifiers the desktop never renders.
  assert.doesNotMatch(adapter, /"telegram_id"/);

  const overview = await previewInvoke("desktop_referral_overview", {
    timezoneOffset: 300,
  });
  assert.equal(typeof overview.link, "string");
  assert.equal(typeof overview.invited, "number");
  assert.equal(typeof overview.trial_required, "number");
  assert.ok(Array.isArray(overview.items));
  for (const item of overview.items) {
    assert.equal(item.telegram_id, undefined);
  }

  // The goal has no server column, so it is a whitelisted device-local choice.
  assert.match(rust, /const GOAL_FILE/);
  assert.match(rust, /const GOAL_KINDS/);
  assert.doesNotMatch(rust, /MIN_GOAL_MINUTES/);
  assert.match(app, /t\("goalLocalNote"\)/);
  assert.match(app, /function openReferralModal\(/);
  assert.match(app, /function shareReferralToTelegram\(/);
  assert.match(app, /function shareReferralToWhatsapp\(/);
  assert.match(app, /whatsapp:\/\/send\?text=/);
  assert.match(app, /tg:\/\/msg_url\?url=/);
  assert.doesNotMatch(app, /https:\/\/wa\.me\/\?text=/);
  assert.match(app, /function shareReferralWithSystem\(/);
  assert.match(app, /function makeReferralQrDataUrl\(/);
  assert.match(app, /function referralLinkFrom\(/);
  assert.match(app, /state\.map\?\.user\?\.referral_code/);
  assert.doesNotMatch(
    app.slice(app.indexOf("function inviteMorph"), app.indexOf("function renderInviteCard")),
    /soonBlock/,
  );
  assert.match(css, /\.referral-layer \{/);
  assert.match(css, /\.referral-destination-grid \{/);
  assert.match(css, /\.referral-qr-image \{/);
  const saved = await previewInvoke("desktop_goal_save", { kind: "hsk" });
  assert.equal(saved.kind, "hsk");
  assert.equal((await previewInvoke("desktop_goal_state")).configured, true);
  // An unknown goal must be refused on both sides of the bridge.
  await assert.rejects(() =>
    previewInvoke("desktop_goal_save", { kind: "whatever" }),
  );
});

test("the study goal is asked in onboarding and only reported in the profile", async () => {
  const app = await source("desktop/ui/js/app.js");
  const html = await source("desktop/ui/index.html");
  const css = await source("desktop/ui/css/workspace.css");

  // One dialog owns the question; a missing goal is what opens it.
  assert.match(html, /id="onboarding-layer"/);
  // Two steps, exactly like the demo: goal, then the Smart Widget intro.
  assert.match(app, /const ONBOARDING_STEPS = 2;/);
  assert.match(app, /function onboardingGoalStep\(\)/);
  assert.match(app, /function onboardingWidgetStep\(\)/);
  assert.match(html, /id="onboarding-steps"/);
  assert.match(html, /id="onboarding-back"/);
  // The widget step must never claim the widget was installed.
  assert.match(app, /return soonBlock\(slide\);/);
  assert.doesNotMatch(app, /widgetInstalled|widgetDetected/);
  // The label stays platform-neutral: Windows has no macOS widget gallery.
  assert.doesNotMatch(app, /t\("widget[A-Za-z]*Mac"\)/);
  assert.match(app, /async function maybeOpenOnboarding\(\)/);
  assert.match(app, /if \(goal\?\.configured\) return;/);
  assert.match(app, /await maybeOpenOnboarding\(\);/);
  // It must never float over the login screen or a running lesson.
  assert.match(app, /function showAuth[\s\S]{0,260}closeOnboarding\(\);/);
  assert.match(app, /if \(dom\.workspace\.hidden \|\| lesson\.isOpen\) return;/);

  // The profile reports the choice; it does not offer a second way to set it.
  assert.doesNotMatch(app, /function renderGoalCard/);
  assert.match(app, /t\("myGoalTitle"\)/);
  assert.match(app, /t\("onboardingReset"\)/);

  // Blocks without an endpoint keep the demo layout and never show a number.
  assert.match(app, /function comingSoonStatCard\(/);
  assert.match(app, /function comingSoonSettingRow\(/);
  assert.match(css, /\.soon-badge \{/);
  for (const key of [
    "syncTitle",
    "statWordsLearned",
    "statStudyMinutes",
    "levelProgressTitle",
    "weakAreasTitle",
    "accuracyTrendTitle",
  ]) {
    assert.match(app, new RegExp(`t\\("${key}"\\)`), `${key} is not rendered`);
  }
  for (const key of ["notifyMaster", "notifyDesktopTitle", "notifyRecentTitle"]) {
    assert.match(app, new RegExp(`t\\("${key}"\\)`), `${key} is not rendered`);
  }
});

test("the profile keeps the demo blocks and parks the extras at the bottom", async () => {
  const app = await source("desktop/ui/js/app.js");
  const css = await source("desktop/ui/css/workspace.css");

  // Blocks without data keep the demo layout and reveal the label on hover,
  // rather than being replaced by a placeholder card.
  assert.match(app, /function soonBlock\(node\)/);
  assert.match(app, /control\.disabled = true;/);
  assert.match(css, /\.soon-block:hover \.soon-veil/);
  assert.match(css, /\.soon-block:focus-within \.soon-veil/);
  assert.match(app, /progress-fill is-placeholder/);
  assert.match(css, /\.summary-progress \.progress-fill\.is-placeholder/);
  // No figure is ever invented: the dash is the only stand-in.
  assert.match(app, /const NO_VALUE = "—";/);

  // The demo pieces that were missing entirely.
  assert.match(app, /function inviteMorph\(link\)/);
  assert.match(app, /function renderSyncCard\(\)/);
  assert.match(app, /function weekBarChart\(progress\)/);
  assert.match(app, /function levelProgressCard\(/);
  assert.match(app, /function weakAreasCard\(\)/);
  assert.match(app, /function accuracyTrendCard\(\)/);
  assert.match(app, /function insightChips\(\)/);
  assert.match(app, /function renderNotificationsCard\(\)/);
  assert.match(app, /class="profile-panda"|"profile-panda"/);
  // `.tag` had no rule at all, so every demo pill rendered as bare text.
  assert.match(css, /^\.tag \{/m);

  // Bar heights are activity flags, never invented minutes.
  assert.doesNotMatch(app, /weekBarChart[\s\S]{0,400}Math\.random/);

  // Subscription, updates, logout and the version have no demo slot, so they
  // sit in their own section under everything else.
  const order = [
    "settingsRow,",
    "accountHead,",
    "accountCard,",
  ].map((token) => app.indexOf(token));
  assert.ok(
    order.every((index, i) => index > 0 && (i === 0 || index > order[i - 1])),
    "the account section must be appended last",
  );
  assert.match(app, /t\("manageSubscription"\)/);
  assert.match(app, /t\("checkUpdatesNow"\)/);
  assert.match(app, /"profile-version"/);
});

test("every user-facing key exists in all three languages", async () => {
  const i18n = await source("desktop/ui/js/i18n.js");
  const blocks = {};
  for (const code of ["uz", "ru", "tj"]) {
    const start = i18n.search(new RegExp(`^  ${code}: \\{$`, "m"));
    assert.ok(start >= 0, `${code} block is missing`);
    const rest = i18n.slice(start);
    const block = rest.slice(0, rest.search(/^ {2}\},$/m));
    blocks[code] = new Set(
      [...block.matchAll(/^ {4}([A-Za-z_][A-Za-z0-9_]*):/gm)].map((m) => m[1]),
    );
  }
  for (const code of ["ru", "tj"]) {
    const missing = [...blocks.uz].filter((key) => !blocks[code].has(key));
    const extra = [...blocks[code]].filter((key) => !blocks.uz.has(key));
    assert.deepEqual(missing, [], `${code} is missing keys`);
    assert.deepEqual(extra, [], `${code} has keys uz does not`);
  }
});
