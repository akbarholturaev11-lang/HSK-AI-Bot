"""AI Voice V8 on the iPhone PWA against the real browser audio pipeline.

The page is served from a loopback origin (a secure context) with a fake
microphone. The Live relay, voice API and Pro overview are routed mocks that
follow app/api/pwa_auth.py and app/api/android_live_voice.py.
"""
import ast
import json
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app/static"
UZ = json.loads((ROOT / "localization/ui/uz/course.json").read_text(encoding="utf-8"))["messages"]


def _inline_pro_html():
    """The exact tags the authenticated route injects before </body>."""
    tree = ast.parse((ROOT / "app/api/pwa_auth.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_PWA_INLINE_PRO_HTML" for t in node.targets
        ):
            return node.value.func.value.value  # "...".encode("utf-8")
    raise AssertionError("inline Pro tags not found")


def voice_document():
    page = (STATIC / "iphone-pwa-voice.html").read_text(encoding="utf-8")
    assert page.count("</body>") == 1
    return page.replace("</body>", _inline_pro_html() + "</body>")


@pytest.fixture(scope="module")
def static_server():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(STATIC)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def open_voice(static_server, *, live=True, remaining=3):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True, args=[
        "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
    ])
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = context.new_page()
    page.set_default_timeout(10000)
    log = {"errors": [], "starts": [], "modes": [], "messages": [], "ends": [],
           "socket": None, "auth": None, "pcm": [], "text": [], "stops": 0, "remaining": remaining}
    page.on("pageerror", lambda error: log["errors"].append(str(error)))
    page.add_init_script("""(() => {
      window.__voiceStreams=[];
      const getMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia=async options=>{const s=await getMedia(options);window.__voiceStreams.push(s);return s};
    })()""")

    def api(route):
        path = urlsplit(route.request.url).path
        if path == "/iphone-pwa/practice/voice":
            return route.fulfill(content_type="text/html", body=voice_document())
        if path == "/api/v3/pwa-auth/session":
            return route.fulfill(json={"ok": True, "user_id": 5, "csrf": "pwa-csrf", "language": "uz"})
        if path == "/api/v3/pwa/voice/me":
            return route.fulfill(json={"ok": True, "remaining_voice_limit": log["remaining"], "language": "uz"},
                                 headers={"X-HSK-PWA-User-ID": "5"})
        body = (route.request.post_data_buffer or b"").decode("utf-8", "replace")
        if path.startswith("/api/v3/pwa/voice/"):
            assert route.request.headers["x-hsk-pwa-csrf"] == "pwa-csrf"
            assert "initData" not in body
        if path == "/api/v3/pwa/voice/session/start":
            log["starts"].append(json.loads(body))
            if log["remaining"] == 0:
                return route.fulfill(status=403, json={"ok": False, "code": "LIMIT_EXCEEDED"})
            return route.fulfill(json={"ok": True, "session_id": "voice-session-1", "live_available": live,
                                       "course_context": {"words": [{"zh": "学生", "pinyin": "xuésheng",
                                                                     "meaning": "talaba"}],
                                                          "review_words": [{"zh": "老师", "pinyin": "lǎoshī",
                                                                            "meaning": "o'qituvchi"}]},
                                       "opening_message": {"chinese_reply": "你好！", "pinyin": "nǐ hǎo",
                                                           "translation": "Salom!",
                                                           "suggestions": [{"zh": "你好，我是学生", "pinyin": "nǐ hǎo",
                                                                            "translation": "Salom, men talabaman"}]}})
        if path == "/api/v3/pwa/voice/session/mode":
            payload = json.loads(body)
            log["modes"].append(payload["mode"])
            return route.fulfill(json={"ok": True, "session_id": payload["session_id"], "mode": payload["mode"]})
        if path == "/api/v3/pwa/voice/message":
            log["messages"].append(route.request)
            return route.fulfill(json={"ok": True, "transcription": "我很好", "chinese_reply": "你忙吗？",
                                       "pinyin": "nǐ máng ma?", "translation": "Bandmisiz?",
                                       "remaining_limit": 2, "turn_count": 1, "session_should_end": False})
        if path == "/api/v3/pwa/voice/session/end":
            log["ends"].append(json.loads(body))
            return route.fulfill(json={"ok": True, "message_count": 1})
        if path == "/api/v3/tts":
            return route.fulfill(status=404, body="")
        if path == "/api/v3/pwa/subscription/overview":
            return route.fulfill(json={"ok": True, "lava": {"mode": "both", "plans": [
                {"plan_type": "1_month", "amount": "10.00", "currency": "USD"},
                {"plan_type": "12_months", "amount": "90.00", "currency": "USD"},
            ]}})
        if path == "/api/v3/pwa/subscription/exit-offer":
            return route.fulfill(json={"ok": True, "available": False})
        if path == "/api/v3/pwa/subscription/inline-event":
            return route.fulfill(json={"ok": True, "recorded": True})
        if path.startswith("/api/") or path.startswith("/iphone-pwa"):
            return route.fulfill(status=200, content_type="text/html", body="<body>elsewhere</body>")
        return route.fallback()

    page.route(re.compile(r"^http://127\.0\.0\.1:\d+/(?:api|iphone-pwa)(?:/.*)?(?:\?.*)?$"), api)

    def relay(socket):
        log["socket"] = socket

        def message(data):
            if isinstance(data, bytes):
                log["pcm"].append(data)
                return
            command = json.loads(data)
            if command["type"] == "auth":
                log["auth"] = command
                socket.send(json.dumps({"type": "ready", "input_sample_rate": 16000,
                                        "output_sample_rate": 24000, "max_dialogs": 0, "max_seconds": 179}))
            elif command["type"] == "text":
                log["text"].append(command["text"])
            elif command["type"] == "stop":
                log["stops"] += 1
        socket.on_message(message)

    page.route_web_socket("**/api/v3/pwa/voice/live", relay)
    page.goto(static_server + "/iphone-pwa/practice/voice?lang=uz")

    def close():
        context.close()
        browser.close()
        playwright.stop()
    return page, log, close


def status(page):
    return page.locator("#orbStatus")


def wait_until(page, predicate, message):
    for _ in range(60):
        if predicate():
            return
        page.wait_for_timeout(100)
    raise AssertionError(message)


def mic_closed(page):
    page.wait_for_function(
        "window.__voiceStreams.length && window.__voiceStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))"
    )


def test_live_conversation_streams_pcm_types_mutes_and_ends_on_time_limit(static_server):
    page, log, close = open_voice(static_server)
    try:
        assert page.evaluate("PompLiveVoice.supported()")
        # «Начать разговор» already started the call: no microphone tap.
        wait_until(page, lambda: len(log["pcm"]) >= 3, "Live must stream microphone PCM")
        assert log["auth"] == {"type": "auth", "session_id": "voice-session-1", "csrf": "pwa-csrf"}
        assert "csrf" not in log["socket"].url and "session" not in log["socket"].url
        assert log["starts"] == [{"role": "friend", "voice": "female"}]
        assert log["modes"] == ["live"]
        assert all(len(packet) == 640 for packet in log["pcm"])
        expect(status(page)).to_have_text(UZ["voiceV8.statusListening"])
        expect(page.locator("#micmuted")).to_have_class(re.compile(r"\boff\b"))
        expect(page.locator("#micmuted")).to_have_attribute("aria-label", UZ["voiceV8.micOff"])

        log["socket"].send(json.dumps({"type": "turn_complete", "turn_count": 1, "transcription": "我很好",
                                       "chinese_reply": "你今天忙吗？", "pinyin": "nǐ jīntiān máng ma?",
                                       "translation": "Bugun bandmisiz?", "session_should_end": False}))
        expect(page.locator("#dialogue .msg.user")).to_have_text("我很好")
        last_ai = page.locator("#dialogue .msg.ai").last
        expect(last_ai.locator(".han")).to_have_text("你今天忙吗？")
        expect(last_ai.locator(".sub.pinyin")).to_be_hidden()
        expect(last_ai.locator(".sub.translation")).to_have_text("Bugun bandmisiz?")

        page.locator("#prompt").fill("我不忙")
        page.locator("#prompt").press("Enter")
        wait_until(page, lambda: log["text"] == ["我不忙"], "typed text must go through the Live socket")
        assert log["messages"] == []
        expect(status(page)).to_have_text(UZ["voiceV8.statusThinking"])

        page.locator("#micmuted").click()
        expect(page.locator("#micmuted")).to_have_attribute("aria-label", UZ["voiceV8.micDisabled"])
        assert page.evaluate("window.__voiceStreams[0].getAudioTracks().every(t=>!t.enabled)")
        page.locator("#micmuted").click()
        expect(page.locator("#micmuted")).to_have_attribute("aria-label", UZ["voiceV8.micOff"])
        assert page.evaluate("window.__voiceStreams[0].getAudioTracks().every(t=>t.enabled)")

        log["socket"].send(json.dumps({"type": "time_limit"}))
        expect(page.locator("#app")).to_have_class(re.compile(r"\bended\b"))
        expect(page.locator(".restart p")).to_have_text(UZ["voiceV8.statusEnd"])
        # The ended screen keeps the conversation and offers restart or exit.
        expect(page.locator("#dialogue .msg.user").first).to_be_visible()
        expect(page.locator("#dialogue .msg.ai").last.locator(".han")).to_have_text("你今天忙吗？")
        expect(page.locator("#restart")).to_have_text(UZ["voiceV8.restart"])
        expect(page.locator("#exitEnded")).to_have_text(UZ["voicePage.exit"])
        # Not only present: on top of the black voice screen and clickable.
        page.locator("#restart").click(trial=True, timeout=3000)
        page.locator("#exitEnded").click(trial=True, timeout=3000)
        wait_until(page, lambda: log["ends"] == [{"session_id": "voice-session-1"}], "session must end on server")
        mic_closed(page)
        page.locator("#exitEnded").click()
        page.wait_for_url(re.compile(r"/iphone-pwa/course\?tab=voice&lang=uz$"))
        assert log["ends"] == [{"session_id": "voice-session-1"}], "exit must not end the session twice"
        assert not log["errors"]
    finally:
        close()


def test_live_drop_falls_back_to_recorded_turns(static_server):
    page, log, close = open_voice(static_server)
    try:
        wait_until(page, lambda: log["auth"] is not None and len(log["pcm"]) >= 1, "Live must connect")
        log["socket"].close()
        expect(status(page)).to_have_text(UZ["voiceV8.statusTurn"])
        wait_until(page, lambda: log["modes"] == ["live", "turn"], "session must return to turn mode")
        expect(page.locator("#micmuted")).not_to_have_class(re.compile(r"\boff\b"))
        assert not log["errors"]
    finally:
        close()


def test_turn_mode_records_uploads_audio_and_shows_reply(static_server):
    page, log, close = open_voice(static_server, live=False)
    try:
        # Without Live the first turn is recording on entry; the button sends it.
        expect(status(page)).to_have_text(UZ["voiceV8.statusRecording"])
        assert log["modes"] == [] and log["socket"] is None
        page.wait_for_timeout(1500)
        page.locator("#micmuted").click()
        wait_until(page, lambda: len(log["messages"]) == 1, "the recording must be uploaded")
        expect(status(page)).not_to_have_text(UZ["voiceV8.statusRecording"])
        assert len(log["starts"]) == 1
        request = log["messages"][0]
        assert request.headers["content-type"].startswith("multipart/form-data")
        body = request.post_data_buffer
        assert b'name="session_id"' in body and b"voice-session-1" in body
        assert re.search(rb'name="audio"; filename="voice\.(?:webm|mp4|ogg)"', body)
        expect(page.locator("#dialogue .msg.user")).to_have_text("我很好")
        expect(page.locator("#dialogue .msg.ai").last.locator(".han")).to_have_text("你忙吗？")
        mic_closed(page)
        assert not log["errors"]
    finally:
        close()


def test_limit_opens_shared_pro_offer_and_closing_leaves_voice(static_server):
    page, log, close = open_voice(static_server, remaining=0)
    try:
        expect(status(page)).to_have_text(UZ["voiceV8.noQuota"])
        page.locator("#prompt").fill("你好")
        page.locator("#prompt").press("Enter")
        page.locator("#hsk-inline-pro button.hip-plan").first.wait_for()
        assert log["starts"] == []
        page.locator("#hsk-inline-pro .hip-close").click()
        page.wait_for_url(re.compile(r"/iphone-pwa/course\?tab=voice&lang=uz$"))
        assert not log["errors"]
    finally:
        close()


def test_spent_allowance_never_auto_starts_and_x_leaves_at_once(static_server):
    page, log, close = open_voice(static_server, remaining=0)
    try:
        expect(status(page)).to_have_text(UZ["voiceV8.noQuota"])
        page.wait_for_timeout(400)
        assert log["starts"] == [] and page.evaluate("window.__voiceStreams.length") == 0
        page.locator("#close").click()
        page.wait_for_url(re.compile(r"/iphone-pwa/course\?tab=voice&lang=uz$"))
        assert log["ends"] == []
        assert not log["errors"]
    finally:
        close()


def test_what_to_say_sheet_offers_lesson_words_suggestions_and_examples(static_server):
    page, log, close = open_voice(static_server, live=False)
    try:
        wait_until(page, lambda: len(log["starts"]) == 1, "the call starts on entry")
        expect(status(page)).to_have_text(UZ["voiceV8.statusRecording"])
        page.locator("#plus").click()
        expect(page.locator("#suggestTitle")).to_have_text(UZ["voicePage.hintTitle"])
        words = page.locator("#hintWordList .hintItem")
        expect(words).to_have_count(2)
        expect(words.first.locator(".hintZh")).to_have_text("学生")
        expect(words.first.locator(".hintPy")).to_have_text("xuésheng")
        expect(words.first.locator(".hintTr")).to_have_text("talaba")
        expect(page.locator("#hintPhraseList .hintItem .hintTr")).to_have_text("Salom, men talabaman")
        expect(page.locator(".addOptions button")).to_have_count(4)
        assert page.locator(".drawerFooter").count() == 0
        page.locator("#hintPhraseList .hintItem").click()
        wait_until(page, lambda: len(log["messages"]) == 1, "a tapped phrase is sent")
        body = log["messages"][0].post_data_buffer
        assert b'name="text"' in body and "你好，我是学生".encode() in body and b'name="audio"' not in body
        expect(page.locator("#dialogue .msg.user").first).to_have_text("你好，我是学生")
        # The recording that was running is dropped, never uploaded later.
        mic_closed(page)
        page.wait_for_timeout(300)
        assert len(log["messages"]) == 1
        assert not log["errors"]
    finally:
        close()


def test_settings_persist_and_topic_change_ends_running_session(static_server):
    page, log, close = open_voice(static_server, live=False)
    try:
        expect(status(page)).to_have_text(UZ["voiceV8.statusRecording"])
        page.locator("#prompt").fill("你好")
        page.locator("#prompt").press("Enter")
        wait_until(page, lambda: len(log["messages"]) == 1, "typed turn must be sent")
        page.locator("#settings").click()
        page.locator("#pinyinToggle").click()
        expect(page.locator("#dialogue .msg.ai .sub.pinyin").first).to_be_visible()
        assert page.evaluate("localStorage.getItem('hsk_voice_pinyin')") == "1"
        page.keyboard.press("Escape")
        page.locator("#history").click()
        expect(page.locator("#topicsLayer")).to_have_class(re.compile(r"\bopen\b"))
        page.locator('#topicList [data-topic="hsk"]').click()
        wait_until(page, lambda: log["ends"] == [{"session_id": "voice-session-1"}], "old session must end")
        # The running call goes on with the new partner: only its greeting is left.
        wait_until(page, lambda: len(log["starts"]) == 2, "new topic starts a new session")
        assert log["starts"][1]["role"] == "teacher_li"
        expect(page.locator("#dialogue .msg")).to_have_count(1)
        expect(page.locator("#currentTopicTitle")).to_have_text(UZ["voiceV8.topicHsk"])
        page.locator("#prompt").fill("老师好")
        page.locator("#prompt").press("Enter")
        wait_until(page, lambda: len(log["messages"]) == 2, "typed turn goes to the new session")
        assert not log["errors"]
    finally:
        close()
