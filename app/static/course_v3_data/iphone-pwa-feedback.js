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
      '<div id="hsk-pwa-feedback-form"></div>' +
      '<p class="hsk-pwa-feedback-status" id="hsk-pwa-feedback-status" role="status" aria-live="polite"></p>' +
      '<button type="button" class="hsk-pwa-feedback-primary" id="hsk-pwa-feedback-submit" hidden></button>' +
    '</section>';
  document.body.appendChild(root);

  var panel = root.querySelector('[role="dialog"]');
  var form = root.querySelector("#hsk-pwa-feedback-form");
  var heading = root.querySelector("#hsk-pwa-feedback-title");
  var status = root.querySelector("#hsk-pwa-feedback-status");
  var submitButton = root.querySelector("#hsk-pwa-feedback-submit");
  var closeButton = root.querySelector(".hsk-pwa-feedback-close");
  var lastFocus = null;
  var generation = 0;
  var currentOwner = null;
  var kind = null;
  var selected = null;
  var busy = false;
  var draft = {};

  function common(key) { return commonMessage(key, ""); }
  function course(key) { return courseMessage(key, ""); }
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
      lastFocus.focus();
    }
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

  function choiceField(mark, options, value, onChange) {
    var field = make("label", "hsk-pwa-feedback-field");
    field.appendChild(make("span", "", mark));
    var select = make("select");
    select.setAttribute("aria-label", mark);
    var placeholder = make("option", "", "—");
    placeholder.value = "";
    select.appendChild(placeholder);
    validChoices(options).forEach(function (item) {
      var option = make("option", "", item.label);
      option.value = item.code;
      select.appendChild(option);
    });
    select.value = value || "";
    select.addEventListener("change", function () { onChange(select.value); renderForm(); });
    field.appendChild(select);
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

  function renderForm() {
    if (kind === "ordinary") renderOrdinary();
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
    if (!kind) {
      heading.textContent = "HSK AI";
      form.replaceChildren();
      setStatus(common("bot.releaseFeedback.notFoundAlert"));
      submitButton.hidden = true;
      return;
    }
    setStatus("");
    submitButton.textContent = course("subscriptionPage.submit");
    submitButton.hidden = false;
    renderForm();
  }

  async function open() {
    if (busy) return;
    var token = ++generation;
    lastFocus = document.activeElement;
    root.hidden = false;
    kind = null;
    selected = null;
    restoreDraft();
    heading.textContent = "HSK AI";
    form.replaceChildren();
    submitButton.hidden = true;
    submitButton.disabled = false;
    closeButton.setAttribute("aria-label", course("subscriptionPage.close"));
    setStatus(course("subscriptionPage.loading"));
    panel.focus();
    try {
      var active = function () { return token === generation && !root.hidden; };
      var data = await request("/api/v3/pwa/feedback/available", undefined, active);
      if (token !== generation || root.hidden) return;
      if (!data.ordinary && (!Array.isArray(data.release) || !data.release.length)) {
        // A user-initiated feedback tap may request the original, eligible
        // ordinary prompt. The server decides if a row can be prepared.
        var prepared = await request("/api/v3/pwa/feedback/ordinary/prepare", {}, active);
        if (token !== generation || root.hidden) return;
        data.ordinary = prepared.ordinary;
      }
      showAvailable(data);
    } catch (_) {
      if (token !== generation || root.hidden) return;
      form.replaceChildren();
      submitButton.hidden = true;
      setStatus(course("subscriptionPage.error"));
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
    if (kind === "ordinary") {
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
      await request(path, body, function () { return token === generation && !root.hidden; });
      if (token !== generation || root.hidden) return;
      kind = null;
      selected = null;
      form.replaceChildren();
      heading.textContent = "HSK AI";
      setStatus(common("bot.releaseFeedback.thanks"));
      submitButton.hidden = true;
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
  window.HskPwaFeedback = {open: open, close: close};
}());
