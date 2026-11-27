"""UIUX-008: lesson length plan + picture pronunciation deck on the real Mini App page.

The server only adds `lesson_plan`; these tests feed a plan through the same
lesson-content transport and check what the learner actually sees.
"""
import json
import re

import pytest
from playwright.sync_api import expect
from test_miniapp_smoke import (
    STATIC_ROOT, app_url, json_response, mock_course_map, mock_learning_audio,
    mock_price_preview, mock_telegram_ready, page,
)

WORDS = [
    {"zh": "苹果", "pinyin": "píngguǒ", "meaning": {"uz": "olma", "ru": "яблоко", "tj": "себ"}, "image": "🍎"},
    {"zh": "猫", "pinyin": "māo", "meaning": {"uz": "mushuk", "ru": "кошка", "tj": "гурба"}, "image": "🐈"},
    {"zh": "书", "pinyin": "shū", "meaning": {"uz": "kitob", "ru": "книга", "tj": "китоб"}, "image": "📕"},
]
PLAN = {
    "version": 1,
    "daily_minutes": 5,
    "omit": [{"section_no": 3, "section_no_note": "practice", "card_no": 1},
             {"section_no": 3, "card_no": 3}],
    "picture_review": {"anchor": {"section_no": 4, "position": "start"}, "words": WORDS},
}
SKIP = {"uz": "O‘tkazib yuborish", "ru": "Пропустить", "tj": "Гузарондан"}
TITLE = {
    "uz": "Rasmga qarang va xitoycha ayting",
    "ru": "Посмотрите на картинку и скажите по-китайски",
    "tj": "Ба расм нигоҳ кунед ва ба хитоӣ гӯед",
}


def _lesson(order=1):
    return json.loads((STATIC_ROOT / f"course_v3_data/hsk1/lesson_{order:02d}.json").read_text("utf-8"))


def open_planned_lesson(page, language="uz", plan=PLAN, pinyin=None):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page, language=language)
    mock_learning_audio(page)

    def content(route):
        payload = _lesson(1)
        if plan:
            payload["lesson_plan"] = plan
        json_response(route, payload, headers={"Cache-Control": "no-store"})

    page.route(re.compile(r".*/api/v3/lesson/content/hsk1/1(?:\?.*)?$"), content)
    init = "localStorage.setItem('hsk_v3_tour','1');localStorage.setItem('hsk_v3_onb','1');"
    if pinyin:
        init += f"localStorage.setItem('hsk_v3_pinyin','{pinyin}');"
    page.add_init_script(init)
    page.goto(app_url(f"/course-v3.html?lang={language}&level=hsk1&lesson=1&autostart=1&onboarded=1"),
              wait_until="networkidle")
    expect(page.locator("#flow")).to_have_class(re.compile(r"\bon\b"))
    page.evaluate("App.closeSheet()")
    return errors


def open_deck(page):
    page.evaluate("""() => {
      var i=Flow.queue.findIndex(c=>c.type==='_picture_review');
      if(i<0)throw Error('no picture step');
      Flow.i=i;renderFlowCard();
    }""")


def fake_microphone(page):
    page.evaluate("""() => {
      window.stopped=0;
      Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:()=>Promise.resolve({getTracks:()=>[{stop:()=>stopped++}]})}});
      window.MediaRecorder=class {
        static isTypeSupported(){return true}
        constructor(){this.state='inactive';this.mimeType='audio/webm'}
        start(){this.state='recording'}
        stop(){this.state='inactive';if(this.ondataavailable)this.ondataavailable({data:new Blob([new Uint8Array(2400)])});if(this.onstop)this.onstop()}
      };
    }""")


def say(page):
    page.locator("#pic-btn").click()
    page.locator("#pic-btn").click()


def front_word(page):
    return page.evaluate("""() => {
      var el=document.querySelector('.pic-card.d0 .pic-img');return el?el.textContent:null;
    }""")


def test_plan_hides_only_extra_practice_and_keeps_material_refs(page):
    errors = open_planned_lesson(page)
    result = page.evaluate("""() => {
      var d=JSON.parse(JSON.stringify(LESSON_DATA_CACHE[lessonDataKey('hsk1',1)]));
      var planned=buildQueue(d),plain=buildQueue((delete d.lesson_plan,d)),preview=buildQueue(LESSON_DATA_CACHE[lessonDataKey('hsk1',1)],{previewHalf:true});
      var refs=q=>q.filter(c=>c._materialRef).map(c=>c._materialRef);
      return {planned:refs(planned),plain:refs(plain),types:planned.map(c=>c.type),
        previewHasDeck:preview.some(c=>c.type==='_picture_review'),previewLen:preview.length,plainLen:plain.length,
        deckAt:planned.findIndex(c=>c.type==='_picture_review'),reviewAt:planned.findIndex(c=>c._sPurpose==='retention_review'&&c.type!=='_picture_review')};
    }""")
    assert "lesson:hsk1:1:section:3:card:1" not in result["planned"]
    assert "lesson:hsk1:1:section:3:card:3" not in result["planned"]
    assert set(result["planned"]) == set(result["plain"]) - {
        "lesson:hsk1:1:section:3:card:1", "lesson:hsk1:1:section:3:card:3"}
    assert result["deckAt"] == result["reviewAt"] - 1
    assert result["types"].count("_picture_review") == 1
    assert result["previewHasDeck"] is False and result["previewLen"] == result["plainLen"]
    assert not errors


@pytest.mark.parametrize("language", ["uz", "ru", "tj"])
@pytest.mark.parametrize("height", [667, 844])
def test_deck_layout_hides_the_answer_until_checked(page, language, height, tmp_path):
    page.set_viewport_size({"width": 390, "height": height})
    errors = open_planned_lesson(page, language)
    open_deck(page)
    expect(page.locator(".pic-review .qq")).to_have_text(TITLE[language])
    assert page.locator(".pic-card").count() == 3
    assert page.locator(".pic-card.d0").count() == 1
    # Orqadagi kartalar biroz yuqoridan ko'rinadi, rasmi esa yashirin.
    front = page.locator(".pic-card.d0").bounding_box()
    behind = page.locator(".pic-card.d1").bounding_box()
    assert behind["y"] < front["y"]
    assert page.locator(".pic-card.d1 .pic-img").evaluate("e=>getComputedStyle(e).visibility") == "hidden"
    # Tekshiruvdan oldin javob DOM'da ham yo'q.
    assert page.locator(".pic-back").evaluate_all("els=>els.every(e=>e.textContent==='')")
    assert page.locator("#f-body .pic-zh").count() == 0
    mic = page.locator("#pic-btn").bounding_box()
    assert mic["width"] == mic["height"] == 78
    assert mic["y"] + mic["height"] < height
    assert front["y"] + front["height"] < mic["y"]
    skip = page.locator(".pic-review .pr-skip.pron-skip")
    expect(skip).to_have_text(re.compile(SKIP[language]))
    assert skip.locator(".ti-player-skip-forward").count() == 1
    skip_box = skip.bounding_box()
    assert skip_box["y"] > mic["y"]
    assert page.locator("#writebtn").is_hidden()
    page.wait_for_timeout(750)
    page.screenshot(path=str(tmp_path / f"deck-{language}-{height}.png"))
    assert not errors


def test_correct_answer_flips_and_leaves_without_touching_lesson_score(page, tmp_path):
    errors = open_planned_lesson(page, "ru")
    fake_microphone(page)
    uploads = []

    def respond(route):
        uploads.append(route.request.post_data_buffer)
        json_response(route, {"ok": True, "score": 92, "passed": True, "heard": "x"})

    page.route("**/api/voice-practice/pronounce", respond)
    open_deck(page)
    before = page.evaluate("({i:Flow.i,hp:HP,graded:Flow.graded||0,correct:Flow.correct||0,mistakes:(Flow.mistakes||[]).length})")
    first = front_word(page)
    say(page)
    card = page.locator(".pic-card.pic-ok")
    expect(card).to_have_count(1)
    expect(card.locator(".pic-zh")).to_have_count(1)
    expect(card.locator(".pic-tr")).not_to_be_empty()
    expect(page.locator(".pic-card.pic-flip")).to_have_count(1)
    target = card.locator(".pic-zh").inner_text()
    page.wait_for_timeout(800)
    page.screenshot(path=str(tmp_path / "deck-correct.png"))
    assert b'name="target"' in uploads[0] and target.encode() in uploads[0]
    card.click()
    page.wait_for_function("document.querySelectorAll('.pic-card.pic-gone').length===1")
    assert front_word(page) != first
    after = page.evaluate("({i:Flow.i,hp:HP,graded:Flow.graded||0,correct:Flow.correct||0,mistakes:(Flow.mistakes||[]).length})")
    assert after == before
    assert page.evaluate("stopped") == 1
    assert not errors


def test_wrong_answer_reveals_and_returns_to_the_back(page, tmp_path):
    errors = open_planned_lesson(page, "uz")
    fake_microphone(page)
    page.route("**/api/voice-practice/pronounce",
               lambda route: json_response(route, {"ok": True, "score": 20, "passed": False, "heard": "x"}))
    open_deck(page)
    first = front_word(page)
    say(page)
    expect(page.locator(".pic-card.pic-no")).to_have_count(1)
    expect(page.locator(".pic-card.pic-no .pic-zh")).to_have_count(1)
    page.wait_for_timeout(800)
    page.screenshot(path=str(tmp_path / "deck-wrong.png"))
    page.locator(".pic-card.pic-no").click()
    page.wait_for_function("document.querySelectorAll('.pic-card.pic-no').length===0")
    page.wait_for_function("!document.querySelector('#pic-btn').disabled")
    assert front_word(page) != first
    # Xato so'z navbat oxirida — yana so'raladi.
    order = page.evaluate("""() => [...document.querySelectorAll('.pic-card')]
      .filter(e=>!e.classList.contains('pic-gone'))
      .sort((a,b)=>Number(b.style.zIndex)-Number(a.style.zIndex)).map(e=>e.querySelector('.pic-img').textContent)""")
    assert order[-1] == first and len(order) == 3
    assert page.locator(".pic-back").evaluate_all("els=>els.every(e=>e.textContent==='')")
    assert not errors


def test_unclear_audio_gives_no_verdict(page):
    errors = open_planned_lesson(page, "tj")
    fake_microphone(page)
    page.route("**/api/voice-practice/pronounce",
               lambda route: json_response(route, {"ok": True, "score": 0, "passed": False, "unclear": True, "heard": ""}))
    open_deck(page)
    first = front_word(page)
    say(page)
    expect(page.locator("#pic-hint")).to_have_text("Пахш карда боз гӯед")
    assert page.locator(".pic-card.pic-ok, .pic-card.pic-no, .pic-card.pic-flip").count() == 0
    assert page.locator(".pic-back").evaluate_all("els=>els.every(e=>e.textContent==='')")
    assert front_word(page) == first
    assert page.locator("#pic-btn").is_enabled()
    assert not errors


def test_skip_moves_on_without_counting_and_ends_the_step(page):
    errors = open_planned_lesson(page, "ru")
    open_deck(page)
    before = page.evaluate("({i:Flow.i,hp:HP,graded:Flow.graded||0,correct:Flow.correct||0})")
    for _ in range(3):
        page.locator(".pic-review .pr-skip").click()
        page.wait_for_timeout(420)
    page.wait_for_function(f"Flow.i==={before['i'] + 1}")
    assert page.locator(".pic-review").count() == 0
    after = page.evaluate("({hp:HP,graded:Flow.graded||0,correct:Flow.correct||0})")
    assert after == {"hp": before["hp"], "graded": before["graded"], "correct": before["correct"]}
    assert not errors


def test_daily_limit_ends_the_deck_and_opens_the_existing_paywall(page):
    errors = open_planned_lesson(page, "uz")
    fake_microphone(page)
    page.route("**/api/voice-practice/pronounce",
               lambda route: json_response(route, {"ok": False, "code": "PRONOUNCE_LIMIT_EXCEEDED"}, status=403))
    page.evaluate("window._paywalls=[];App.openPaywall=function(k){_paywalls.push(k)};0")
    open_deck(page)
    start = page.evaluate("Flow.i")
    say(page)
    page.wait_for_function(f"Flow.i==={start + 1}")
    assert page.evaluate("_paywalls") == ["pronLimit"]
    assert page.locator(".pic-review").count() == 0
    assert not errors


def test_pinyin_setting_hides_pinyin_but_keeps_hanzi_and_translation(page):
    errors = open_planned_lesson(page, "uz", pinyin="off")
    fake_microphone(page)
    page.route("**/api/voice-practice/pronounce",
               lambda route: json_response(route, {"ok": True, "score": 95, "passed": True, "heard": "x"}))
    open_deck(page)
    say(page)
    expect(page.locator(".pic-card.pic-ok .pic-zh")).to_be_visible()
    assert page.locator(".pic-card.pic-ok .pic-py").is_hidden()
    expect(page.locator(".pic-card.pic-ok .pic-tr")).to_be_visible()
    assert not errors


def test_reduced_motion_still_completes(page):
    page.emulate_media(reduced_motion="reduce")
    errors = open_planned_lesson(page, "ru")
    fake_microphone(page)
    page.route("**/api/voice-practice/pronounce",
               lambda route: json_response(route, {"ok": True, "score": 95, "passed": True, "heard": "x"}))
    open_deck(page)
    start = page.evaluate("Flow.i")
    for _ in range(3):
        say(page)
        page.locator(".pic-card.pic-ok").click()
        page.wait_for_function("!document.querySelector('.pic-card.pic-ok')")
    page.wait_for_function(f"Flow.i==={start + 1}")
    assert not errors


def test_lesson_without_plan_is_unchanged(page):
    errors = open_planned_lesson(page, "uz", plan=None)
    types = page.evaluate("Flow.queue.map(c=>c.type)")
    assert "_picture_review" not in types
    lesson = _lesson(1)
    expected = sum(len(s["cards"]) for s in lesson["sections"])
    assert len(types) == expected
    assert not errors
