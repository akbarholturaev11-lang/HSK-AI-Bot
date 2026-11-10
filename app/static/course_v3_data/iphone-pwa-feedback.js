/* iPhone browser PWA feedback view over the original course.
   Server owns eligibility, release delivery, code choices, rewards and payment.
   This module is presentation-only and never runs in Telegram Mini App. */
(function () {
  "use strict";
  if (location.pathname !== "/iphone-pwa/course") return;

  var root = document.createElement("div");
  root.id = "hsk-pwa-feedback-root";
  root.hidden = true;
  root.innerHTML =
    '<div class="hsk-pwa-feedback-scrim" data-pwa-feedback-close></div>' +
    '<section class="hsk-pwa-feedback-card" role="dialog" aria-modal="true" ' +
      'aria-labelledby="hsk-pwa-feedback-title" tabindex="-1">' +
      '<div class="hsk-pwa-feedback-head">' +
        '<h2 class="hsk-pwa-feedback-title" id="hsk-pwa-feedback-title">HSK AI</h2>' +
        '<button type="button" class="hsk-pwa-feedback-close" data-pwa-feedback-close>×</button>' +
      '</div>' +
      '<p class="hsk-pwa-feedback-context" id="hsk-pwa-feedback-context"></p>' +
      '<div id="hsk-pwa-feedback-form"></div>' +
      '<p class="hsk-pwa-feedback-status" id="hsk-pwa-feedback-status" role="status" aria-live="polite"></p>' +
      '<button type="button" class="hsk-pwa-feedback-primary" id="hsk-pwa-feedback-submit" hidden></button>' +
    '</section>';
  document.body.appendChild(root);

  var panel = root.querySelector('[role="dialog"]');
  var form = root.querySelector("#hsk-pwa-feedback-form");
  var heading = root.querySelector("#hsk-pwa-feedback-title");
  var contextCopy = root.querySelector("#hsk-pwa-feedback-context");
  var status = root.querySelector("#hsk-pwa-feedback-status");
  var submitButton = root.querySelector("#hsk-pwa-feedback-submit");
  submitButton.hidden = true;
  var closeButton = root.querySelector(".hsk-pwa-feedback-close");
  var lastFocus = null;
  var generation = 0;
  var currentOwner = null;
  var kind = null;
  var selected = null;
  var busy = false;
  var draft = {};
  var sessionPrompted = false;

  function common(key) { return commonMessage(key, ""); }
  function course(key) { return courseMessage(key, ""); }
  function lessonTitle(level, lessonId) {
    var label = String(level || "").toUpperCase()
      .replace(/^NHSK([1-3])$/, "HSK 3.0 $1")
      .replace(/^HSK([1-4])$/, "HSK $1");
    return course("pwaFeedback.title").replace("{level}", label).replace("{n}", String(lessonId));
  }
  function setStatus(text) { status.textContent = text || ""; }
  function numberId(value) {
    var id = Number(value);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  }
  function make(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }
  function isValidLabel(text) { return typeof text === "string" && text.length > 0; }
  function validChoices(options) {
    return Array.isArray(options)
      ? options.filter(function (x) {
          return x && typeof x.code === "string" && typeof x.label === "string";
        }) : [];
  }

  function close() {
    if (root.hidden) return;
    generation++;
    root.hidden = true;
    kind = null;
    selected = null;
    busy = false;
    submitButton.disabled = false;
    draft = {};
    if (lastFocus && lastFocus.isConnected && typeof lastFocus.focus === "function") {
      lastFocus.focus({preventScroll:true});
    }
    if (window.NavBack) NavBack.sync();
  }

  async function ownedSession() {
    var actor = await pwaCourseActor();
    var id = numberId(actor && actor.user_id);
    if (!id) throw new Error("pwa_invalid_actor");
    if (currentOwner && currentOwner !== id) {
      root.hidden = true;
      location.replace("/iphone-pwa");
      throw new Error("pwa_actor_changed");
    }
    var session = await fetch("/api/v3/pwa-auth/session", {
      credentials: "same-origin", cache: "no-store", redirect: "error"
    });
    if (!session.ok) {
      if (session.status === 401) location.replace("/iphone-pwa");
      throw new Error("pwa_session_expired");
    }
    var checked = await session.json();
    if (!checked || checked.ok !== true || numberId(checked.user_id) !== id) {
      root.hidden = true;
      location.replace("/iphone-pwa");
      throw new Error("pwa_actor_changed");
    }
    currentOwner = id;
    return checked;
  }

  async function request(path, payload, isStillOpen) {
    var session = await ownedSession();
    // The cookie check can take time. Never send a fresh mutation after
    // the learner dismissed this instance of the dialog.
    if (isStillOpen && !isStillOpen()) throw new Error("pwa_dialog_closed");
    var options = {
      credentials: "same-origin", cache: "no-store", redirect: "error"
    };
    if (payload !== undefined) {
      options.method = "POST";
      options.headers = {
        "Content-Type": "application/json",
        "X-HSK-PWA-CSRF": session.csrf
      };
      options.body = JSON.stringify(payload);
    }
    var response = await fetch(path, options);
    if (response.status === 401) location.replace("/iphone-pwa");
    var data = await response.json();
    if (!response.ok || !data || data.ok !== true) {
      throw new Error(data && data.error || "pwa_feedback_failed");
    }
    return data;
  }

  // Same text variants as the bot's inline buttons: one tap per answer.
  var QUESTIONS = {"✓":"pwaFeedback.paidQ", "👍":"pwaFeedback.likedQ",
    "👎":"pwaFeedback.dislikedQ", "›":"pwaFeedback.detailQ"};
  function choiceField(mark, options, value, onChange) {
    var question = course(QUESTIONS[mark] || "") || mark;
    var field = make("div", "hsk-pwa-feedback-field hsk-pwa-feedback-choice");
    field.setAttribute("data-mark", mark);
    field.appendChild(make("span", "hsk-pwa-feedback-question", question));
    var group = make("div", "hsk-pwa-feedback-options");
    group.setAttribute("role", "radiogroup");
    group.setAttribute("aria-label", question);
    group.value = value || "";
    validChoices(options).forEach(function (item) {
      var button = make("button", "hsk-pwa-feedback-option", item.label);
      button.type = "button";
      button.setAttribute("role", "radio");
      button.setAttribute("data-code", item.code);
      button.setAttribute("aria-checked", String(item.code === value));
      button.addEventListener("click", function () { onChange(item.code); renderForm(); });
      group.appendChild(button);
    });
    field.appendChild(group);
    return field;
  }
  function commentField(label, key) {
    var field = make("label", "hsk-pwa-feedback-field");
    field.appendChild(make("span", "", label));
    var box = make("textarea");
    box.setAttribute("aria-label", label);
    box.maxLength = 1000;
    box.rows = 3;
    box.value = draft[key] || "";
    box.addEventListener("input", function () { draft[key] = box.value; });
    field.appendChild(box);
    return field;
  }
  function restoreDraft() {
    draft = {
      liked_code: "", liked_sub_code: "", liked_other_text: "",
      disliked_code: "", disliked_detail_text: "",
      paid_code: "", paid_sub_code: "", paid_other_text: "",
      rating: 0, comment_text: ""
    };
  }

  function renderOrdinary() {
    form.replaceChildren();
    if (!selected || !selected.choices) return;
    var choices = selected.choices;
    var commentLabel = common("bot.releaseFeedback.commentButton");
    if (selected.paid) {
      form.appendChild(choiceField("✓", choices.paid, draft.paid_code, function (code) {
        draft.paid_code = code;
        draft.paid_sub_code = "";
        draft.paid_other_text = "";
      }));
      if (draft.paid_code) {
        var positive = draft.paid_code === "worth" || draft.paid_code === "useful";
        var sub = positive ? choices.paid_sub_positive : choices.paid_sub_negative;
        form.appendChild(choiceField("›", sub, draft.paid_sub_code, function (code) {
          draft.paid_sub_code = code;
          draft.paid_other_text = "";
        }));
        if (draft.paid_sub_code === "other") {
          form.appendChild(commentField(commentLabel, "paid_other_text"));
        }
      }
    } else {
      form.appendChild(choiceField("👍", choices.liked, draft.liked_code, function (code) {
        draft.liked_code = code;
        draft.liked_sub_code = "";
        draft.liked_other_text = "";
      }));
      var subs = choices.liked_sub && choices.liked_sub[draft.liked_code];
      if (validChoices(subs).length) {
        form.appendChild(choiceField("›", subs, draft.liked_sub_code, function (code) {
          draft.liked_sub_code = code;
          draft.liked_other_text = "";
        }));
      }
      if (draft.liked_code === "other" || draft.liked_sub_code === "other") {
        form.appendChild(commentField(commentLabel, "liked_other_text"));
      }
      form.appendChild(choiceField("👎", choices.disliked, draft.disliked_code, function (code) {
        draft.disliked_code = code;
        draft.disliked_detail_text = "";
      }));
      if (Array.isArray(choices.disliked_detail_required) &&
          choices.disliked_detail_required.includes(draft.disliked_code)) {
        form.appendChild(commentField(commentLabel, "disliked_detail_text"));
      }
    }
  }

  function renderRelease() {
    form.replaceChildren();
    var stars = make("div", "hsk-pwa-feedback-stars");
    stars.setAttribute("role", "group");
    for (var rating = 1; rating <= 5; rating++) {
      (function (n) {
        var btn = make("button", "", "★");
        btn.type = "button";
        btn.setAttribute("aria-label", n + " / 5");
        btn.setAttribute("aria-pressed", String(n <= draft.rating));
        btn.addEventListener("click", function () { draft.rating = n; renderForm(); });
        stars.appendChild(btn);
      }(rating));
    }
    form.appendChild(stars);
    var label = common("bot.releaseFeedback.commentButton");
    form.appendChild(commentField(label, "comment_text"));
  }

  function renderCompact() {
    form.replaceChildren();
    var items = ["positive", "unclear", "technical"].map(function(code) {
      return {code:code, label:course("pwaFeedback." + code)};
    });
    form.appendChild(choiceField("", items, draft.answer, function(code) {draft.answer = code;}));
    if (draft.answer === "unclear" || draft.answer === "technical") {
      form.appendChild(commentField(course("pwaFeedback.optionalComment"), "comment_text"));
    }
    submitButton.disabled = !draft.answer;
  }

  function renderForm() {
    if (kind === "context") renderCompact();
    else if (kind === "ordinary") renderOrdinary();
    else if (kind === "release") renderRelease();
  }

  function showAvailable(data) {
    selected = null;
    kind = null;
    restoreDraft();
    if (Array.isArray(data.release) && data.release.length) {
      var entry = data.release.find(function (item) {
        return item && numberId(item.campaign_id);
      });
      if (entry) {
        kind = "release";
        selected = entry;
        heading.textContent = isValidLabel(entry.title) ? entry.title : "HSK AI";
      }
    }
    if (!kind && data.ordinary && numberId(data.ordinary.feedback_id)) {
      kind = "ordinary";
      selected = data.ordinary;
      // Respect an unfinished answer already owned by the canonical bot flow.
      // Replacing its recorded first choice would fail the original server guard.
      if (selected.paid) {
        draft.paid_code = typeof selected.liked_code === "string" &&
          selected.liked_code.indexOf("paid_") === 0 ? selected.liked_code.slice(5) : "";
        draft.paid_sub_code = typeof selected.disliked_code === "string" &&
          selected.disliked_code.indexOf("paid_") === 0 ? selected.disliked_code.slice(5) : "";
      } else {
        draft.liked_code = typeof selected.liked_code === "string" ? selected.liked_code : "";
        draft.disliked_code = typeof selected.disliked_code === "string" ? selected.disliked_code : "";
      }
      heading.textContent = "HSK AI";
    }
    if (!kind) return false;
    setStatus("");
    submitButton.textContent = course("subscriptionPage.submit");
    submitButton.hidden = false;
    renderForm();
    return true;
  }

  async function openContext(context) {
    if (busy || !root.hidden || sessionPrompted || !context || context.confirmed !== true ||
        !["lesson", "foundation", "practice", "voice"].includes(context.kind) ||
        !/^(hsk[1-4]|nhsk[1-3])$/.test(context.level) || document.visibilityState === "hidden") return;
    var token = ++generation;
    function current() {
      return token === generation && root.hidden && document.visibilityState !== "hidden" &&
        (!context.canOpen || context.canOpen());
    }
    var binding = {kind:context.kind, level:context.level};
    if (context.kind === "lesson") binding.lesson_id = Number(context.lessonId);
    try {
      var data = await request("/api/v3/pwa/feedback/ordinary/prepare", {context:binding}, current);
      if (!current() || !data.ordinary || !numberId(data.ordinary.feedback_id) || !data.ordinary.compact) return;
      selected = data.ordinary;
      kind = "context";
      restoreDraft();
      heading.textContent = context.kind === "lesson" ? lessonTitle(context.level, context.lessonId)
        : course("pwaFeedback." + context.kind + "Title");
      contextCopy.textContent = course("pwaFeedback.quickQuestion");
      setStatus("");
      submitButton.textContent = course("subscriptionPage.submit");
      submitButton.hidden = false;
      closeButton.setAttribute("aria-label", course("subscriptionPage.close"));
      renderForm();
      lastFocus = document.activeElement;
      root.hidden = false;
      sessionPrompted = true;
      panel.focus({preventScroll:true});
      if (window.NavBack) NavBack.sync();
    } catch (_) { /* Optional feedback must not block returning to study. */ }
  }

  async function open(context) {
    if (context && context.kind) return openContext(context);
    if (busy || !root.hidden) return;
    var lessonId = Number(context && context.lessonId);
    var level = String(context && context.level || "");
    if (!context || context.confirmed !== true || !Number.isSafeInteger(lessonId) ||
        lessonId < 1 || lessonId > 500 || !/^(hsk[1-4]|nhsk[1-3])$/.test(level) ||
        document.visibilityState === "hidden") return;
    var token = ++generation;
    function current() {
      return token === generation && root.hidden && document.visibilityState !== "hidden" &&
        (typeof context.canOpen !== "function" || context.canOpen());
    }
    try {
      var data = await request("/api/v3/pwa/feedback/lesson/prepare", {
        lesson_id:lessonId,level:level
      }, current);
      if (!current()) return;
      var feedback = data.ordinary;
      var choices = feedback && feedback.choices;
      // No due feedback and ineligible/unavailable responses are expected
      // after some lessons. The course stays in focus until a form is ready.
      if (!feedback || !numberId(feedback.feedback_id) || !choices) return;
      if (feedback.paid ? !validChoices(choices.paid).length :
          !validChoices(choices.liked).length || !validChoices(choices.disliked).length) return;
      if (!showAvailable({ordinary:feedback,release:[]})) return;
      lastFocus = document.activeElement;
      heading.textContent = lessonTitle(level, lessonId);
      contextCopy.textContent = course("pwaFeedback.body");
      submitButton.disabled = false;
      closeButton.setAttribute("aria-label", course("subscriptionPage.close"));
      root.hidden = false;
      panel.focus({preventScroll:true});
      if (window.NavBack) NavBack.sync();
    } catch (_) {
      // An automatic, optional prompt should never interrupt study on error.
    }
  }

  // Star rating for a bot release-feedback campaign already delivered to this
  // account (Telegram/Android). Shown at most once per campaign on a device;
  // the learner can still answer it in the bot.
  var RELEASE_SEEN_PREFIX = "hsk_pwa_release_seen_v1:";
  function releaseSeen(id) {
    try { return localStorage.getItem(RELEASE_SEEN_PREFIX + id) === "1"; } catch (_) { return true; }
  }
  async function openRelease(context) {
    if (busy || !root.hidden || document.visibilityState === "hidden") return;
    var token = ++generation;
    function current() {
      return token === generation && root.hidden && document.visibilityState !== "hidden" &&
        (!context || typeof context.canOpen !== "function" || context.canOpen());
    }
    try {
      var data = await request("/api/v3/pwa/feedback/available", undefined, current);
      if (!current()) return;
      var release = (Array.isArray(data.release) ? data.release : []).filter(function (item) {
        return item && numberId(item.campaign_id) && !releaseSeen(item.campaign_id);
      });
      if (!release.length || !showAvailable({ordinary:null, release:release.slice(0, 1)})) return;
      try { localStorage.setItem(RELEASE_SEEN_PREFIX + release[0].campaign_id, "1"); } catch (_) { return; }
      lastFocus = document.activeElement;
      contextCopy.textContent = isValidLabel(release[0].message_text) ? release[0].message_text.slice(0, 400) : "";
      submitButton.disabled = false;
      closeButton.setAttribute("aria-label", course("subscriptionPage.close"));
      root.hidden = false;
      panel.focus({preventScroll:true});
      if (window.NavBack) NavBack.sync();
    } catch (_) {
      // Optional prompt: never interrupt study on error.
    }
  }

  function ordinaryPayload() {
    var choices = selected && selected.choices;
    if (!choices || !numberId(selected.feedback_id)) return null;
    if (selected.paid) {
      if (!validChoices(choices.paid).some(function (x) { return x.code === draft.paid_code; })) return null;
      var subs = (draft.paid_code === "worth" || draft.paid_code === "useful")
        ? choices.paid_sub_positive : choices.paid_sub_negative;
      if (!validChoices(subs).some(function (x) { return x.code === draft.paid_sub_code; })) return null;
      if (draft.paid_sub_code === "other" && !draft.paid_other_text.trim()) return null;
      return {
        feedback_id: selected.feedback_id,
        paid_code: draft.paid_code,
        paid_sub_code: draft.paid_sub_code,
        paid_other_text: draft.paid_sub_code === "other" ? draft.paid_other_text.trim() : null
      };
    }
    if (!validChoices(choices.liked).some(function (x) { return x.code === draft.liked_code; })) return null;
    if (!validChoices(choices.disliked).some(function (x) { return x.code === draft.disliked_code; })) return null;
    var sub = choices.liked_sub && choices.liked_sub[draft.liked_code];
    if (validChoices(sub).length &&
        !validChoices(sub).some(function (x) { return x.code === draft.liked_sub_code; })) return null;
    if ((draft.liked_code === "other" || draft.liked_sub_code === "other") &&
        !draft.liked_other_text.trim()) return null;
    var detailNeeded = Array.isArray(choices.disliked_detail_required) &&
      choices.disliked_detail_required.includes(draft.disliked_code);
    if (detailNeeded && !draft.disliked_detail_text.trim()) return null;
    return {
      feedback_id: selected.feedback_id,
      liked_code: draft.liked_code,
      liked_sub_code: validChoices(sub).length ? draft.liked_sub_code : null,
      liked_other_text: (draft.liked_code === "other" || draft.liked_sub_code === "other")
        ? draft.liked_other_text.trim() : null,
      disliked_code: draft.disliked_code,
      disliked_detail_text: detailNeeded ? draft.disliked_detail_text.trim() : null
    };
  }

  async function submit() {
    if (busy || root.hidden || !selected || !kind) return;
    var path, body;
    if (kind === "context") {
      if (!["positive", "unclear", "technical"].includes(draft.answer)) return;
      path = "/api/v3/pwa/feedback/ordinary/submit";
      body = {feedback_id:selected.feedback_id, context:selected.compact,
        answer:draft.answer, comment:draft.comment_text.trim() || null};
    } else if (kind === "ordinary") {
      body = ordinaryPayload();
      path = "/api/v3/pwa/feedback/ordinary/submit";
    } else {
      if (!numberId(selected.campaign_id) || draft.rating < 1 || draft.rating > 5) {
        setStatus(common("bot.releaseFeedback.chooseRatingAlert"));
        return;
      }
      if (draft.rating <= 2 && !draft.comment_text.trim()) {
        // This browser form supports text only; do not promise screenshot upload
        // or an eligibility-dependent discount in a validation hint.
        setStatus(common("bot.releaseFeedback.commentButton"));
        return;
      }
      path = "/api/v3/pwa/feedback/release/respond";
      body = {
        campaign_id: selected.campaign_id,
        rating: draft.rating,
        comment_text: draft.comment_text.trim() || null
      };
    }
    if (!body) { setStatus(course("subscriptionPage.error")); return; }
    busy = true;
    submitButton.disabled = true;
    setStatus(course("subscriptionPage.loading"));
    var token = generation;
    try {
      var compactSubmission = kind === "context";
      await request(path, body, function () { return token === generation && !root.hidden; });
      if (token !== generation || root.hidden) return;
      kind = null;
      selected = null;
      form.replaceChildren();
      heading.textContent = "HSK AI";
      setStatus(common("bot.releaseFeedback.thanks"));
      submitButton.hidden = true;
      if (compactSubmission) setTimeout(function(){if(token === generation)close();},1200);
    } catch (_) {
      if (token !== generation || root.hidden) return;
      setStatus(course("subscriptionPage.error"));
    } finally {
      // A slow old submission must not unlock a newer reopened dialog.
      if (token === generation) {
        busy = false;
        submitButton.disabled = false;
      }
    }
  }

  root.addEventListener("click", function (ev) {
    if (ev.target.closest("[data-pwa-feedback-close]")) close();
  });
  submitButton.addEventListener("click", submit);
  document.addEventListener("keydown", function (ev) {
    if (root.hidden) return;
    if (ev.key === "Escape") { ev.preventDefault(); close(); return; }
    if (ev.key !== "Tab") return;
    var focusable = Array.from(panel.querySelectorAll("button:not([hidden]):not(:disabled),select,textarea"))
      .filter(function (el) { return el.offsetParent !== null && el.tabIndex >= 0; });
    if (!focusable.length) { ev.preventDefault(); panel.focus(); return; }
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (ev.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
      ev.preventDefault(); last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault(); first.focus();
    }
  });
  window.HskPwaFeedback = {
    open: open, openRelease: openRelease, close: close,
    backTarget: function () { return root.hidden ? null : panel; }
  };
}());
