import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

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
  "desktop_bootstrap",
  "desktop_logout",
  "desktop_course_map",
  "desktop_lesson_data",
  "desktop_lesson_complete",
  "desktop_set_language",
  "desktop_subscription_overview",
  "desktop_subscription_quote",
  "desktop_subscription_submit",
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
  const workspaceCss = await source("desktop/ui/css/workspace.css");
  const javascript = await Promise.all(
    [
      "app.js",
      "bridge.js",
      "i18n.js",
      "lesson.js",
      "preview-mock.js",
      "subscription.js",
    ].map((file) => source(`desktop/ui/js/${file}`)),
  );
  assert.match(html, /<script type="module" src="\.\/js\/app\.js"><\/script>/);
  assert.doesNotMatch(html, /\son[a-z]+\s*=/i);
  assert.doesNotMatch(html, /\sstyle\s*=/i);
  assert.doesNotMatch(html, /<script(?![^>]*\ssrc=)[^>]*>/i);
  assert.match(html, /src="\.\/assets\/hsk-ai-avatar\.webp"/);
  assert.doesNotMatch(html, /class="(?:brand-mark|panda-badge|panda-mini)"[^>]*>[汉阿]</);
  assert.match(workspaceCss, /\.rail-action \.rail-icon[\s\S]*fill: none;[\s\S]*stroke: currentColor;/);
  for (const content of javascript) {
    assert.doesNotMatch(content, /\.style\./);
    assert.doesNotMatch(content, /\b(fetch|XMLHttpRequest|WebSocket)\b/);
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

test("updater auto-installs only while the learning workspace is idle", async () => {
  const app = await source("desktop/ui/js/app.js");
  const bridge = await source("desktop/ui/js/bridge.js");
  const rust = await source("desktop/src-tauri/src/lib.rs");
  assert.match(app, /void checkForUpdates\(\)/);
  assert.match(app, /scheduleAutomaticUpdate\(\)/);
  assert.match(app, /lesson\.isOpen[\s\S]*state\.aiBusy[\s\S]*state\.aiInstallBusy/);
  assert.match(app, /desktopBridge\.updateInstall\(\)/);
  assert.match(app, /desktop-update:\/\/progress/);
  assert.match(bridge, /listenDesktopUpdate/);
  assert.match(rust, /download_and_install[\s\S]*emit_update_progress/);
  assert.doesNotMatch(app, /setInterval\([^)]*installUpdate/);
});

test("local AI is explicit, bounded and never replaced with preview answers", async () => {
  const bridge = await source("desktop/ui/js/bridge.js");
  const app = await source("desktop/ui/js/app.js");
  const preview = await source("desktop/ui/js/preview-mock.js");
  assert.match(bridge, /MAX_LOCAL_AI_PROMPT_CHARS = 4_000/);
  assert.match(bridge, /MAX_LOCAL_AI_HISTORY_MESSAGES = 12/);
  assert.match(app, /desktopBridge\.localAiInstallStart\(\)/);
  assert.match(app, /desktopBridge\.localAiChat\(/);
  assert.match(app, /local-ai:\/\/chat-delta/);
  assert.match(app, /function resetAiSession\(\)/);
  assert.match(app, /state\.aiMessages = \[\];/);
  assert.match(app, /function showAuth[\s\S]{0,350}resetAiSession\(\)/);
  assert.match(preview, /case "local_ai_chat":/);
  assert.match(preview, /throw new Error\("local_ai_runtime_missing"\)/);
  assert.doesNotMatch(preview, /case "local_ai_chat":[\s\S]{0,300}text:/);
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
