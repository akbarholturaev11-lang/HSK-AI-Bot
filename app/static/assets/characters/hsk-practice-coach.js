/* The practice pages' coach.
 *
 * course-v3.html grew its own coach for the LESSON (`renderLessonCoach` /
 * `reactLessonCoach`). The standalone practice pages — mistakes, recognition,
 * pronunciation — had none, so a learner met the cast in the lesson and then
 * walked into a drill where nobody was there. This module is that same dock,
 * written once instead of three times, so the three pages cannot drift apart
 * from each other the way they drifted from the lesson.
 *
 * Depends on hsk-character-pack.js and hsk-character-motion.js, and degrades
 * to doing nothing at all if either is missing — a coach is decoration, and
 * a drill must never fail to run because decoration did not load.
 *
 * Cast roles come from CAST in hsk-character-pack.js; the Android client
 * maps the same roles onto the same screens in PracticeCharacters.kt.
 */
(function (global) {
  "use strict";

  /* Word-for-word the lesson's `lessonCharacterLabel` (course-v3.html), so
     one character is not "Wuwu · mashq" in a lesson and "Monkey" in a drill. */
  var LABELS = {
    panda: { uz: "Panda", ru: "Панда", tj: "Панда" },
    dragon: { uz: "Longlong · marra", ru: "Лунлун · финиш", tj: "Лунлун · марра" },
    crane: { uz: "Hehe · grammatika", ru: "Хэхэ · грамматика", tj: "Хэхэ · грамматика" },
    monkey: { uz: "Wuwu · mashq", ru: "Уу-у · практика", tj: "Уу-у · машқ" },
    rabbit: { uz: "Yueyue · eslab qolish", ru: "Юэюэ · запоминание", tj: "Юэюэ · ёдгирӣ" }
  };

  var dock = null;
  var host = null;
  var bubbleEl = null;
  var slotEl = null;
  var lang = "ru";
  var streak = 0;
  var current = "panda";

  function labelFor(id) {
    var row = LABELS[id] || LABELS.panda;
    return row[lang] || row.ru || "Panda";
  }

  /** What the coach is saying. Empty text collapses the bubble entirely. */
  function say(text) {
    if (!dock || !bubbleEl) return;
    var value = text == null ? "" : String(text);
    bubbleEl.textContent = value;
    dock.classList.toggle("mute", value === "");
  }

  function hasPack() {
    return !!(global.HSKCharacters && typeof global.HSKCharacters.mount === "function");
  }

  /* The ladder is shared with the lesson and with Android's `hskReactionFor`:
     four correct answers in a row turn a jump into a celebration. The lesson's
     extra "last heart" rung does not exist here — practice has no hearts. */
  function reactionFor(ok, run) {
    if (ok && run >= 4) return "celebrate";
    return ok ? "jump" : "wrong";
  }

  /**
   * Build the dock and put it in the page.
   * opts.after — selector of the element to sit under (usually the top bar).
   * opts.lang  — uz | ru | tj.
   */
  function init(opts) {
    opts = opts || {};
    lang = ["uz", "ru", "tj"].indexOf(opts.lang) >= 0 ? opts.lang : "ru";
    /* Idempotent on purpose: every page calls this from `start()`, and
       `start()` runs again on replay. Building a second dock would leave two
       coaches stacked above the question. */
    if (dock && dock.parentNode) return dock;

    var anchor = typeof opts.after === "string" ? document.querySelector(opts.after) : opts.after;
    if (!anchor || !anchor.parentNode) return null;

    dock = document.createElement("div");
    dock.className = "pcoach-dock";

    /* The character is decoration; the bubble is the instruction, which a
       screen reader should read once and from here rather than twice. */
    host = document.createElement("div");
    host.className = "pcoach hsk-character-stage";
    host.setAttribute("aria-hidden", "true");

    bubbleEl = document.createElement("p");
    bubbleEl.className = "pcoach-bubble";

    /* The column to the coach's right: its line, and — in "beside" mode —
       the question itself underneath. */
    var col = document.createElement("div");
    col.className = "pcoach-col";
    slotEl = document.createElement("div");
    slotEl.className = "pcoach-slot";
    col.appendChild(bubbleEl);
    col.appendChild(slotEl);

    dock.appendChild(host);
    dock.appendChild(col);
    anchor.parentNode.insertBefore(dock, anchor.nextSibling);
    return dock;
  }

  /**
   * Stand the coach BESIDE the question: [node] is moved into the column at
   * the coach's right, under its line.
   *
   * Moved, not copied — the pages rebuild their question markup on every
   * render, so the node handed over here is always a fresh one and the slot
   * is emptied first. Passing nothing returns to the plain row.
   */
  function beside(node) {
    if (!dock || !slotEl) return;
    slotEl.innerHTML = "";
    if (!node) { dock.classList.remove("beside"); return; }
    slotEl.appendChild(node);
    dock.classList.add("beside");
  }

  /** Waiting for an answer. [text] is the question's own instruction. */
  function idle(id, text) {
    if (!dock || !host || !hasPack()) return;
    current = LABELS[id] ? id : "panda";
    dock.classList.add("on");
    dock.classList.remove("hero");
    if (arguments.length > 1) say(text);
    global.HSKCharacters.mount(host, current, "idle");
    host.setAttribute("data-character", current);
  }

  /**
   * An answer landed. Returns the reaction that was played.
   *
   * With no [text] the bubble keeps whatever it was saying — the question's
   * instruction is still true after the answer. Forwarding an absent argument
   * as `undefined` would blank the bubble and leave the character standing
   * alone, which is the thing this layout exists to avoid.
   */
  function answer(id, ok, text) {
    streak = ok ? streak + 1 : 0;
    var reaction = reactionFor(!!ok, streak);
    if (arguments.length > 2) show(id, reaction, text);
    else show(id, reaction);
    return reaction;
  }

  /** Play an explicit reaction (see hsk-character-motion.js for the names). */
  function show(id, reaction, text) {
    if (!dock || !host || !hasPack()) return;
    current = LABELS[id] ? id : "panda";
    dock.classList.add("on");
    // Only `finish` puts the coach centre stage; every other call is the
    // small aside beside a question, so drop the hero size on the way past.
    dock.classList.remove("hero");
    if (arguments.length > 2) say(text);
    if (global.HSKCharacterMotion && global.HSKCharacterMotion.react) {
      global.HSKCharacterMotion.react(host, current, reaction);
    } else {
      global.HSKCharacters.mount(host, current, "idle");
    }
    host.setAttribute("data-character", current);
  }

  /** A session ended well: the dragon's ground (`energy_milestone`). */
  function celebrate(id) {
    show(id || "dragon", "celebrate");
  }

  /* The closing face, by result. Thresholds and characters mirror Android's
     PracticeCompletionOutcome.reaction + completionCharacterFor, so the same
     score does not earn a dragon on one client and a panda on the other.
     Nothing below is a sad face: the score is already on screen, and a coach
     sulking at a weak run is how people stop opening the app. */
  function finishFor(percent) {
    if (percent >= 90) return { id: "dragon", reaction: "celebrate" };
    if (percent >= 70) return { id: "panda", reaction: "correct" };
    if (percent >= 50) return { id: "panda", reaction: "proud" };
    return { id: "rabbit", reaction: "pop" };
  }

  /** Close the session on the face its result earned. */
  function finish(score, total, text) {
    var percent = total > 0 ? Math.round((score / total) * 100) : 0;
    var picked = finishFor(percent);
    show(picked.id, picked.reaction, arguments.length > 2 ? text : "");
    // After `show`, which clears it: the closing screen is the one place the
    // coach is the subject rather than an aside.
    // The closing screen has no question to stand beside.
    if (dock) { dock.classList.remove("beside"); dock.classList.add("hero"); }
    if (slotEl) slotEl.innerHTML = "";
    return picked;
  }

  function hide() {
    if (dock) dock.classList.remove("on", "beside", "hero");
    // The question that was standing next to the coach goes with it; leaving
    // it parked in the slot is how a stale card survives a screen change.
    if (slotEl) slotEl.innerHTML = "";
  }

  function reset() {
    streak = 0;
  }

  function run() {
    return streak;
  }

  global.PracticeCoach = {
    version: "1.0.0",
    labels: LABELS,
    init: init,
    idle: idle,
    say: say,
    beside: beside,
    answer: answer,
    show: show,
    celebrate: celebrate,
    finish: finish,
    finishFor: finishFor,
    hide: hide,
    reset: reset,
    streak: run,
    reactionFor: reactionFor
  };
})(window);
