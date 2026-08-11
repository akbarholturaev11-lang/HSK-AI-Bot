from pathlib import Path
from playwright.sync_api import sync_playwright, expect


OUT = Path("/Users/kaijimima1234/Desktop/HSK AI bot/output/playwright")
URL = "http://127.0.0.1:8768/?mock=1&goal=hsk"


def click_nav(page, test_id):
    page.locator(f"#{test_id}").click()
    page.wait_for_timeout(250)


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980})
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        expect(page.locator("#workspace")).to_be_visible(timeout=10000)

        checks = [
            ("show-today", ".gridToday", "desktop-today-demo.png"),
            ("show-course", ".courseLayout .coursePathUnit .pathNode", "desktop-course-demo.png"),
            ("show-practice", ".practiceGrid .practiceCard", "desktop-practice-demo.png"),
            ("show-voice", ".voice-v3-root .voice-v3-lead", "desktop-voice-demo.png"),
            ("show-vocabulary", ".vocabLayout .wordRow", "desktop-vocab-demo.png"),
            ("show-rating", ".ratingHero .ratingLeagueCard", "desktop-rating-demo.png"),
            ("show-subscription", ".subWrap .planGrid .plan", "desktop-subscription-demo.png"),
        ]
        for nav, selector, screenshot in checks:
            click_nav(page, nav)
            expect(page.locator(selector).first).to_be_visible(timeout=10000)
            page.screenshot(path=str(OUT / screenshot), full_page=True)

        click_nav(page, "show-vocabulary")
        page.locator(".wordRow").first.click()
        expect(page.locator(".wordDetailGrid .wordHeroDetail")).to_be_visible(timeout=10000)
        page.screenshot(path=str(OUT / "desktop-vocab-detail-demo.png"), full_page=True)

        browser.close()

    serious = [msg for msg in errors if "favicon" not in msg.lower()]
    if serious:
        raise AssertionError("\n".join(serious))
    print("desktop remaining section smoke passed")


if __name__ == "__main__":
    main()
