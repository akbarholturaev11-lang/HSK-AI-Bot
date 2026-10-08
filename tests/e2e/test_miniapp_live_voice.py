"""Run the real browser capture/worklet/playback pipeline with a routed relay."""
import base64
import json
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from test_miniapp_smoke import (
    STATIC_ROOT, _mock_voice_environment, mock_course_map, mock_price_preview,
    mock_telegram_ready, route_static_files,
)


@pytest.fixture(scope="module")
def static_server():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(STATIC_ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture()
def live_browser(static_server, request):
    language = getattr(request, "param", "uz")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=[
            "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
        ])
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("""(() => {
          window.__voiceStreams=[];window.__voiceContexts=[];window.__voiceBuffers=[];window.__voiceSources=[];window.__voiceStops=0;
          const getMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
          navigator.mediaDevices.getUserMedia=async options=>{
            const stream=await getMedia(options);window.__voiceStreams.push(stream);return stream;
          };
          const Audio=window.AudioContext;
          window.AudioContext=class extends Audio {
            constructor(...args){super(...args);window.__voiceContexts.push(this)}
            createBuffer(...args){const b=super.createBuffer(...args);window.__voiceBuffers.push(b);return b}
            createBufferSource(){const s=super.createBufferSource();window.__voiceSources.push(s);const stop=s.stop.bind(s);
              s.stop=(...args)=>{window.__voiceStops++;return stop(...args)};return s}
          };
        })()""")
        route_static_files(page)
        mock_price_preview(page)
        mock_telegram_ready(page)
        mock_course_map(page, language=language)
        starts = _mock_voice_environment(page, live=True)
        modes = []
        def mode_request(route):
            body = json.loads(route.request.post_data)
            modes.append(body)
            route.fulfill(json={"ok": True, "mode": body["mode"], "session_id": body["session_id"]})
        page.route("**/api/voice-practice/session/mode", mode_request)
        state = {"socket": None, "auth": None, "pcm": [], "text": [], "ends": 0, "reject": False}
        def relay(socket):
            state["socket"] = socket
            def message(data):
                if isinstance(data, bytes):
                    state["pcm"].append(data)
                    return
                command = json.loads(data)
                if command["type"] == "auth":
                    state["auth"] = command
                    if state["reject"]:
                        socket.send(json.dumps({"type": "error", "code": "live_voice_unavailable"}))
                        return
                    socket.send(json.dumps({"type": "ready", "input_sample_rate": 16000,
                        "output_sample_rate": 24000, "max_dialogs": 0, "max_seconds": 179}))
                elif command["type"] == "text":
                    state["text"].append(command["text"])
                elif command["type"] == "stop":
                    state["ends"] += 1
            socket.on_message(message)
        page.route_web_socket("**/api/voice-practice/live", relay)
        page.goto(static_server + "/course-v3.html?lang=" + language + "&level=hsk1&onboarded=1", wait_until="networkidle")
        page.evaluate("App.openVoiceCall()")
        expect(page.locator("#vc-mic")).to_be_enabled()
        yield page, state, starts, modes, errors
        context.close()
        browser.close()


def start_live(page, state):
    assert page.evaluate("PompLiveVoice.supported()")
    page.locator("#vc-mic").click()
    expect(page.locator("#vc-mic")).to_have_class(re.compile(r"\brec\b"))
    for _ in range(50):
        if len(state["pcm"]) >= 3:
            break
        page.wait_for_timeout(100)
    assert len(state["pcm"]) >= 3, "The real AudioWorklet must send microphone PCM"
    assert all(len(packet) == 640 for packet in state["pcm"])
    assert state["auth"]["initData"] == "query_id=smoke"
    assert state["auth"]["session_id"] == "sess-smoke"
    assert "initData" not in state["socket"].url


def send_turn(state, count):
    state["socket"].send(json.dumps({"type": "turn_complete", "turn_count": count,
        "transcription": "我很好", "chinese_reply": "你今天忙吗？", "pinyin": "nǐ jīntiān máng ma?",
        "translation": "Bugun bandmisiz?", "remaining_limit": 1, "max_dialogs": 0,
        "session_should_end": False, "suggestions": []}))


def assert_microphone_closed(page):
    page.wait_for_function("window.__voiceStreams.length && window.__voiceStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))")
    assert page.evaluate("window.__voiceContexts.at(-1).state") == "closed"


def test_live_streams_real_pcm_plays_audio_interrupts_and_keeps_eight_turns(live_browser):
    page, state, starts, modes, errors = live_browser
    start_live(page, state)
    assert len(starts) == 1
    assert [body["mode"] for body in modes] == ["live"]
    page.evaluate("VOICE.toggleRate()")
    state["socket"].send(json.dumps({"type": "audio", "data": base64.b64encode(b"\x00\x00" * 24000).decode()}))
    page.wait_for_function("window.__voiceBuffers.length > 0")
    assert page.evaluate("window.__voiceBuffers.at(-1).sampleRate") == 24000
    assert page.evaluate("window.__voiceSources.at(-1).playbackRate.value") == pytest.approx(0.85)
    state["socket"].send(json.dumps({"type": "interrupted"}))
    page.wait_for_function("window.__voiceStops > 0")
    for count in range(1, 9):
        send_turn(state, count)
        expect(page.locator("#vc-cnt")).to_contain_text(f"{count + 1}-javob")
    expect(page.locator("#vc-chat .ai .py").last).to_have_text("nǐ jīntiān máng ma?")
    expect(page.locator("#vc-chat .ai .tr").last).to_have_text("Bugun bandmisiz?")
    expect(page.locator("#vc-done")).not_to_have_class(re.compile(r"\bon\b"))
    page.locator("#vc-ctrlRow .sq").first.click()
    page.locator("#vc-kbText").fill("我不忙")
    page.locator("#vc-kbSend").click()
    page.wait_for_timeout(100)
    assert state["text"] == ["我不忙"]
    page.evaluate("VOICE.closeKb()")
    Path("output/playwright").mkdir(parents=True, exist_ok=True)
    page.screenshot(path="output/playwright/miniapp-live.png")
    page.locator("#vc-mic").click()
    expect(page.locator("#vc-done")).to_have_class(re.compile(r"\bon\b"))
    assert_microphone_closed(page)
    assert not errors


def test_live_network_failure_reuses_the_same_session_for_upload_fallback(live_browser):
    page, state, starts, modes, errors = live_browser
    start_live(page, state)
    state["socket"].close(code=1011, reason="test provider unavailable")
    expect(page.locator("#vc-status")).to_contain_text("Live ulanmayapti")
    expect(page.locator("#vc-mic")).to_be_enabled()
    assert [body["mode"] for body in modes] == ["live", "turn"]
    assert len(starts) == 1
    assert all(body["session_id"] == "sess-smoke" for body in modes)
    assert_microphone_closed(page)
    page.locator("#vc-ctrlRow .sq").first.click()
    page.locator("#vc-kbText").fill("我去医院")
    page.locator("#vc-kbSend").click()
    expect(page.locator("#vc-chat .ai .zh").last).to_have_text("很好！")
    assert not errors


@pytest.mark.parametrize("terminal", ["time_limit", "budget_limit"])
def test_live_caps_close_audio_and_do_not_downgrade_to_bypass_limits(live_browser, terminal):
    page, state, starts, modes, errors = live_browser
    start_live(page, state)
    state["socket"].send(json.dumps({"type": terminal}))
    expect(page.locator("#vc-done")).to_have_class(re.compile(r"\bon\b"))
    assert [body["mode"] for body in modes] == ["live"]
    assert_microphone_closed(page)
    assert not errors


def test_live_backgrounding_releases_the_microphone(live_browser):
    page, state, starts, modes, errors = live_browser
    start_live(page, state)
    page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
    expect(page.locator("#vc-done")).to_have_class(re.compile(r"\bon\b"))
    assert_microphone_closed(page)
    assert not errors


@pytest.mark.parametrize("live_browser,expected", [("ru", "Микрофон включён"), ("tj", "Микрофон фаъол")], indirect=["live_browser"])
def test_live_controls_follow_the_learners_language(live_browser, expected):
    page, state, starts, modes, errors = live_browser
    start_live(page, state)
    expect(page.locator("#vc-holdhint")).to_contain_text(expected)
    page.evaluate("VOICE.close()")
    assert_microphone_closed(page)
    assert not errors


def test_denied_microphone_keeps_the_same_session_in_turn_mode(live_browser):
    page, state, starts, modes, errors = live_browser
    page.evaluate("() => { navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('test denied','NotAllowedError')); }")
    page.locator("#vc-mic").click()
    expect(page.locator("#vc-status")).to_contain_text("ruxsat")
    expect(page.locator("#vc-mic")).to_be_enabled()
    assert not state["auth"]
    assert [body["mode"] for body in modes] == ["turn"]
    assert len(starts) == 1
    assert page.evaluate("window.__voiceContexts.at(-1).state") == "closed"
    assert not errors


def test_leaving_during_microphone_permission_does_not_restart_capture(live_browser):
    page, state, starts, modes, errors = live_browser
    page.evaluate("""(() => {
      const getMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia=options=>new Promise(resolve=>{
        window.__resolveVoiceMic=()=>getMedia(options).then(resolve);
      });
    })()""")
    page.locator("#vc-mic").click()
    page.wait_for_function("typeof window.__resolveVoiceMic==='function'")
    page.evaluate("VOICE.close();window.__resolveVoiceMic()")
    assert_microphone_closed(page)
    assert not modes
    assert not state["auth"]
    assert not errors


def test_rejected_live_handshake_falls_back_without_a_new_daily_session(live_browser):
    page, state, starts, modes, errors = live_browser
    state["reject"] = True
    page.locator("#vc-mic").click()
    expect(page.locator("#vc-status")).to_contain_text("Live ulanmayapti")
    assert [body["mode"] for body in modes] == ["live", "turn"]
    assert len(starts) == 1
    assert_microphone_closed(page)
    assert not errors
