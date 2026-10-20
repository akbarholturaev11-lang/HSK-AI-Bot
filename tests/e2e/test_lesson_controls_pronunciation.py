"""Lesson exit, pronunciation and corrected translation on the real Mini App page."""
import json
import re

import pytest
from playwright.sync_api import expect
from test_miniapp_smoke import (
    STATIC_ROOT, app_url, json_response, mock_course_map, mock_learning_audio,
    mock_price_preview, mock_telegram_ready, page,
)


def open_lesson(page, language="ru"):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page, language=language)
    mock_learning_audio(page)
    page.add_init_script("localStorage.setItem('hsk_v3_tour','1');localStorage.setItem('hsk_v3_onb','1')")
    page.goto(app_url(f"/course-v3.html?lang={language}&level=hsk1&lesson=1&autostart=1&onboarded=1"), wait_until="networkidle")
    expect(page.locator("#flow")).to_have_class(re.compile(r"\bon\b"))
    page.evaluate("App.closeSheet()")
    return errors


def pronunciation(page):
    page.evaluate("""() => {
      var i=Flow.queue.findIndex(c=>c.type==='pronunciation');
      if(i<0)throw Error('real lesson has no pronunciation');
      Flow.i=i;renderFlowCard();
    }""")


@pytest.mark.parametrize("language,exit_text,keep_text", [
    ("ru", "Выйти", "Продолжить урок"),
    ("uz", "Chiqish", "Darsni davom ettirish"),
    ("tj", "Баромадан", "Идома додани дарс"),
])
def test_settings_exit_confirmation_and_native_back(page, language, exit_text, keep_text, tmp_path):
    errors = open_lesson(page, language)
    start = page.evaluate("Flow.i")
    assert page.locator(".ftop > button").count() == 1
    assert page.locator(".ftop > :first-child .ti-settings").count() == 1
    page.locator(".ftop .fgear").click()
    page.locator(".lesson-exit").click()
    expect(page.locator("#sheet.lesson-exit-confirm.on")).to_be_visible()
    box = page.locator("#sheet .si").bounding_box()
    assert abs(box["y"] + box["height"] / 2 - 422) < 35
    page.screenshot(path=str(tmp_path / f"exit-{language}.png"))
    page.get_by_role("button", name=keep_text, exact=True).click()
    assert page.evaluate("Flow.i") == start
    assert page.locator("#flow.on").count() == 1
    page.evaluate("NavBack.goBack()")
    expect(page.locator("#sheet.lesson-exit-confirm.on")).to_be_visible()
    page.get_by_role("button", name=exit_text, exact=True).click()
    assert page.locator("#flow.on").count() == 0
    assert page.evaluate("JSON.parse(localStorage.getItem(lessonResumeKey('hsk1',1))).i") == start
    assert not errors


@pytest.mark.parametrize("language,skip", [("uz", "O‘tkazib yuborish"), ("ru", "Пропустить"), ("tj", "Гузарондан")])
@pytest.mark.parametrize("height", [667, 844])
def test_pronunciation_layout_skip_and_forced_exit(page, language, skip, height, tmp_path):
    page.set_viewport_size({"width": 390, "height": height})
    errors = open_lesson(page, language)
    pronunciation(page)
    before = page.evaluate("({i:Flow.i,hp:HP,graded:Flow.graded||0})")
    character = page.locator(".lesson-pron-character").bounding_box()
    phrase = page.locator(".lesson-pron-phrase").bounding_box()
    mic = page.locator("#pron-btn").bounding_box()
    assert phrase["y"] + phrase["height"] <= character["y"]
    assert abs(character["x"] + character["width"] / 2 - 195) < 2
    assert mic["y"] > character["y"] + character["height"]
    assert mic["width"] == mic["height"] == 78
    assert mic["y"] + mic["height"] < height
    assert page.locator("#f-body .han").inner_text().strip()
    assert page.locator("#f-body .p4").inner_text().strip()
    assert page.locator("#f-body .t4").inner_text().strip()
    assert page.locator("#writebtn").is_hidden()
    page.screenshot(path=str(tmp_path / f"pron-{language}-{height}.png"))
    page.get_by_role("button", name=skip).click()
    assert page.evaluate("Flow.i") == before["i"] + 1
    assert page.evaluate("HP") == before["hp"]
    assert page.evaluate("Flow.graded||0") == before["graded"]
    assert not page.locator("#f-body.has-lesson-pron").count()
    page.evaluate("App.exitFlow()")
    assert not page.locator("#sheet.lesson-exit-confirm.on").count()
    assert not errors


@pytest.mark.parametrize("action", ["skip", "exit"])
def test_late_microphone_permission_releases_stream_without_upload(page, action):
    errors = open_lesson(page)
    pronunciation(page)
    page.evaluate("""() => {
      window.stopped=0;window.micRequests=0;
      Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:()=>{
        micRequests++;return new Promise(resolve=>window.allowMic=()=>resolve({getTracks:()=>[{stop:()=>stopped++}]}));
      }}});
      window.MediaRecorder=class {};
    }""")
    page.locator("#pron-btn").click()
    page.locator("#pron-btn").click()
    assert page.evaluate("micRequests") == 1
    if action == "skip":
        page.locator(".lesson-pron .pr-skip").click()
    else:
        page.evaluate("App.requestExitFlow();App.confirmExitFlow()")
    page.evaluate("allowMic()")
    page.wait_for_function("stopped===1")
    if action == "skip":
        assert page.evaluate("Flow.answered") is False
    else:
        assert not page.locator("#flow.on").count()
    assert not errors


def test_pronunciation_upload_grade_and_recording_cleanup(page):
    errors = open_lesson(page)
    pronunciation(page)
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
    uploads = []
    def respond(route):
        uploads.append(route.request.post_data_buffer)
        json_response(route, {"ok": True, "score": 90, "heard": "你好"})
    page.route("**/api/voice-practice/pronounce", respond)
    graded = page.evaluate("Flow.graded||0")
    page.locator("#pron-btn").click()
    expect(page.locator("#pron-btn")).to_have_attribute("aria-label", "Слушаю…")
    page.locator("#pron-btn").click()
    expect(page.locator("#f-bar")).to_be_visible()
    assert page.evaluate("Flow.graded") == graded + 1
    assert page.evaluate("stopped") == 1
    assert len(uploads) == 1
    for field in (b'name="target"', b'name="target_pinyin"', b'name="initData"', b'name="language"', b'name="level"', b'filename="voice.webm"'):
        assert field in uploads[0]
    assert not errors


@pytest.mark.parametrize("language,answer", [("ru", "привет"), ("uz", "salom"), ("tj", "салом")])
def test_corrected_real_translation_is_graded_without_pronunciation_note(page, language, answer):
    errors = open_lesson(page, language)
    page.evaluate("Flow.i=Flow.queue.findIndex(c=>c.type==='reverse_builder'&&c.zh==='你好');renderFlowCard()")
    assert page.evaluate("Flow.i") >= 0
    page.locator("#bld-bank button", has_text=re.compile("^" + answer + "$" )).click()
    assert page.evaluate("Flow.answered") is True
    assert page.locator("#f-bar").is_visible()
    assert page.evaluate("Flow.correct") >= 1
    assert not errors
