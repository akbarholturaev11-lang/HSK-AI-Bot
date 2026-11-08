"""Actual browser behavior of the PWA-only first-render shell.

The source of the HTML fragments is read from the code under test. A delayed
map is simulated by leaving the shell in place, then replacing the section.
No production endpoint, cookie, account, network or private cache is involved.
"""
import ast
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


def parts():
    tree = ast.parse(Path("app/api/pwa_auth.py").read_text(encoding="utf-8"))
    required = {
        "_PWA_COURSE_BOOT_HEAD",
        "_PWA_COURSE_SKELETON_NEW",
        "_PWA_COURSE_BOOT_SCRIPT",
    }
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in required:
                    found[name.id] = ast.literal_eval(node.value).decode("utf-8")
    assert set(found) == required
    return found


def test_stalled_bootstrap_shows_retry_without_authorizing_tabs():
    fragments = parts()
    script = fragments["_PWA_COURSE_BOOT_SCRIPT"]
    assert script.count("},14000);") == 1
    script = script.replace("},14000);", "},20);")
    html = (
        '<!doctype html><html class="hsk-pwa-browser"><head>'
        + fragments["_PWA_COURSE_BOOT_HEAD"]
        + '</head><body class="hsk-scene-page hsk-pwa-shell-loading">'
        + fragments["_PWA_COURSE_SKELETON_NEW"]
        + '<nav class="nav" id="nav" inert><button>Course</button></nav>'
        + script + '</body></html>'
    )
    engine = os.environ.get("PWA_E2E_ENGINE", "chromium")
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_content(html)
            page.locator(".hsk-pwa-boot-error").wait_for(timeout=3000)
            assert page.locator(".hsk-pwa-boot-shell").count() == 0
            assert page.get_by_role("button", name="Повторить").is_visible()
            assert page.locator("#nav").get_attribute("inert") == ""
            assert page.locator("#s-course").get_attribute("aria-busy") is None
        finally:
            browser.close()


@pytest.mark.parametrize("reduced_motion", [False, True])
def test_authenticated_shell_visible_without_map_and_settles_independently(reduced_motion):
    fragments = parts()
    html = (
        '<!doctype html><html class="hsk-pwa-browser"><head>'
        + fragments["_PWA_COURSE_BOOT_HEAD"]
        + '</head><body class="hsk-scene-page hsk-pwa-shell-loading">'
        + '<div id="hsk-launch-splash">Full-screen splash</div>'
        + fragments["_PWA_COURSE_SKELETON_NEW"]
        + '<nav class="nav" id="nav" inert><button type="button">Курс</button></nav>'
        + fragments["_PWA_COURSE_BOOT_SCRIPT"]
        + '</body></html>'
    )
    engine = os.environ.get("PWA_E2E_ENGINE", "chromium")
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        try:
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                reduced_motion="reduce" if reduced_motion else "no-preference",
            )
            page = context.new_page()
            page.set_content(html)
            assert page.locator("#hsk-launch-splash").is_hidden()
            assert page.get_by_role("heading", name="HSK AI").is_visible()
            assert page.locator(".hsk-pwa-boot-shell").is_visible()
            assert page.locator(".hsk-pwa-boot-card").count() == 3
            assert page.locator("#s-course").get_attribute("aria-busy") == "true"
            assert page.locator("#nav").get_attribute("inert") == ""
            assert page.locator(".hsk-pwa-boot-shell").bounding_box()["y"] < 844
            if reduced_motion:
                assert page.locator(".hsk-pwa-boot-line").first.evaluate(
                    "(node) => getComputedStyle(node).animationName"
                ) == "none"

            # The canonical private map has now validated the actor and
            # replaced the course section. The shell releases nav/aria state.
            page.locator("#s-course").evaluate(
                "(node) => { node.innerHTML = '<div class=\"actual-course\">Verified map</div>'; }"
            )
            page.wait_for_function(
                "() => !document.querySelector('#nav').hasAttribute('inert')"
            )
            assert page.locator("#s-course").get_attribute("aria-busy") is None
            assert page.locator("body").get_attribute("class") == "hsk-scene-page"
            assert page.get_by_text("Verified map").is_visible()
        finally:
            browser.close()
