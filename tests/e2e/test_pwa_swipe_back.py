"""Edge swipe-back in the learner PWA: one gesture is exactly one step back.

Regression for two owner-reported bugs. A swipe that started at the very left
edge went back two sections, because the in-page drag and the browser's own
history swipe (its popstate) both navigated. The dictionary word page was also
see-through while dragged, so list rows showed through it.

The touch events are synthetic and handed straight to NavBack, so the same
checks run on Chromium and WebKit (PWA_E2E_ENGINE=webkit).
"""
from urllib.parse import urlsplit

from tests.e2e.test_pwa_installed_trial import browser  # noqa: F401  (fixture)
from tests.e2e.test_pwa_learning_parity import STATIC
from tests.e2e.test_pwa_screen_alignment import ScreenPage

SWIPE_JS = """
window.__touch = (x, target) => ({
  touches: [{clientX: x, clientY: 420}], cancelable: true, defaultPrevented: false,
  target: target || document.body, preventDefault() { this.defaultPrevented = true; },
});
window.__swipe = (x0, x1, release = true) => {
  const first = __touch(x0);
  NavBack.start(first);
  for (let i = 1; i <= 8; i++) NavBack.move(__touch(x0 + (x1 - x0) * i / 8));
  if (release) NavBack.end();
  return first.defaultPrevented;
};
"""

STATE_JS = """() => {
  const doc = document.querySelector('#resource-dict iframe').contentDocument;
  return {
    dictionaryOpen: document.getElementById('resourceov').classList.contains('on'),
    detailOpen: !doc.getElementById('view-detail').classList.contains('hidden'),
    listOpen: !doc.getElementById('view-list').classList.contains('hidden'),
    screen: SCREEN,
  };
}"""


class DictionaryPage(ScreenPage):
    def serve(self, route):
        if urlsplit(route.request.url).path == "/iphone-pwa/dictionary":
            route.fulfill(content_type="text/html", path=str(STATIC / "hsk-lugat.html"))
        else:
            super().serve(route)


def open_word(browser):
    page = DictionaryPage("uz").open(browser, 390)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.locator('#nav [data-s="mashq"]').click()
    page.evaluate("RESOURCE.open('dict')")
    frame = page.frame_locator("#resource-dict iframe")
    frame.locator("#list .row").first.wait_for()
    frame.locator("#list").evaluate("el => { el.scrollTop = 88 * 40; }")
    page.wait_for_timeout(150)
    frame.locator("#list").evaluate(
        "el => [...el.querySelectorAll('.row')].find(r => r.getBoundingClientRect().top > 300).click()")
    frame.locator("#view-detail:not(.hidden)").wait_for()
    page.add_script_tag(content=SWIPE_JS)
    assert page.evaluate(STATE_JS) == {
        "dictionaryOpen": True, "detailOpen": True, "listOpen": False, "screen": "mashq"}
    return page, frame, errors


def word_closed(page):
    return {"dictionaryOpen": True, "detailOpen": False, "listOpen": True, "screen": "mashq"} \
        == page.evaluate(STATE_JS)


def test_edge_swipe_with_browser_popstate_first_goes_back_once(browser):
    page, _, errors = open_word(browser)
    claimed = page.evaluate("__swipe(4, 300)")
    assert claimed, "a left-edge touch must stop the browser's own history swipe"
    page.evaluate("history.back()")  # the browser's own swipe lands before the drag settles
    page.wait_for_timeout(450)
    assert word_closed(page), page.evaluate(STATE_JS)
    assert not errors
    page.context.close()


def test_edge_swipe_with_late_browser_popstate_goes_back_once(browser):
    page, _, errors = open_word(browser)
    page.evaluate("__swipe(4, 300)")
    page.wait_for_timeout(300)
    assert word_closed(page), page.evaluate(STATE_JS)
    page.evaluate("history.back()")  # the browser's own swipe lands after the drag settled
    page.wait_for_timeout(300)
    assert word_closed(page), page.evaluate(STATE_JS)
    assert page.evaluate("NavBack._guarded"), "Android back must still have its history guard"
    assert not errors
    page.context.close()


def test_each_edge_swipe_is_one_step_word_list_practice_course(browser):
    page, _, errors = open_word(browser)
    page.evaluate("__swipe(4, 300)")
    page.wait_for_timeout(300)
    assert word_closed(page), page.evaluate(STATE_JS)
    page.evaluate("__swipe(4, 300)")
    page.wait_for_timeout(300)
    state = page.evaluate(STATE_JS)
    assert not state["dictionaryOpen"] and state["screen"] == "mashq", state
    page.evaluate("__swipe(4, 300)")
    page.wait_for_timeout(300)
    assert page.evaluate("SCREEN") == "course"
    assert not errors
    page.context.close()


def test_edge_claim_spares_controls_and_inner_touches(browser):
    page, _, errors = open_word(browser)
    button = "document.querySelector('#resourceov button, #nav button, button')"
    assert not page.evaluate(f"() => {{ const e = __touch(4, {button}); NavBack.start(e); NavBack.cancel(); return e.defaultPrevented; }}")
    assert not page.evaluate("() => { const e = __touch(60); NavBack.start(e); NavBack.cancel(); return e.defaultPrevented; }")
    assert not errors
    page.context.close()


def test_dragged_word_page_is_opaque_and_closes_before_it_snaps_back(browser):
    page, frame, errors = open_word(browser)
    page.evaluate("__swipe(4, 200, false)")
    detail = frame.locator("#view-detail")
    style = detail.evaluate("el => ({cls: el.className, bg: getComputedStyle(el).backgroundColor, "
                            "transform: el.style.transform})")
    assert "nb-drag" in style["cls"] and style["transform"] == "translateX(196px)", style
    assert style["bg"] not in ("transparent", "rgba(0, 0, 0, 0)"), style
    assert not style["bg"].startswith("rgba(") or style["bg"].endswith(", 1)"), style
    # The list under it is revealed at the position the learner left it.
    assert frame.locator("#list").evaluate("el => el.scrollTop") >= 88 * 39
    page.evaluate("""() => {
      const original = NavBack.goBack;
      NavBack.goBack = function () {
        window.__transformAtBack = document.querySelector('#resource-dict iframe')
          .contentDocument.getElementById('view-detail').style.transform;
        return original.apply(this, arguments);
      };
    }""")
    page.evaluate("NavBack.end()")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__transformAtBack") == "translateX(390px)", \
        "the word page must close while still off-screen, not flash back at x=0"
    assert word_closed(page), page.evaluate(STATE_JS)
    assert not errors
    page.context.close()
